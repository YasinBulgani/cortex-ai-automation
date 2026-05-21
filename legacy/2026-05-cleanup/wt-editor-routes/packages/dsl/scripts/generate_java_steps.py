#!/usr/bin/env python3
"""
generate_java_steps.py — YAML katalogdan Java step sınıfı üretici.

Java tarafında Cucumber JVM runtime'da dinamik step registration mümkün değil;
onun yerine compile-time code generation yapılır.

Üretilen dosyalar:
    frameworks/selenium-cucumber-java/src/test/java/stepdefinitions/generated/
    ├── GeneratedClickSteps.java
    ├── GeneratedInputSteps.java
    └── ...

Üretilen her sınıf, katalogdaki alias'ları mevcut step method'larına delegate eder.
Mevcut ClickSteps.java, InputSteps.java vb. dosyalara DOKUNULMAZ.

Kullanım:
    python3 packages/dsl/scripts/generate_java_steps.py
    python3 packages/dsl/scripts/generate_java_steps.py --category ui
    python3 packages/dsl/scripts/generate_java_steps.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("PyYAML gerekli: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = ROOT / "packages" / "dsl" / "catalog"
JAVA_OUT_DIR = (
    ROOT
    / "frameworks"
    / "selenium-cucumber-java"
    / "src"
    / "test"
    / "java"
    / "stepdefinitions"
    / "generated"
)


@dataclass
class JavaBinding:
    action_id: str
    keyword: str  # Given/When/Then
    alias: str
    lang: str
    delegate_class: str  # e.g. "stepdefinitions.ClickSteps"
    delegate_method: str  # e.g. "clickOnElement"
    params: List[tuple[str, str]]  # (name, java_type)


TYPE_MAP: Dict[str, str] = {
    "string": "String",
    "int": "int",
    "float": "double",
    "bool": "boolean",
    "locator": "String",
    "url": "String",
    "duration_ms": "long",
    "json": "String",
}


def java_type_from_hint(name_or_hint: str) -> str:
    return TYPE_MAP.get(name_or_hint.lower(), "String")


def extract_params(pattern: str) -> List[tuple[str, str]]:
    """Pattern'den Java parametreleri çıkar.

    Cucumber expression: {string}, {int}, {float}, {word}, {}
    """
    out: List[tuple[str, str]] = []
    i = 0
    unnamed_count = 0
    for m in re.finditer(r'\{([^}]*)\}', pattern):
        token = m.group(1).strip()
        if not token or token in ("string", "int", "float", "word", "long"):
            unnamed_count += 1
            name = f"arg{unnamed_count}"
            typ = java_type_from_hint(token or "string")
        elif ":" in token:
            name, type_hint = token.split(":", 1)
            typ = java_type_from_hint(type_hint)
        else:
            name = token
            typ = "String"
        # Java identifier'a göre normalize et
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if not name or not name[0].isalpha():
            name = f"arg{i}"
        out.append((name, typ))
        i += 1
    return out


def to_java_string_literal(s: str) -> str:
    """Java string için escape."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def to_pascal_case(s: str) -> str:
    return "".join(w.capitalize() for w in re.split(r'[^a-zA-Z0-9]', s) if w)


def detect_keyword(tags: List[str]) -> str:
    for kw in ("given", "when", "then"):
        if kw in tags:
            return kw.capitalize()
    return "When"


def load_actions() -> List[dict]:
    actions: List[dict] = []
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for a in data.get("actions") or []:
            if isinstance(a, dict):
                a.setdefault("_source_yaml", path.name)
                actions.append(a)
    return actions


def build_bindings(
    actions: List[dict],
    only_category: Optional[str] = None,
) -> Dict[str, List[JavaBinding]]:
    """Java-backed eylemleri üst-kategoriye göre grupla."""
    by_cat: Dict[str, List[JavaBinding]] = defaultdict(list)

    for action in actions:
        aid = action.get("id", "?")
        category = action.get("category", "")
        top_cat = category.split(".")[0] or "misc"

        if only_category and top_cat != only_category:
            continue

        java_impl = (action.get("implementations") or {}).get("java")
        if not java_impl:
            continue

        # class ve method'u bul
        delegate_class = java_impl.get("class")
        delegate_method = java_impl.get("method") or java_impl.get("function")

        if not delegate_class:
            # source_file'dan class tahmin et
            source = java_impl.get("source_file", "")
            m = re.search(r'([A-Z][A-Za-z0-9_]+Steps)\.java$', source)
            if m:
                delegate_class = f"stepdefinitions.{m.group(1)}"
        if not delegate_class or not delegate_method:
            continue

        keyword = detect_keyword(action.get("tags") or [])

        aliases = action.get("aliases") or {}
        for lang, arr in aliases.items():
            for alias in arr or []:
                params = extract_params(alias)
                by_cat[top_cat].append(
                    JavaBinding(
                        action_id=aid,
                        keyword=keyword,
                        alias=alias,
                        lang=lang,
                        delegate_class=delegate_class,
                        delegate_method=delegate_method,
                        params=params,
                    )
                )

    return by_cat


def render_class(top_cat: str, bindings: List[JavaBinding]) -> str:
    """Tek bir üretilen Java class'ı oluştur."""
    class_name = f"Generated{to_pascal_case(top_cat)}Steps"

    # Delegate class'ları topla (her biri bir field olacak)
    delegate_classes = sorted({b.delegate_class for b in bindings})

    lines: List[str] = []
    lines.append("/*")
    lines.append(" * AUTO-GENERATED — DO NOT EDIT")
    lines.append(" * Üretildi: packages/dsl/scripts/generate_java_steps.py")
    lines.append(" * Kaynak: packages/dsl/catalog/*.yaml")
    lines.append(" */")
    lines.append("package stepdefinitions.generated;")
    lines.append("")
    lines.append("import io.cucumber.java.en.Given;")
    lines.append("import io.cucumber.java.en.When;")
    lines.append("import io.cucumber.java.en.Then;")
    lines.append("")
    for dc in delegate_classes:
        lines.append(f"import {dc};")
    lines.append("")
    lines.append(f"public class {class_name} {{")
    lines.append("")
    # Delegate field'lar
    for dc in delegate_classes:
        simple = dc.rsplit(".", 1)[-1]
        field_name = simple[0].lower() + simple[1:]
        lines.append(f"    private final {simple} {field_name} = new {simple}();")
    lines.append("")

    # Her binding için metod
    used_method_names: set[str] = set()
    for i, b in enumerate(bindings):
        simple_class = b.delegate_class.rsplit(".", 1)[-1]
        field_name = simple_class[0].lower() + simple_class[1:]

        base = f"{b.delegate_method}_{b.lang}"
        method_name = base
        suffix = 0
        while method_name in used_method_names:
            suffix += 1
            method_name = f"{base}_{suffix}"
        used_method_names.add(method_name)

        param_decl = ", ".join(f"{p[1]} {p[0]}" for p in b.params)
        param_pass = ", ".join(p[0] for p in b.params)

        lines.append("    /** " + b.action_id + f" [{b.lang}] */")
        lines.append(f'    @{b.keyword}("{to_java_string_literal(b.alias)}")')
        lines.append(f"    public void {method_name}({param_decl}) {{")
        lines.append(f"        {field_name}.{b.delegate_method}({param_pass});")
        lines.append("    }")
        lines.append("")

    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", help="Sadece bu üst kategori için üret (ui/api/...)")
    ap.add_argument("--dry-run", action="store_true", help="Dosya yazma, sadece özet")
    ap.add_argument("--out", type=Path, default=JAVA_OUT_DIR, help="Çıktı dizini")
    args = ap.parse_args()

    actions = load_actions()
    print(f"Katalog: {len(actions)} action okundu")

    by_cat = build_bindings(actions, args.category)
    total = sum(len(v) for v in by_cat.values())
    print(f"Java-backed: {total} alias, {len(by_cat)} kategori")

    if not by_cat:
        print("Üretilecek bir şey yok.")
        return 0

    if args.dry_run:
        for cat, arr in sorted(by_cat.items()):
            print(f"  {cat}: {len(arr)} alias")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    for cat, bindings in sorted(by_cat.items()):
        code = render_class(cat, bindings)
        out_path = args.out / f"Generated{to_pascal_case(cat)}Steps.java"
        out_path.write_text(code, encoding="utf-8")
        print(f"  [OK] {out_path.relative_to(ROOT)} ({len(bindings)} alias)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
