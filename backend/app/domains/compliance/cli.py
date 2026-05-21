"""Compliance CLI — evidence pack export + coverage raporu.

Kullanım:
    python -m app.domains.compliance.cli --standard KVKK
    python -m app.domains.compliance.cli --export reports/compliance/pack.json
    python -m app.domains.compliance.cli --coverage

Exit 0 her durumda; ``--fail-on-gap`` verilirse unmapped kontrol varsa 1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from .mapping import (
    build_evidence_pack,
    export_evidence,
    list_controls,
    mappings_for,
    unmapped_controls,
)


def _parse(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m app.domains.compliance.cli")
    p.add_argument("--standard", default=None, help="KVKK|BDDK|ISO27001|SOC2")
    p.add_argument("--export", default=None, help="Evidence pack JSON çıktı path'i")
    p.add_argument(
        "--coverage",
        action="store_true",
        help="Coverage + unmapped gap raporu",
    )
    p.add_argument(
        "--fail-on-gap",
        action="store_true",
        help="Unmapped kontrol varsa exit 1",
    )
    p.add_argument("--json", action="store_true", help="Listeleme JSON formatında")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse(argv)

    if args.export:
        path = export_evidence(Path(args.export))
        print(f"Evidence pack yazıldı: {path}")
        return 0

    controls = list_controls(args.standard)
    unmapped = unmapped_controls()
    if args.standard:
        unmapped = [c for c in unmapped if c.standard.lower() == args.standard.lower()]

    if args.coverage:
        pack = build_evidence_pack()
        if args.json:
            print(json.dumps(pack, ensure_ascii=False, indent=2))
        else:
            print(f"Kontrol sayısı     : {len(pack['controls'])}")
            print(f"Mapping sayısı     : {len(pack['mappings'])}")
            print(f"Unmapped kontrol   : {len(pack['unmapped'])}")
            print(f"Coverage           : %{pack['coverage_pct']}")
            if unmapped:
                print("\nUnmapped:")
                for c in unmapped:
                    print(f"  - [{c.id}] ({c.standard}) {c.title}")
        return 1 if (args.fail_on_gap and unmapped) else 0

    # Default: kontrol listesi
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "id": c.id,
                        "standard": c.standard,
                        "article": c.article,
                        "title": c.title,
                        "mappings": [m.feature_name for m in mappings_for(c.id)],
                    }
                    for c in controls
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for c in controls:
            mappings = mappings_for(c.id)
            feat = ", ".join(m.feature_name for m in mappings) if mappings else "—"
            print(f"[{c.id}] {c.standard} {c.article} — {c.title}")
            print(f"   Feature: {feat}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
