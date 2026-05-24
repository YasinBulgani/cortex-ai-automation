"""Public service facade for the accessibility domain.

Single entry point for other domains that need accessibility analysis.
Direct imports of internal modules (analyzer, schemas) should be avoided
outside this module.
"""
from __future__ import annotations

import logging

from app.domains.accessibility.analyzer import (
    AccessibilityAnalyzer,
    accessibility_analyzer,
)
from app.domains.accessibility.schemas import (
    AnalyzeA11yRequest,
    AnalyzeA11yResponse,
)

logger = logging.getLogger(__name__)

__all__ = [
    "AccessibilityAnalyzer",
    "accessibility_analyzer",
    "AnalyzeA11yRequest",
    "AnalyzeA11yResponse",
    "run_accessibility_scan",
]


def run_accessibility_scan(url: str, project_id: str) -> dict:
    """Trigger a full accessibility scan for a URL and persist results.

    Args:
        url: The page URL to scan.
        project_id: The owning project's identifier.

    Returns:
        A dict with scan findings keyed by WCAG criterion.

    Raises:
        NotImplementedError: Until the crawler + persistence layer is wired up.
    """
    raise NotImplementedError(
        "TODO: implement run_accessibility_scan — see docs/planning/END_USER_GAPS_PLAN.md"
    )
