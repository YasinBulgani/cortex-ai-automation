#!/usr/bin/env python3
"""
add_action.py — BGTS DSL Katalog Düzenleme Aracı

Kataloga yeni cümlecik ekler veya mevcut bir cümleciğe alias/implementation
ekler. YAML'ları manuel açmaktansa hızlı komut satırı kullanımı sağlar.

Kullanım:

    # Yeni cümlecik ekle
    python3 packages/dsl/scripts/add_action.py add \\
        --id click_save_button \\
        --category ui.click \\
        --description "Kaydet butonuna tıklar" \\
        --tr '"{name}" kaydet butonuna tıklar' \\
        --en 'user clicks save button {name}' \\
        --python engine/steps/click_steps.py:step_click_save \\
        --tag ui,click --tag pilot

    # Mevcut cümleciğe alias ekle
    python3 packages/dsl/scripts/add_action.py alias \\
        --id step_click_element \\
        --en 'I click on element {key}' \\
        --en '{key} element is clicked'

    # Mevcut cümleciğe implementation ekle
    python3 packages/dsl/scripts/add_action.py impl \\
        --id step_click_element \\
        --lang typescript \\
        --source_file frameworks/playwright-cucumber-ts/steps/web-steps.ts \\
        --function clickElement

Makefile kısayolları:
    make dsl-add ID=... CATEGORY=ui.click DESCRIPTION=... TR=... EN=... PYTHON=...
    make dsl-alias ID=... EN='I click on {key}'
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("PyYAML gerekli: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = ROOT / "packages" / "dsl" / "catalog"


FILE_MAP = {
    "ui": "ui-actions.yaml",
    "api": "api-actions.yaml",
    "assert": "assertions.yaml",
    "bgts": "bgts-domain.yaml",
    "setup": "setup-steps.yaml",
    "uncategorized": "uncategorized.yaml",
}


def top_cat(category: str) -> str:
    return (category or "uncategorized").split(".")[0]


def file_for_category(category: str) -> Path:
    return CATALOG_DIR / FILE_MAP.get(top_cat(category), "uncategorized.yaml")


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {"version": "1.0.0", "category_name": path.stem, "actions": []}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"actions": []}


def save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, width=120, default_flow_style=False)


def find_action_file(action_id: str) -> Optional[tuple[Path, dict, int]]:
    """Tüm YAML dosyalarını gez, action_id'yi bul. Dosya + data + index döner."""
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        data = load_yaml(path)
        actions = data.get("actions") or []
        for i, a in enumerate(actions):
            if isinstance(a, dict) and a.get("id") == action_id:
                return path, data, i
    return None


def parse_python_impl(value: str) -> Dict[str, str]:
    """'module.path:function' veya 'path/to/file.py:function' parse et."""
    if ":" not in value:
        return {"source_file": value}
    src, fn = value.rsplit(":", 1)
    impl: Dict[str, str] = {"function": fn}
    if src.endswith(".py") or "/" in src:
        impl["source_file"] = src
        # module path üret
        impl["module"] = src.replace("/", ".").removesuffix(".py")
    else:
        impl["module"] = src
        impl["source_file"] = src.replace(".", "/") + ".py"
    return impl


def parse_java_impl(value: str) -> Dict[str, str]:
    """'com.bgts.ClickSteps#clickMethod@frameworks/.../ClickSteps.java'"""
    if "@" in value:
        ref, source = value.rsplit("@", 1)
    else:
        ref, source = value, ""
    impl: Dict[str, str] = {}
    if source:
        impl["source_file"] = source
    if "#" in ref:
        cls, method = ref.rsplit("#", 1)
        impl["class"] = cls
        impl["method"] = method
    else:
        impl["class"] = ref
    return impl


def parse_ts_impl(value: str) -> Dict[str, str]:
    """'module-name:function@source_file.ts'"""
    if "@" in value:
        ref, source = value.rsplit("@", 1)
    else:
        ref, source = value, ""
    impl: Dict[str, str] = {}
    if source:
        impl["source_file"] = source
    if ":" in ref:
        mod, fn = ref.rsplit(":", 1)
        impl["module"] = mod
        impl["function"] = fn
    else:
        impl["module"] = ref
    return impl


def cmd_add(args: argparse.Namespace) -> int:
    aid = args.id
    existing = find_action_file(aid)
    if existing:
        print(f"Hata: '{aid}' kimliği zaten '{existing[0].name}' içinde mevcut.", file=sys.stderr)
        print("Alias veya implementation eklemek için 'alias' veya 'impl' alt komutunu kullanın.", file=sys.stderr)
        return 1

    path = file_for_category(args.category)
    data = load_yaml(path)

    aliases: Dict[str, List[str]] = {}
    if args.tr:
        aliases["tr"] = list(args.tr)
    if args.en:
        aliases["en"] = list(args.en)
    if not aliases:
        print("Hata: En az bir alias (--tr veya --en) gerekli.", file=sys.stderr)
        return 1

    impls: Dict[str, Any] = {}
    if args.python:
        impls["python"] = parse_python_impl(args.python)
    if args.java:
        impls["java"] = parse_java_impl(args.java)
    if args.typescript:
        impls["typescript"] = parse_ts_impl(args.typescript)
    if not impls:
        print("Hata: En az bir implementation gerekli (--python, --java veya --typescript).", file=sys.stderr)
        return 1

    tags: List[str] = []
    for t in args.tag or []:
        tags.extend(x.strip() for x in t.split(",") if x.strip())

    entry: Dict[str, Any] = {
        "id": aid,
        "category": args.category,
        "description": args.description,
        "aliases": aliases,
        "implementations": impls,
    }
    if tags:
        entry["tags"] = tags
    if args.since:
        entry["since"] = args.since

    data.setdefault("actions", []).append(entry)
    save_yaml(path, data)

    print(f"[OK] '{aid}' eklendi: {path.relative_to(ROOT)}")
    return 0


def cmd_alias(args: argparse.Namespace) -> int:
    aid = args.id
    found = find_action_file(aid)
    if not found:
        print(f"Hata: '{aid}' bulunamadı.", file=sys.stderr)
        return 1
    path, data, idx = found
    action = data["actions"][idx]
    aliases = action.setdefault("aliases", {})

    added = 0
    for lang, values in (("tr", args.tr or []), ("en", args.en or [])):
        if not values:
            continue
        cur = aliases.setdefault(lang, [])
        for v in values:
            if v in cur:
                print(f"  [atlandı] zaten var: {lang}: {v}")
                continue
            cur.append(v)
            added += 1
            print(f"  [+] {lang}: {v}")

    if added == 0:
        print("Hiçbir yeni alias eklenmedi.")
        return 0
    save_yaml(path, data)
    print(f"[OK] {added} alias eklendi: {path.relative_to(ROOT)}")
    return 0


def cmd_impl(args: argparse.Namespace) -> int:
    aid = args.id
    found = find_action_file(aid)
    if not found:
        print(f"Hata: '{aid}' bulunamadı.", file=sys.stderr)
        return 1
    path, data, idx = found
    action = data["actions"][idx]
    impls = action.setdefault("implementations", {})
    if args.lang in impls and not args.force:
        print(f"Hata: '{args.lang}' için implementasyon zaten tanımlı. --force ile üzerine yazılır.", file=sys.stderr)
        return 1

    impl: Dict[str, str] = {}
    if args.source_file:
        impl["source_file"] = args.source_file
    if args.module:
        impl["module"] = args.module
    if args.function:
        impl["function"] = args.function
    if args.cls:
        impl["class"] = args.cls
    if args.method:
        impl["method"] = args.method
    if args.pattern:
        impl["pattern"] = args.pattern
    if args.function_ref:
        impl["function_ref"] = args.function_ref

    if not impl:
        print("Hata: En az bir impl alanı girin (--source_file, --module, --function, vb).", file=sys.stderr)
        return 1

    impls[args.lang] = impl
    save_yaml(path, data)
    print(f"[OK] '{aid}' için {args.lang} implementasyonu güncellendi: {path.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="BGTS DSL katalog düzenleyici")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # add
    pa = sub.add_parser("add", help="Yeni cümlecik ekle")
    pa.add_argument("--id", required=True)
    pa.add_argument("--category", required=True, help="ui.click / api.http / ...")
    pa.add_argument("--description", required=True)
    pa.add_argument("--tr", action="append", help="Türkçe alias (birden fazla kere)")
    pa.add_argument("--en", action="append", help="İngilizce alias (birden fazla kere)")
    pa.add_argument("--python", help="'module.path:function' veya 'path/to/file.py:function'")
    pa.add_argument("--java", help="'com.pkg.Class#method@source_file.java'")
    pa.add_argument("--typescript", help="'module:function@source_file.ts'")
    pa.add_argument("--tag", action="append", help="Virgülle çoklu olabilir")
    pa.add_argument("--since", help="YYYY-MM-DD")

    # alias
    pl = sub.add_parser("alias", help="Mevcut cümleciğe alias ekle")
    pl.add_argument("--id", required=True)
    pl.add_argument("--tr", action="append")
    pl.add_argument("--en", action="append")

    # impl
    pi = sub.add_parser("impl", help="Mevcut cümleciğe implementasyon ekle")
    pi.add_argument("--id", required=True)
    pi.add_argument("--lang", required=True, choices=["python", "java", "typescript"])
    pi.add_argument("--source_file")
    pi.add_argument("--module")
    pi.add_argument("--function")
    pi.add_argument("--class", dest="cls")
    pi.add_argument("--method")
    pi.add_argument("--pattern")
    pi.add_argument("--function_ref")
    pi.add_argument("--force", action="store_true")

    args = ap.parse_args()
    if args.cmd == "add":
        return cmd_add(args)
    if args.cmd == "alias":
        return cmd_alias(args)
    if args.cmd == "impl":
        return cmd_impl(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
