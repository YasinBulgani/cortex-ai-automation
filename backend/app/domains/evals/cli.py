"""Eval CLI — CI ve dev'de çalıştırma için giriş noktası.

Kullanım:
    python -m app.domains.evals.cli                      # tüm suite'ler
    python -m app.domains.evals.cli --suite dsl_retrieval
    python -m app.domains.evals.cli --suites-dir /path
    python -m app.domains.evals.cli --json report.json
    python -m app.domains.evals.cli --no-report          # rapor yazma
    python -m app.domains.evals.cli --strict-skip        # skip'i fail say

Exit kodları:
    0 : tüm suite'ler pass (skipped dahil, --strict-skip yoksa)
    1 : en az bir suite fail
    2 : argüman/konfig hatası
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .loader import default_suites_dir, load_suites
from .reporting import write_reports
from .runner import run_suite
from .schemas import SuiteResult

logger = logging.getLogger("evals.cli")


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m app.domains.evals.cli")
    p.add_argument(
        "--suite",
        action="append",
        default=None,
        help="Sadece bu suite'i koş (birden çok kez verilebilir). Yoksa hepsi.",
    )
    p.add_argument(
        "--suites-dir",
        default=None,
        help=f"Suite YAML dizini (varsayılan: {default_suites_dir()})",
    )
    p.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Case başına paralellik (varsayılan: ENV EVAL_MAX_WORKERS veya 4)",
    )
    p.add_argument(
        "--json",
        default=None,
        help="JSON özeti (overall) bu dosyaya yaz.",
    )
    p.add_argument(
        "--no-report",
        action="store_true",
        help="reports/evals/ altına JSON+HTML yazmayı atla.",
    )
    p.add_argument(
        "--strict-skip",
        action="store_true",
        help="Adapter available değilse suite'i FAIL say (varsayılan: pass/skip).",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="DEBUG loglama"
    )
    return p.parse_args(argv)


def _overall_summary(results: List[SuiteResult], strict_skip: bool) -> dict:
    suites = []
    fail_count = 0
    for r in results:
        skipped = r.aggregate.get("skipped") == 1.0
        effective_pass = r.passed and not (strict_skip and skipped)
        if not effective_pass:
            fail_count += 1
        suites.append(
            {
                "name": r.suite_name,
                "adapter": r.adapter_name,
                "passed": effective_pass,
                "skipped": skipped,
                "cases_total": len(r.cases),
                "cases_passed": r.count_passed(),
                "threshold_failures": r.threshold_failures,
                "aggregate": r.aggregate,
                "total_latency_ms": r.total_latency_ms,
            }
        )
    return {
        "overall_passed": fail_count == 0,
        "suites": suites,
        "total_suites": len(results),
        "failed_suites": fail_count,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    suites_dir = Path(args.suites_dir) if args.suites_dir else None
    try:
        suites = load_suites(directory=suites_dir, names=args.suite)
    except ValueError as exc:
        logger.error("Suite yüklenemedi: %s", exc)
        return 2

    if not suites:
        requested = f"(filtered={args.suite}) " if args.suite else ""
        logger.warning("Koşulacak suite yok %s— exit 0", requested)
        return 0

    results = [run_suite(s, max_workers=args.max_workers) for s in suites]

    # Özet stdout'a
    summary = _overall_summary(results, strict_skip=args.strict_skip)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if not args.no_report:
        report_dir = write_reports(results)
        logger.info("Rapor yazıldı: %s", report_dir)

    if args.json:
        try:
            Path(args.json).write_text(
                json.dumps(summary, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("--json çıktı yazılamadı: %s", exc)

    return 0 if summary["overall_passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
