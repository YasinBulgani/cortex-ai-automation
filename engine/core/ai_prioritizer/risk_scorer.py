"""
RiskScorer — Her test için risk skoru hesaplar.

Faktörler:
  - Değişen dosya ↔ test eşleşmesi (ağırlık: %30)
  - Geçmiş failure oranı (ağırlık: %25)
  - İş kritikliği (ağırlık: %20)
  - Son değişiklik tarihi (ağırlık: %10)
  - Karmaşıklık skoru (ağırlık: %10)
  - Dependency derinliği (ağırlık: %5)
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

WEIGHTS = {
    "file_impact": 0.30,
    "failure_rate": 0.25,
    "criticality": 0.20,
    "recency": 0.10,
    "complexity": 0.10,
    "dependency": 0.05,
}


@dataclass
class TestRiskProfile:
    test_id: str
    test_name: str
    risk_score: float = 0.0
    file_impact_score: float = 0.0
    failure_rate_score: float = 0.0
    criticality_score: float = 0.0
    recency_score: float = 0.0
    complexity_score: float = 0.0
    dependency_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    covers_files: list[str] = field(default_factory=list)


class RiskScorer:
    """Test risk skoru hesaplayıcı."""

    def __init__(self, history_path: str | Path | None = None):
        repo_root = settings.BASE_DIR.parent
        self.history_path = Path(history_path) if history_path else repo_root / "reports" / "test-history.json"
        self._history: dict = {}
        self._load_history()

    def score(
        self,
        test: dict,
        changed_files: list[str],
    ) -> TestRiskProfile:
        """Tek bir test için risk profili hesapla."""
        profile = TestRiskProfile(
            test_id=test.get("id", test.get("name", "")),
            test_name=test.get("name", ""),
            tags=test.get("tags", []),
            covers_files=test.get("covers_files", []),
        )

        profile.file_impact_score = self._calc_file_impact(
            test.get("covers_files", []), changed_files
        )
        profile.failure_rate_score = self._calc_failure_rate(profile.test_id)
        profile.criticality_score = self._calc_criticality(test)
        profile.recency_score = self._calc_recency(profile.test_id)
        profile.complexity_score = self._calc_complexity(test)
        profile.dependency_score = self._calc_dependency(test)

        profile.risk_score = round(
            profile.file_impact_score * WEIGHTS["file_impact"]
            + profile.failure_rate_score * WEIGHTS["failure_rate"]
            + profile.criticality_score * WEIGHTS["criticality"]
            + profile.recency_score * WEIGHTS["recency"]
            + profile.complexity_score * WEIGHTS["complexity"]
            + profile.dependency_score * WEIGHTS["dependency"],
            4,
        )

        return profile

    def score_all(
        self, tests: list[dict], changed_files: list[str]
    ) -> list[TestRiskProfile]:
        """Tüm testleri skorla ve sırala."""
        profiles = [self.score(t, changed_files) for t in tests]
        profiles.sort(key=lambda p: p.risk_score, reverse=True)
        return profiles

    def _calc_file_impact(
        self, covers: list[str], changed: list[str]
    ) -> float:
        if not covers or not changed:
            return 0.3
        overlap = set(covers) & set(changed)
        if overlap:
            return min(1.0, len(overlap) / len(covers) + 0.5)
        partial = 0.0
        for c in covers:
            for ch in changed:
                if _share_directory(c, ch):
                    partial = max(partial, 0.4)
        return partial

    def _calc_failure_rate(self, test_id: str) -> float:
        history = self._history.get(test_id, {})
        total = history.get("total_runs", 0)
        fails = history.get("failures", 0)
        if total == 0:
            return 0.5
        return min(1.0, fails / total)

    def _calc_criticality(self, test: dict) -> float:
        tags = test.get("tags", [])
        if any(t in tags for t in ["@critical", "@P0", "@smoke"]):
            return 1.0
        if any(t in tags for t in ["@P1", "@regression"]):
            return 0.7
        if any(t in tags for t in ["@P2"]):
            return 0.4
        return test.get("business_criticality", 0.5)

    def _calc_recency(self, test_id: str) -> float:
        history = self._history.get(test_id, {})
        last_change = history.get("last_modified_ts", 0)
        if not last_change:
            return 0.5
        days_ago = (time.time() - last_change) / 86400
        if days_ago < 7:
            return 0.9
        elif days_ago < 30:
            return 0.6
        return 0.3

    def _calc_complexity(self, test: dict) -> float:
        steps = test.get("step_count", 5)
        if steps > 20:
            return 1.0
        elif steps > 10:
            return 0.7
        return 0.4

    def _calc_dependency(self, test: dict) -> float:
        deps = len(test.get("dependencies", []))
        if deps > 5:
            return 1.0
        elif deps > 2:
            return 0.6
        return 0.3

    def record_result(self, test_id: str, passed: bool) -> None:
        """Test sonucunu geçmişe kaydet."""
        if test_id not in self._history:
            self._history[test_id] = {"total_runs": 0, "failures": 0}
        self._history[test_id]["total_runs"] += 1
        if not passed:
            self._history[test_id]["failures"] += 1
        self._history[test_id]["last_run_ts"] = time.time()
        self._history[test_id]["last_modified_ts"] = time.time()
        self._persist_history()

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
                json.dump(self._history, f, indent=2)
        except OSError:
            logger.warning("History persist failed")


def _share_directory(path_a: str, path_b: str) -> bool:
    """İki dosyanın aynı dizinde olup olmadığını kontrol et."""
    parts_a = Path(path_a).parts[:-1]
    parts_b = Path(path_b).parts[:-1]
    return len(parts_a) > 0 and parts_a == parts_b
