"""
Test geçmişinden flaky testleri tespit eden ve karantinaya alan servis.

Flaky skoru = 0.6 × flip_ratio + 0.4 × failure_ratio
Eşik değeri aşan testler karantinaya alınır ve CI'dan çıkarılır.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class FlakyTestInfo:
    test_id: str
    flaky_score: float
    total_runs: int
    pass_count: int
    fail_count: int
    flip_count: int
    recommendation: str  # "stable" | "monitor" | "quarantine" | "fix"
    last_failure_reason: str

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "flaky_score": self.flaky_score,
            "total_runs": self.total_runs,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "flip_count": self.flip_count,
            "recommendation": self.recommendation,
            "last_failure_reason": self.last_failure_reason,
        }


class FlakyDetector:
    QUARANTINE_THRESHOLD = 0.3
    MONITOR_THRESHOLD = 0.1

    def __init__(self, history_path: str | Path = "reports/test-history.json"):
        self._path = _REPO_ROOT / history_path
        self.history: dict[str, list[dict]] = self._load_json()
        self._merge_feedback_loop_history()

    def analyze_all(self, window: int = 20) -> list[FlakyTestInfo]:
        results: list[FlakyTestInfo] = []
        for test_id, runs in self.history.items():
            recent = runs[-window:]
            if len(recent) < 5:
                continue
            results.append(self._analyze_test(test_id, recent))
        results.sort(key=lambda t: t.flaky_score, reverse=True)
        return results

    def get_quarantine_list(self) -> list[str]:
        return [t.test_id for t in self.analyze_all() if t.recommendation == "quarantine"]

    def generate_pytest_deselect_args(self) -> list[str]:
        return [f"--deselect={tid}" for tid in self.get_quarantine_list()]

    def save_report(self, output_path: str | Path = "reports/flaky-report.json"):
        results = self.analyze_all()
        try:
            out = _REPO_ROOT / output_path
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False))
        except OSError as exc:
            logger.warning("Flaky raporu yazılamadı: %s", exc)

    # ── analysis ────────────────────────────────────────────────────────────

    def _analyze_test(self, test_id: str, runs: list[dict]) -> FlakyTestInfo:
        statuses = [r.get("status", "unknown") for r in runs]
        pass_count = statuses.count("passed")
        fail_count = statuses.count("failed")
        total = len(statuses)

        flip_count = sum(1 for i in range(1, len(statuses)) if statuses[i] != statuses[i - 1])

        flip_ratio = flip_count / max(total - 1, 1)
        failure_ratio = fail_count / max(total, 1)
        flaky_score = round(0.6 * flip_ratio + 0.4 * failure_ratio, 3)

        if flaky_score >= self.QUARANTINE_THRESHOLD:
            recommendation = "quarantine"
        elif flaky_score >= self.MONITOR_THRESHOLD:
            recommendation = "monitor"
        elif fail_count == 0:
            recommendation = "stable"
        else:
            recommendation = "fix"

        last_failure = next(
            (r.get("error", "Bilinmeyen hata") for r in reversed(runs) if r.get("status") == "failed"),
            "",
        )

        return FlakyTestInfo(
            test_id=test_id,
            flaky_score=flaky_score,
            total_runs=total,
            pass_count=pass_count,
            fail_count=fail_count,
            flip_count=flip_count,
            recommendation=recommendation,
            last_failure_reason=last_failure,
        )

    def _merge_feedback_loop_history(self) -> None:
        """Merge execution data from core/feedback_loop into the flaky history."""
        try:
            from core.feedback_loop.collector import ResultCollector
            collector = ResultCollector()
            runs = collector.get_history(limit=50)
            for run in runs:
                for record in run.get("records", []):
                    tid = record.get("test_id", "")
                    if not tid:
                        continue
                    status_map = {"pass": "passed", "fail": "failed", "healed": "passed",
                                  "skip": "skipped", "flaky": "failed"}
                    entry = {
                        "status": status_map.get(record.get("status", ""), record.get("status", "")),
                        "duration_ms": record.get("duration_ms", 0),
                        "error": record.get("error", ""),
                    }
                    self.history.setdefault(tid, []).append(entry)
        except Exception as exc:
            logger.debug("Feedback loop history merge skipped: %s", exc)

    def _load_json(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Flaky history JSON okunamadı: %s", exc)
        return {}
