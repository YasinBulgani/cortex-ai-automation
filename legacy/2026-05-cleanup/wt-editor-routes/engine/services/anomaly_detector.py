"""
Test sonuçları ve performans metriklerinde anomaly tespiti.

Z-score tabanlı temel anomaly detection sağlar.
Flaky test, performans regresyonu ve beklenmedik davranış değişiklikleri
erken uyarı olarak bildirilir.
"""
from __future__ import annotations

import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class Anomaly:
    metric_name: str
    current_value: float
    expected_range: tuple[float, float]
    z_score: float
    severity: str  # "warning" | "critical"
    description: str

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "current_value": round(self.current_value, 2),
            "expected_range": [round(self.expected_range[0], 2), round(self.expected_range[1], 2)],
            "z_score": self.z_score,
            "severity": self.severity,
            "description": self.description,
        }


class AnomalyDetector:

    def __init__(
        self,
        history_path: str | Path = "reports/metrics-history.json",
        z_threshold_warning: float = 2.0,
        z_threshold_critical: float = 3.0,
    ):
        self._history_path = _REPO_ROOT / history_path
        self.history: list[dict] = self._load_history()
        self._merge_feedback_loop_history()
        self.z_warning = z_threshold_warning
        self.z_critical = z_threshold_critical

    def analyze_test_run(self, run_results: dict) -> list[Anomaly]:
        total = max(run_results.get("total", 1), 1)
        metrics = {
            "total_duration_seconds": run_results.get("total_duration"),
            "failure_rate": run_results.get("failed", 0) / total,
            "avg_test_duration": run_results.get("avg_duration"),
            "flaky_count": run_results.get("flaky_count", 0),
        }

        anomalies: list[Anomaly] = []
        for name, value in metrics.items():
            if value is None:
                continue
            historical = self._get_metric_history(name)
            if len(historical) < 5:
                continue
            anomaly = self._detect(name, value, historical)
            if anomaly:
                anomalies.append(anomaly)

        self._append_history(metrics)
        return anomalies

    def analyze_k6_results(self, k6_summary: dict) -> list[Anomaly]:
        anomalies: list[Anomaly] = []
        raw_metrics = k6_summary.get("metrics", {})

        perf: dict[str, float | None] = {}
        if "http_req_duration" in raw_metrics:
            vals = raw_metrics["http_req_duration"].get("values", {})
            perf["p95_response_ms"] = vals.get("p(95)")
            perf["avg_response_ms"] = vals.get("avg")
        if "http_req_failed" in raw_metrics:
            perf["error_rate"] = raw_metrics["http_req_failed"].get("values", {}).get("rate", 0)

        for name, value in perf.items():
            if value is None:
                continue
            historical = self._get_metric_history(f"k6_{name}")
            if len(historical) >= 5:
                anomaly = self._detect(f"k6_{name}", value, historical)
                if anomaly:
                    anomalies.append(anomaly)

        k6_entry = {k: v for k, v in perf.items() if v is not None}
        if k6_entry:
            self._append_history({f"k6_{k}": v for k, v in k6_entry.items()})

        return anomalies

    # ── core detection ──────────────────────────────────────────────────────

    def _detect(self, name: str, current: float, historical: list[float]) -> Anomaly | None:
        mean = statistics.mean(historical)
        stdev = statistics.stdev(historical) if len(historical) > 1 else 0.0
        if stdev == 0:
            return None

        z_score = round((current - mean) / stdev, 2)

        if abs(z_score) >= self.z_critical:
            severity = "critical"
        elif abs(z_score) >= self.z_warning:
            severity = "warning"
        else:
            return None

        lo = round(mean - 2 * stdev, 2)
        hi = round(mean + 2 * stdev, 2)
        return Anomaly(
            metric_name=name,
            current_value=current,
            expected_range=(lo, hi),
            z_score=z_score,
            severity=severity,
            description=f"{name}: {current:.2f} (beklenen: {mean:.2f} ± {2 * stdev:.2f}, z={z_score})",
        )

    # ── persistence ─────────────────────────────────────────────────────────

    def _get_metric_history(self, metric_name: str) -> list[float]:
        return [entry[metric_name] for entry in self.history if metric_name in entry][-30:]

    def _append_history(self, metrics: dict):
        entry = {"timestamp": datetime.now().isoformat(), **{k: v for k, v in metrics.items() if v is not None}}
        self.history.append(entry)
        self._save_history()

    def _merge_feedback_loop_history(self) -> None:
        """Merge execution summaries from core/feedback_loop into anomaly history."""
        try:
            from core.feedback_loop.collector import ResultCollector
            collector = ResultCollector()
            runs = collector.get_history(limit=50)
            for run in runs:
                total = max(run.get("total", 1), 1)
                entry = {
                    "timestamp": datetime.fromtimestamp(run.get("timestamp", 0)).isoformat() if run.get("timestamp") else None,
                    "total_duration_seconds": run.get("duration_ms", 0) / 1000,
                    "failure_rate": run.get("failed", 0) / total,
                    "avg_test_duration": (run.get("duration_ms", 0) / total) / 1000,
                }
                self.history.append(entry)
        except Exception as exc:
            logger.debug("Feedback loop merge for anomaly history skipped: %s", exc)

    def _load_history(self) -> list[dict]:
        if self._history_path.exists():
            try:
                return json.loads(self._history_path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not load anomaly history: %s", exc)
        return []

    def _save_history(self):
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            self._history_path.write_text(json.dumps(self.history[-200:], indent=2, ensure_ascii=False))
        except OSError as exc:
            logger.warning("Anomaly history yazılamadı: %s", exc)
