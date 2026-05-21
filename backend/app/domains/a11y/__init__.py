"""A11y (accessibility) — axe-core rapor parse + skor."""
from .service import (
    A11yReport,
    AggregateSummary,
    Violation,
    aggregate_reports,
    compute_score,
    parse_axe_report,
)

__all__ = [
    "A11yReport",
    "AggregateSummary",
    "Violation",
    "aggregate_reports",
    "compute_score",
    "parse_axe_report",
]
