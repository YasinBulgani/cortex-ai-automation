"""Public service facade for the automation domain.

Wraps the AutomationBrainService and related helpers from brain.py so that
callers outside this domain import from one stable surface.
"""
from __future__ import annotations

import logging

from app.domains.automation.brain import (
    ADAPTERS,
    AutomationAdapter,
    AutomationBrainService,
    AutomationRunStore,
    SqlAlchemyAutomationRunStore,
)

logger = logging.getLogger(__name__)

__all__ = [
    "ADAPTERS",
    "AutomationAdapter",
    "AutomationBrainService",
    "AutomationRunStore",
    "SqlAlchemyAutomationRunStore",
    "run_suite",
    "get_suite_status",
    "list_suites",
]


def run_suite(suite_id: str, *, project_id: str, triggered_by: str | None = None) -> dict:
    """Trigger a named automation suite run and return a run handle.

    Args:
        suite_id: Identifier of the suite to run.
        project_id: The owning project's identifier.
        triggered_by: User or system that initiated the run.

    Returns:
        A dict with ``run_id`` and ``status``.

    Raises:
        NotImplementedError: Until suite orchestration is implemented.
    """
    raise NotImplementedError(
        "TODO: implement run_suite — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def get_suite_status(run_id: str) -> dict:
    """Return the live status of an automation suite run.

    Raises:
        NotImplementedError: Until suite status tracking is implemented.
    """
    raise NotImplementedError(
        "TODO: implement get_suite_status — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def list_suites(project_id: str) -> list[dict]:
    """Return all automation suites registered for a project.

    Raises:
        NotImplementedError: Until the suite registry is implemented.
    """
    raise NotImplementedError(
        "TODO: implement list_suites — see docs/planning/END_USER_GAPS_PLAN.md"
    )
