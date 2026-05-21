"""Accessibility (a11y) AI Analyzer domain.

WCAG violation verilerini (axe-core, Pa11y, Lighthouse benzeri) alır ve
AI Gateway üzerinden Türkçe açıklama + somut fix önerisi üretir.

Mevcut pipeline:
    Frontend / Engine → axe-core taraması → violation listesi
         ↓
    Backend (BU MODÜL)
         ↓
    AI Gateway (task_type=accessibility_analysis)
         ↓
    Türkçe remediation (structured: açıklama + fix + kod örneği)
"""

from app.domains.accessibility.analyzer import (  # noqa: F401
    AccessibilityAnalyzer,
    accessibility_analyzer,
)
from app.domains.accessibility.router import router  # noqa: F401
from app.domains.accessibility.schemas import (  # noqa: F401
    A11yImpact,
    A11yRemediation,
    A11yViolation,
    AnalyzeA11yRequest,
    AnalyzeA11yResponse,
)
