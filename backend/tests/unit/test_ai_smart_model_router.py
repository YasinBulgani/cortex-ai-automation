"""Unit tests for app.domains.ai.smart_model_router — pure routing helpers.

Tests are fully self-contained: no DB, no HTTP, no LLM calls.
Covers: Tier enum, _base_routing decision matrix, _apply_global_mode,
        should_fallback / record_circuit_failure / record_circuit_success,
        _next_tier, ModelRecommendation dataclass.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

try:
    from app.domains.ai.smart_model_router import (
        Tier,
        ModelRecommendation,
        _base_routing,
        _apply_global_mode,
        _next_tier,
        should_fallback,
        record_circuit_failure,
        record_circuit_success,
        _CIRCUIT_THRESHOLD,
        _circuit_state,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="smart_model_router import failed")


@pytest.fixture(autouse=True)
def _clear_circuit_state():
    """Reset circuit breaker state before and after each test."""
    _circuit_state.clear()
    yield
    _circuit_state.clear()


@pytest.fixture(autouse=True)
def _balanced_mode(monkeypatch):
    """Default to 'balanced' routing mode so _apply_global_mode is a no-op."""
    import app.domains.ai.smart_model_router as mod
    monkeypatch.setattr(mod.settings, "ai_routing_mode", "balanced", raising=False)
    yield


# ---------------------------------------------------------------------------
# Tier enum
# ---------------------------------------------------------------------------

class TestTier:
    def test_tier_values(self):
        assert Tier.MINI.value == "mini"
        assert Tier.MID.value == "mid"
        assert Tier.PREMIUM.value == "premium"
        assert Tier.LOCAL.value == "local"

    def test_tier_is_str(self):
        for t in Tier:
            assert isinstance(t, str)


# ---------------------------------------------------------------------------
# _base_routing — decision matrix
# ---------------------------------------------------------------------------

class TestBaseRouting:
    def _route(self, task_type="chat", complexity="medium", endpoint_count=1,
               has_financial=False, has_pii=False, risk_level="medium"):
        return _base_routing(
            task_type=task_type,
            complexity=complexity,
            endpoint_count=endpoint_count,
            has_financial=has_financial,
            has_pii=has_pii,
            risk_level=risk_level,
        )

    # security_audit
    def test_security_audit_critical_is_premium(self):
        r = self._route(task_type="security_audit", risk_level="critical")
        assert r.tier is Tier.PREMIUM
        assert r.temperature == pytest.approx(0.10)

    def test_security_audit_medium_is_premium(self):
        r = self._route(task_type="security_audit", risk_level="medium")
        assert r.tier is Tier.PREMIUM
        assert r.temperature == pytest.approx(0.15)

    # test_generation
    def test_test_generation_financial_is_premium(self):
        r = self._route(task_type="test_generation", has_financial=True)
        assert r.tier is Tier.PREMIUM

    def test_test_generation_pii_is_premium(self):
        r = self._route(task_type="test_generation", has_pii=True)
        assert r.tier is Tier.PREMIUM

    def test_test_generation_high_risk_is_premium(self):
        r = self._route(task_type="test_generation", risk_level="high")
        assert r.tier is Tier.PREMIUM

    def test_test_generation_low_complexity_is_mini(self):
        r = self._route(task_type="test_generation", complexity="low", risk_level="low")
        assert r.tier is Tier.MINI

    def test_test_generation_medium_is_mid(self):
        r = self._route(task_type="test_generation", complexity="medium", risk_level="medium")
        assert r.tier is Tier.MID

    # chain_builder
    def test_chain_builder_is_premium(self):
        r = self._route(task_type="chain_builder")
        assert r.tier is Tier.PREMIUM

    # quality_judge
    def test_quality_judge_is_premium(self):
        r = self._route(task_type="quality_judge")
        assert r.tier is Tier.PREMIUM
        assert r.temperature == pytest.approx(0.10)

    # spec_analysis
    def test_spec_analysis_few_endpoints_is_mini(self):
        r = self._route(task_type="spec_analysis", endpoint_count=3)
        assert r.tier is Tier.MINI

    def test_spec_analysis_many_endpoints_is_mid(self):
        r = self._route(task_type="spec_analysis", endpoint_count=6)
        assert r.tier is Tier.MID

    def test_spec_analysis_financial_is_mid(self):
        r = self._route(task_type="spec_analysis", has_financial=True, endpoint_count=1)
        assert r.tier is Tier.MID

    # code_generation
    def test_code_generation_is_mid(self):
        r = self._route(task_type="code_generation")
        assert r.tier is Tier.MID

    # default / chat
    def test_chat_is_mini(self):
        r = self._route(task_type="chat")
        assert r.tier is Tier.MINI

    def test_unknown_task_is_mini(self):
        r = self._route(task_type="unknown_type_xyz")
        assert r.tier is Tier.MINI

    # result attributes
    def test_result_has_reason(self):
        r = self._route(task_type="chat")
        assert isinstance(r.reason, str)
        assert len(r.reason) > 0

    def test_result_has_max_tokens(self):
        r = self._route(task_type="chat")
        assert r.max_tokens > 0

    def test_result_has_temperature(self):
        r = self._route(task_type="chat")
        assert 0.0 <= r.temperature <= 1.0


# ---------------------------------------------------------------------------
# _apply_global_mode
# ---------------------------------------------------------------------------

class TestApplyGlobalMode:
    def _make_result(self, tier, temperature=0.25, max_tokens=4096, reason="test"):
        from app.domains.ai.smart_model_router import _RoutingResult
        return _RoutingResult(tier=tier, temperature=temperature, max_tokens=max_tokens, reason=reason)

    def test_balanced_mode_no_change(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", "balanced")
        r = self._make_result(Tier.PREMIUM)
        out = _apply_global_mode(r, "security_audit")
        assert out.tier is Tier.PREMIUM

    def test_cost_optimized_downgrades_premium_to_mid(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", "cost_optimized")
        r = self._make_result(Tier.PREMIUM)
        out = _apply_global_mode(r, "test_generation")
        assert out.tier is Tier.MID

    def test_cost_optimized_keeps_quality_judge_premium(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", "cost_optimized")
        r = self._make_result(Tier.PREMIUM)
        out = _apply_global_mode(r, "quality_judge")
        assert out.tier is Tier.PREMIUM

    def test_quality_first_upgrades_mini_to_mid(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", "quality_first")
        r = self._make_result(Tier.MINI)
        out = _apply_global_mode(r, "chat")
        assert out.tier is Tier.MID

    def test_quality_first_upgrades_mid_to_premium(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", "quality_first")
        r = self._make_result(Tier.MID)
        out = _apply_global_mode(r, "code_generation")
        assert out.tier is Tier.PREMIUM

    def test_quality_first_premium_unchanged(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", "quality_first")
        r = self._make_result(Tier.PREMIUM)
        out = _apply_global_mode(r, "security_audit")
        assert out.tier is Tier.PREMIUM

    def test_mode_none_treated_as_balanced(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        monkeypatch.setattr(mod.settings, "ai_routing_mode", None)
        r = self._make_result(Tier.PREMIUM)
        out = _apply_global_mode(r, "chat")
        assert out.tier is Tier.PREMIUM


# ---------------------------------------------------------------------------
# _next_tier — fallback chain
# ---------------------------------------------------------------------------

class TestNextTier:
    def test_premium_falls_to_mid(self):
        assert _next_tier(Tier.PREMIUM) is Tier.MID

    def test_mid_falls_to_mini(self):
        assert _next_tier(Tier.MID) is Tier.MINI

    def test_mini_falls_to_local(self):
        assert _next_tier(Tier.MINI) is Tier.LOCAL

    def test_local_stays_local(self):
        assert _next_tier(Tier.LOCAL) is Tier.LOCAL


# ---------------------------------------------------------------------------
# Circuit breaker: record_circuit_failure / success / should_fallback
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_no_failures_no_fallback(self):
        assert should_fallback("some-model") is False

    def test_below_threshold_no_fallback(self):
        for _ in range(_CIRCUIT_THRESHOLD - 1):
            record_circuit_failure("model-a")
        assert should_fallback("model-a") is False

    def test_at_threshold_triggers_fallback(self):
        for _ in range(_CIRCUIT_THRESHOLD):
            record_circuit_failure("model-b")
        assert should_fallback("model-b") is True

    def test_success_resets_circuit(self):
        for _ in range(_CIRCUIT_THRESHOLD):
            record_circuit_failure("model-c")
        assert should_fallback("model-c") is True
        record_circuit_success("model-c")
        assert should_fallback("model-c") is False

    def test_success_on_clean_model_noop(self):
        record_circuit_success("never-failed-model")
        assert should_fallback("never-failed-model") is False

    def test_failure_count_accumulates(self):
        record_circuit_failure("model-d")
        record_circuit_failure("model-d")
        count, _ = _circuit_state["model-d"]
        assert count == 2

    def test_circuit_reset_after_window(self, monkeypatch):
        import app.domains.ai.smart_model_router as mod
        import time
        for _ in range(_CIRCUIT_THRESHOLD):
            record_circuit_failure("model-e")
        # Simulate reset window expired by back-dating the last_failure
        count, _ = _circuit_state["model-e"]
        _circuit_state["model-e"] = (count, time.time() - mod._CIRCUIT_RESET_SECS - 1)
        assert should_fallback("model-e") is False


# ---------------------------------------------------------------------------
# ModelRecommendation dataclass
# ---------------------------------------------------------------------------

class TestModelRecommendation:
    def test_can_instantiate(self):
        rec = ModelRecommendation(
            model="gpt-4o-mini",
            tier=Tier.MINI,
            temperature=0.25,
            max_tokens=4096,
            reason="test",
        )
        assert rec.model == "gpt-4o-mini"
        assert rec.tier is Tier.MINI
        assert rec.estimated_cost_usd == 0.0

    def test_cost_field_settable(self):
        rec = ModelRecommendation(
            model="gpt-4o",
            tier=Tier.MID,
            temperature=0.2,
            max_tokens=4096,
            reason="test",
            estimated_cost_usd=0.005,
        )
        assert rec.estimated_cost_usd == pytest.approx(0.005)
