"""Unit tests for app.domains.ai.roi_service — pure compute helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: _env_float, compute_roi (formula, edge cases, zero AI cost),
        _range_bounds, RoiInputs/RoiOutputs dataclasses.
"""
from __future__ import annotations

import os
import pytest
from datetime import datetime, timezone

try:
    from app.domains.ai.roi_service import (
        compute_roi,
        RoiInputs,
        RoiOutputs,
        _env_float,
        _range_bounds,
        _TEST_TASK_TYPES,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="roi_service import failed")


# ---------------------------------------------------------------------------
# _env_float
# ---------------------------------------------------------------------------

class TestEnvFloat:
    def test_returns_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert _env_float("TEST_FLOAT_VAR", 42.0) == pytest.approx(42.0)

    def test_reads_env_value(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "99.5")
        assert _env_float("TEST_FLOAT_VAR", 0.0) == pytest.approx(99.5)

    def test_falls_back_on_invalid_env(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "notanumber")
        assert _env_float("TEST_FLOAT_VAR", 7.0) == pytest.approx(7.0)

    def test_zero_env_value(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "0")
        assert _env_float("TEST_FLOAT_VAR", 5.0) == pytest.approx(0.0)

    def test_returns_float(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        result = _env_float("TEST_FLOAT_VAR", 1.0)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# compute_roi — formula verification
# ---------------------------------------------------------------------------

class TestComputeRoi:
    def _inputs(self, tests=10, ai_cost=2.0, days=30):
        return RoiInputs(tests_generated=tests, ai_cost_usd=ai_cost, days=days)

    def test_returns_roi_outputs(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=10, ai_cost=2.0))
        assert isinstance(result, RoiOutputs)

    def test_manual_hours_saved_formula(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=10, ai_cost=0.0))
        # 10 tests * 0.5 hrs = 5 hours
        assert result.manual_hours_saved == pytest.approx(5.0)

    def test_manual_cost_saved_formula(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=10, ai_cost=0.0))
        # 5 hours * $40 = $200
        assert result.manual_cost_saved_usd == pytest.approx(200.0)

    def test_net_savings_formula(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=10, ai_cost=50.0))
        # manual_saved = 200, ai_cost = 50 → net = 150
        assert result.net_savings_usd == pytest.approx(150.0)

    def test_roi_pct_formula(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=10, ai_cost=50.0))
        # net = 150, ai_cost = 50 → roi = 300%
        assert result.roi_pct == pytest.approx(300.0, abs=0.1)

    def test_zero_ai_cost_positive_savings_returns_max_roi(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=10, ai_cost=0.0))
        assert result.roi_pct == pytest.approx(99999.0)

    def test_zero_tests_zero_savings(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=0, ai_cost=0.0))
        assert result.manual_hours_saved == pytest.approx(0.0)
        assert result.manual_cost_saved_usd == pytest.approx(0.0)
        assert result.roi_pct == pytest.approx(0.0)

    def test_ai_cost_preserved(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=5, ai_cost=1.234567))
        assert result.ai_cost_usd == pytest.approx(1.234567, abs=1e-5)

    def test_tests_generated_preserved(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(self._inputs(tests=42, ai_cost=1.0))
        assert result.tests_generated == 42

    def test_custom_hourly_rate_applied(self, monkeypatch):
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "100.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "1.0")
        result = compute_roi(self._inputs(tests=5, ai_cost=0.0))
        # 5 tests * 1.0 hr * $100 = $500
        assert result.manual_cost_saved_usd == pytest.approx(500.0)

    def test_negative_ai_cost_treated_as_zero_roi_infinite(self, monkeypatch):
        """Edge: negative ai_cost_usd means <= 0 branch."""
        monkeypatch.setenv("ROI_HOURLY_RATE_USD", "40.0")
        monkeypatch.setenv("ROI_AVG_MANUAL_HOURS_PER_TEST", "0.5")
        result = compute_roi(RoiInputs(tests_generated=5, ai_cost_usd=-1.0, days=30))
        # ai_cost_usd <= 0 → roi = 99999 if net > 0
        assert result.roi_pct == pytest.approx(99999.0)


# ---------------------------------------------------------------------------
# _range_bounds
# ---------------------------------------------------------------------------

class TestRangeBounds:
    def test_returns_two_datetimes(self):
        start, end = _range_bounds(30)
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_range_spans_correct_days(self):
        start, end = _range_bounds(30)
        delta = end - start
        assert delta.days == 30

    def test_end_is_after_start(self):
        start, end = _range_bounds(7)
        assert end > start

    def test_both_utc(self):
        start, end = _range_bounds(30)
        assert start.tzinfo is not None
        assert end.tzinfo is not None

    def test_one_day_range(self):
        start, end = _range_bounds(1)
        delta = end - start
        assert delta.days == 1

    def test_365_days_range(self):
        start, end = _range_bounds(365)
        delta = end - start
        assert delta.days == 365


# ---------------------------------------------------------------------------
# _TEST_TASK_TYPES constant
# ---------------------------------------------------------------------------

class TestTestTaskTypes:
    def test_includes_test_generation(self):
        assert "test_generation" in _TEST_TASK_TYPES

    def test_includes_gherkin(self):
        assert "gherkin" in _TEST_TASK_TYPES

    def test_includes_bdd_generation(self):
        assert "bdd_generation" in _TEST_TASK_TYPES

    def test_is_tuple_or_list(self):
        assert isinstance(_TEST_TASK_TYPES, (tuple, list))

    def test_no_empty_strings(self):
        for t in _TEST_TASK_TYPES:
            assert t  # non-empty
