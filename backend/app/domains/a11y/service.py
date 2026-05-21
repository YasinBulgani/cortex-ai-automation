"""Accessibility (A11y) — axe-core raporlarını parse et ve dashboard'a bağla.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §4 / E2.5.

Akış:
    1. Playwright test @axe-core/playwright ile rapor üretir (JSON)
    2. POST /a11y/reports endpoint'i raporu backend'e yükler
    3. Bu modül raporu parse eder, ihlalleri sever'lere ayırır
    4. Toplam skor üretir (yok → %100, max severity'e göre ağırlıklı)

Axe JSON yapısı (özetle):
    {
      "violations": [{"id": "color-contrast", "impact": "serious",
                     "help": "...", "nodes": [{"target": [...]}]}],
      "passes": [...], "incomplete": [...], "inapplicable": [...],
      "url": "https://...", "timestamp": "..."
    }

Skor:
    critical × 25, serious × 10, moderate × 3, minor × 1 puan düşürür.
    Başlangıç 100. Alt limit 0.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


Severity = Literal["critical", "serious", "moderate", "minor"]

_SEVERITY_WEIGHTS: Dict[str, int] = {
    "critical": 25,
    "serious": 10,
    "moderate": 3,
    "minor": 1,
}

_VALID_SEVERITIES = set(_SEVERITY_WEIGHTS.keys())


# ── Parsed types ─────────────────────────────────────────────────────────


class Violation(BaseModel):
    id: str
    impact: Severity = "moderate"
    help: str = ""
    help_url: Optional[str] = None
    description: str = ""
    node_count: int = 0
    sample_targets: List[str] = Field(default_factory=list)


class A11yReport(BaseModel):
    url: Optional[str] = None
    timestamp: Optional[str] = None
    score: int = Field(ge=0, le=100)
    severity_counts: Dict[str, int] = Field(default_factory=dict)
    violations: List[Violation] = Field(default_factory=list)
    passes_count: int = 0
    incomplete_count: int = 0
    inapplicable_count: int = 0
    total_nodes_with_violations: int = 0


# ── Pure parse + score ───────────────────────────────────────────────────


def parse_axe_report(raw: Dict[str, Any]) -> A11yReport:
    """axe-core JSON'u A11yReport'a çevir. Eksik alanlar graceful kabul."""
    if not isinstance(raw, dict):
        raise ValueError("axe raporu dict olmalı")

    raw_violations = raw.get("violations") or []
    if not isinstance(raw_violations, list):
        raw_violations = []

    violations: List[Violation] = []
    severity_counts: Dict[str, int] = {s: 0 for s in _VALID_SEVERITIES}
    total_nodes = 0

    for v in raw_violations:
        if not isinstance(v, dict):
            continue
        impact_raw = str(v.get("impact") or "moderate").lower().strip()
        impact: Severity = impact_raw if impact_raw in _VALID_SEVERITIES else "moderate"  # type: ignore[assignment]
        nodes = v.get("nodes") or []
        if not isinstance(nodes, list):
            nodes = []
        sample_targets: List[str] = []
        for n in nodes[:5]:
            if not isinstance(n, dict):
                continue
            target = n.get("target") or []
            if isinstance(target, list):
                sample_targets.append(
                    " ".join(str(t) for t in target) if target else ""
                )
        violations.append(
            Violation(
                id=str(v.get("id") or ""),
                impact=impact,
                help=str(v.get("help") or ""),
                help_url=v.get("helpUrl") or v.get("help_url"),
                description=str(v.get("description") or ""),
                node_count=len(nodes),
                sample_targets=sample_targets,
            )
        )
        severity_counts[impact] = severity_counts.get(impact, 0) + 1
        total_nodes += len(nodes)

    score = compute_score(severity_counts)

    return A11yReport(
        url=raw.get("url"),
        timestamp=raw.get("timestamp"),
        score=score,
        severity_counts=severity_counts,
        violations=violations,
        passes_count=_safe_len(raw.get("passes")),
        incomplete_count=_safe_len(raw.get("incomplete")),
        inapplicable_count=_safe_len(raw.get("inapplicable")),
        total_nodes_with_violations=total_nodes,
    )


def compute_score(severity_counts: Dict[str, int]) -> int:
    """100'den başla, ağırlıklı ceza düş. 0..100 arası integer."""
    score = 100
    for sev, count in severity_counts.items():
        w = _SEVERITY_WEIGHTS.get(sev, 0)
        score -= w * int(count)
    return max(0, min(100, score))


def _safe_len(v: Any) -> int:
    if isinstance(v, list):
        return len(v)
    return 0


# ── Aggregate (birden çok rapor) ────────────────────────────────────────


@dataclass
class AggregateSummary:
    total_reports: int
    avg_score: float
    worst_score: int
    severity_totals: Dict[str, int]
    most_common_violations: List[tuple[str, int]]  # (rule_id, occurrences)


def aggregate_reports(reports: List[A11yReport]) -> AggregateSummary:
    if not reports:
        return AggregateSummary(
            total_reports=0,
            avg_score=0.0,
            worst_score=0,
            severity_totals={s: 0 for s in _VALID_SEVERITIES},
            most_common_violations=[],
        )
    scores = [r.score for r in reports]
    avg = sum(scores) / len(scores)
    worst = min(scores)

    totals: Dict[str, int] = {s: 0 for s in _VALID_SEVERITIES}
    rule_hits: Dict[str, int] = {}
    for r in reports:
        for sev, c in r.severity_counts.items():
            totals[sev] = totals.get(sev, 0) + c
        for v in r.violations:
            rule_hits[v.id] = rule_hits.get(v.id, 0) + v.node_count

    top = sorted(rule_hits.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return AggregateSummary(
        total_reports=len(reports),
        avg_score=round(avg, 2),
        worst_score=worst,
        severity_totals=totals,
        most_common_violations=top,
    )
