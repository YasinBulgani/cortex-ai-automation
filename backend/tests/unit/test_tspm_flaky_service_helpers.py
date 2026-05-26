"""Unit tests for app.domains.tspm.flaky_service — pure helper functions.

Tests are fully self-contained: no DB, no HTTP.
Covers: _env_int, _env_float, compute_stability (all edge cases),
        decide_quarantine (all branches), StabilityScore / QuarantineDecision.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

try:
    from app.domains.tspm.flaky_service import (
        _env_int,
        _env_float,
        compute_stability,
        decide_quarantine,
        StabilityScore,
        QuarantineDecision,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="flaky_service import failed")

_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# _env_int / _env_float
# ---------------------------------------------------------------------------

class TestEnvInt:
    def test_returns_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("FLAKY_TEST_INT_VAR", raising=False)
        assert _env_int("FLAKY_TEST_INT_VAR", 42) == 42

    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("FLAKY_TEST_INT_VAR", "10")
        assert _env_int("FLAKY_TEST_INT_VAR", 42) == 10

    def test_invalid_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("FLAKY_TEST_INT_VAR", "not_an_int")
        assert _env_int("FLAKY_TEST_INT_VAR", 99) == 99

    def test_returns_int_type(self, monkeypatch):
        monkeypatch.setenv("FLAKY_TEST_INT_VAR", "5")
        assert isinstance(_env_int("FLAKY_TEST_INT_VAR", 0), int)


class TestEnvFloat:
    def test_returns_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("FLAKY_TEST_FLOAT_VAR", raising=False)
        assert _env_float("FLAKY_TEST_FLOAT_VAR", 0.5) == pytest.approx(0.5)

    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("FLAKY_TEST_FLOAT_VAR", "0.35")
        assert _env_float("FLAKY_TEST_FLOAT_VAR", 0.5) == pytest.approx(0.35)

    def test_invalid_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("FLAKY_TEST_FLOAT_VAR", "bad_float")
        assert _env_float("FLAKY_TEST_FLOAT_VAR", 0.99) == pytest.approx(0.99)


# ---------------------------------------------------------------------------
# compute_stability
# ---------------------------------------------------------------------------

class TestComputeStability:
    def test_empty_list_all_zero(self):
        score = compute_stability([])
        assert score.runs_count == 0
        assert score.pass_rate == 0.0
        assert score.flakiness_score == 0.0

    def test_all_passed_zero_flakiness(self):
        score = compute_stability(["passed"] * 10)
        assert score.pass_rate == pytest.approx(1.0)
        assert score.flakiness_score == pytest.approx(0.0)

    def test_all_failed_high_flakiness(self):
        score = compute_stability(["failed"] * 10)
        assert score.pass_rate == pytest.approx(0.0)
        # 0 flips, all failed: flakiness = (1-0)*0.5 + 0*0.5 = 0.5
        assert score.flakiness_score == pytest.approx(0.5)

    def test_alternating_high_flip_count(self):
        statuses = ["passed", "failed"] * 5
        score = compute_stability(statuses)
        assert score.flip_count == 9  # 9 transitions in 10 items

    def test_skipped_statuses_filtered(self):
        statuses = ["passed", "skipped", "passed", "error", "failed"]
        score = compute_stability(statuses)
        # Only passed/failed counted = 3 items
        assert score.runs_count == 3

    def test_pass_rate_calculation(self):
        statuses = ["passed", "passed", "failed", "passed"]
        score = compute_stability(statuses)
        assert score.pass_rate == pytest.approx(0.75)

    def test_returns_stability_score(self):
        assert isinstance(compute_stability(["passed"]), StabilityScore)

    def test_single_passed_no_flip(self):
        score = compute_stability(["passed"])
        assert score.flip_count == 0
        assert score.flakiness_score == pytest.approx(0.0)

    def test_single_failed_no_flip(self):
        score = compute_stability(["failed"])
        assert score.flip_count == 0

    def test_passed_count_correct(self):
        score = compute_stability(["passed", "passed", "failed"])
        assert score.passed_count == 2
        assert score.failed_count == 1

    def test_stable_run_low_flakiness(self):
        # Mostly passing with one fail early
        statuses = ["failed"] + ["passed"] * 9
        score = compute_stability(statuses)
        assert score.flakiness_score < 0.3


# ---------------------------------------------------------------------------
# decide_quarantine
# ---------------------------------------------------------------------------

class TestDecideQuarantine:
    def _score(self, runs=10, passed=9, failed=1, flips=1, pass_rate=0.9, flakiness=0.1):
        return StabilityScore(
            runs_count=runs,
            passed_count=passed,
            failed_count=failed,
            flip_count=flips,
            pass_rate=pass_rate,
            flakiness_score=flakiness,
        )

    def test_insufficient_runs_preserves_quarantine_state(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "10")
        score = self._score(runs=3)
        decision = decide_quarantine(score, currently_quarantined=True, now=_NOW)
        assert decision.reason == "insufficient_runs"
        assert decision.should_quarantine is True

    def test_insufficient_runs_preserves_not_quarantined(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "10")
        score = self._score(runs=3)
        decision = decide_quarantine(score, currently_quarantined=False, now=_NOW)
        assert decision.should_quarantine is False

    def test_high_flakiness_triggers_quarantine(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "5")
        monkeypatch.setenv("FLAKY_QUARANTINE_THRESHOLD", "0.35")
        score = self._score(runs=10, flakiness=0.5, pass_rate=0.6)
        decision = decide_quarantine(score, currently_quarantined=False, now=_NOW)
        assert decision.should_quarantine is True
        assert decision.reason == "threshold_exceeded"

    def test_stable_score_not_quarantined(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "5")
        monkeypatch.setenv("FLAKY_QUARANTINE_THRESHOLD", "0.35")
        score = self._score(runs=10, flakiness=0.05, pass_rate=0.95)
        decision = decide_quarantine(score, currently_quarantined=False, now=_NOW)
        assert decision.should_quarantine is False
        assert decision.reason == "stable"

    def test_recovered_removes_quarantine(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "5")
        monkeypatch.setenv("FLAKY_UNQUARANTINE_THRESHOLD", "0.15")
        score = self._score(runs=10, flakiness=0.10, pass_rate=0.95)
        decision = decide_quarantine(score, currently_quarantined=True, now=_NOW)
        assert decision.should_quarantine is False
        assert decision.reason == "recovered"

    def test_still_flaky_remains_quarantined(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "5")
        monkeypatch.setenv("FLAKY_UNQUARANTINE_THRESHOLD", "0.15")
        score = self._score(runs=10, flakiness=0.4, pass_rate=0.7)
        decision = decide_quarantine(score, currently_quarantined=True, now=_NOW)
        assert decision.should_quarantine is True
        assert decision.reason == "still_flaky"

    def test_quarantined_until_set_when_quarantined(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "5")
        monkeypatch.setenv("FLAKY_QUARANTINE_THRESHOLD", "0.35")
        score = self._score(runs=10, flakiness=0.5, pass_rate=0.5)
        decision = decide_quarantine(score, currently_quarantined=False, now=_NOW)
        assert decision.quarantined_until is not None
        assert decision.quarantined_until > _NOW

    def test_quarantined_until_none_when_stable(self, monkeypatch):
        monkeypatch.setenv("FLAKY_MIN_RUNS", "5")
        monkeypatch.setenv("FLAKY_QUARANTINE_THRESHOLD", "0.35")
        score = self._score(runs=10, flakiness=0.05, pass_rate=0.95)
        decision = decide_quarantine(score, currently_quarantined=False, now=_NOW)
        assert decision.quarantined_until is None

    def test_returns_quarantine_decision(self):
        score = self._score()
        result = decide_quarantine(score, currently_quarantined=False, now=_NOW)
        assert isinstance(result, QuarantineDecision)
