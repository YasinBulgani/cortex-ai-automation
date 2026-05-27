"""Compliance domain service facade.

Thin facade over ``mapping.py``.  The router and any non-HTTP callers
(CLI, tests, scheduled jobs) should import from here rather than
reaching into the mapping module directly.

Exposed API
-----------
list_controls(standard)       -> list[Control]
get_control(control_id)       -> Control | None
mappings_for(control_id)      -> list[Mapping]
build_evidence_pack()         -> dict
export_evidence(target)       -> Path
unmapped_controls()           -> list[Control]
controls_for_feature(feature) -> list[Control]
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from app.domains.compliance.mapping import (
    Control,
    Mapping,
    build_evidence_pack,
    controls_for_feature,
    export_evidence,
    get_control,
    list_controls,
    mappings_for,
    unmapped_controls,
)

__all__ = [
    "Control",
    "Mapping",
    "list_controls",
    "get_control",
    "mappings_for",
    "controls_for_feature",
    "unmapped_controls",
    "build_evidence_pack",
    "export_evidence",
]


def get_coverage_summary() -> Dict[str, object]:
    """Return a high-level coverage dict suitable for dashboards and CI gates.

    Convenience wrapper around ``build_evidence_pack`` that keeps the
    router lean.  Includes ``total_controls``, ``total_mappings``,
    ``unmapped`` ids, ``coverage_pct``, and ``standards``.
    """
    pack = build_evidence_pack()
    return {
        "total_controls": len(pack["controls"]),
        "total_mappings": len(pack["mappings"]),
        "unmapped": list(pack["unmapped"]),
        "coverage_pct": pack["coverage_pct"],
        "standards": pack["generated_standards"],
    }
