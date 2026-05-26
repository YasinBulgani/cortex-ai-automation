"""Unit tests for app.domains.ai.router_learning — pure scoring helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: _compute_composite, RoutingStats.to_dict, and the scoring formula.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.router_learning import (
        _compute_composite,
        RoutingStats,
        _W_SUCCESS,
        _W_JUDGE,
        _W_COST,
        _W_LATENCY,
        _COST_NORMALIZER,
        _LATENCY_NORMALIZER,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="router_learning import failed")


def _stats(**kwargs) -> RoutingStats:
    defaults = dict(
        task_type="chat",
        model="gpt-4o-mini",
        success_rate=0.9,
        judge_avg=None,
        avg_cost_usd=0.001,
        avg_latency_ms=500,
    )
    defaults.update(kwargs)
    return RoutingStats(**defaults)


# ---------------------------------------------------------------------------
# _compute_composite — formula verification
# ---------------------------------------------------------------------------

class TestComputeComposite:
    def test_returns_float(self):
        s = _stats()
        result = _compute_composite(s)
        assert isinstance(result, float)

    def test_perfect_model_high_score(self):
        """Perfect success, best judge, zero cost and latency → high score."""
        s = _stats(
            success_rate=1.0,
            judge_avg=10.0,
            avg_cost_usd=0.0,
            avg_latency_ms=0,
        )
        result = _compute_composite(s)
        # W_SUCCESS + W_JUDGE * 1.0 = 0.40 + 0.30 = 0.70
        assert result == pytest.approx(0.70, abs=0.01)

    def test_expensive_model_penalized(self):
        """Higher cost reduces score."""
        cheap = _stats(avg_cost_usd=0.0, success_rate=0.9, avg_latency_ms=0)
        expensive = _stats(avg_cost_usd=0.01, success_rate=0.9, avg_latency_ms=0)  # = normalizer
        assert _compute_composite(cheap) > _compute_composite(expensive)

    def test_slow_model_penalized(self):
        """Higher latency reduces score."""
        fast = _stats(avg_latency_ms=0, success_rate=0.9, avg_cost_usd=0.0)
        slow = _stats(avg_latency_ms=5000, success_rate=0.9, avg_cost_usd=0.0)  # = normalizer
        assert _compute_composite(fast) > _compute_composite(slow)

    def test_better_success_rate_higher_score(self):
        poor = _stats(success_rate=0.5, judge_avg=None, avg_cost_usd=0.0, avg_latency_ms=0)
        good = _stats(success_rate=0.9, judge_avg=None, avg_cost_usd=0.0, avg_latency_ms=0)
        assert _compute_composite(good) > _compute_composite(poor)

    def test_judge_avg_none_uses_success_rate(self):
        """When judge_avg is None, judge_part = success_rate."""
        s = _stats(success_rate=0.8, judge_avg=None, avg_cost_usd=0.0, avg_latency_ms=0)
        result = _compute_composite(s)
        # W_SUCCESS * 0.8 + W_JUDGE * 0.8 = (0.40 + 0.30) * 0.8
        expected = 0.8 * (_W_SUCCESS + _W_JUDGE)
        assert result == pytest.approx(expected, abs=0.01)

    def test_judge_avg_provided_uses_scaled_judge(self):
        """When judge_avg is given, judge_part = judge_avg/10."""
        s = _stats(success_rate=0.8, judge_avg=8.0, avg_cost_usd=0.0, avg_latency_ms=0)
        result = _compute_composite(s)
        expected = 0.8 * _W_SUCCESS + 0.8 * _W_JUDGE
        assert result == pytest.approx(expected, abs=0.01)

    def test_cost_capped_at_1_0(self):
        """Cost penalty is capped at 1.0 regardless of extreme cost."""
        cheap = _stats(avg_cost_usd=_COST_NORMALIZER * 2, success_rate=1.0, avg_latency_ms=0)
        expens = _stats(avg_cost_usd=_COST_NORMALIZER * 100, success_rate=1.0, avg_latency_ms=0)
        # Both should have same penalty since min(1.0, ...) = 1.0
        assert _compute_composite(cheap) == pytest.approx(_compute_composite(expens), abs=0.001)

    def test_latency_capped_at_1_0(self):
        """Latency penalty is capped at 1.0."""
        fast = _stats(avg_latency_ms=int(_LATENCY_NORMALIZER * 2), success_rate=1.0, avg_cost_usd=0.0)
        slow = _stats(avg_latency_ms=int(_LATENCY_NORMALIZER * 10), success_rate=1.0, avg_cost_usd=0.0)
        assert _compute_composite(fast) == pytest.approx(_compute_composite(slow), abs=0.001)

    def test_weights_sum_to_one(self):
        """All weights should sum to exactly 1.0."""
        assert _W_SUCCESS + _W_JUDGE + _W_COST + _W_LATENCY == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# RoutingStats.to_dict
# ---------------------------------------------------------------------------

class TestRoutingStatsToDict:
    def test_returns_dict(self):
        s = _stats()
        assert isinstance(s.to_dict(), dict)

    def test_has_task_type(self):
        s = _stats(task_type="security_audit")
        d = s.to_dict()
        assert d["task_type"] == "security_audit"

    def test_has_model(self):
        s = _stats(model="gpt-4o")
        d = s.to_dict()
        assert d["model"] == "gpt-4o"

    def test_success_rate_rounded(self):
        s = _stats(success_rate=0.912345)
        d = s.to_dict()
        assert d["success_rate"] == pytest.approx(0.912, abs=0.001)

    def test_judge_avg_none_when_not_set(self):
        s = _stats(judge_avg=None)
        d = s.to_dict()
        assert d["judge_avg"] is None

    def test_judge_avg_rounded_when_set(self):
        s = _stats(judge_avg=7.654321)
        d = s.to_dict()
        assert d["judge_avg"] == pytest.approx(7.65, abs=0.01)

    def test_cost_rounded(self):
        s = _stats(avg_cost_usd=0.001234567)
        d = s.to_dict()
        assert d["avg_cost_usd"] == pytest.approx(0.001235, abs=0.0001)

    def test_composite_rounded(self):
        s = _stats()
        s.composite_score = 0.712345
        d = s.to_dict()
        assert d["composite_score"] == pytest.approx(0.7123, abs=0.001)
