"""
ResultCollector — Test execution sonuçlarını toplar ve saklar.

Her çalıştırma için:
  - Test sonuçları (pass/fail/skip/flaky)
  - Süre bilgileri
  - Hata detayları
  - DOM snapshot (fail durumunda)
  - Screenshot path
  - Healing uygulanma bilgisi
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TestExecutionRecord:
    test_id: str
    test_name: str
    status: str         # pass, fail, skip, flaky, healed
    duration_ms: int
    timestamp: float = 0.0
    error: str = ""
    screenshot: str = ""
    healing_category: str = ""
    tags: list[str] = field(default_factory=list)
    retry_count: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class ExecutionSummary:
    run_id: str
    timestamp: float
    total: int
    passed: int
    failed: int
    skipped: int
    flaky: int
    healed: int
    duration_ms: int
    records: list[TestExecutionRecord] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        effective = self.total - self.skipped
        if effective == 0:
            return 0.0
        return round((self.passed + self.healed) / effective * 100, 1)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "flaky": self.flaky,
            "healed": self.healed,
            "pass_rate": self.pass_rate,
            "duration_ms": self.duration_ms,
            "records": [asdict(r) for r in self.records],
        }


class ResultCollector:
    """Test sonuçlarını toplar, özetler ve kalıcı depoya yazar."""

    DB_FILE = "execution_history.json"

    def __init__(self):
        self._db_path = settings.REPORTS_DIR / self.DB_FILE
        self._current_records: list[TestExecutionRecord] = []
        self._history: list[dict] = []
        self._load()

    def record(self, record: TestExecutionRecord) -> None:
        """Tek bir test sonucunu kaydet."""
        self._current_records.append(record)

    def record_batch(self, records: list[TestExecutionRecord]) -> None:
        """Toplu kayıt."""
        self._current_records.extend(records)

    def finalize_run(self, run_id: str) -> ExecutionSummary:
        """Mevcut çalıştırmanın özetini oluştur ve kaydet."""
        records = self._current_records
        summary = ExecutionSummary(
            run_id=run_id,
            timestamp=time.time(),
            total=len(records),
            passed=sum(1 for r in records if r.status == "pass"),
            failed=sum(1 for r in records if r.status == "fail"),
            skipped=sum(1 for r in records if r.status == "skip"),
            flaky=sum(1 for r in records if r.status == "flaky"),
            healed=sum(1 for r in records if r.status == "healed"),
            duration_ms=sum(r.duration_ms for r in records),
            records=records,
        )

        self._history.append(summary.to_dict())
        self._persist()
        self._current_records = []

        logger.info(
            "Run %s finalized: %d tests, %d pass, %d fail, %d healed (%.1f%%)",
            run_id, summary.total, summary.passed, summary.failed,
            summary.healed, summary.pass_rate,
        )
        return summary

    def get_history(self, limit: int = 50) -> list[dict]:
        """Son N çalıştırma özetini döndür."""
        return self._history[-limit:]

    def get_test_history(self, test_id: str, limit: int = 20) -> list[dict]:
        """Belirli bir testin son N sonucunu döndür."""
        results = []
        for run in reversed(self._history):
            for record in run.get("records", []):
                if record.get("test_id") == test_id:
                    results.append(record)
                    if len(results) >= limit:
                        return results
        return results

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._history = []

    def _persist(self) -> None:
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._db_path, "w", encoding="utf-8") as f:
                json.dump(self._history[-200:], f, indent=2, ensure_ascii=False)
        except OSError:
            logger.warning("Execution history persist failed")
