"""
Banking routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/banking_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/banking.py — APIRouter, port 8000 (consolidated)

Bu pattern her route file için takip edilir. Bir Python developer kopyala-yapıştır + dönüştür yapar.
"""

from __future__ import annotations

import csv
import io
import json
import os
import random
import sqlite3 as _sqlite3
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/banking", tags=["engine", "banking"])

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

# ── Lazy import (banking paketi yüklü değilse graceful degradation) ──────────
try:
    from core.banking.generators.identity    import generate_tc_kimlik, validate_tc_kimlik, generate_vkn, validate_vkn, generate_tc_kimlik_batch
    from core.banking.generators.account     import generate_tr_iban, validate_tr_iban, generate_swift, get_bank_list, TR_BANK_CODES
    from core.banking.generators.card        import generate_card_number, luhn_check, generate_cvv, generate_card_expiry, mask_card_number
    from core.banking.generators.transaction import generate_eft_reference, generate_fast_reference, generate_doviz_kuru, generate_transaction_date, generate_cek_numarasi, generate_aciklama, generate_merchant, DOVIZ_KURLAR
    from core.banking.generators.credit      import generate_faiz_orani, generate_kredi_limiti, generate_risk_skoru, classify_segment, generate_aylik_gelir, SEGMENT_KURALLAR, FAIZ_SPREAD, TCMB_POLITIKA_FAIZ
    from core.banking.factories.banking_factories import generate_banking_data, generate_relational_dataset, FACTORY_MAP
    BANKING_AVAILABLE = True
    _IMPORT_ERROR = ""
except ImportError as e:
    BANKING_AVAILABLE = False
    _IMPORT_ERROR = str(e)


def _check_banking() -> None:
    """Banking modülü kullanılamıyorsa 503 fırlatır."""
    if not BANKING_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Banking modülü yüklenemedi: {_IMPORT_ERROR}",
        )


_PROJECT_DB_ROOT = os.path.join(_PROJECT_ROOT, "engine", "data")
_DEMO_DB_PATH = os.path.join(_PROJECT_DB_ROOT, "demo_banking.sqlite")

# Oturum bazlı DB bağlantı cache (basit in-memory)
_db_connections: dict = {}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class TcKimlikRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)
    seed: Optional[int] = None
    mode: str = Field(default="generate", pattern="^(generate|validate)$")
    tc: Optional[str] = None


class VknRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)
    seed: Optional[int] = None
    mode: str = Field(default="generate", pattern="^(generate|validate)$")
    vkn: Optional[str] = None


class IbanRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)
    bank_code: Optional[str] = None
    seed: Optional[int] = None
    mode: str = Field(default="generate", pattern="^(generate|validate)$")
    iban: Optional[str] = None


class CardRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)
    card_type: str = Field(default="troy")
    masked: bool = False
    seed: Optional[int] = None


class TransactionRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=5000)
    islem_turu: Optional[str] = None
    seed: Optional[int] = None


class CreditRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=1000)
    kredi_turu: str = "ihtiyac_kredisi"
    seed: Optional[int] = None


class GenerateRequest(BaseModel):
    entity_type: str = "musteri"
    count: int = Field(default=10, ge=1, le=1000)
    seed: Optional[int] = None


class MultiTableRequest(BaseModel):
    musteri_count: int = Field(default=3, ge=1, le=200)
    hesap_per_musteri: int = Field(default=2, ge=1, le=10)
    islem_per_hesap: int = Field(default=5, ge=1, le=50)
    kredi_per_musteri: int = Field(default=1, ge=1, le=5)
    seed: Optional[int] = None


class ValidateRequest(BaseModel):
    value: str = ""
    type: str = "auto"


class EdgeCasesRequest(BaseModel):
    scenarios: list[str] = ["all"]


class ExportRequest(BaseModel):
    entity_type: str = "musteri"
    count: int = Field(default=100, ge=1, le=5000)
    format: str = Field(default="json", pattern="^(json|csv)$")
    seed: Optional[int] = None


class DbConnectRequest(BaseModel):
    db_type: str = "demo"
    conn_str: str = ""
    label: str = ""


class DbAnalyzeRequest(BaseModel):
    schema_ddl: str
    schema_dict: dict = {}


class DbAiGenerateRequest(BaseModel):
    schema_dict: dict
    schema_ddl: str = ""
    counts: dict = {}
    extra_rules: str = ""
    analysis: Optional[dict] = None
    seed: Optional[int] = None
    model: Optional[str] = None


class DbInsertRequest(BaseModel):
    db_type: str = "demo"
    conn_str: str = ""
    dataset: dict
    table_order: Optional[list[str]] = None
    truncate_first: bool = False


class DbQueryRequest(BaseModel):
    db_type: str = "demo"
    conn_str: str = ""
    sql: str
    limit: int = Field(default=50, ge=1, le=500)


# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def _serialize(v: Any) -> Any:
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _serialize_rows(rows: list[dict]) -> list[dict]:
    return [{k: (_serialize(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
             for k, v in row.items()}
            for row in rows]


def _get_schema_reader(db_type: str, conn_str: str):
    from banking.db_schema_reader import SchemaReader
    return SchemaReader(db_type=db_type, conn_str=conn_str)


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/info")
def banking_info():
    """Bankacılık modülü bilgisi ve endpoint listesi."""
    return {
        "ok": True,
        "module": "Neurex Banking DataSim",
        "version": "1.0.0",
        "bddk_compliant": True,
        "kvkk_compliant": True,
        "ai_used": False,
        "available": BANKING_AVAILABLE,
        "endpoints": {
            "GET  /api/banking/info":               "Bu endpoint",
            "GET  /api/banking/banks":              "Türk banka listesi",
            "POST /api/banking/tc-kimlik":          "TC Kimlik No üretimi",
            "POST /api/banking/vkn":                "VKN üretimi",
            "POST /api/banking/iban":               "TR IBAN üretimi",
            "POST /api/banking/card":               "Luhn kart no üretimi",
            "POST /api/banking/transaction":        "İşlem verisi üretimi",
            "POST /api/banking/credit":             "Kredi verisi üretimi",
            "POST /api/banking/generate":           "Genel bankacılık verisi (tip seç)",
            "POST /api/banking/multi-table":        "İlişkisel çok tablo üretimi",
            "POST /api/banking/validate":           "Veri doğrulama (TC/VKN/IBAN/Luhn)",
            "POST /api/banking/edge-cases":         "Edge case senaryoları",
            "POST /api/banking/export":             "CSV/JSON export",
        },
        "supported_types": list(FACTORY_MAP.keys()) if BANKING_AVAILABLE else [],
    }


@router.get("/banks")
def get_banks():
    """Türk banka kodu, adı ve SWIFT listesi."""
    _check_banking()
    bank_list = get_bank_list()
    return {"ok": True, "banks": bank_list, "count": len(bank_list)}


# ── Kimlik ────────────────────────────────────────────────────────────────────

@router.post("/tc-kimlik")
def tc_kimlik_endpoint(body: TcKimlikRequest):
    """TC Kimlik No üretimi ve doğrulama."""
    _check_banking()
    if body.mode == "validate":
        tc = body.tc or ""
        valid = validate_tc_kimlik(str(tc))
        return {
            "ok": True, "tc": tc, "valid": valid,
            "reason": "Geçerli" if valid else "Algoritma doğrulaması başarısız",
        }
    batch = generate_tc_kimlik_batch(body.count, seed=body.seed)
    return {
        "ok": True, "count": len(batch), "data": batch,
        "algorithm": "Mod-10 (11 hane)",
        "bddk_note": "Algoritmik üretim - gerçek kimlik değil",
    }


@router.post("/vkn")
def vkn_endpoint(body: VknRequest):
    """VKN üretimi ve doğrulama."""
    _check_banking()
    if body.mode == "validate":
        vkn = body.vkn or ""
        valid = validate_vkn(str(vkn))
        return {"ok": True, "vkn": vkn, "valid": valid}
    if body.seed is not None:
        random.seed(body.seed)
    batch = [generate_vkn() for _ in range(body.count)]
    return {"ok": True, "count": len(batch), "data": batch, "algorithm": "10 hane - yerleşik checksum"}


# ── Hesap ─────────────────────────────────────────────────────────────────────

@router.post("/iban")
def iban_endpoint(body: IbanRequest):
    """TR IBAN üretimi ve doğrulama."""
    _check_banking()
    if body.mode == "validate":
        iban = body.iban or ""
        valid = validate_tr_iban(str(iban))
        return {"ok": True, "iban": iban, "valid": valid, "standard": "ISO 13616 MOD-97-10"}
    if body.seed is not None:
        random.seed(body.seed)
    ibans = [generate_tr_iban(body.bank_code) for _ in range(body.count)]
    swift = generate_swift(body.bank_code)
    return {
        "ok": True, "count": len(ibans), "data": ibans,
        "bank_code": body.bank_code or "random",
        "bank_name": TR_BANK_CODES.get(body.bank_code, "Rastgele") if body.bank_code else "Rastgele",
        "swift": swift,
        "standard": "ISO 13616, TR format: TR + 2 check + 5 banka + 1 rezerv + 16 hesap = 26",
    }


# ── Kart ──────────────────────────────────────────────────────────────────────

@router.post("/card")
def card_endpoint(body: CardRequest):
    """Luhn geçerli kart numarası üretimi."""
    _check_banking()
    if body.seed is not None:
        random.seed(body.seed)
    cards = []
    for _ in range(body.count):
        no = generate_card_number(body.card_type)
        cvv = generate_cvv(body.card_type)
        exp = generate_card_expiry()
        cards.append({
            "number": mask_card_number(no) if body.masked else no,
            "cvv": cvv,
            "expiry": exp,
            "type": body.card_type,
            "valid": luhn_check(no),
        })
    return {
        "ok": True, "count": len(cards), "data": cards,
        "algorithm": "Luhn (ISO/IEC 7812)",
        "prefix_info": {"troy": "9792xx", "visa": "4xxxxx", "mastercard": "51-55xxxx"},
    }


# ── İşlem ─────────────────────────────────────────────────────────────────────

@router.post("/transaction")
def transaction_endpoint(body: TransactionRequest):
    """Bankacılık işlem verisi üretimi."""
    _check_banking()
    turu_list = ["EFT", "Havale", "FAST", "POS", "ATM", "Faiz", "Masraf"]
    if body.seed is not None:
        random.seed(body.seed)
    islemler = []
    for _ in range(body.count):
        turu = body.islem_turu or random.choice(turu_list)
        islemler.append({
            "referans_no": generate_eft_reference(),
            "islem_turu":  turu,
            "tutar":       round(random.uniform(1, 50000), 2),
            "para_birimi": random.choice(["TRY", "TRY", "TRY", "USD", "EUR"]),
            "aciklama":    generate_aciklama(turu),
            "tarih":       generate_transaction_date(),
            "durum":       random.choice(["Tamamlandı", "Tamamlandı", "Tamamlandı", "Beklemede", "İptal"]),
            "isyeri":      generate_merchant() if turu == "POS" else None,
        })
    return {"ok": True, "count": len(islemler), "data": islemler}


# ── Kredi ─────────────────────────────────────────────────────────────────────

@router.post("/credit")
def credit_endpoint(body: CreditRequest):
    """Kredi verisi üretimi."""
    _check_banking()
    if body.seed is not None:
        random.seed(body.seed)
    krediler = []
    for i in range(body.count):
        gelir = round(random.uniform(5000, 80000), 2)
        segment = classify_segment(gelir)
        risk = generate_risk_skoru(segment)
        yas = random.randint(22, 65)
        limit = generate_kredi_limiti(gelir, segment, yas, risk)
        faiz = generate_faiz_orani(body.kredi_turu)
        vade = random.randint(6, 120)
        krediler.append({
            "kredi_no":           f"KRD{i+1:010d}",
            "kredi_turu":         body.kredi_turu,
            "anapara":            round(random.uniform(limit * 0.1, limit), 2),
            "faiz_orani":         faiz,
            "vade_ay":            vade,
            "aylik_taksit":       round((limit * (faiz / 100 / 12)) / (1 - (1 + faiz / 100 / 12) ** (-vade)), 2),
            "musteri_gelir":      gelir,
            "musteri_segment":    segment,
            "risk_skoru":         risk,
            "tcmb_politika_faiz": TCMB_POLITIKA_FAIZ,
            "durum":              random.choice(["Aktif", "Aktif", "Aktif", "Kapalı", "Gecikme"]),
        })
    return {"ok": True, "count": len(krediler), "data": krediler}


# ── Genel üretim ──────────────────────────────────────────────────────────────

@router.post("/generate")
def banking_generate(body: GenerateRequest):
    """Genel bankacılık veri üretimi (tip parametreli)."""
    _check_banking()
    if body.entity_type not in FACTORY_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"ok": False, "error": f"Geçersiz entity_type: '{body.entity_type}'",
                    "valid_types": list(FACTORY_MAP.keys())},
        )
    rows = generate_banking_data(body.entity_type, body.count, body.seed)
    serialized = _serialize_rows(rows)
    return {
        "ok": True,
        "entity_type": body.entity_type,
        "count": len(serialized),
        "columns": list(serialized[0].keys()) if serialized else [],
        "data": serialized,
        "bddk_compliant": True,
    }


# ── İlişkisel çok tablo ───────────────────────────────────────────────────────

@router.post("/multi-table")
def multi_table(body: MultiTableRequest):
    """FK bütünlüklü ilişkisel bankacılık veri seti üretimi."""
    _check_banking()
    dataset = generate_relational_dataset(
        musteri_count=body.musteri_count,
        hesap_per_musteri=body.hesap_per_musteri,
        islem_per_hesap=body.islem_per_hesap,
        kredi_per_musteri=body.kredi_per_musteri,
        seed=body.seed,
    )

    def serialize_dataset(ds: dict) -> dict:
        result = {}
        for key, rows in ds.items():
            if key == "meta":
                result[key] = rows
                continue
            result[key] = [{k: (v.isoformat() if hasattr(v, "isoformat") else v)
                            for k, v in row.items()}
                           for row in rows]
        return result

    return {
        "ok": True,
        "meta": dataset["meta"],
        "dataset": serialize_dataset(dataset),
        "fk_integrity": True,
        "bddk_compliant": True,
    }


# ── Doğrulama ─────────────────────────────────────────────────────────────────

@router.post("/validate")
def validate_endpoint(body: ValidateRequest):
    """TC Kimlik, VKN, IBAN, Kart No doğrulama."""
    _check_banking()
    value = str(body.value)
    data_type = body.type
    results: dict = {}

    if data_type in ("auto", "tc_kimlik"):
        results["tc_kimlik"] = {"valid": validate_tc_kimlik(value), "algorithm": "Mod-10 (11 hane)"}
    if data_type in ("auto", "vkn"):
        results["vkn"] = {"valid": validate_vkn(value), "algorithm": "Checksum (10 hane)"}
    if data_type in ("auto", "iban"):
        results["iban"] = {"valid": validate_tr_iban(value), "standard": "ISO 13616 MOD-97-10"}
    if data_type in ("auto", "luhn"):
        results["luhn"] = {"valid": luhn_check(value.replace(" ", "")), "standard": "ISO/IEC 7812"}

    best_match = next((t for t, r in results.items() if r["valid"]), None)
    return {
        "ok": True,
        "value": value,
        "type_requested": data_type,
        "results": results,
        "best_match": best_match,
    }


# ── Edge case senaryoları ─────────────────────────────────────────────────────

@router.post("/edge-cases")
def edge_cases(body: EdgeCasesRequest):
    """Bankacılık edge case ve sınır değer senaryoları üretimi."""
    _check_banking()
    SCENARIOS = {
        "sifir_bakiye": {
            "description": "Sıfır bakiyeli hesap — yetersiz bakiye testi",
            "data": {"hesap_no": "HSP0000000001", "iban": generate_tr_iban(), "bakiye": 0.0, "para_birimi": "TRY"},
        },
        "maksimum_limit": {
            "description": "Limit üstü transfer denemesi",
            "data": {"tutar": 9_999_999.99, "para_birimi": "TRY", "aciklama": "Maksimum limit aşımı testi"},
        },
        "negatif_islem": {
            "description": "Negatif/iade işlemi",
            "data": {"tutar": -500.00, "islem_turu": "İade", "aciklama": "POS iade - 3 gün içinde"},
        },
        "yabanci_musteri": {
            "description": "Yabancı uyruklu müşteri — pasaport ile",
            "data": {
                "kimlik_tipi": "PASAPORT",
                "kimlik_no": f"P{''.join([str(random.randint(0, 9)) for _ in range(7)])}",
                "uyruk": random.choice(["DE", "GB", "US", "NL", "FR"]),
                "tc_kimlik": None,
            },
        },
        "tuzel_kisi": {
            "description": "Tüzel kişi — VKN ile, TC yok",
            "data": {"kimlik_tipi": "VKN", "vkn": generate_vkn(), "tc_kimlik": None, "segment": "KOBİ"},
        },
        "artik_yil": {
            "description": "29 Şubat doğum tarihi edge case",
            "data": {"dogum_tarihi": "2000-02-29", "tc_kimlik": generate_tc_kimlik(),
                     "not": "2025 yılında yaş hesabı: 28 Şubat mı yoksa 1 Mart mı?"},
        },
        "yil_sonu": {
            "description": "Yıl sonu kapanış işlemi",
            "data": {"tarih": "2025-12-31T23:59:59", "islem_turu": "Yıl Sonu Kapanış",
                     "tutar": round(random.uniform(100, 10000), 2)},
        },
        "doviz_cevrim": {
            "description": "USD→TRY döviz çevrim işlemi",
            "data": {
                "kaynak_para_birimi": "USD",
                "hedef_para_birimi": "TRY",
                "tutar_usd": round(random.uniform(100, 5000), 2),
                "kur": generate_doviz_kuru("USD", "TRY"),
                "islem_turu": "Döviz Alım-Satım",
            },
        },
        "temerrut": {
            "description": "Temerrüt müşteri senaryosu",
            "data": {
                "tc_kimlik": generate_tc_kimlik(),
                "risk_skoru": generate_risk_skoru("Temel", temerrut=True),
                "gecikme_gun": random.randint(30, 180),
                "segment": "Temel",
                "kredi_durumu": "Gecikme",
            },
        },
    }

    if "all" in body.scenarios:
        result = SCENARIOS
    else:
        result = {k: SCENARIOS[k] for k in body.scenarios if k in SCENARIOS}

    return {
        "ok": True,
        "count": len(result),
        "scenarios": result,
        "available_scenarios": list(SCENARIOS.keys()),
    }


# ── Export ────────────────────────────────────────────────────────────────────

@router.post("/export")
def export_data(body: ExportRequest):
    """Üretilen veriyi CSV veya JSON olarak indir."""
    _check_banking()
    rows = generate_banking_data(body.entity_type, body.count, body.seed)
    serialized = [{k: _serialize(v) for k, v in row.items()} for row in rows]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if body.format == "csv":
        if not serialized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Veri yok")
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=serialized[0].keys())
        writer.writeheader()
        writer.writerows(serialized)
        content = output.getvalue().encode("utf-8-sig")
        filename = f"banking_{body.entity_type}_{body.count}_{timestamp}.csv"
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    content = json.dumps(serialized, ensure_ascii=False, indent=2).encode("utf-8")
    filename = f"banking_{body.entity_type}_{body.count}_{timestamp}.json"
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── DB Şema Okuma + AI Veri Üretimi ──────────────────────────────────────────

@router.get("/db/providers")
def list_llm_providers():
    """Kullanılabilir LLM sağlayıcıları listele (Anthropic, OpenAI, Ollama)."""
    try:
        from banking.ai_data_generator import AIDataGenerator
        providers = AIDataGenerator.get_available_providers()
        active = next((p for p, info in providers.items() if info["available"]), None)
        return {"ok": True, "providers": providers, "active": active}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/db/connections")
def list_db_connections():
    """Kullanılabilir DB bağlantılarını listele (demo dahil)."""
    connections = [
        {
            "id":       "demo",
            "label":    "🏦 Demo Bankacılık DB (SQLite)",
            "db_type":  "sqlite",
            "conn_str": _DEMO_DB_PATH,
            "built_in": True,
            "description": "7 tablolu Türk bankacılık şeması — MUSTERILER, HESAPLAR, ISLEMLER, KREDILER, KARTLAR, KURUMSAL_MUSTERILER, DOVIZ_ISLEMLERI",
        }
    ]
    for cid, info in _db_connections.items():
        connections.append({
            "id":       cid,
            "label":    info.get("label", cid),
            "db_type":  info.get("db_type"),
            "built_in": False,
            "description": f"{info.get('db_type', '?')} — {info.get('conn_str', '?')[:60]}",
        })
    return {"ok": True, "connections": connections}


@router.post("/db/connect")
def db_connect(body: DbConnectRequest):
    """
    Bir DB'ye bağlan ve şemasını oku.
    Özel: db_type='demo' → demo SQLite'ı kullan.
    """
    db_type = body.db_type
    conn_str = body.conn_str
    label = body.label

    if db_type == "demo":
        db_type = "sqlite"
        conn_str = _DEMO_DB_PATH
        label = "🏦 Demo Bankacılık DB"

    if not conn_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conn_str zorunlu")

    try:
        reader = _get_schema_reader(db_type, conn_str)
        reader.connect()
        tables = reader.read_schema()
        schema_dict = reader.schema_to_dict(tables)
        schema_ddl = reader.schema_to_ddl(tables)
        topo_order = reader.topological_order(tables)
        reader.disconnect()

        conn_id = f"conn_{len(_db_connections)+1}"
        _db_connections[conn_id] = {
            "db_type": db_type,
            "conn_str": conn_str,
            "label": label or conn_id,
        }

        default_counts = {t: 10 for t in topo_order}
        return {
            "ok": True,
            "conn_id": conn_id,
            "label": label or conn_id,
            "db_type": db_type,
            "schema": schema_dict,
            "schema_ddl": schema_ddl,
            "table_order": topo_order,
            "table_count": len(topo_order),
            "default_counts": default_counts,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/db/analyze")
def db_analyze_schema(body: DbAnalyzeRequest):
    """LLM ile şemayı analiz et, iş kurallarını çıkar."""
    if not body.schema_ddl:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="schema_ddl zorunlu")
    try:
        from banking.ai_data_generator import AIDataGenerator
        gen = AIDataGenerator()
        analysis = gen.analyze_schema(body.schema_ddl)
        return {
            "ok": True,
            "has_llm": gen.has_llm,
            "model": gen.model,
            "provider": gen.provider,
            "analysis": analysis,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/db/ai-generate")
def db_ai_generate(body: DbAiGenerateRequest):
    """Şema + LLM analizi kullanarak test verisi üret."""
    if not body.schema_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="schema_dict zorunlu")

    counts = body.counts or {t: 10 for t in body.schema_dict.keys()}
    counts = {t: min(int(n), 100) for t, n in counts.items()}

    try:
        from banking.ai_data_generator import AIDataGenerator
        gen = AIDataGenerator(preferred_model=body.model)
        result = gen.generate(
            schema_dict=body.schema_dict,
            schema_ddl=body.schema_ddl,
            counts=counts,
            extra_rules=body.extra_rules,
            analysis=body.analysis,
            seed=body.seed,
        )
        meta = {t: len(rows) for t, rows in result["data"].items()}
        return {
            "ok": True,
            "method": result["method"],
            "model": result.get("model"),
            "message": result.get("message", ""),
            "analysis": result.get("analysis", {}),
            "dataset": result["data"],
            "meta": meta,
        }
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "trace": traceback.format_exc()[-500:]},
        )


@router.post("/db/insert")
def db_insert(body: DbInsertRequest):
    """Üretilen veriyi hedef DB'ye INSERT et."""
    db_type = body.db_type
    conn_str = body.conn_str

    if db_type == "demo":
        db_type = "sqlite"
        conn_str = _DEMO_DB_PATH

    if not body.dataset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="dataset boş")

    table_order = body.table_order or list(body.dataset.keys())

    try:
        if db_type == "sqlite":
            conn = _sqlite3.connect(conn_str)
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()

            insert_counts: dict = {}
            errors: list = []

            for tname in table_order:
                rows = body.dataset.get(tname, [])
                if not rows:
                    continue
                if body.truncate_first:
                    try:
                        cursor.execute(f"DELETE FROM `{tname}`")
                    except Exception as e:
                        errors.append(f"TRUNCATE {tname}: {e}")

                cols = [k for k in rows[0].keys()]
                placeholders = ",".join(["?" for _ in cols])
                sql = f"INSERT OR IGNORE INTO `{tname}` ({','.join(cols)}) VALUES ({placeholders})"

                inserted = 0
                for row in rows:
                    try:
                        vals = [row.get(c) for c in cols]
                        cursor.execute(sql, vals)
                        inserted += 1
                    except Exception as e:
                        errors.append(f"{tname}: {e}")
                insert_counts[tname] = inserted

            conn.commit()
            conn.close()

            return {
                "ok": True,
                "insert_counts": insert_counts,
                "total": sum(insert_counts.values()),
                "errors": errors[:10],
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{db_type} insert henüz desteklenmiyor",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/db/query")
def db_query(body: DbQueryRequest):
    """DB'de SELECT sorgusu çalıştır (sadece SELECT, güvenlik için)."""
    db_type = body.db_type
    conn_str = body.conn_str

    if db_type == "demo":
        db_type = "sqlite"
        conn_str = _DEMO_DB_PATH

    if not body.sql.strip().upper().startswith("SELECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sadece SELECT sorgusuna izin verilir",
        )

    try:
        conn = _sqlite3.connect(conn_str)
        conn.row_factory = _sqlite3.Row
        c = conn.cursor()
        c.execute(f"{body.sql} LIMIT {body.limit}")
        rows = [dict(r) for r in c.fetchall()]
        cols = [d[0] for d in c.description] if c.description else []
        conn.close()
        return {"ok": True, "rows": rows, "columns": cols, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
