"""
SuiteOptimizer — Feedback loop verilerine dayanarak test suite'ini optimize eder.

Optimizasyon aksiyonları:
  - Flaky testleri quarantine'e al
  - Test sırasını optimize et (hızlı testler önce)
  - Gereksiz testleri devre dışı bırak
  - Coverage boşluklarını raporla
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class OptimizationAction:
    action_type: str     # quarantine, reorder, disable, alert
    test_id: str
    reason: str
    auto_applied: bool = False


@dataclass
class OptimizationReport:
    actions: list[OptimizationAction] = field(default_factory=list)
    estimated_time_saved_ms: int = 0
    quality_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action_count": len(self.actions),
            "estimated_time_saved_ms": self.estimated_time_saved_ms,
            "quality_score": self.quality_score,
            "actions": [
                {
                    "type": a.action_type,
                    "test_id": a.test_id,
                    "reason": a.reason,
                    "auto_applied": a.auto_applied,
                }
                for a in self.actions
            ],
        }


class SuiteOptimizer:
    """Test suite optimizasyon motoru."""

    QUARANTINE_FILE = "quarantined_tests.json"

    def __init__(self):
        self._quarantine_path = settings.REPORTS_DIR / self.QUARANTINE_FILE
        self._quarantined: list[str] = []
        self._load_quarantine()

    def optimize(
        self, history: list[dict], insights: list[dict] | None = None
    ) -> OptimizationReport:
        """Geçmiş veriler ve insight'lardan optimizasyon önerileri üret."""
        report = OptimizationReport()

        flaky_actions = self._handle_flaky(history)
        report.actions.extend(flaky_actions)

        reorder_actions = self._suggest_reorder(history)
        report.actions.extend(reorder_actions)

        report.quality_score = self._calculate_quality_score(history)

        for action in report.actions:
            if action.action_type == "quarantine" and action.auto_applied:
                report.estimated_time_saved_ms += self._avg_duration(
                    action.test_id, history
                )

        return report

    def quarantine_test(self, test_id: str, reason: str) -> None:
        """Testi quarantine'e al."""
        if test_id not in self._quarantined:
            self._quarantined.append(test_id)
            self._persist_quarantine()
            logger.info("Test quarantined: %s (%s)", test_id, reason)

    def unquarantine_test(self, test_id: str) -> None:
        """Testi quarantine'den çıkar."""
        if test_id in self._quarantined:
            self._quarantined.remove(test_id)
            self._persist_quarantine()

    def get_quarantined(self) -> list[str]:
        return list(self._quarantined)

    def is_quarantined(self, test_id: str) -> bool:
        return test_id in self._quarantined

    def _handle_flaky(self, history: list[dict]) -> list[OptimizationAction]:
        """Flaky testler için quarantine önerisi."""
        actions = []
        test_stats: dict[str, dict] = {}

        for run in history[-15:]:
            for record in run.get("records", []):
                tid = record.get("test_id", "")
                status = record.get("status", "")
                if not tid:
                    continue
                if tid not in test_stats:
                    test_stats[tid] = {"pass": 0, "fail": 0, "total": 0}
                test_stats[tid]["total"] += 1
                if status in ("pass", "healed"):
                    test_stats[tid]["pass"] += 1
                elif status == "fail":
                    test_stats[tid]["fail"] += 1

        for tid, stats in test_stats.items():
            total = stats["total"]
            if total < 3:
                continue
            flaky_rate = min(stats["pass"], stats["fail"]) / total
            if flaky_rate > 0.3:
                actions.append(OptimizationAction(
                    action_type="quarantine",
                    test_id=tid,
                    reason=f"Flaky rate: {flaky_rate:.0%} (son {total} çalıştırma)",
                    auto_applied=flaky_rate > 0.4,
                ))
                if flaky_rate > 0.4:
                    self.quarantine_test(tid, "Auto-quarantine: high flaky rate")

        return actions

    def _suggest_reorder(self, history: list[dict]) -> list[OptimizationAction]:
        """Yavaş testleri sona taşıma önerisi."""
        actions = []
        test_durations: dict[str, list[int]] = {}

        for run in history[-10:]:
            for record in run.get("records", []):
                tid = record.get("test_id", "")
                dur = record.get("duration_ms", 0)
                if tid and dur > 0:
                    test_durations.setdefault(tid, []).append(dur)

        for tid, durations in test_durations.items():
            avg = sum(durations) / len(durations)
            if avg > 30000:
                actions.append(OptimizationAction(
                    action_type="reorder",
                    test_id=tid,
                    reason=f"Ortalama süre: {avg/1000:.1f}s — suite sonuna taşınabilir",
                ))

        return actions

    def _calculate_quality_score(self, history: list[dict]) -> float:
        """Son çalıştırmalardan genel kalite skoru hesapla (0-100)."""
        if not history:
            return 0.0
        recent = history[-5:]
        total_pass = 0
        total_tests = 0
        for run in recent:
            total_pass += run.get("passed", 0) + run.get("healed", 0)
            total_tests += run.get("total", 0) - run.get("skipped", 0)
        if total_tests == 0:
            return 0.0
        return round((total_pass / total_tests) * 100, 1)

    def _avg_duration(self, test_id: str, history: list[dict]) -> int:
        durations = []
        for run in history[-10:]:
            for record in run.get("records", []):
                if record.get("test_id") == test_id:
                    durations.append(record.get("duration_ms", 0))
        return int(sum(durations) / len(durations)) if durations else 0

    def _load_quarantine(self) -> None:
        if self._quarantine_path.exists():
            try:
                with open(self._quarantine_path, "r", encoding="utf-8") as f:
                    self._quarantined = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._quarantined = []

    def _persist_quarantine(self) -> None:
        try:
            self._quarantine_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._quarantine_path, "w", encoding="utf-8") as f:
                json.dump(self._quarantined, f, indent=2)
        except OSError:
            logger.warning("Quarantine persist failed")
