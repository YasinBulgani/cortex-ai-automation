"""
Git diff ve test geçmişine dayalı akıllı test önceliklendirme.

Kod değişikliklerinden etkilenen testleri risk skoruna göre sıralayarak
CI süresini kısaltır ve erken hata tespitini artırır.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_ENGINE_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _ENGINE_ROOT.parent


@dataclass
class ScoredTest:
    test_id: str
    file_path: str
    risk_score: float
    factors: dict[str, float] = field(default_factory=dict)


@dataclass
class PrioritizationResult:
    total_tests: int
    selected_tests: list[ScoredTest]
    skipped_tests: list[ScoredTest]
    estimated_time_saved_seconds: int

    def to_dict(self) -> dict:
        return {
            "total_tests": self.total_tests,
            "selected_count": len(self.selected_tests),
            "skipped_count": len(self.skipped_tests),
            "estimated_time_saved_seconds": self.estimated_time_saved_seconds,
            "selected": [
                {"test_id": t.test_id, "score": round(t.risk_score, 3), "factors": t.factors}
                for t in self.selected_tests
            ],
        }


class TestPrioritizer:
    # pytest "Test*" isimli class'lari otomatik collect eder; bu bir domain
    # sinifi (test prioritizer), pytest test case'i degil. `__test__ = False`
    # ile collection warning'ini kapatiyoruz.
    __test__ = False

    def __init__(
        self,
        test_history_path: str | Path = "reports/test-history.json",
        dependency_map_path: str | Path = "reports/test-dependency-map.json",
    ):
        self.test_history = self._load_json(_REPO_ROOT / test_history_path)
        self.dependency_map = self._load_json(_REPO_ROOT / dependency_map_path)
        self._merge_risk_scorer_history()

    def prioritize(
        self,
        git_diff: str | None = None,
        time_budget_seconds: int = 300,
        min_score_threshold: float = 0.1,
    ) -> PrioritizationResult:
        if git_diff is None:
            git_diff = self._get_git_diff()

        changed_files = self._parse_changed_files(git_diff)
        all_tests = self._discover_tests()

        scored: list[ScoredTest] = []
        for t in all_tests:
            score, factors = self._calculate_risk_score(t, changed_files)
            scored.append(ScoredTest(test_id=t["id"], file_path=t["file"], risk_score=score, factors=factors))

        scored.sort(key=lambda s: s.risk_score, reverse=True)

        selected: list[ScoredTest] = []
        skipped: list[ScoredTest] = []
        accumulated = 0

        for test in scored:
            est = self._estimate_test_time(test.test_id)
            if test.risk_score >= min_score_threshold and accumulated + est <= time_budget_seconds:
                selected.append(test)
                accumulated += est
            else:
                skipped.append(test)

        return PrioritizationResult(
            total_tests=len(all_tests),
            selected_tests=selected,
            skipped_tests=skipped,
            estimated_time_saved_seconds=sum(self._estimate_test_time(t.test_id) for t in skipped),
        )

    # ── risk scoring ────────────────────────────────────────────────────────

    def _calculate_risk_score(self, test: dict, changed_files: list[str]) -> tuple[float, dict[str, float]]:
        factors: dict[str, float] = {}

        deps = self.dependency_map.get(test["id"], [])
        dep_overlap = len(set(deps) & set(changed_files))
        factors["dependency"] = min(dep_overlap / max(len(deps), 1), 1.0)

        history = self.test_history.get(test["id"], [])
        if history:
            recent = history[-20:]
            failures = sum(1 for h in recent if h.get("status") == "failed")
            factors["failure_rate"] = failures / len(recent)
        else:
            factors["failure_rate"] = 0.5

        if history:
            last_change = history[-1].get("code_changed_days_ago", 30)
            factors["recency"] = max(0.0, 1 - (last_change / 30))
        else:
            factors["recency"] = 0.5

        weights = {"dependency": 0.4, "failure_rate": 0.35, "recency": 0.25}
        score = sum(factors[k] * weights[k] for k in weights)
        return score, {k: round(v, 3) for k, v in factors.items()}

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _get_git_diff() -> str:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True, text=True, timeout=10, cwd=str(_REPO_ROOT),
            )
            return result.stdout
        except Exception:
            return ""

    @staticmethod
    def _parse_changed_files(diff: str) -> list[str]:
        return [line.strip() for line in diff.strip().split("\n") if line.strip()]

    @staticmethod
    def _discover_tests() -> list[dict]:
        tests: list[dict] = []
        e2e_dir = _REPO_ROOT / "e2e"
        if e2e_dir.exists():
            for spec in e2e_dir.glob("*.spec.ts"):
                tests.append({"id": spec.stem, "file": str(spec.relative_to(_REPO_ROOT)), "type": "e2e"})

        engine_tests = _ENGINE_ROOT / "tests"
        if engine_tests.exists():
            for tf in engine_tests.rglob("test_*.py"):
                tests.append({"id": tf.stem, "file": str(tf.relative_to(_REPO_ROOT)), "type": "engine"})
        return tests

    def _estimate_test_time(self, test_id: str) -> int:
        history = self.test_history.get(test_id, [])
        if history:
            durations = [h.get("duration_seconds", 30) for h in history[-5:]]
            return max(1, int(sum(durations) / len(durations)))
        return 30

    def _merge_risk_scorer_history(self) -> None:
        """Merge data from core/ai_prioritizer/risk_scorer into test history."""
        try:
            from core.ai_prioritizer.risk_scorer import RiskScorer
            scorer = RiskScorer()
            for test_id, data in scorer._history.items():
                if test_id not in self.test_history:
                    self.test_history[test_id] = []
                total = data.get("total_runs", 0)
                failures = data.get("failures", 0)
                if total > 0:
                    for _ in range(total - failures):
                        self.test_history[test_id].append({"status": "passed", "duration_seconds": 30})
                    for _ in range(failures):
                        self.test_history[test_id].append({"status": "failed", "duration_seconds": 30})
        except Exception as exc:
            logger.debug("Risk scorer history merge skipped: %s", exc)

    @staticmethod
    def _load_json(path: Path) -> dict:
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not load JSON %s: %s", path, exc)
        return {}
