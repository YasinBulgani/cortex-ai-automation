"""Unit tests for app.domains.ai.quality_metrics — pure helper functions.

Tests are fully self-contained: no DB, no HTTP.
Covers: _empty_metrics (structure), _generate_recommendations
        (all trigger conditions).
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.quality_metrics import (
        _empty_metrics,
        _generate_recommendations,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="quality_metrics import failed")


# ---------------------------------------------------------------------------
# _empty_metrics
# ---------------------------------------------------------------------------

class TestEmptyMetrics:
    def test_returns_dict(self):
        result = _empty_metrics(30)
        assert isinstance(result, dict)

    def test_has_period_key(self):
        result = _empty_metrics(30)
        assert "period" in result
        assert result["period"]["days"] == 30

    def test_has_overview_key(self):
        result = _empty_metrics(30)
        assert "overview" in result

    def test_overview_all_zeros(self):
        result = _empty_metrics(30)
        ov = result["overview"]
        assert ov["total_calls"] == 0
        assert ov["success_rate"] == 0

    def test_by_agent_empty_list(self):
        result = _empty_metrics(30)
        assert result["by_agent"] == []

    def test_by_model_empty_list(self):
        result = _empty_metrics(30)
        assert result["by_model"] == []

    def test_daily_trend_empty_list(self):
        result = _empty_metrics(30)
        assert result["daily_trend"] == []

    def test_recommendations_has_message(self):
        result = _empty_metrics(30)
        recs = result["recommendations"]
        assert isinstance(recs, list)
        assert len(recs) >= 1

    def test_has_expected_keys(self):
        result = _empty_metrics(7)
        for key in ("period", "overview", "by_agent", "by_model",
                    "daily_trend", "error_distribution", "recommendations"):
            assert key in result


# ---------------------------------------------------------------------------
# _generate_recommendations
# ---------------------------------------------------------------------------

def _overview(**overrides):
    base = {
        "total_calls": 100,
        "success_rate": 95.0,
        "json_parse_rate": 92.0,
        "avg_latency_ms": 2000,
        "unique_agents": 3,
        "unique_models": 2,
        "total_cost_usd": 0.0,
        "avg_cost_usd": 0.0,
    }
    base.update(overrides)
    return base


class TestGenerateRecommendations:
    def test_returns_list(self):
        recs = _generate_recommendations(_overview(), [], [], {})
        assert isinstance(recs, list)

    def test_no_issues_returns_all_normal_message(self):
        recs = _generate_recommendations(_overview(), [], [], {})
        combined = " ".join(recs).lower()
        assert "normal" in combined or "izleme" in combined

    def test_low_json_parse_rate_triggers_recommendation(self):
        recs = _generate_recommendations(_overview(json_parse_rate=85), [], [], {})
        combined = " ".join(recs)
        assert "json" in combined.lower() or "JSON" in combined

    def test_high_latency_triggers_recommendation(self):
        recs = _generate_recommendations(_overview(avg_latency_ms=6000), [], [], {})
        combined = " ".join(recs).lower()
        assert "latency" in combined or "ms" in combined

    def test_cost_summary_when_nonzero(self):
        recs = _generate_recommendations(_overview(total_cost_usd=5.0, avg_cost_usd=0.05), [], [], {})
        combined = " ".join(recs)
        assert "$" in combined or "maliyet" in combined.lower()

    def test_timeout_errors_trigger_recommendation(self):
        recs = _generate_recommendations(_overview(), [], [], {"timeout": 5})
        combined = " ".join(recs).lower()
        assert "timeout" in combined

    def test_connection_errors_trigger_recommendation(self):
        recs = _generate_recommendations(_overview(), [], [], {"connection_error": 3})
        combined = " ".join(recs).lower()
        assert "bağlantı" in combined or "ollama" in combined

    def test_low_success_rate_agent_triggers_recommendation(self):
        by_agent = [{"agent": "BadAgent", "success_rate": 80.0, "calls": 10, "json_parse_rate": 92}]
        recs = _generate_recommendations(_overview(), by_agent, [], {})
        combined = " ".join(recs)
        assert "BadAgent" in combined

    def test_high_p95_latency_model_triggers_recommendation(self):
        by_model = [{"model": "slow-model", "p95_latency_ms": 15000, "calls": 10}]
        recs = _generate_recommendations(_overview(), [], by_model, {})
        combined = " ".join(recs)
        assert "slow-model" in combined

    def test_regression_alert_in_recommendations(self):
        alerts = [{"severity": "P1", "message": "Başarı orani dustu"}]
        recs = _generate_recommendations(_overview(), [], [], {}, regression_alerts=alerts)
        combined = " ".join(recs)
        assert "P1" in combined and "Başarı orani dustu" in combined

    def test_agent_with_few_calls_not_flagged(self):
        # calls < 5 → not flagged even if success_rate is low
        by_agent = [{"agent": "RareAgent", "success_rate": 50.0, "calls": 2, "json_parse_rate": 90}]
        recs = _generate_recommendations(_overview(), by_agent, [], {})
        combined = " ".join(recs)
        assert "RareAgent" not in combined

    def test_agent_low_json_parse_rate_flagged(self):
        by_agent = [{"agent": "JsonAgent", "success_rate": 95.0, "calls": 10, "json_parse_rate": 70.0}]
        recs = _generate_recommendations(_overview(), by_agent, [], {})
        combined = " ".join(recs)
        assert "JsonAgent" in combined
