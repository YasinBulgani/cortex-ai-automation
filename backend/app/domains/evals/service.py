"""Public service facade for the evals domain.

Wraps the runner, loader, and reporting modules so that callers outside this
domain only need to import from here.
"""
from __future__ import annotations

import logging

from app.domains.evals.loader import (
    default_suites_dir,
    load_suite_file,
    load_suites,
)
from app.domains.evals.reporting import (
    history_report,
    history_summary,
    latest_report,
    write_reports,
)
from app.domains.evals.runner import run_suite

logger = logging.getLogger(__name__)

__all__ = [
    # loader
    "load_suite_file",
    "load_suites",
    "default_suites_dir",
    # runner
    "run_suite",
    # reporting
    "write_reports",
    "latest_report",
    "history_report",
    "history_summary",
    # stubs
    "run_eval_suite",
    "get_eval_results",
]


def run_eval_suite(suite_name: str, *, project_id: str) -> dict:
    """Run a named eval suite by looking it up in the suite registry.

    This higher-level wrapper resolves the suite by name, executes it via
    the runner, and persists the results — unlike the low-level
    :func:`run_suite` which requires a pre-loaded ``Suite`` object.

    Args:
        suite_name: Name of the YAML suite to execute.
        project_id: The owning project's identifier.

    Returns:
        A dict with ``run_id``, ``passed``, and aggregate metrics.

    Raises:
        NotImplementedError: Until suite-name resolution + persistence is done.
    """
    raise NotImplementedError(
        "TODO: implement run_eval_suite — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def get_eval_results(run_id: str) -> dict:
    """Return the full results for a completed eval run.

    Args:
        run_id: Identifier returned by :func:`run_eval_suite`.

    Returns:
        Serialised :class:`~app.domains.evals.schemas.SuiteResult`.

    Raises:
        NotImplementedError: Until result persistence is implemented.
    """
    raise NotImplementedError(
        "TODO: implement get_eval_results — see docs/planning/END_USER_GAPS_PLAN.md"
    )
