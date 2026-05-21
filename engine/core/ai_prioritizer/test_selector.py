"""
IntelligentTestSelector — Risk tabanlı test suite optimizasyonu.

Akıllı seçim algoritması:
  1. Tüm testleri risk skorla
  2. Threshold üzerindeki testleri seç
  3. Smoke suite her zaman dahil
  4. Tag-bazlı filtre uygula
  5. CI/CD matrix çıktısı üret
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.ai_prioritizer.risk_scorer import RiskScorer, TestRiskProfile

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.30


@dataclass
class SelectionResult:
    selected: list[TestRiskProfile]
    skipped: list[TestRiskProfile]
    total_tests: int = 0
    selected_count: int = 0
    estimated_time_saved_pct: float = 0.0


class IntelligentTestSelector:
    """Risk tabanlı akıllı test seçici."""

    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        always_run_tags: list[str] | None = None,
        history_path: str | Path | None = None,
    ):
        self.threshold = threshold
        self.always_run_tags = always_run_tags or ["@smoke", "@critical", "@P0"]
        self.scorer = RiskScorer(history_path=history_path)

    def select(
        self,
        tests: list[dict],
        changed_files: list[str],
    ) -> SelectionResult:
        """
        Risk tabanlı test seçimi yap.

        Args:
            tests: Test listesi (her biri dict: name, tags, covers_files, vb.)
            changed_files: Değişen dosyaların listesi (git diff)

        Returns:
            SelectionResult
        """
        profiles = self.scorer.score_all(tests, changed_files)

        selected = []
        skipped = []

        for profile in profiles:
            if self._should_always_run(profile):
                selected.append(profile)
            elif profile.risk_score >= self.threshold:
                selected.append(profile)
            else:
                skipped.append(profile)

        time_saved = 0.0
        if profiles:
            time_saved = round((len(skipped) / len(profiles)) * 100, 1)

        result = SelectionResult(
            selected=selected,
            skipped=skipped,
            total_tests=len(profiles),
            selected_count=len(selected),
            estimated_time_saved_pct=time_saved,
        )

        logger.info(
            "Test selection: %d/%d selected (threshold=%.2f, saved=%.1f%%)",
            result.selected_count,
            result.total_tests,
            self.threshold,
            result.estimated_time_saved_pct,
        )

        return result

    def to_github_matrix(self, result: SelectionResult) -> str:
        """GitHub Actions matrix format çıktısı üret (include syntax)."""
        includes = [{"test": p.test_name} for p in result.selected]
        return json.dumps({"include": includes})

    def _should_always_run(self, profile: TestRiskProfile) -> bool:
        """Tag'lere göre her zaman çalışacak testleri belirle."""
        for tag in profile.tags:
            if tag in self.always_run_tags:
                return True
        return False
