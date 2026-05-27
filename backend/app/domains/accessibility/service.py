"""Accessibility domain service facade — UX-F3-306.

Thin facade over the core ``analyzer`` module.  The router delegates
here; callers outside the HTTP layer (tests, scripts, other domains)
can also import from this module without touching FastAPI internals.

Exposed API
-----------
analyze_violations(request) -> AnalyzeA11yResponse
    Feed a list of axe-core / Pa11y / Lighthouse violations to the AI
    gateway and receive Turkish-language remediation suggestions.

analyzer_info() -> dict
    Return the current feature-flag state and telemetry counters for
    the accessibility analyzer.
"""
from __future__ import annotations

from app.domains.accessibility.analyzer import accessibility_analyzer
from app.domains.accessibility.schemas import (
    AnalyzeA11yRequest,
    AnalyzeA11yResponse,
)


def analyze_violations(request: AnalyzeA11yRequest) -> AnalyzeA11yResponse:
    """Analyze WCAG violations and return Turkish remediation suggestions.

    Delegates to ``AccessibilityAnalyzer.analyze``.  When the feature
    flag ``AI_ACCESSIBILITY_ENABLED`` is *false* the call is a no-op
    that returns ``ok=True`` with an empty remediations list.
    """
    return accessibility_analyzer.analyze(request)


def analyzer_info() -> dict:
    """Return feature-flag state and telemetry counters.

    Intended for the ``GET /accessibility/status`` endpoint and for
    health-check dashboards that want to know whether AI remediation
    is active.
    """
    return accessibility_analyzer.info()
