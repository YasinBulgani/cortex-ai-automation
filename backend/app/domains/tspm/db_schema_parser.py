"""
db_schema_parser.py
~~~~~~~~~~~~~~~~~~~
DB şema girişlerini (DDL SQL, CSV, doğal dil) WizardTable[] formatına dönüştürür
ve LLM ile zenginleştirme yapar.

Bağımlılıklar:
  - stdlib: re, csv, io, json, logging
  - app.domains.ai.service: call_llm, _parse_json_response
  - Yerel PII/Classification kuralları (cross-package import yok)
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SQL Type → ColType eşleme
# ─────────────────────────────────────────────────────────────────────────────

SQL_TO_COL_TYPE: list[tuple[str, str]] = [
    (r"bool(?:ean)?|tinyint\s*\(1\)",                      "boolean"),
    (r"uuid",                                               "uuid"),
    (r"(?:big)?serial|identity",                            "auto_increment"),
    (r"int(?:eger|2|4|8|64)?|bigint|smallint|tinyint",     "integer"),
    (r"decimal|numeric|float|double(?: precision)?|real|money|number", "decimal"),
    (r"varchar|nvarchar|char|nchar|text|clob|longtext|mediumtext|tinytext|string", "string"),
    (r"timestamp(?:tz)?|datetime",                          "date"),
    (r"date",                                               "date"),
    (r"jsonb?|xml|array|hstore",                            "text"),
]

# Kolonun adından anlamsal tür tespiti için basit kurallar
NAME_TO_COL_TYPE: list[tuple[str, str]] = [
    (r"e?mail",                                             "email"),
    (r"phone|telefon|tel\b|gsm",                           "phone"),
    (r"(?:ad|soyad|isim|name|first.?name|last.?name|full.?name|surname)", "name"),
    (r"first.?name|ad\b",                                  "first_name"),
    (r"last.?name|soyad\b|surname",                        "last_name"),
    (r"address|adres",                                      "address"),
    (r"city|sehir|şehir",                                  "city"),
    (r"company|sirket|şirket|firma",                        "company"),
    (r"iban",                                               "iban"),
    (r"tc.?kimlik|tcno|kimlik.?no",                        "tc_kimlik"),
    (r"uuid|guid",                                          "uuid"),
    (r"tarih|date(?!time)",                                 "date"),
]

# PII sütun adı tespiti
PII_PATTERNS: list[str] = [
    r"e?mail", r"phone|telefon|tel\b|gsm", r"tc.?kimlik|tcno",
    r"iban", r"ad\b|isim|name", r"soyad|surname|last.?name",
    r"address|adres", r"birth|dogum|dob", r"passport|pasaport",
    r"ssn|social.?security", r"kredi.?kart|credit.?card",
]


def _sql_type_to_col_type(sql_type: str) -> str:
    """SQL veri tipini ColType'a dönüştür."""
    sql_lower = sql_type.lower().strip()
    for pattern, col_type in SQL_TO_COL_TYPE:
        if re.search(pattern, sql_lower):
            return col_type
    return "string"


def _name_to_col_type(col_name: str) -> str | None:
    """Kolon adından anlamsal tür çıkar. Bulamazsa None döner."""
    name_lower = col_name.lower()
    for pattern, col_type in NAME_TO_COL_TYPE:
        if re.search(pattern, name_lower):
            return col_type
    return None


def _is_pii(col_name: str) -> bool:
    """Kolon adı PII (kişisel veri) içeriyor mu?"""
    name_lower = col_name.lower()
    return any(re.search(p, name_lower) for p in PII_PATTERNS)


def _assign_ids(tables: list[dict]) -> list[dict]:
    """Tablolara ve kolonlara sıralı id ata (frontend ref için)."""
    tbl_id = 1
    col_id = 1
    result = []
    for t in tables:
        cols = []
        for c in t.get("columns", []):
            cols.append({**c, "id": col_id})
            col_id += 1
        result.append({**t, "id": tbl_id, "columns": cols})
        tbl_id += 1
    return result


# ─────────────────────────────────────────────────────────────────────────────
# DDL Parser — Regex tabanlı (LLM'siz)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ddl_regex(ddl: str) -> dict:
    """
    CREATE TABLE bloklarını regex ile ayrıştırır.
    Döner: { tables: [...], confidence: float, warnings: [...] }
    """
    warnings: list[str] = []
    tables: list[dict] = []
    parsed_cols = 0
    total_cols = 0

    # CREATE TABLE bloklarını bul
    table_pattern = re.compile(
        r"CREATE\s+(?:TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:`?\"?[\w.]+\"?`?\s*\.)?"      # optional schema prefix
        r"`?\"?([\w]+)\"?`?\s*\((.+?)\)\s*;?",
        re.IGNORECASE | re.DOTALL,
    )

    for m in table_pattern.finditer(ddl):
        tbl_name = m.group(1)
        body = m.group(2)
        cols: list[dict] = []
        pk_cols: set[str] = set()
        fk_map: dict[str, str] = {}  # col_name -> "ref_table.ref_col"
        unique_cols: set[str] = set()

        # PRIMARY KEY (col1, col2, ...) constraint
        for pk_m in re.finditer(r"PRIMARY\s+KEY\s*\(([^)]+)\)", body, re.IGNORECASE):
            for c in pk_m.group(1).split(","):
                pk_cols.add(c.strip().strip('"').strip("`"))

        # UNIQUE (col) constraint
        for uq_m in re.finditer(r"UNIQUE\s*\(?([^,)\n]+)\)?", body, re.IGNORECASE):
            uq_cols = uq_m.group(1).split(",")
            for c in uq_cols:
                c = c.strip().strip('"').strip("`").strip("()")
                if c:
                    unique_cols.add(c)

        # FOREIGN KEY ... REFERENCES
        for fk_m in re.finditer(
            r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+`?\"?([\w]+)\"?`?\s*\(([^)]+)\)",
            body, re.IGNORECASE,
        ):
            local_col = fk_m.group(1).strip().strip('"').strip("`")
            ref_table = fk_m.group(2).strip()
            ref_col   = fk_m.group(3).strip().strip('"').strip("`")
            fk_map[local_col] = f"{ref_table}.{ref_col}"

        # Kolon satırlarını ayrıştır
        col_lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
        for line in col_lines:
            # Constraint satırlarını atla
            if re.match(r"(PRIMARY|FOREIGN|UNIQUE|CHECK|INDEX|KEY|CONSTRAINT)\b", line, re.IGNORECASE):
                continue
            # Kolon: adı + tipi
            col_m = re.match(
                r"`?\"?([\w]+)\"?`?\s+([A-Z][A-Z0-9_\s(,)]*?)(?:\s+|$)",
                line, re.IGNORECASE,
            )
            if not col_m:
                continue

            col_name = col_m.group(1)
            sql_type = col_m.group(2).strip().rstrip(",")
            total_cols += 1

            # Tip belirleme
            is_primary = (
                col_name in pk_cols
                or bool(re.search(r"PRIMARY\s+KEY", line, re.IGNORECASE))
                or bool(re.search(r"AUTO_INCREMENT|AUTOINCREMENT|SERIAL|GENERATED\s+ALWAYS", line, re.IGNORECASE))
            )

            if col_name in fk_map:
                col_type = "foreign_key"
            elif is_primary and re.search(r"int|serial|bigint|smallint", sql_type, re.IGNORECASE):
                col_type = "auto_increment"
            elif is_primary and re.search(r"uuid", sql_type, re.IGNORECASE):
                col_type = "uuid"
            else:
                # Önce isme bak, sonra SQL tipine
                col_type = _name_to_col_type(col_name) or _sql_type_to_col_type(sql_type)

            # enum CHECK kısıtı (CHECK (col IN ('a','b')))
            enum_vals: str | None = None
            check_m = re.search(
                rf"{re.escape(col_name)}\s+IN\s*\(([^)]+)\)", line, re.IGNORECASE
            )
            if not check_m:
                check_m = re.search(r"CHECK\s*\([^)]*IN\s*\(([^)]+)\)[^)]*\)", line, re.IGNORECASE)
            if check_m:
                col_type = "enum"
                enum_vals = re.sub(r"['\"`]", "", check_m.group(1))

            # min/max (CHECK col BETWEEN x AND y)
            min_val: str | None = None
            max_val: str | None = None
            between_m = re.search(
                rf"{re.escape(col_name)}\s*(?:>=|>)\s*(\d+(?:\.\d+)?)\s*AND\s*"
                rf"{re.escape(col_name)}\s*(?:<=|<)\s*(\d+(?:\.\d+)?)",
                line, re.IGNORECASE,
            )
            if between_m:
                min_val = between_m.group(1)
                max_val = between_m.group(2)

            col_def: dict[str, Any] = {
                "name": col_name,
                "type": col_type,
                "unique": (col_name in unique_cols) or is_primary,
            }
            if col_name in fk_map:
                col_def["references"] = fk_map[col_name]
            if enum_vals:
                col_def["values"] = enum_vals
            if min_val:
                col_def["min"] = min_val
            if max_val:
                col_def["max"] = max_val

            cols.append(col_def)
            parsed_cols += 1

        if cols:
            tables.append({"name": tbl_name, "rowCount": 10, "columns": cols})
        else:
            warnings.append(f"'{tbl_name}' tablosunda kolon ayrıştırılamadı.")

    confidence = (parsed_cols / max(total_cols, 1)) * (0.5 if not tables else 1.0)
    if not tables:
        confidence = 0.0
        warnings.append("Hiçbir CREATE TABLE bloğu bulunamadı.")

    return {
        "tables": _assign_ids(tables),
        "confidence": round(min(confidence, 1.0), 2),
        "warnings": warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DDL Parser — LLM tabanlı fallback
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_DDL_PARSE = """\
Sen bir kıdemli veritabanı mühendisi ve DDL analistisin.
Verilen SQL DDL kodunu ayrıştırarak yapılandırılmış bir WizardTable[] JSON'una dönüştür.
SADECE geçerli JSON döndür, hiçbir Markdown veya açıklama ekleme.
"""

USER_PROMPT_DDL_PARSE = """\
Aşağıdaki DDL SQL'i WizardTable[] formatına dönüştür:

DDL:
{ddl}

MUTLAKA şu JSON formatında yanıt ver:
{{
  "tables": [
    {{
      "id": 1,
      "name": "tablo_adi",
      "rowCount": 10,
      "columns": [
        {{
          "id": 1,
          "name": "kolon_adi",
          "type": "auto_increment",
          "unique": false,
          "references": null,
          "values": null,
          "min": null,
          "max": null
        }}
      ]
    }}
  ],
  "confidence": 0.95,
  "warnings": []
}}

Kullanılabilir tipler: auto_increment, uuid, string, integer, decimal, boolean, enum,
regex, sequence, foreign_key, name, first_name, last_name, email, phone, address,
city, company, text, sentence, word, date, iban, tc_kimlik

Kurallar:
- INTEGER PRIMARY KEY veya SERIAL → auto_increment
- UUID PRIMARY KEY → uuid
- FOREIGN KEY REFERENCES tbl(col) → type: "foreign_key", references: "tbl.col"
- CHECK (col IN ('a','b')) → type: "enum", values: "a,b"
- email/phone/adres isimli kolonlar → ilgili özel tipe çevir
- Anlaşılamayan durumları warnings'e ekle
"""


def _parse_ddl_llm(ddl: str) -> dict:
    """LLM ile DDL ayrıştır."""
    from app.domains.ai.service import call_llm, _parse_json_response  # type: ignore
    try:
        raw = call_llm(
            SYSTEM_PROMPT_DDL_PARSE,
            USER_PROMPT_DDL_PARSE.format(ddl=ddl[:4000]),
            json_mode=True,
        )
        result = _parse_json_response(raw)
        result.setdefault("tables", [])
        result.setdefault("confidence", 0.85)
        result.setdefault("warnings", [])
        result["tables"] = _assign_ids(result["tables"])
        return result
    except Exception as exc:
        logger.error("DDL LLM parse hatası: %s", exc)
        return {"tables": [], "confidence": 0.0, "warnings": [f"LLM hatası: {exc}"]}


def parse_ddl(ddl: str) -> dict:
    """
    DDL SQL'i WizardTable[]'a dönüştür.
    Önce regex dener; confidence < 0.6 ise LLM fallback.
    """
    result = _parse_ddl_regex(ddl)
    if result["confidence"] < 0.6:
        result["warnings"].append("Regex ayrıştırma yetersiz, AI kullanılıyor…")
        llm_result = _parse_ddl_llm(ddl)
        if llm_result["tables"]:
            llm_result["warnings"] = result["warnings"] + llm_result["warnings"]
            return llm_result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CSV Parser
# ─────────────────────────────────────────────────────────────────────────────

def _classify_csv_column(col_name: str, samples: list[str]) -> dict:
    """
    Kolon adı ve örnek değerlerden ColType tahmin et.
    Döner: { type, unique, pii, confidence }
    """
    # 1. Kolona göre anlam tahmini
    name_type = _name_to_col_type(col_name)
    if name_type:
        return {"type": name_type, "unique": False, "pii": _is_pii(col_name), "confidence": 0.85}

    # 2. Örnek değerlerden tip tahmini
    non_empty = [s for s in samples if s.strip()]
    if not non_empty:
        return {"type": "string", "unique": False, "pii": False, "confidence": 0.3}

    # UUID kontrolü
    uuid_pat = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    if all(uuid_pat.match(v) for v in non_empty[:5]):
        return {"type": "uuid", "unique": True, "pii": False, "confidence": 0.95}

    # Tam sayı kontrolü
    if all(re.match(r"^-?\d+$", v) for v in non_empty[:5]):
        vals = [int(v) for v in non_empty[:5]]
        if vals == list(range(vals[0], vals[0] + len(vals))):
            return {"type": "auto_increment", "unique": True, "pii": False, "confidence": 0.9}
        return {"type": "integer", "unique": False, "pii": False, "confidence": 0.85}

    # Ondalık kontrolü
    if all(re.match(r"^-?\d+\.\d+$", v) for v in non_empty[:5]):
        return {"type": "decimal", "unique": False, "pii": False, "confidence": 0.85}

    # Boolean kontrolü
    bool_vals = {"true", "false", "1", "0", "yes", "no", "evet", "hayır", "t", "f"}
    if all(v.lower() in bool_vals for v in non_empty[:5]):
        return {"type": "boolean", "unique": False, "pii": False, "confidence": 0.9}

    # Email kontrolü
    if any("@" in v and "." in v.split("@")[-1] for v in non_empty[:3]):
        return {"type": "email", "unique": True, "pii": True, "confidence": 0.95}

    # Tarih kontrolü
    date_pat = re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}")
    if all(date_pat.search(v) for v in non_empty[:3]):
        return {"type": "date", "unique": False, "pii": False, "confidence": 0.88}

    # Düşük kardinalite → enum
    unique_vals = list(set(non_empty))
    if len(unique_vals) <= 8 and len(non_empty) >= 3:
        return {
            "type": "enum",
            "unique": False,
            "pii": False,
            "confidence": 0.8,
            "values": ",".join(unique_vals),
        }

    return {"type": "string", "unique": False, "pii": _is_pii(col_name), "confidence": 0.5}


def parse_csv(csv_text: str, table_name: str = "imported_table", has_header: bool = True) -> dict:
    """
    CSV metnini WizardTable[]'a dönüştür.
    """
    warnings: list[str] = []
    try:
        reader = csv.reader(io.StringIO(csv_text.strip()))
        rows = list(reader)
    except Exception as exc:
        return {"tables": [], "confidence": 0.0, "warnings": [f"CSV parse hatası: {exc}"]}

    if not rows:
        return {"tables": [], "confidence": 0.0, "warnings": ["CSV boş."]}

    if has_header:
        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:21]  # max 20 örnek satır
    else:
        headers = [f"col_{i+1}" for i in range(len(rows[0]))]
        data_rows = rows[:20]

    if not headers:
        return {"tables": [], "confidence": 0.0, "warnings": ["Başlık satırı bulunamadı."]}

    columns: list[dict] = []
    confidences: list[float] = []
    for i, h in enumerate(headers):
        if not h:
            warnings.append(f"Kolon {i+1} başlığı boş, 'col_{i+1}' olarak atandı.")
            h = f"col_{i+1}"
        samples = [r[i] for r in data_rows if i < len(r)]
        info = _classify_csv_column(h, samples)
        col: dict[str, Any] = {
            "name": h,
            "type": info["type"],
            "unique": info.get("unique", False),
        }
        if "values" in info:
            col["values"] = info["values"]
        columns.append(col)
        confidences.append(info["confidence"])

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

    table = {"name": table_name, "rowCount": 10, "columns": columns}
    return {
        "tables": _assign_ids([table]),
        "confidence": round(avg_confidence, 2),
        "warnings": warnings,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Doğal Dil Parser — LLM
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_NL_SCHEMA = """\
Sen bir veritabanı tasarımcısı ve test veri mühendisisin.
Türkçe veya İngilizce doğal dil açıklamalarından ilişkisel veritabanı şemaları tasarlarsın.
SADECE geçerli JSON döndür, hiçbir Markdown veya açıklama ekleme.
"""

USER_PROMPT_NL_SCHEMA = """\
Aşağıdaki açıklamadan bir WizardTable[] şeması tasarla:

{description}

MUTLAKA şu JSON formatında yanıt ver:
{{
  "tables": [
    {{
      "id": 1,
      "name": "tablo_adi",
      "rowCount": 50,
      "columns": [
        {{
          "id": 1,
          "name": "kolon_adi",
          "type": "auto_increment",
          "unique": false,
          "references": null,
          "values": null,
          "min": null,
          "max": null
        }}
      ]
    }}
  ],
  "confidence": 0.85,
  "warnings": []
}}

Kullanılabilir tipler: auto_increment, uuid, string, integer, decimal, boolean, enum,
regex, sequence, foreign_key, name, first_name, last_name, email, phone, address,
city, company, text, sentence, word, date, iban, tc_kimlik

Tasarım kuralları:
- Her tablo id kolonuyla (auto_increment) başlasın
- Tablolar arası ilişkileri foreign_key ve references alanıyla kur
- Durum/statü/tip kolonları → enum, values alanına olası değerleri virgülle yaz
- Fiyat/tutar → decimal, min/max öner
- Kişisel veri kolonları uygun tipe çekilsin (email, phone, tc_kimlik vb.)
- Ana tablolar rowCount:50, detay tablolar rowCount:200 olsun
- Açıklamada belirtilmeyen ama beklenen kolonları da ekle (created_at gibi)
"""


def parse_natural_language(description: str) -> dict:
    """Doğal dil açıklamasından WizardTable[] üret."""
    from app.domains.ai.service import call_llm, _parse_json_response  # type: ignore
    try:
        raw = call_llm(
            SYSTEM_PROMPT_NL_SCHEMA,
            USER_PROMPT_NL_SCHEMA.format(description=description[:3000]),
            json_mode=True,
        )
        result = _parse_json_response(raw)
        result.setdefault("tables", [])
        result.setdefault("confidence", 0.8)
        result.setdefault("warnings", [])
        result["tables"] = _assign_ids(result["tables"])
        return result
    except Exception as exc:
        logger.error("NL parse hatası: %s", exc)
        raise ValueError(f"AI servisi hatası: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# AI Zenginleştirme
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_ENRICH = """\
Sen bir kıdemli veri mühendisi ve test veri uzmanısın.
Verilen WizardTable[] şemasını analiz ederek her kolona iş kuralları ekle,
PII verilerini işaretle ve veri kalitesi önerileri sun.
SADECE geçerli JSON döndür, hiçbir Markdown veya açıklama ekleme.
"""

USER_PROMPT_ENRICH = """\
Aşağıdaki WizardTable şemasını zenginleştir:

Şema:
{schema_json}

Domain ipucu: {domain_hint}

MUTLAKA şu JSON formatında yanıt ver:
{{
  "tables": [...],
  "pii_columns": ["tablo.kolon", ...],
  "suggested_rules": {{
    "tablo.kolon": "Kural açıklaması"
  }},
  "quality_hints": [
    "Kalite önerisi"
  ]
}}

Kurallar:
- Mevcut tipleri koru, sadece eksik min/max/values/pattern alanlarını tamamla
- Her sayısal kolona gerçekçi aralık (min, max) ekle
- Her enum kolonun values alanını doldur
- PII kolonları tespit et: email, phone, tc_kimlik, iban, adres, ad/soyad
- Gereksiz rowCount değerlerini güncelle (ana tablo: 50, çocuk tablo: 200)
- Kalite önerileri kısa ve uygulanabilir olsun (max 5 ipucu)
"""


def enrich_schema(tables: list[dict], domain_hint: str = "") -> dict:
    """
    2-pass zenginleştirme:
    1. Regex/kural tabanlı PII tespiti (hızlı, LLM'siz)
    2. LLM ile iş kuralları ve kalite önerileri
    """
    # Pass 1: Kural tabanlı PII tespiti
    pii_columns: list[str] = []
    for tbl in tables:
        for col in tbl.get("columns", []):
            if _is_pii(col.get("name", "")):
                pii_columns.append(f"{tbl['name']}.{col['name']}")

    # Pass 2: LLM zenginleştirme
    from app.domains.ai.service import call_llm, _parse_json_response  # type: ignore
    try:
        schema_json = json.dumps(tables, ensure_ascii=False, indent=2)[:5000]
        raw = call_llm(
            SYSTEM_PROMPT_ENRICH,
            USER_PROMPT_ENRICH.format(
                schema_json=schema_json,
                domain_hint=domain_hint or "genel",
            ),
            json_mode=True,
        )
        result = _parse_json_response(raw)
        result.setdefault("tables", tables)
        # PII listelerini birleştir (LLM + kural)
        llm_pii = result.get("pii_columns", [])
        combined_pii = list(set(pii_columns + llm_pii))
        result["pii_columns"] = combined_pii
        result.setdefault("suggested_rules", {})
        result.setdefault("quality_hints", [])
        result["tables"] = _assign_ids(result["tables"])
        return result
    except Exception as exc:
        logger.error("Zenginleştirme hatası: %s", exc)
        # LLM başarısız olsa da kural tabanlı PII bilgisini döndür
        return {
            "tables": _assign_ids(tables),
            "pii_columns": pii_columns,
            "suggested_rules": {},
            "quality_hints": [f"AI zenginleştirme başarısız: {exc}"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Simülasyon sonrası kalite kontrolü
# ─────────────────────────────────────────────────────────────────────────────

def run_quality_check(sim_result: dict, tables_def: list[dict]) -> dict:
    """
    Üretilmiş veri üzerinde kalite ve FK bütünlük kontrolü.
    Döner: { quality_score, quality_report }
    """
    tables = sim_result.get("tables", {})
    fk_violations = 0
    null_total = 0
    cell_total = 0
    unique_violations = 0
    warnings: list[str] = []

    for tbl_def in tables_def:
        tbl_name = tbl_def.get("name", "")
        tbl_data = tables.get(tbl_name, {})
        if not tbl_data:
            continue

        columns: list[str] = tbl_data.get("columns", [])
        rows: list[list[str]] = tbl_data.get("rows", [])

        col_idx = {c: i for i, c in enumerate(columns)}
        col_values: dict[str, list[str]] = {c: [r[i] for r in rows if i < len(r)]
                                             for i, c in enumerate(columns)}

        for col_def in tbl_def.get("columns", []):
            col_name = col_def.get("name", "")
            col_type = col_def.get("type", "")
            idx = col_idx.get(col_name)
            if idx is None:
                continue

            vals = col_values.get(col_name, [])
            cell_total += len(vals)

            # Null/boş değer sayısı
            nulls = sum(1 for v in vals if not str(v).strip())
            null_total += nulls

            # FK bütünlük kontrolü
            if col_type == "foreign_key" and col_def.get("references"):
                ref = col_def["references"]
                parts = ref.split(".")
                if len(parts) == 2:
                    ref_tbl, ref_col = parts
                    ref_data = tables.get(ref_tbl, {})
                    ref_cols = ref_data.get("columns", [])
                    ref_rows = ref_data.get("rows", [])
                    if ref_col in ref_cols:
                        ref_idx = ref_cols.index(ref_col)
                        valid_vals = {r[ref_idx] for r in ref_rows if ref_idx < len(r)}
                        violations = sum(1 for v in vals if v not in valid_vals)
                        fk_violations += violations
                        if violations:
                            warnings.append(
                                f"{tbl_name}.{col_name}: {violations} FK ihlali ({ref} referansı)"
                            )

            # Unique ihlal kontrolü
            if col_def.get("unique"):
                dups = len(vals) - len(set(vals))
                unique_violations += dups
                if dups:
                    warnings.append(f"{tbl_name}.{col_name}: {dups} tekrar değer (unique ihlali)")

    null_rate = null_total / max(cell_total, 1)
    total_rows = sum(t.get("row_count", 0) for t in tables.values())
    fk_penalty = min(fk_violations / max(total_rows, 1), 1.0) * 0.4
    null_penalty = null_rate * 0.3
    uniq_penalty = min(unique_violations / max(total_rows, 1), 1.0) * 0.3
    quality_score = round(max(0.0, 1.0 - fk_penalty - null_penalty - uniq_penalty), 2)

    return {
        "quality_score": quality_score,
        "quality_report": {
            "fk_integrity": fk_violations == 0,
            "null_rate": round(null_rate, 3),
            "unique_violations": unique_violations,
            "warnings": warnings,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Canlı DB Bağlantısı — SQLAlchemy Inspector
# ─────────────────────────────────────────────────────────────────────────────

# PostgreSQL iç type → ColType eşlemesi
PG_TYPE_MAP: dict[str, str] = {
    "integer": "integer", "bigint": "integer", "smallint": "integer",
    "serial": "auto_increment", "bigserial": "auto_increment",
    "numeric": "decimal", "decimal": "decimal", "real": "decimal",
    "double precision": "decimal", "money": "decimal",
    "character varying": "string", "varchar": "string",
    "character": "string", "char": "string", "text": "string",
    "boolean": "boolean",
    "uuid": "uuid",
    "date": "date", "timestamp": "date", "timestamp without time zone": "date",
    "timestamp with time zone": "date", "time": "date",
    "json": "text", "jsonb": "text", "xml": "text", "array": "text",
    "bytea": "string",
}


def _pg_type_to_col_type(pg_type: str) -> str:
    return PG_TYPE_MAP.get(pg_type.lower(), _sql_type_to_col_type(pg_type))


def parse_db_connection(
    connection_string: str,
    schema_name: str = "public",
    exclude_tables: list[str] | None = None,
) -> dict:
    """
    Canlı veritabanına bağlan, şemayı introspect et, WizardTable[]'a dönüştür.

    connection_string örnekleri:
      postgresql://twai_user@localhost:5432/syndata_db
      postgresql://user:pass@host:5432/dbname
      sqlite:///path/to/file.db
    """
    try:
        from sqlalchemy import create_engine, inspect as sa_inspect, text
    except ImportError:
        raise ValueError("sqlalchemy paketi yüklü değil.")

    _excluded = set(exclude_tables or [])
    warnings: list[str] = []
    tables_out: list[dict] = []

    try:
        engine = create_engine(connection_string, connect_args={"connect_timeout": 10})
        inspector = sa_inspect(engine)
    except Exception as exc:
        raise ValueError(f"Veritabanına bağlanılamadı: {exc}")

    # SQLite için schema parametresi yok; PostgreSQL için her zaman explicit geçir
    is_sqlite  = connection_string.startswith("sqlite")
    pg_schema  = None if is_sqlite else (schema_name or "public")

    try:
        table_names = inspector.get_table_names(schema=pg_schema)
    except Exception as exc:
        raise ValueError(f"Tablo listesi alınamadı: {exc}")

    all_table_names = list(table_names)  # hepsini sakla (debug için)

    excluded_count = sum(1 for t in all_table_names if t in _excluded)
    if excluded_count and excluded_count == len(all_table_names):
        warnings.append(
            f"Tüm {excluded_count} tablo 'Hariç Tutulacak Tablolar' listesinde — "
            "listeyi temizleyip tekrar deneyin."
        )
        return {"tables": [], "confidence": 1.0, "warnings": warnings}

    for tbl_name in all_table_names:
        if tbl_name in _excluded:
            continue

        try:
            raw_cols   = inspector.get_columns(tbl_name, schema=pg_schema)
            pk_info    = inspector.get_pk_constraint(tbl_name, schema=pg_schema)
            fk_list    = inspector.get_foreign_keys(tbl_name, schema=pg_schema)
            uq_list    = inspector.get_unique_constraints(tbl_name, schema=pg_schema)
        except Exception as exc:
            warnings.append(f"{tbl_name}: kolon bilgisi alınamadı ({exc})")
            continue

        pk_cols = set(pk_info.get("constrained_columns", []))
        unique_cols: set[str] = set()
        for uq in uq_list:
            for c in uq.get("column_names", []):
                unique_cols.add(c)

        # FK haritası: col_name → "ref_table.ref_col"
        fk_map: dict[str, str] = {}
        for fk in fk_list:
            local_cols   = fk.get("constrained_columns", [])
            ref_table    = fk.get("referred_table", "")
            ref_cols     = fk.get("referred_columns", [])
            for lc, rc in zip(local_cols, ref_cols):
                fk_map[lc] = f"{ref_table}.{rc}"

        columns: list[dict] = []
        for rc in raw_cols:
            col_name = rc["name"]
            # SQLAlchemy type → string
            try:
                sql_type_str = str(rc["type"]).lower()
            except Exception:
                sql_type_str = "varchar"

            # Tip belirleme önceliği: PK serial → FK → isim tahmini → sql tip
            is_pk   = col_name in pk_cols
            is_fk   = col_name in fk_map
            is_serial = "int" in sql_type_str and is_pk and len(pk_cols) == 1

            if is_serial:
                col_type = "auto_increment"
            elif sql_type_str in ("uuid",) and is_pk:
                col_type = "uuid"
            elif is_fk:
                col_type = "foreign_key"
            else:
                # İsim tahmini önce
                name_type = _name_to_col_type(col_name)
                col_type  = name_type if name_type else _pg_type_to_col_type(sql_type_str)

            col: dict[str, Any] = {
                "name": col_name,
                "type": col_type,
                "unique": (col_name in unique_cols or is_pk),
            }
            if is_fk:
                col["references"] = fk_map[col_name]
            # Enum ipucu: CHECK kısıtlarına ulaşamıyoruz kolayca,
            # ama kullanıcı AI zenginleştirme ile tamamlayabilir

            columns.append(col)

        tables_out.append({
            "name": tbl_name,
            "rowCount": 50,
            "columns": columns,
        })

    if not tables_out:
        if all_table_names:
            warnings.append(
                f"Tüm tablolar ({len(all_table_names)} adet) hariç tutuldu. "
                "'Hariç Tutulacak Tablolar' alanını temizleyip tekrar deneyin."
            )
        else:
            warnings.append(
                f"'{pg_schema}' şemasında hiç tablo bulunamadı. "
                "Şema adını ve bağlantı dizesini kontrol edin."
            )

    # Platform sistem tablolarını filtrele (isteğe bağlı uyarı)
    platform_tbls = [t["name"] for t in tables_out
                     if t["name"].startswith(("tspm_", "sd_", "alembic_"))]
    if platform_tbls:
        warnings.append(
            f"TestwrightAI sistem tabloları da listede: {', '.join(platform_tbls[:5])}… "
            "Simüle etmek istemiyorsanız dışarıda bırakın."
        )

    return {
        "tables": _assign_ids(tables_out),
        "confidence": 1.0,
        "warnings": warnings,
    }
