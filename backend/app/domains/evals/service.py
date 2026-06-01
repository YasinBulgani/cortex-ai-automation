"""Evals domain service facade.

Thin facade over the eval sub-modules (``loader``, ``runner``,
``reporting``, ``scorers``, ``adapters``).  Callers outside the HTTP
layer — CI scripts, other domains, the job scheduler — import from
here for a stable, documented entry-point.

Exposed API
-----------
run_eval_suite(suite_name, max_workers) -> SuiteResult
    Load and run a single named eval suite.

run_all_suites(suite_names, max_workers) -> list[SuiteResult]
    Run every suite (or a named subset) and persist the reports.

get_history(limit) -> list[dict]
    Return the last *limit* run records from the report store.

get_latest() -> dict | None
    Return the most recent run record, or None if no runs exist yet.

list_suite_names() -> list[str]
    Return the names of all available eval suites.
"""
from __future__ import annotations

from typing import List, Optional

from .adapters import list_adapters
from .loader import load_suites
from .reporting import history_report, latest_report, write_reports
from .runner import run_suite
from .schemas import SuiteResult
from .scorers import list_scorers


def run_eval_suite(
    suite_name: str,
    max_workers: Optional[int] = None,
) -> SuiteResult:
    """Load and run a single named eval suite synchronously.

    Args:
        suite_name:  Exact name of the suite as declared in the suites
                     directory (case-sensitive).
        max_workers: Thread-pool size for parallel case execution.
                     ``None`` uses the runner default.

    Returns:
        ``SuiteResult`` with per-case scores, pass/fail flag, and
        aggregate metrics.

    Raises:
        ValueError: if no suite with *suite_name* exists.
    """
    suites = load_suites(names=[suite_name])
    if not suites:
        raise ValueError(f"Eval suite not found: {suite_name!r}")
    result = run_suite(suites[0], max_workers=max_workers)
    write_reports([result])
    return result


def run_all_suites(
    suite_names: Optional[List[str]] = None,
    max_workers: Optional[int] = None,
) -> List[SuiteResult]:
    """Run all suites (or a named subset) and persist the reports.

    Args:
        suite_names: Optional allow-list of suite names.  ``None`` runs
                     every registered suite.
        max_workers: Thread-pool size forwarded to each suite runner.

    Returns:
        List of ``SuiteResult`` objects, one per suite, in load order.
    """
    suites = load_suites(names=suite_names)
    results = [run_suite(s, max_workers=max_workers) for s in suites]
    write_reports(results)
    return results


def get_history(limit: int = 50) -> List[dict]:
    """Return recent run records from the report store.

    Args:
        limit: Maximum number of records to return (clamped 1–500).

    Returns:
        List of run dicts ordered newest-first.
    """
    return history_report(limit=max(1, min(limit, 500)))


def get_latest() -> Optional[dict]:
    """Return the most recent run record, or ``None`` if no runs exist."""
    return latest_report()


def list_suite_names() -> List[str]:
    """Return the names of all available eval suites."""
    return [s.name for s in load_suites()]
