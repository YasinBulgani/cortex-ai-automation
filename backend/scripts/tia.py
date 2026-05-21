"""TIA CLI — CI'da çağrılır.

Kullanım:
    python -m scripts.tia                        # origin/main...HEAD
    python -m scripts.tia --base develop
    python -m scripts.tia --coverage coverage.xml --coverage coverage-e2e/lcov.info
    python -m scripts.tia --json  # tests listesi JSON

Çıktı: stdout'a newline-ayrılmış test dosyası yolu VEYA ``__RUN_ALL__``.
Exit 0 her durumda; CI stream bu satırları doğrudan pytest'e pipe edebilir.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from app.domains.cicd.tia import (
    ImpactResult,
    git_diff_names,
    is_test_file,
    map_changes_to_tests,
)


def _find_src_count(repo_root: Path) -> Optional[int]:
    # Kaba heuristic: src dizinlerinin .py/.ts/.tsx dosyaları
    count = 0
    for pat in ("*.py", "*.ts", "*.tsx", "*.js"):
        for p in repo_root.rglob(pat):
            # node_modules + .venv hariç
            parts = set(p.parts)
            if any(skip in parts for skip in ("node_modules", ".venv", "venv", ".git", "dist", "build")):
                continue
            if is_test_file(str(p)):
                continue
            count += 1
    return count if count > 0 else None


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m scripts.tia")
    p.add_argument("--repo-root", default=".", help="Repo kökü (varsayılan cwd)")
    p.add_argument("--base", default="origin/main")
    p.add_argument("--head", default="HEAD")
    p.add_argument(
        "--coverage",
        action="append",
        default=[],
        help="coverage.xml veya lcov.info (birden çok)",
    )
    p.add_argument(
        "--test-root",
        action="append",
        default=[],
        help="Test dizini (birden çok; import graph için)",
    )
    p.add_argument("--json", action="store_true", help="JSON çıktı ver")
    p.add_argument(
        "--changed",
        action="append",
        default=None,
        help="Git diff yerine explicit dosya listesi (test için)",
    )
    return p.parse_args(argv)


def _emit(result: ImpactResult, as_json: bool) -> int:
    if as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if result.run_all:
        print("__RUN_ALL__")
    else:
        for t in result.tests:
            print(t)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    changed = args.changed if args.changed is not None else git_diff_names(
        repo_root, base=args.base, head=args.head
    )
    cov_paths = [Path(c) for c in args.coverage]
    test_roots = [Path(r) for r in args.test_root] or [
        repo_root / "backend" / "tests",
        repo_root / "tests",
        repo_root / "e2e",
    ]
    total_src = _find_src_count(repo_root)
    result = map_changes_to_tests(
        repo_root=repo_root,
        changed_files=changed,
        coverage_paths=cov_paths or None,
        test_roots=[tr for tr in test_roots if tr.exists()],
        total_src_count=total_src,
    )
    return _emit(result, args.json)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
