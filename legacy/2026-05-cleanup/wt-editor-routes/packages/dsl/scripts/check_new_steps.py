#!/usr/bin/env python3
"""
check_new_steps.py — Pre-commit Hook: Katalogda Olmayan Step'leri Uyar

Staged dosyalarda yeni @given/@when/@then decorator'leri tespit edip
bunların kataloğa (packages/dsl/catalog/*.yaml) kayıtlı olup olmadığını
kontrol eder. Kayıtsızsa uyarır (opsiyonel: --strict ile hata yapar).

Kullanım:
    # Tek seferlik kontrol
    python3 packages/dsl/scripts/check_new_steps.py

    # Pre-commit hook modu (yalnız staged dosyaları tara)
    python3 packages/dsl/scripts/check_new_steps.py --staged

    # Hata modu (CI için)
    python3 packages/dsl/scripts/check_new_steps.py --strict

Pre-commit framework ile kullanım:
    # .pre-commit-config.yaml içinde
    - repo: local
      hooks:
        - id: dsl-catalog-sync
          name: DSL Katalog Senkronizasyonu
          entry: python3 packages/dsl/scripts/check_new_steps.py --staged
          language: system
          pass_filenames: false
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("PyYAML gerekli: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = ROOT / "packages" / "dsl" / "catalog"


# Step tanım regex'leri (extract_steps.py ile tutarlı)
PY_PATTERN = re.compile(
    r"""@(given|when|then|step)\s*\(\s*
        (?:parsers\.(?:parse|re|cfparse)\s*\(\s*)?
        [frub]*
        (?:"""
    r'''"""(.+?)"""|'''
    r"""\'\'\'(.+?)\'\'\'|"""
    r'''"((?:\\.|[^"\\])*)"|'''
    r"""'((?:\\.|[^'\\])*)')""",
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

JAVA_PATTERN = re.compile(r'@(Given|When|Then|And|But)\s*\(\s*"([^"]+)"')
TS_PATTERN = re.compile(r'\b(Given|When|Then)\s*\(\s*[\'"`]([^\'"`]+)[\'"`]')


def staged_files() -> List[Path]:
    """git diff --cached ile staged edilmiş dosyaları dön."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    files = [ROOT / line.strip() for line in result.stdout.splitlines() if line.strip()]
    return [f for f in files if f.exists()]


def all_source_files() -> List[Path]:
    exts = {".py", ".ts", ".java"}
    out: List[Path] = []
    for base in [
        ROOT / "engine" / "steps",
        ROOT / "backend" / "tests" / "bdd" / "steps",
        ROOT / "frameworks" / "selenium-cucumber-java" / "src" / "test" / "java" / "stepdefinitions",
        ROOT / "frameworks" / "playwright-cucumber-ts" / "steps",
    ]:
        if not base.is_dir():
            continue
        for f in base.rglob("*"):
            if f.suffix in exts and "generated" not in f.parts:
                out.append(f)
    return out


def extract_patterns(path: Path) -> List[str]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if path.suffix == ".py":
        matches = PY_PATTERN.findall(content)
        return [m[1] or m[2] or m[3] or m[4] for m in matches if any(m[1:])]
    if path.suffix == ".java":
        return [m[1] for m in JAVA_PATTERN.findall(content)]
    if path.suffix == ".ts":
        return [m[1] for m in TS_PATTERN.findall(content)]
    return []


def catalog_patterns() -> Set[str]:
    out: Set[str] = set()
    if not CATALOG_DIR.is_dir():
        return out
    for path in CATALOG_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        for a in data.get("actions") or []:
            if not isinstance(a, dict):
                continue
            for arr in (a.get("aliases") or {}).values():
                if isinstance(arr, list):
                    out.update(arr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true", help="Sadece staged dosyaları tara (pre-commit için)")
    ap.add_argument("--strict", action="store_true", help="Bulunursa exit 1 (CI için)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    files = staged_files() if args.staged else all_source_files()
    files = [f for f in files if f.suffix in {".py", ".ts", ".java"}]

    if args.staged and not files:
        # Staged içinde step dosyası yoksa sessiz geç
        return 0

    in_code: List[tuple[Path, str]] = []
    for f in files:
        for pat in extract_patterns(f):
            in_code.append((f, pat))

    if args.verbose:
        print(f"Taranan dosya: {len(files)}, bulunan step pattern: {len(in_code)}")

    cat_set = catalog_patterns()
    missing: List[tuple[Path, str]] = []
    for f, pat in in_code:
        if pat not in cat_set:
            missing.append((f, pat))

    if not missing:
        if args.verbose or not args.staged:
            print(f"[OK] Tüm step'ler katalogda ({len(in_code)} pattern, {len(cat_set)} katalog alias).")
        return 0

    print()
    print("[UYARI] Katalog'da olmayan step pattern'leri bulundu:")
    print()
    for f, pat in missing[:20]:
        rel = f.relative_to(ROOT)
        print(f"  - {rel}")
        print(f"      pattern: {pat}")
    if len(missing) > 20:
        print(f"  ... ve {len(missing) - 20} tane daha")
    print()
    print("Düzeltmek için:")
    print("  1. make dsl-extract   # mevcut step'leri tara")
    print("  2. make dsl-rebuild   # kataloğu yeniden üret")
    print("  3. VEYA elle: make dsl-alias ID=<action_id> EN='<pattern>'")
    print()

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
