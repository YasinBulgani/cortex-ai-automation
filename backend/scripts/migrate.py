"""Migration CLI.

Kullanım:
    python -m scripts.migrate --source selenium-java --file StepDefs.java
    python -m scripts.migrate --source selenium-py --dir old_steps/
    python -m scripts.migrate --source katalon --file TestCase.groovy --json
    python -m scripts.migrate --source selenium-java --file X.java --out migrated.spec.ts

Dosya verilirse stdout'a TS/Py kodu + kısa özet. ``--dir`` ile birden çok
dosyayı batch işler. ``--json`` tüm MigrationResult'ı raporlar.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from app.domains.migration.assistant import (
    SourceFramework,
    migrate_directory,
    migrate_source,
)


_FRAMEWORKS = ("selenium-java", "selenium-py", "katalon")


def _parse(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m scripts.migrate")
    p.add_argument(
        "--source",
        choices=_FRAMEWORKS,
        required=True,
        help="Kaynak framework",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="Tek dosya path'i")
    g.add_argument("--dir", help="Kök dizin (recursive)")
    p.add_argument("--out", help="Çıktı dosyası (tek file için)")
    p.add_argument("--json", action="store_true", help="JSON rapor çıktısı")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse(argv)
    framework: SourceFramework = args.source  # type: ignore[assignment]

    if args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"hata: dosya yok: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8", errors="replace")
        r = migrate_source(framework, text, source_file=str(path))
        if args.json:
            print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
        else:
            if args.out:
                Path(args.out).write_text(r.output_code, encoding="utf-8")
                print(
                    f"✓ {r.steps_migrated}/{r.steps_total} step çevrildi → {args.out}"
                )
            else:
                print(r.output_code)
            if r.unhandled:
                print(f"\n⚠ {len(r.unhandled)} adım manuel migration gerektirir:", file=sys.stderr)
                for u in r.unhandled[:10]:
                    print(f"  - {u.original[:80]}", file=sys.stderr)
        return 0 if r.steps_unhandled == 0 else 1

    # --dir
    directory = Path(args.dir)
    if not directory.is_dir():
        print(f"hata: dizin yok: {directory}", file=sys.stderr)
        return 2
    results = migrate_directory(framework, directory)
    total = sum(r.steps_total for r in results)
    ok = sum(r.steps_migrated for r in results)
    unhandled = sum(r.steps_unhandled for r in results)
    if args.json:
        print(
            json.dumps(
                {
                    "framework": framework,
                    "directory": str(directory),
                    "files": len(results),
                    "steps_total": total,
                    "steps_migrated": ok,
                    "steps_unhandled": unhandled,
                    "results": [r.to_dict() for r in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"Framework : {framework}")
        print(f"Dizin     : {directory}")
        print(f"Dosya     : {len(results)}")
        print(f"Step (toplam / çevrildi / elle) : {total} / {ok} / {unhandled}")
        rate = round(100 * ok / total, 1) if total else 0.0
        print(f"Başarı oranı : %{rate}")
        if results:
            print("\nEn çok elle-migration gereken dosyalar:")
            worst = sorted(
                results, key=lambda r: r.steps_unhandled, reverse=True
            )[:5]
            for r in worst:
                print(
                    f"  [{r.steps_unhandled}/{r.steps_total}] {r.source_file}"
                )
    return 0 if unhandled == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
