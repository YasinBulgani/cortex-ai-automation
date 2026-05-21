#!/usr/bin/env python3
"""
build_catalog.py — Canonical Catalog Builder

extract_steps.py'nin bulduğu 723 step'i gerçek, temiz, canonical
catalog/*.yaml dosyalarına dönüştürür.

Strateji:
  1. Fonksiyon adını (varsa) birincil ID yap — genelde zaten snake_case
  2. Aynı function_name = aynı eylemin TR+EN versiyonu → TEK ID, iki alias grubu
  3. Fonksiyon adı yoksa pattern'den türet
  4. Kategori heuristiğini iyileştir (fonksiyon adı + pattern + source_file)
  5. Description üret (Türkçe kısa cümle)
  6. Parametreleri tiplendir (key→locator, {...:d}→int, sayi/days→int)
  7. Duplikatları birleştir (aynı normalize edilmiş pattern)

Kullanım:
    python3 packages/dsl/scripts/build_catalog.py
    python3 packages/dsl/scripts/build_catalog.py --dry-run
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("❌ PyYAML gerekli: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[3]
DSL_DIR = ROOT / "packages" / "dsl"
CATALOG_DIR = DSL_DIR / "catalog"
EXTRACTED_CSV = CATALOG_DIR / "_extracted" / "all-steps.csv"


# ──────────────────────────── Yardımcılar ────────────────────────────

TR_CHARS = re.compile(r'[çğıöşüÇĞİÖŞÜ]')

def is_turkish(text: str) -> bool:
    if TR_CHARS.search(text):
        return True
    tr_words = r'\b(kullanici|kullan\u0131c\u0131|tiklar|tiklanir|yazar|gorunur|olmali|eklenir|silinir|sec|gir|yaz|git|bas|kontrol|bekle|kaydedil|ac\u0131l|olustur|onay|yonet|guncellenir|projede|senaryo|gereksinim|isimli|butonuna)\b'
    return bool(re.search(tr_words, text, re.IGNORECASE))


def is_english(text: str) -> bool:
    return bool(re.search(
        r'\b(the|user|clicks?|opens?|should|must|enters?|verifies?|see|fills?|submits?|navigates?|visits?|types?|selects?)\b',
        text, re.IGNORECASE
    ))


def detect_lang(text: str) -> str:
    tr = is_turkish(text)
    en = is_english(text)
    if tr and not en: return "tr"
    if en and not tr: return "en"
    if tr and en: return "tr"     # TR öncelikli (TR'de İngilizce kelime olabilir)
    return "unknown"


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def sanitize_id(raw: str) -> str:
    """Snake_case, sadece a-z0-9_, ilk harf a-z"""
    n = camel_to_snake(raw)
    n = re.sub(r'[^a-z0-9_]', "_", n)
    n = re.sub(r'_+', "_", n).strip("_")
    if n and not n[0].isalpha():
        n = "step_" + n
    return n[:60] or "action"


def extract_params(pattern: str) -> list[tuple[str, str]]:
    """{param:type} veya {param} dön döner. [(name, type), ...]"""
    out: list[tuple[str, str]] = []
    for m in re.finditer(r'\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z]+))?\}', pattern):
        name, typ = m.group(1), m.group(2) or ""
        out.append((name, typ))
    return out


TYPE_HINTS = {
    "d": "int", "i": "int", "n": "int",
    "s": "string", "str": "string",
    "f": "float",
    "b": "bool",
}


def guess_param_type(name: str, hint: str) -> str:
    if hint:
        return TYPE_HINTS.get(hint.lower(), "string")
    n = name.lower()
    if n in ("key", "element_key", "locator"):
        return "locator"
    if n in ("url", "endpoint", "path"):
        return "url"
    if n in ("count", "num", "n", "number", "days", "hours", "minutes", "seconds", "code", "port", "id", "status_code"):
        return "int"
    if n in ("ms", "timeout", "wait_ms", "duration_ms"):
        return "duration_ms"
    if n in ("enabled", "visible", "active", "flag"):
        return "bool"
    return "string"


# ────────────────────── Kategori belirleme ──────────────────────

CATEGORY_RULES = [
    # (pattern_regex, function_regex, source_regex, category)
    (r'\b(api|endpoint|http|request|response|status|payload|header)\b', None, None, "api.http"),
    (None, None, r'/api/', "api.http"),
    (None, None, r'bgts_api_steps', "api.http"),
    (None, None, r'backend/tests/bdd', "api.http"),

    (r'\b(cift tiklar|çift tıkla|double.?click)\b', None, None, "ui.click.double"),
    (r'\b(sag tiklar|sağ tıkla|right.?click)\b', None, None, "ui.click.right"),
    (r'\b(tiklar|tıkla|click)\b', None, None, "ui.click"),

    (r'\b(yazar|yazilir|yazılır|type|enters?|fill|inputs?)\b', None, None, "ui.input"),
    (r'\b(sec|seç|selects?|dropdown|choose)\b', None, None, "ui.select"),
    (r'\b(hover|uzerine)\b', None, None, "ui.hover"),
    (r'\b(scroll|kaydir|kaydır)\b', None, None, "ui.scroll"),
    (r'\b(checkbox|tick)\b', None, None, "ui.checkbox"),
    (r'\b(radio)\b', None, None, "ui.radio"),
    (r'\b(drag|surukle|sürükle|drop)\b', None, None, "ui.drag_drop"),
    (r'\b(upload|yukle|yükle|dosya)\b', None, None, "ui.upload"),
    (r'\b(keyboard|tus|tuş|press)\b', None, None, "ui.keyboard"),
    (r'\b(screenshot|ekran.?g)\b', None, None, "ui.screenshot"),
    (r'\b(open|acar|aç|navigate|visit|go to|git)\b', None, None, "ui.navigation"),
    (r'\b(wait|bekler|beklenir|beklemeli)\b', None, None, "ui.wait"),

    (r'\b(should|olmali|olmalı|gorunur|görünür|visible|display)\b', None, None, "assert.visibility"),
    (r'\b(assert|verify|kontrol|dogrulan|doğrulan)\b', None, None, "assert.general"),
    (r'\b(contains?|icer|iceriyor|içerir)\b', None, None, "assert.text"),
    (r'\b(equal|esit|eşit)\b', None, None, "assert.equality"),

    (r'\b(onay|approval)\b', None, None, "bgts.approval"),
    (r'\b(proje|project)\b', None, None, "bgts.project"),
    (r'\b(senaryo|scenario)\b', None, None, "bgts.scenario"),
    (r'\b(regresyon|regression)\b', None, None, "bgts.regression"),
    (r'\b(synthetic|sentetik)\b', None, None, "bgts.synthetic"),
    (r'\b(import|ice ak|içe ak)\b', None, None, "bgts.import"),
    (r'\b(login|giris|giriş|auth|jwt|token)\b', None, None, "bgts.auth"),
    (r'\b(smoke)\b', None, None, "bgts.smoke"),

    (None, None, r'api_tests|api-tests', "api.http"),
]


def infer_category(pattern: str, function: str, source_file: str) -> str:
    text = f"{pattern} || {function}"
    for pat_re, fn_re, src_re, cat in CATEGORY_RULES:
        if pat_re and re.search(pat_re, text, re.IGNORECASE):
            return cat
        if fn_re and re.search(fn_re, function or "", re.IGNORECASE):
            return cat
        if src_re and re.search(src_re, source_file or "", re.IGNORECASE):
            return cat
    return "uncategorized.general"


# ────────────────────── Açıklama (description) üret ──────────────────────

def make_description(pattern: str, category: str, keyword: str) -> str:
    p = pattern.strip()
    if len(p) < 80:
        if keyword == "given":
            return f"(Ön koşul) {p}"
        if keyword == "when":
            return f"Eylem: {p}"
        if keyword == "then":
            return f"Doğrulama: {p}"
        return p
    return p[:77] + "..."


# ────────────────────── ID üretimi (akıllı) ──────────────────────

def choose_id(function_name: str, pattern: str, used_ids: set[str]) -> str:
    # 1. Fonksiyon adı varsa ve henüz kullanılmadıysa o
    if function_name:
        cid = sanitize_id(function_name)
        if cid and cid not in used_ids:
            return cid
        if cid:
            # suffix ekle
            for i in range(2, 100):
                cand = f"{cid}_{i}"
                if cand not in used_ids:
                    return cand

    # 2. Pattern'den üret (ASCII, parametreleri at)
    n = re.sub(r'\{[^}]+\}', " ", pattern)
    n = re.sub(r'[^a-zA-Z0-9\s]', " ", n)
    n = re.sub(r'\s+', "_", n.strip()).lower()[:40]
    n = sanitize_id(n) or "action"

    if n not in used_ids:
        return n
    for i in range(2, 1000):
        cand = f"{n}_{i}"
        if cand not in used_ids:
            return cand
    return f"action_{len(used_ids)}"


# ────────────────────── Ana algoritma ──────────────────────

def load_steps() -> list[dict]:
    if not EXTRACTED_CSV.exists():
        print(f"❌ Önce extract_steps.py çalıştırın — CSV yok: {EXTRACTED_CSV}", file=sys.stderr)
        sys.exit(1)
    with EXTRACTED_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_pattern(pattern: str) -> str:
    """{param:d} → {X}, whitespace sıkıştır, lowercase"""
    n = re.sub(r'\{[^}]+\}', "{X}", pattern)
    n = re.sub(r'\s+', " ", n).strip().lower()
    return n


def group_key(step: dict) -> str:
    """Aynı 'eylem' olarak birleştirilecek step'lerin ortak anahtarı.
    Primary: normalize edilmiş pattern (cross-lang + cross-file birleştirir).
    Bu sayede:
      - Java "I click on {string}" + TS "I click on {string}" = tek eylem
      - Python "kullanici {key} tiklar" (TR) + EN "user clicks on {key}" ise
        farklı kaldı, ama alias-merge pass ikisini sonradan birleştirebilir.
    """
    return normalize_pattern(step["pattern"])


def build_action(group: list[dict], used_ids: set[str]) -> dict:
    primary = group[0]
    pattern = primary["pattern"]
    function = primary["function_name"]
    source = primary["source_file"]
    keyword = primary["keyword"]

    aid = choose_id(function, pattern, used_ids)
    used_ids.add(aid)

    category = infer_category(pattern, function, source)

    # Alias toplama (TR/EN ayır)
    tr_aliases: set[str] = set()
    en_aliases: set[str] = set()
    for s in group:
        p = s["pattern"]
        lang = detect_lang(p)
        if lang == "tr":
            tr_aliases.add(p)
        elif lang == "en":
            en_aliases.add(p)
        else:
            # çoğu durumda ASCII TR (ı yerine i) — TR'ye koy
            tr_aliases.add(p)

    aliases: dict[str, list[str]] = {}
    if tr_aliases:
        aliases["tr"] = sorted(tr_aliases)
    if en_aliases:
        aliases["en"] = sorted(en_aliases)

    # Parametreler
    all_params: dict[str, str] = {}
    for s in group:
        for name, hint in extract_params(s["pattern"]):
            if name not in all_params:
                all_params[name] = guess_param_type(name, hint)

    params_list = [{"name": n, "type": t, "required": True} for n, t in all_params.items()]

    # Implementations — aynı dil için birden fazla yer varsa ilk olanı al,
    # ama source_file'ı farklıysa notes'ta belirt
    impls: dict[str, dict] = {}
    extra_locs: list[str] = []
    for s in group:
        lang = s["lang"]
        if lang in impls:
            existing = impls[lang]
            if existing["source_file"] != s["source_file"]:
                extra_locs.append(f"{lang}:{s['source_file']}")
            continue
        impl: dict = {"source_file": s["source_file"]}
        if s.get("function_name"):
            impl["function"] = s["function_name"]
        impl["pattern"] = s["pattern"]
        impls[lang] = impl

    entry: dict = {
        "id": aid,
        "category": category,
        "description": make_description(pattern, category, keyword),
        "aliases": aliases,
        "implementations": impls,
        "tags": ["auto-extracted", keyword],
        "since": "2026-04-17",
    }
    if params_list:
        entry["parameters"] = params_list
    if extra_locs:
        entry["notes"] = "Ek implementasyon konumları: " + ", ".join(extra_locs)

    return entry


def top_level_category(cat: str) -> str:
    return cat.split(".")[0]


def build(dry_run: bool = False) -> dict[str, int]:
    steps = load_steps()
    print(f"  📖 {len(steps)} step okundu")

    # Grupla
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in steps:
        groups[group_key(s)].append(s)

    print(f"  🔗 {len(groups)} benzersiz eylem (pattern normalize sonrası)")

    # Her grup için action oluştur
    used_ids: set[str] = set()
    actions = [build_action(g, used_ids) for g in groups.values()]

    # Kategoriye göre grupla
    by_top: dict[str, list[dict]] = defaultdict(list)
    for a in actions:
        by_top[top_level_category(a["category"])].append(a)

    # ID'ye göre sırala
    for k in by_top:
        by_top[k].sort(key=lambda x: x["id"])

    stats = {
        "total_steps_scanned": len(steps),
        "unique_actions": len(actions),
    }

    # Her üst kategori için dosya yaz
    file_map = {
        "ui": "ui-actions.yaml",
        "api": "api-actions.yaml",
        "assert": "assertions.yaml",
        "setup": "setup-steps.yaml",
        "bgts": "bgts-domain.yaml",
        "uncategorized": "uncategorized.yaml",
    }

    print()
    for top, items in sorted(by_top.items()):
        fname = file_map.get(top, f"{top}.yaml")
        path = CATALOG_DIR / fname
        doc = {
            "version": "1.0.0",
            "category_name": f"{top.title()} Actions",
            "generated_by": "packages/dsl/scripts/build_catalog.py",
            "generated_at": "2026-04-17",
            "actions": items,
        }
        if dry_run:
            print(f"  [dry-run] {fname:<28} → {len(items)} cümlecik")
        else:
            with path.open("w", encoding="utf-8") as f:
                yaml.dump(doc, f, allow_unicode=True, sort_keys=False, width=120, default_flow_style=False)
            print(f"  ✅ {fname:<28} → {len(items)} cümlecik")
        stats[f"category_{top}"] = len(items)

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("🏗️  BGTS Catalog Builder\n")
    stats = build(args.dry_run)
    print()
    print("  📊 Özet:")
    for k, v in stats.items():
        print(f"     {k:<30} {v}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
