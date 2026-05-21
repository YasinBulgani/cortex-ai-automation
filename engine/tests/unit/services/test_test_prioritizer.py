"""Test Prioritizer unit tests."""

import pytest

from services.test_prioritizer import TestPrioritizer, ScoredTest, PrioritizationResult

@pytest.fixture
def prioritizer(tmp_path):
    history_file = tmp_path / "test-history.json"
    dep_file = tmp_path / "test-dep-map.json"
    history_file.write_text('{"login": [{"status": "passed", "duration_seconds": 10, "code_changed_days_ago": 2}, {"status": "failed", "duration_seconds": 12, "code_changed_days_ago": 1}]}')
    dep_file.write_text('{"login": ["e2e/login.spec.ts", "e2e/pages/login.page.ts"]}')
    return TestPrioritizer(test_history_path=str(history_file), dependency_map_path=str(dep_file))

class TestPrioritization:
    def test_prioritize_with_diff(self, prioritizer):
        result = prioritizer.prioritize(git_diff="e2e/login.spec.ts\nbackend/app/auth.py", time_budget_seconds=600)
        assert isinstance(result, PrioritizationResult)
        assert result.total_tests > 0

    def test_prioritize_empty_diff(self, prioritizer):
        result = prioritizer.prioritize(git_diff="", time_budget_seconds=300)
        assert isinstance(result, PrioritizationResult)

    def test_to_dict(self, prioritizer):
        result = prioritizer.prioritize(git_diff="", time_budget_seconds=300)
        d = result.to_dict()
        assert "total_tests" in d
        assert "selected_count" in d

    def test_time_budget_respected(self, prioritizer):
        result = prioritizer.prioritize(git_diff="e2e/login.spec.ts", time_budget_seconds=5)
        total_time = sum(prioritizer._estimate_test_time(t.test_id) for t in result.selected_tests)
        assert total_time <= 5 or len(result.selected_tests) <= 1

class TestRiskScoring:
    def test_score_range(self, prioritizer):
        test = {"id": "login", "file": "e2e/login.spec.ts", "type": "e2e"}
        score, factors = prioritizer._calculate_risk_score(test, ["e2e/login.spec.ts"])
        assert 0 <= score <= 1
        assert "dependency" in factors
        assert "failure_rate" in factors
        assert "recency" in factors

    def test_unknown_test_gets_default_score(self, prioritizer):
        test = {"id": "unknown_test", "file": "e2e/unknown.spec.ts", "type": "e2e"}
        score, factors = prioritizer._calculate_risk_score(test, [])
        assert factors["failure_rate"] == 0.5
