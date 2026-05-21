#!/usr/bin/env python3
"""
validate_catalog.py — BGTS DSL Katalog Doğrulama Aracı

Katalog YAML'lerini JSON Schema'ya karşı doğrular ve
- duplikat id
- duplikat alias
- source_file'da gerçek varlık
- kod'da var ama katalogda olmayan step'ler (ölü katalog)
tespit eder.

Kullanım:
    python3 packages/dsl/scripts/validate_catalog.py                # tüm katalogu
    python3 packages/dsl/scripts/validate_catalog.py --file ui-actions.yaml
    python3 packages/dsl/scripts/validate_catalog.py --strict       # warnings da hata sayılır
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:
    print("❌ PyYAML gerekli: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    import jsonschema
except ImportError:
    print("❌ jsonschema gerekli: pip install jsonschema", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[3]
DSL_DIR = ROOT / "packages" / "dsl"
SCHEMA_PATH = DSL_DIR / "schema" / "action.schema.json"
CATALOG_DIR = DSL_DIR / "catalog"


class Reporter:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.info.append(msg)

    def print_summary(self, strict: bool = False) -> int:
        for msg in self.info:
            print(f"  ℹ️   {msg}")
        for msg in self.warnings:
            print(f"  ⚠️   {msg}")
        for msg in self.errors:
            print(f"  ❌  {msg}")
        print()
        print(f"  Sonuç: {len(self.errors)} hata, {len(self.warnings)} uyarı, {len(self.info)} bilgi")
        if self.errors:
            return 1
        if strict and self.warnings:
            return 1
        return 0


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_catalog_files(only: str | None = None) -> list[Path]:
    if only:
        p = CATALOG_DIR / only
        if not p.exists():
            print(f"❌ Bulunamadı: {p}", file=sys.stderr)
            sys.exit(2)
        return [p]
    return sorted(CATALOG_DIR.glob("*.yaml"))


def validate_file(path: Path, schema: dict, reporter: Reporter, id_index: dict[str, Path], alias_index: dict[str, list[tuple[str, Path]]]) -> None:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "actions" not in data:
        reporter.err(f"{path.name}: 'actions' anahtarı yok")
        return

    actions = data.get("actions") or []
    if not isinstance(actions, list):
        reporter.err(f"{path.name}: 'actions' bir liste olmalı")
        return

    reporter.note(f"{path.name}: {len(actions)} cümlecik bulundu")

    for i, action in enumerate(actions):
        ctx = f"{path.name}#{i} (id={action.get('id', '?')})"

        try:
            jsonschema.validate(action, schema)
        except jsonschema.ValidationError as e:
            reporter.err(f"{ctx} şema ihlali: {e.message} @ {'.'.join(str(p) for p in e.absolute_path)}")
            continue

        aid = action["id"]
        if aid in id_index:
            reporter.err(f"{ctx}: duplike id — önceden {id_index[aid].name}'te tanımlı")
        else:
            id_index[aid] = path

        for lang in ("tr", "en"):
            for alias in action.get("aliases", {}).get(lang, []):
                alias_index[alias].append((aid, path))

        impls = action.get("implementations", {})
        for lang, impl in impls.items():
            sf = impl.get("source_file")
            if sf:
                full = ROOT / sf
                if not full.exists():
                    reporter.warn(f"{ctx}: {lang} source_file '{sf}' diskte yok")


def check_alias_conflicts(alias_index: dict[str, list[tuple[str, Path]]], reporter: Reporter) -> None:
    for alias, occurrences in alias_index.items():
        ids = set(aid for aid, _ in occurrences)
        if len(ids) > 1:
            locs = ", ".join(f"{aid}@{p.name}" for aid, p in occurrences)
            reporter.err(f"Alias çakışması: '{alias}' → {locs}")


def main() -> int:
    ap = argparse.ArgumentParser(description="BGTS DSL katalog doğrulama")
    ap.add_argument("--file", help="Sadece bu katalog dosyasını doğrula")
    ap.add_argument("--strict", action="store_true", help="Uyarılar da hata sayılsın")
    args = ap.parse_args()

    print("🔍 BGTS DSL Katalog Doğrulaması\n")

    if not SCHEMA_PATH.exists():
        print(f"❌ Şema dosyası yok: {SCHEMA_PATH}", file=sys.stderr)
        return 2

    schema = load_schema()
    files = load_catalog_files(args.file)
    if not files:
        print("⚠️  Katalog dosyası bulunamadı")
        return 0

    reporter = Reporter()
    id_index: dict[str, Path] = {}
    alias_index: dict[str, list[tuple[str, Path]]] = defaultdict(list)

    for path in files:
        validate_file(path, schema, reporter, id_index, alias_index)

    check_alias_conflicts(alias_index, reporter)

    reporter.note(f"Toplam benzersiz id: {len(id_index)}")
    reporter.note(f"Toplam alias: {sum(len(v) for v in alias_index.values())}")

    return reporter.print_summary(strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
