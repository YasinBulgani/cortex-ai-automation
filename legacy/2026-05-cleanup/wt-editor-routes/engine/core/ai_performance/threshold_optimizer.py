"""
ThresholdOptimizer — k6/JMeter performans testi threshold'larını AI ile optimize eder.

Geleneksel sabit threshold'lar yerine geçmiş verilere dayalı dinamik threshold'lar hesaplar.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ThresholdRecommendation:
    metric: str
    current_value: float
    recommended_threshold: float
    percentile: str  # p50, p95, p99
    trend: str       # stable, degrading, improving
    confidence: float


@dataclass
class PerformanceBaseline:
    metric: str
    p50: float
    p95: float
    p99: float
    mean: float
    std: float
    sample_count: int


class ThresholdOptimizer:
    """Dinamik performans threshold hesaplayıcı."""

    def __init__(self, history_path: str | Path | None = None):
        self.history_path = (
            Path(history_path) if history_path
            else settings.REPORTS_DIR / "perf_history.json"
        )
        self._history: dict = {}
        self._load_history()

    def calculate_thresholds(
        self,
        current_results: dict,
        tolerance_factor: float = 1.2,
    ) -> list[ThresholdRecommendation]:
        """
        Mevcut sonuçlar + geçmiş verilerden threshold önerileri üret.

        Args:
            current_results: k6/JMeter sonuç metrikleri
            tolerance_factor: Baseline üzerine tolerans çarpanı
        """
        recommendations = []

        for metric, value in current_results.items():
            baseline = self._get_baseline(metric)
            if not baseline:
                recommendations.append(ThresholdRecommendation(
                    metric=metric,
                    current_value=value,
                    recommended_threshold=value * tolerance_factor,
                    percentile="p95",
                    trend="unknown",
                    confidence=0.5,
                ))
                continue

            trend = self._calculate_trend(metric, value)
            recommended = baseline.p95 * tolerance_factor

            recommendations.append(ThresholdRecommendation(
                metric=metric,
                current_value=value,
                recommended_threshold=round(recommended, 2),
                percentile="p95",
                trend=trend,
                confidence=min(0.95, 0.5 + (baseline.sample_count / 100)),
            ))

        return recommendations

    def record_results(self, results: dict) -> None:
        """Performans sonuçlarını geçmişe kaydet."""
        import time
        for metric, value in results.items():
            if metric not in self._history:
                self._history[metric] = []
            self._history[metric].append({
                "value": value,
                "timestamp": time.time(),
            })
            if len(self._history[metric]) > 500:
                self._history[metric] = self._history[metric][-500:]
        self._persist_history()

    def detect_regression(
        self,
        current_results: dict,
        threshold_pct: float = 20.0,
    ) -> list[dict]:
        """Performans regresyonlarını tespit et."""
        regressions = []
        for metric, value in current_results.items():
            baseline = self._get_baseline(metric)
            if not baseline:
                continue
            pct_change = ((value - baseline.mean) / baseline.mean) * 100 if baseline.mean else 0
            if pct_change > threshold_pct:
                regressions.append({
                    "metric": metric,
                    "current": value,
                    "baseline_mean": baseline.mean,
                    "pct_change": round(pct_change, 1),
                    "severity": "critical" if pct_change > 50 else "warning",
                })
        return regressions

    def _get_baseline(self, metric: str) -> Optional[PerformanceBaseline]:
        entries = self._history.get(metric, [])
        if len(entries) < 5:
            return None
        values = [e["value"] for e in entries[-50:]]
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n
        std = math.sqrt(variance) if variance > 0 else 0

        return PerformanceBaseline(
            metric=metric,
            p50=sorted_vals[int(n * 0.5)],
            p95=sorted_vals[int(n * 0.95)] if n > 20 else sorted_vals[-1],
            p99=sorted_vals[int(n * 0.99)] if n > 100 else sorted_vals[-1],
            mean=round(mean, 2),
            std=round(std, 2),
            sample_count=n,
        )

    def _calculate_trend(self, metric: str, current: float) -> str:
        entries = self._history.get(metric, [])
        if len(entries) < 10:
            return "unknown"
        recent = [e["value"] for e in entries[-10:]]
        older = [e["value"] for e in entries[-20:-10]]
        if not older:
            return "unknown"
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        pct = ((recent_avg - older_avg) / older_avg) * 100 if older_avg else 0
        if pct > 10:
            return "degrading"
        elif pct < -10:
            return "improving"
        return "stable"

    def _load_history(self) -> None:
        if self.history_path.exists():
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._history = {}

    def _persist_history(self) -> None:
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f)
        except OSError:
            logger.warning("Performance history persist failed")
