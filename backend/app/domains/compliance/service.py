"""Public service facade for the compliance domain.

Exposes KVKK/BDDK/ISO-27001 control mappings and provides the interface for
programmatic compliance checks and report generation.
"""
from __future__ import annotations

import logging

from app.domains.compliance.mapping import (
    Control,
    Mapping,
    controls_for_feature,
    get_control,
    list_controls,
    mappings_for,
    unmapped_controls,
)

logger = logging.getLogger(__name__)

__all__ = [
    # mapping
    "Control",
    "Mapping",
    "get_control",
    "list_controls",
    "mappings_for",
    "controls_for_feature",
    "unmapped_controls",
    # stubs
    "run_compliance_check",
    "get_compliance_report",
]


def run_compliance_check(
    project_id: str,
    *,
    standards: list[str] | None = None,
) -> dict:
    """Run automated compliance checks against the registered control mappings.

    Args:
        project_id: The project to check.
        standards: Optional list of standards to limit the check to
            (e.g. ``["KVKK", "BDDK"]``). Defaults to all standards.

    Returns:
        A dict with ``passed``, ``failed``, and per-control details.

    Raises:
        NotImplementedError: Until automated check execution is implemented.
    """
    raise NotImplementedError(
        "TODO: implement run_compliance_check — see docs/planning/END_USER_GAPS_PLAN.md"
    )


def get_compliance_report(project_id: str, *, format: str = "json") -> dict:
    """Generate a compliance evidence report for a project.

    Args:
        project_id: The project to report on.
        format: Output format — ``"json"`` or ``"html"``.

    Returns:
        A dict with report metadata and the rendered report content.

    Raises:
        NotImplementedError: Until report generation is implemented.
    """
    raise NotImplementedError(
        "TODO: implement get_compliance_report — see docs/planning/END_USER_GAPS_PLAN.md"
    )
