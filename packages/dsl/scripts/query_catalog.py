#!/usr/bin/env python3
"""
query_catalog.py — BGTS DSL Katalog Sorgulama / Listeleme Araci

Canonical catalog/*.yaml dosyalarindan okur ve komut satirindan kullanim
icin liste / arama / istatistik verir.

Kullanim:
    python3 packages/dsl/scripts/query_catalog.py list
    python3 packages/dsl/scripts/query_catalog.py list --category ui
    python3 packages/dsl/scripts/query_catalog.py list --lang tr
    python3 packages/dsl/scripts/query_catalog.py search tikla
    python3 packages/dsl/scripts/query_catalog.py search "I click" --lang en
    python3 packages/dsl/scripts/query_catalog.py stats
    python3 packages/dsl/scripts/query_catalog.py show click_on_element
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:
    print("PyYAML gerekli: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = ROOT / "packages" / "dsl" / "catalog"


def load_all_actions() -> list[dict]:
    actions: list[dict] = []
    for yaml_path in sorted(CATALOG_DIR.glob("*.yaml")):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for a in data.get("actions", []) or []:
            a.setdefault("_source_yaml", yaml_path.name)
            actions.append(a)
    return actions


def iter_aliases(action: dict, only_lang: str | None = None) -> Iterable[tuple[str, str]]:
    for lang, arr in (action.get("aliases") or {}).items():
        if only_lang and lang != only_lang:
            continue
        for alias in arr or []:
            yield lang, alias


def matches_filters(action: dict, category: str | None, lang: str | None, tag: str | None) -> bool:
    if category:
        cat = action.get("category", "")
        if not (cat == category or cat.startswith(category + ".")):
            return False
    if lang:
        langs = set((action.get("aliases") or {}).keys())
        if lang not in langs:
            return False
    if tag:
        tags = set(action.get("tags") or [])
        if tag not in tags:
            return False
    return True


def cmd_list(args: argparse.Namespace, actions: list[dict]) -> int:
    filtered = [a for a in actions if matches_filters(a, args.category, args.lang, args.tag)]
    filtered.sort(key=lambda a: (a.get("category", "zzz"), a.get("id", "")))

    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
        return 0

    current_cat = None
    for a in filtered:
        cat = a.get("category", "?")
        if cat != current_cat:
            print(f"\n== {cat} ==")
            current_cat = cat
        langs = "/".join(sorted((a.get("aliases") or {}).keys())) or "-"
        impls = ",".join(sorted((a.get("implementations") or {}).keys())) or "-"
        aid = a.get("id", "?")
        desc = (a.get("description") or "").replace("\n", " ")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        print(f"  [{langs:<5}] [{impls:<20}] {aid:<40} {desc}")

    print(f"\nToplam: {len(filtered)} cumlecik")
    return 0


def cmd_search(args: argparse.Namespace, actions: list[dict]) -> int:
    q = args.query
    flags = 0 if args.case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(q, flags)
    except re.error:
        pattern = re.compile(re.escape(q), flags)

    hits: list[tuple[dict, list[tuple[str, str]]]] = []
    for a in actions:
        if args.category and not matches_filters(a, args.category, None, None):
            continue
        found: list[tuple[str, str]] = []
        for lang, alias in iter_aliases(a, args.lang):
            if pattern.search(alias):
                found.append((lang, alias))
        if not found:
            if pattern.search(a.get("id", "")) or pattern.search(a.get("description") or ""):
                found.append(("meta", a.get("description") or a.get("id", "")))
        if found:
            hits.append((a, found))

    if args.json:
        payload = [
            {
                "id": a["id"],
                "category": a.get("category"),
                "matches": [{"lang": l, "alias": s} for l, s in ms],
            }
            for a, ms in hits
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    for a, ms in hits:
        print(f"\n{a['id']}  [{a.get('category', '?')}]")
        for lang, alias in ms:
            print(f"    {lang}: {alias}")

    print(f"\n{len(hits)} eslesme bulundu")
    return 0


def cmd_show(args: argparse.Namespace, actions: list[dict]) -> int:
    target = args.id
    for a in actions:
        if a.get("id") == target:
            print(yaml.dump(a, allow_unicode=True, sort_keys=False, width=100))
            return 0
    print(f"Bulunamadi: {target}", file=sys.stderr)
    return 1


def cmd_stats(args: argparse.Namespace, actions: list[dict]) -> int:
    total = len(actions)
    cats = Counter(a.get("category", "?").split(".")[0] for a in actions)
    full_cats = Counter(a.get("category", "?") for a in actions)
    tags = Counter(t for a in actions for t in (a.get("tags") or []))
    impls = Counter(l for a in actions for l in (a.get("implementations") or {}).keys())

    tr_count = sum(1 for a in actions if "tr" in (a.get("aliases") or {}))
    en_count = sum(1 for a in actions if "en" in (a.get("aliases") or {}))
    both = sum(1 for a in actions if {"tr", "en"}.issubset((a.get("aliases") or {}).keys()))

    yaml_counts: Counter = Counter()
    for a in actions:
        yaml_counts[a.get("_source_yaml", "?")] += 1

    if args.json:
        payload = {
            "total": total,
            "by_top_category": dict(cats),
            "by_full_category": dict(full_cats),
            "by_implementation": dict(impls),
            "by_tag_top20": dict(tags.most_common(20)),
            "by_source_file": dict(yaml_counts),
            "aliases": {"tr": tr_count, "en": en_count, "both": both},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"== BGTS DSL Katalog Istatistikleri ==\n")
    print(f"Toplam cumlecik: {total}\n")
    print("Ust kategori dagilimi:")
    for c, n in cats.most_common():
        print(f"   {n:>4}  {c}")
    print("\nImplementation dili:")
    for c, n in impls.most_common():
        print(f"   {n:>4}  {c}")
    print("\nAlias dili:")
    print(f"   {tr_count:>4}  TR")
    print(f"   {en_count:>4}  EN")
    print(f"   {both:>4}  TR + EN (ikisi birden)")
    print("\nKatalog dosyalari:")
    for c, n in yaml_counts.most_common():
        print(f"   {n:>4}  {c}")
    print("\nEn cok kullanilan 10 tag:")
    for c, n in tags.most_common(10):
        print(f"   {n:>4}  {c}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="BGTS DSL katalog sorgulama araci")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="Tum cumlecikleri listele")
    pl.add_argument("--category", help="Sadece bu kategori (ust-kategori de olabilir: ui)")
    pl.add_argument("--lang", help="Sadece bu alias diline sahip olanlar (tr/en)")
    pl.add_argument("--tag", help="Sadece bu tag'li olanlar")
    pl.add_argument("--json", action="store_true")

    ps = sub.add_parser("search", help="Alias veya aciklamada regex arama")
    ps.add_argument("query")
    ps.add_argument("--lang", help="Sadece bu dilde ara (tr/en)")
    ps.add_argument("--category", help="Kategoriye gore filtrele")
    ps.add_argument("--case-sensitive", action="store_true")
    ps.add_argument("--json", action="store_true")

    pshow = sub.add_parser("show", help="Tek bir cumleciği detayli goster")
    pshow.add_argument("id")

    pst = sub.add_parser("stats", help="Katalog istatistikleri")
    pst.add_argument("--json", action="store_true")

    args = ap.parse_args()

    actions = load_all_actions()
    if not actions:
        print("Katalog bos: packages/dsl/catalog/*.yaml bulunamadi", file=sys.stderr)
        return 2

    if args.cmd == "list":
        return cmd_list(args, actions)
    if args.cmd == "search":
        return cmd_search(args, actions)
    if args.cmd == "show":
        return cmd_show(args, actions)
    if args.cmd == "stats":
        return cmd_stats(args, actions)
    return 2


if __name__ == "__main__":
    sys.exit(main())
