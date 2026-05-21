#!/usr/bin/env python3
"""
extract_steps.py — BGTS Step Definition Ekstraktörü

Projedeki tüm step definition dosyalarını tarar:
  🐍 engine/steps/*.py, backend/tests/bdd/steps/*.py          (pytest-bdd)
  ☕ frameworks/selenium-cucumber-java/.../stepdefinitions/   (Cucumber JVM)
  📘 frameworks/playwright-cucumber-ts/steps/*.ts             (cucumber-js)

Her step için şunları çıkarır:
  - Pattern (raw string)
  - Keyword (given/when/then)
  - Dosya yolu
  - Fonksiyon/metot adı (varsa)
  - Dil (TR/EN, otomatik tespit)

Çıktı:
  - packages/dsl/catalog/_extracted/                          (taslak YAML'ler)
  - stdout: özet rapor
  - --csv FILE: tüm step'leri CSV olarak dök
  - --json FILE: ham veri JSON

Kullanım:
    python3 packages/dsl/scripts/extract_steps.py
    python3 packages/dsl/scripts/extract_steps.py --csv extracted.csv
    python3 packages/dsl/scripts/extract_steps.py --yaml
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

# Python: @given/@when/@then yakalar; fonksiyon adını opsiyonel olarak arar
# (arada başka dekoratörler de olabilir)
# ÖNEMLİ: pattern iç tırnaklı olabilir (örn: 'yanıtta "foo" olmalı')
# Bu yüzden açılış tırnağı ne ise onunla aynı kapanış tırnağına kadar al:
#   - '...' açılmışsa kapanış ' (ve " içindekiler içeriğe dahil)
#   - "..." açılmışsa kapanış " (ve ' içindekiler içeriğe dahil)
#   - Üçlü tırnak (''' veya """) de destekle
PY_PATTERN = re.compile(
    r'''(?sx)
    @(given|when|then|step)\s*\(\s*
    (?:parsers\.(?:parse|re|cfparse)\s*\(\s*)?
    [frub]*
    (?:
        """ (.+?) """                   # triple double
      | \'\'\' (.+?) \'\'\'             # triple single
      | " ((?:\\.|[^"\\])*) "           # double
      | \' ((?:\\.|[^\'\\])*) \'        # single
    )
    ''',
    re.IGNORECASE,
)
# Python fonksiyon adını ayrı olarak, dekoratörün hemen sonrasındaki ilk def'den bul
PY_FUNC_AFTER = re.compile(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', re.IGNORECASE)

JAVA_PATTERN = re.compile(
    r'@(Given|When|Then|And|But)\s*\(\s*"([^"]+)"\s*\)',
)
JAVA_FUNC_AFTER = re.compile(r'public\s+(?:static\s+)?void\s+([a-zA-Z_][a-zA-Z0-9_]*)')

TS_PATTERN = re.compile(
    r'\b(Given|When|Then)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]\s*,\s*(?:async\s*)?(?:\([^)]*\)|function[^\(]*\([^)]*\))?',
    re.MULTILINE,
)

TR_CHARS = re.compile(r'[çğıöşüÇĞİÖŞÜ]')
# ASCII Turkish phonetic markers — word-like patterns only found in TR
ASCII_TR_HINTS = re.compile(r'\b(kullanici|kullan\u0131c\u0131|tiklar|tiklanir|yazar|gorunur|olmali|eklenir|silinir|sec|gir|yaz|git|bas|kontrol|bekle|kaydedil|ac\u0131l|olustur|onay|yonet|guncellenir)\b', re.IGNORECASE)


@dataclass
class Step:
    lang: str                   # python | java | typescript
    keyword: str                # given | when | then | step | and | but
    pattern: str                # raw step pattern
    source_file: str            # relative to project root
    function_name: str = ""     # optional
    language_hint: str = ""     # tr | en | unknown
    params: list[str] = field(default_factory=list)  # {param} names

    def as_dict(self) -> dict:
        return asdict(self)


def detect_language(text: str) -> str:
    if TR_CHARS.search(text) or ASCII_TR_HINTS.search(text):
        return "tr"
    if re.search(r'\b(the|user|clicks?|opens?|should|must|enters?|verifies?)\b', text, re.I):
        return "en"
    return "unknown"


def extract_params(pattern: str) -> list[str]:
    return re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)(?::[a-zA-Z]+)?\}', pattern)


def _find_next_name(content: str, after_pos: int, regex: re.Pattern, within_chars: int = 400) -> str:
    window = content[after_pos : after_pos + within_chars]
    m = regex.search(window)
    return m.group(1) if m else ""


def scan_python(root: Path) -> list[Step]:
    steps: list[Step] = []
    dirs = [
        root / "engine" / "steps",
        root / "backend" / "tests" / "bdd" / "steps",
    ]
    for d in dirs:
        if not d.is_dir():
            continue
        for py in sorted(d.rglob("*.py")):
            if py.name.startswith("__") or py.name == "conftest.py":
                continue
            content = py.read_text(encoding="utf-8", errors="ignore")
            for m in PY_PATTERN.finditer(content):
                kw = m.group(1)
                pat = m.group(2) or m.group(3) or m.group(4) or m.group(5) or ""
                if not pat:
                    continue
                fn = _find_next_name(content, m.end(), PY_FUNC_AFTER)
                steps.append(Step(
                    lang="python",
                    keyword=kw.lower(),
                    pattern=pat,
                    source_file=str(py.relative_to(root)),
                    function_name=fn,
                    language_hint=detect_language(pat),
                    params=extract_params(pat),
                ))
    return steps


def scan_java(root: Path) -> list[Step]:
    steps: list[Step] = []
    java_dir = root / "frameworks" / "selenium-cucumber-java" / "src" / "test" / "java" / "stepdefinitions"
    if not java_dir.is_dir():
        return steps
    for j in sorted(java_dir.rglob("*.java")):
        content = j.read_text(encoding="utf-8", errors="ignore")
        for m in JAVA_PATTERN.finditer(content):
            kw, pat = m.group(1), m.group(2)
            fn = _find_next_name(content, m.end(), JAVA_FUNC_AFTER)
            steps.append(Step(
                lang="java",
                keyword=kw.lower(),
                pattern=pat,
                source_file=str(j.relative_to(root)),
                function_name=fn,
                language_hint=detect_language(pat),
                params=extract_params(pat),
            ))
    return steps


def scan_typescript(root: Path) -> list[Step]:
    steps: list[Step] = []
    ts_dir = root / "frameworks" / "playwright-cucumber-ts" / "steps"
    if not ts_dir.is_dir():
        return steps
    for t in sorted(ts_dir.rglob("*.ts")):
        content = t.read_text(encoding="utf-8", errors="ignore")
        for m in TS_PATTERN.finditer(content):
            kw, pat = m.group(1), m.group(2)
            steps.append(Step(
                lang="typescript",
                keyword=kw.lower(),
                pattern=pat,
                source_file=str(t.relative_to(root)),
                function_name="",
                language_hint=detect_language(pat),
                params=extract_params(pat),
            ))
    return steps


def normalize(pattern: str) -> str:
    """{param:type} → {X}, ardışık whitespace sıkıştır, lower-case."""
    n = re.sub(r'\{[^}]+\}', "{X}", pattern)
    n = re.sub(r'\s+', " ", n).strip().lower()
    return n


def group_by_normalized(steps: list[Step]) -> dict[str, list[Step]]:
    groups: dict[str, list[Step]] = defaultdict(list)
    for s in steps:
        groups[normalize(s.pattern)].append(s)
    return groups


def suggest_id(pattern: str) -> str:
    """Kaba bir snake_case ID önerisi"""
    n = re.sub(r'\{[^}]+\}', "", pattern)
    n = re.sub(r'[^a-zA-Z0-9]+', "_", n).strip("_").lower()
    return n[:40] or "action"


def infer_category(keyword: str, pattern: str, source_file: str) -> str:
    pat = pattern.lower()
    if "api" in pat or "api" in source_file:
        return "api.http"
    if any(w in pat for w in ["tikla", "tıkla", "click"]):
        return "ui.click"
    if any(w in pat for w in ["yaz", "type", "enter", "input", "fill"]):
        return "ui.input"
    if any(w in pat for w in ["sec", "seç", "select", "dropdown"]):
        return "ui.select"
    if any(w in pat for w in ["hover"]):
        return "ui.hover"
    if any(w in pat for w in ["scroll", "kaydır"]):
        return "ui.scroll"
    if any(w in pat for w in ["assert", "should", "gorunur", "görünür", "olmali", "olmalı", "verify"]):
        return "assert.general"
    if any(w in pat for w in ["onay", "approval"]):
        return "bgts.approval"
    if any(w in pat for w in ["proje", "project"]):
        return "bgts.project"
    if any(w in pat for w in ["senaryo", "scenario"]):
        return "bgts.scenario"
    if keyword == "given":
        return "setup.given"
    if keyword == "then":
        return "assert.general"
    return "uncategorized"


def write_extracted_yaml(steps: list[Step], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = group_by_normalized(steps)
    by_cat: dict[str, list[dict]] = defaultdict(list)
    used_ids: set[str] = set()
    for norm, group in sorted(groups.items()):
        primary = group[0]
        cat = infer_category(primary.keyword, primary.pattern, primary.source_file)
        base_id = suggest_id(primary.pattern)
        idx = 0
        aid = base_id
        while aid in used_ids:
            idx += 1
            aid = f"{base_id}_{idx}"
        used_ids.add(aid)

        tr_aliases = sorted({s.pattern for s in group if s.language_hint == "tr"})
        en_aliases = sorted({s.pattern for s in group if s.language_hint == "en"})
        unk_aliases = sorted({s.pattern for s in group if s.language_hint == "unknown"})

        aliases: dict[str, list[str]] = {}
        if tr_aliases: aliases["tr"] = tr_aliases
        if en_aliases: aliases["en"] = en_aliases
        if not aliases and unk_aliases:
            aliases["en" if re.search(r'[a-zA-Z]', unk_aliases[0]) else "tr"] = unk_aliases

        impls: dict[str, dict] = {}
        for s in group:
            if s.lang in impls:
                continue
            impl: dict = {"source_file": s.source_file}
            if s.function_name:
                impl["function"] = s.function_name
            impl["pattern"] = s.pattern
            impls[s.lang] = impl

        params = sorted({p for s in group for p in s.params})
        params_list = [{"name": p, "type": "string", "required": True} for p in params]

        entry: dict = {
            "id": aid,
            "category": cat,
            "description": f"(taslak) {primary.pattern}",
            "aliases": aliases,
            "implementations": impls,
            "tags": ["draft", "auto-extracted"],
            "since": "2026-04-17",
        }
        if params_list:
            entry["parameters"] = params_list

        by_cat[cat.split(".")[0]].append(entry)

    import yaml
    for top_cat, entries in by_cat.items():
        path = out_dir / f"{top_cat}.draft.yaml"
        doc = {
            "version": "0.1.0-draft",
            "category_name": f"{top_cat.title()} (OTOMATIK CIKARILDI)",
            "notes": "Bu dosya extract_steps.py tarafindan uretildi. Lutfen rotuslayip catalog/ altina tasiyın.",
            "actions": entries,
        }
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(doc, f, allow_unicode=True, sort_keys=False, width=120)
        print(f"  ✅ {path.relative_to(ROOT)} ({len(entries)} cümlecik)")


def main() -> int:
    ap = argparse.ArgumentParser(description="BGTS step definition ekstraktörü")
    ap.add_argument("--csv", help="Tüm step'leri CSV dosyasına yaz")
    ap.add_argument("--json", help="Ham veriyi JSON'a yaz")
    ap.add_argument("--yaml", action="store_true", help="catalog/_extracted/ altına YAML taslaklar üret")
    ap.add_argument("--list", action="store_true", help="Tüm step'leri stdout'a basit listele")
    args = ap.parse_args()

    print("🔎 BGTS Step Ekstraktörü\n")
    steps = scan_python(ROOT) + scan_java(ROOT) + scan_typescript(ROOT)

    lang_counts = Counter(s.lang for s in steps)
    hint_counts = Counter(s.language_hint for s in steps)
    kw_counts = Counter(s.keyword for s in steps)

    print(f"  Toplam step: {len(steps)}")
    for lang, c in lang_counts.most_common():
        print(f"    {lang:<12} {c}")
    print()
    print("  Dil tahmini (pattern dilinden):")
    for h, c in hint_counts.most_common():
        print(f"    {h:<12} {c}")
    print()
    print("  Keyword dağılımı:")
    for k, c in kw_counts.most_common():
        print(f"    {k:<12} {c}")
    print()

    groups = group_by_normalized(steps)
    print(f"  Benzersiz normalize edilmiş kalıp: {len(groups)}")
    multi = [(n, g) for n, g in groups.items() if len(g) > 1]
    print(f"    Bunlardan {len(multi)} tanesi birden fazla dilde/framework'te duplike/eşdeğer")
    print()

    if args.list:
        for s in steps:
            print(f"  [{s.lang:4}|{s.keyword:5}|{s.language_hint:3}] {s.pattern}")
        print()

    if args.csv:
        Path(args.csv).parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["lang", "keyword", "pattern", "source_file", "function_name", "language_hint", "params"])
            w.writeheader()
            for s in steps:
                row = s.as_dict()
                row["params"] = ",".join(row["params"])
                w.writerow(row)
        print(f"  📄 CSV yazıldı: {args.csv}")

    if args.json:
        Path(args.json).write_text(json.dumps([s.as_dict() for s in steps], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  📄 JSON yazıldı: {args.json}")

    if args.yaml:
        out = ROOT / "packages" / "dsl" / "catalog" / "_extracted"
        print(f"  📝 YAML taslakları üretiliyor → {out.relative_to(ROOT)}")
        write_extracted_yaml(steps, out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
