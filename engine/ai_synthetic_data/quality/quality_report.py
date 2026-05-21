"""
Sentetik veri kalite raporu üretici.

İstatistiksel sadakat, korelasyon koruma ve FK bütünlüğü kontrollerini
birleştirerek kapsamlı bir kalite raporu oluşturur.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .statistical_fidelity import StatisticalFidelity


@dataclass
class QualityReport:
    timestamp: str
    original_row_count: int
    synthetic_row_count: int
    overall_score: float
    fidelity_scores: list[dict] = field(default_factory=list)
    fk_integrity: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class QualityReporter:
    """Sentetik veri kalite raporu oluşturur."""

    def __init__(self):
        self.fidelity = StatisticalFidelity()

    def generate_report(
        self,
        original: list[dict],
        synthetic: list[dict],
        fk_checks: dict | None = None,
    ) -> QualityReport:
        scores = self.fidelity.compare_distributions(original, synthetic)
        overall = sum(s.score for s in scores) / max(len(scores), 1)
        warnings: list[str] = []
        for s in scores:
            if s.score < 0.7:
                warnings.append(f"Düşük sadakat: {s.column} ({s.metric}) = {s.score:.2f}")

        fk_result = fk_checks or {}

        return QualityReport(
            timestamp=datetime.now().isoformat(),
            original_row_count=len(original),
            synthetic_row_count=len(synthetic),
            overall_score=round(overall, 3),
            fidelity_scores=[s.to_dict() for s in scores],
            fk_integrity=fk_result,
            warnings=warnings,
        )

    @staticmethod
    def save_report(report: QualityReport, output_path: str | Path = "reports/syndata-quality.json"):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": report.timestamp,
            "original_row_count": report.original_row_count,
            "synthetic_row_count": report.synthetic_row_count,
            "overall_score": report.overall_score,
            "fidelity_scores": report.fidelity_scores,
            "fk_integrity": report.fk_integrity,
            "warnings": report.warnings,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    @staticmethod
    def check_fk_integrity(
        parent_records: list[dict],
        child_records: list[dict],
        parent_key: str,
        child_fk: str,
    ) -> dict:
        """FK bütünlüğünü kontrol eder."""
        parent_ids = {str(r[parent_key]) for r in parent_records if parent_key in r}
        child_fks = [str(r[child_fk]) for r in child_records if child_fk in r]
        orphans = [fk for fk in child_fks if fk not in parent_ids]
        return {
            "parent_key": parent_key,
            "child_fk": child_fk,
            "parent_count": len(parent_ids),
            "child_count": len(child_fks),
            "orphan_count": len(orphans),
            "integrity_pct": round((1 - len(orphans) / max(len(child_fks), 1)) * 100, 1),
        }
