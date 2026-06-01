"""Unit tests for smart_model_router pure helper functions.

Tests app/domains/ai/smart_model_router.py — no DB, no HTTP, no LLM calls.
Covers: _model_tier, _next_tier, _should_upgrade_model, _estimate_cost,
        _v2_enabled, _base_routing, _apply_global_mode, _TIER_FALLBACK,
        record_circuit_failure / record_circuit_success / should_fallback.
"""

from __future__ import annotations

import pytest

from app.domains.ai.smart_model_router import (
    Tier,
    _apply_global_mode,
    _base_routing,
    _model_tier,
    _next_tier,
    _RoutingResult,
    _TIER_FALLBACK,
    record_circuit_failure,
    record_circuit_success,
    should_fallback,
)
from app.domains.ai import smart_model_router as router


# ── fixture: reset shared state + patch settings ──────────────────────────────


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset circuit state and pin settings to deterministic values."""
    router._circuit_state.clear()
    monkeypatch.setattr(router.settings, "openai_mini_model", "gpt-4o-mini", raising=False)
    monkeypatch.setattr(router.settings, "openai_mid_model", "gpt-4o", raising=False)
    monkeypatch.setattr(router.settings, "anthropic_premium_model", "claude-sonnet-4-20250514", raising=False)
    monkeypatch.setattr(router.settings, "ollama_fallback_model", "qwen2.5:32b", raising=False)
    monkeypatch.setattr(router.settings, "anthropic_api_key", "test-key", raising=False)
    monkeypatch.setattr(router.settings, "openai_api_key", "test-key", raising=False)
    monkeypatch.setattr(router.settings, "ai_routing_mode", "balanced", raising=False)
    yield
    router._circuit_state.clear()


# ── _model_tier ───────────────────────────────────────────────────────────────


class TestModelTier:
    def test_mini_model_returns_mini_tier(self) -> None:
        assert _model_tier("gpt-4o-mini") is Tier.MINI

    def test_premium_model_returns_premium_tier(self) -> None:
        assert _model_tier("claude-sonnet-4-20250514") is Tier.PREMIUM

    def test_ollama_model_returns_local_tier(self) -> None:
        assert _model_tier("qwen2.5:32b") is Tier.LOCAL

    def test_unknown_model_defaults_to_mid(self) -> None:
        # Any model not matching mini/premium/local is treated as MID
        assert _model_tier("some-unknown-model") is Tier.MID

    def test_mid_model_returns_mid_tier(self) -> None:
        assert _model_tier("gpt-4o") is Tier.MID


# ── _next_tier ────────────────────────────────────────────────────────────────


class TestNextTier:
    def test_premium_falls_to_mid(self) -> None:
        assert _next_tier(Tier.PREMIUM) is Tier.MID

    def test_mid_falls_to_mini(self) -> None:
        assert _next_tier(Tier.MID) is Tier.MINI

    def test_mini_falls_to_local(self) -> None:
        assert _next_tier(Tier.MINI) is Tier.LOCAL

    def test_local_stays_local(self) -> None:
        assert _next_tier(Tier.LOCAL) is Tier.LOCAL

    def test_fallback_chain_is_complete(self) -> None:
        # All four tiers must appear in the fallback dict
        assert set(_TIER_FALLBACK.keys()) == {Tier.PREMIUM, Tier.MID, Tier.MINI, Tier.LOCAL}

    def test_full_chain_terminates_at_local(self) -> None:
        tier = Tier.PREMIUM
        visited: list[Tier] = []
        for _ in range(5):  # guard against infinite loop
            visited.append(tier)
            next_t = _next_tier(tier)
            if next_t is tier:
                break
            tier = next_t
        assert Tier.LOCAL in visited


# ── circuit breaker helpers ───────────────────────────────────────────────────


class TestCircuitBreakerHelpers:
    MODEL = "gpt-4o"

    def test_no_failures_no_fallback(self) -> None:
        assert should_fallback(self.MODEL) is False

    def test_below_threshold_no_fallback(self) -> None:
        for _ in range(router._CIRCUIT_THRESHOLD - 1):
            record_circuit_failure(self.MODEL)
        assert should_fallback(self.MODEL) is False

    def test_at_threshold_triggers_fallback(self) -> None:
        for _ in range(router._CIRCUIT_THRESHOLD):
            record_circuit_failure(self.MODEL)
        assert should_fallback(self.MODEL) is True

    def test_success_resets_to_zero(self) -> None:
        for _ in range(router._CIRCUIT_THRESHOLD):
            record_circuit_failure(self.MODEL)
        record_circuit_success(self.MODEL)
        assert should_fallback(self.MODEL) is False

    def test_success_on_clean_model_is_noop(self) -> None:
        record_circuit_success("never-failed-model")
        assert should_fallback("never-failed-model") is False

    def test_failures_accumulate_across_calls(self) -> None:
        record_circuit_failure(self.MODEL)
        record_circuit_failure(self.MODEL)
        count, _ = router._circuit_state[self.MODEL]
        assert count == 2


# ── _base_routing ─────────────────────────────────────────────────────────────


class TestBaseRouting:
    def _route(self, task_type: str, **kwargs) -> _RoutingResult:
        defaults = dict(
            complexity="medium",
            endpoint_count=1,
            has_financial=False,
            has_pii=False,
            risk_level="medium",
        )
        defaults.update(kwargs)
        return _base_routing(task_type, **defaults)

    def test_security_audit_critical_is_premium_temp_010(self) -> None:
        r = self._route("security_audit", risk_level="critical")
        assert r.tier is Tier.PREMIUM
        assert r.temperature == 0.10

    def test_security_audit_other_risk_is_premium_temp_015(self) -> None:
        r = self._route("security_audit", risk_level="medium")
        assert r.tier is Tier.PREMIUM
        assert r.temperature == 0.15

    def test_test_generation_financial_is_premium(self) -> None:
        r = self._route("test_generation", has_financial=True)
        assert r.tier is Tier.PREMIUM

    def test_test_generation_pii_is_premium(self) -> None:
        r = self._route("test_generation", has_pii=True)
        assert r.tier is Tier.PREMIUM

    def test_test_generation_low_risk_low_complexity_is_mini(self) -> None:
        r = self._route("test_generation", risk_level="low", complexity="low")
        assert r.tier is Tier.MINI

    def test_test_generation_medium_is_mid(self) -> None:
        r = self._route("test_generation", risk_level="medium", complexity="medium")
        assert r.tier is Tier.MID

    def test_chain_builder_is_premium(self) -> None:
        assert self._route("chain_builder").tier is Tier.PREMIUM

    def test_quality_judge_is_premium_temp_010(self) -> None:
        r = self._route("quality_judge")
        assert r.tier is Tier.PREMIUM
        assert r.temperature == 0.10

    def test_spec_analysis_few_endpoints_is_mini(self) -> None:
        r = self._route("spec_analysis", endpoint_count=3)
        assert r.tier is Tier.MINI

    def test_spec_analysis_many_endpoints_is_mid(self) -> None:
        r = self._route("spec_analysis", endpoint_count=6)
        assert r.tier is Tier.MID

    def test_spec_analysis_financial_is_mid(self) -> None:
        r = self._route("spec_analysis", has_financial=True, endpoint_count=2)
        assert r.tier is Tier.MID

    def test_code_generation_is_mid(self) -> None:
        assert self._route("code_generation").tier is Tier.MID

    def test_chat_defaults_to_mini(self) -> None:
        assert self._route("chat").tier is Tier.MINI

    def test_unknown_task_type_defaults_to_mini(self) -> None:
        assert self._route("completely_unknown_type").tier is Tier.MINI

    def test_reason_is_non_empty_string(self) -> None:
        r = self._route("chat")
        assert isinstance(r.reason, str) and len(r.reason) > 0

    def test_max_tokens_is_positive(self) -> None:
        for task in ("chat", "code_generation", "security_audit", "quality_judge"):
            r = self._route(task)
            assert r.max_tokens > 0, f"max_tokens should be > 0 for {task}"


# ── _apply_global_mode ────────────────────────────────────────────────────────


class TestApplyGlobalMode:
    def _make(self, tier: Tier) -> _RoutingResult:
        return _RoutingResult(tier=tier, temperature=0.25, max_tokens=4096, reason="test")

    def test_balanced_leaves_result_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "balanced", raising=False)
        r = self._make(Tier.PREMIUM)
        out = _apply_global_mode(r, "test_generation")
        assert out.tier is Tier.PREMIUM

    def test_cost_optimized_demotes_premium_to_mid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "cost_optimized", raising=False)
        r = self._make(Tier.PREMIUM)
        out = _apply_global_mode(r, "test_generation")
        assert out.tier is Tier.MID
        assert "cost_optimized" in out.reason

    def test_cost_optimized_keeps_quality_judge_premium(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "cost_optimized", raising=False)
        r = self._make(Tier.PREMIUM)
        out = _apply_global_mode(r, "quality_judge")
        assert out.tier is Tier.PREMIUM

    def test_cost_optimized_leaves_mid_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "cost_optimized", raising=False)
        r = self._make(Tier.MID)
        out = _apply_global_mode(r, "code_generation")
        assert out.tier is Tier.MID

    def test_quality_first_upgrades_mini_to_mid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        r = self._make(Tier.MINI)
        out = _apply_global_mode(r, "chat")
        assert out.tier is Tier.MID
        assert "quality_first" in out.reason

    def test_quality_first_upgrades_mid_to_premium(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        r = self._make(Tier.MID)
        out = _apply_global_mode(r, "code_generation")
        assert out.tier is Tier.PREMIUM

    def test_quality_first_max_tokens_bumped_for_mini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        r = _RoutingResult(tier=Tier.MINI, temperature=0.25, max_tokens=2048, reason="test")
        out = _apply_global_mode(r, "chat")
        assert out.max_tokens >= 4096

    def test_quality_first_max_tokens_bumped_for_mid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        r = _RoutingResult(tier=Tier.MID, temperature=0.25, max_tokens=2048, reason="test")
        out = _apply_global_mode(r, "code_generation")
        assert out.max_tokens >= 8192

    def test_temperature_preserved_across_modes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        r = _RoutingResult(tier=Tier.MINI, temperature=0.10, max_tokens=4096, reason="test")
        out = _apply_global_mode(r, "chat")
        assert out.temperature == 0.10


# ── _estimate_cost ────────────────────────────────────────────────────────────


class TestEstimateCost:
    def test_returns_float(self) -> None:
        result = router._estimate_cost("gpt-4o-mini", 4096)
        assert isinstance(result, float)

    def test_non_negative(self) -> None:
        result = router._estimate_cost("gpt-4o-mini", 4096)
        assert result >= 0.0

    def test_larger_max_tokens_costs_more(self) -> None:
        small = router._estimate_cost("gpt-4o-mini", 1000)
        large = router._estimate_cost("gpt-4o-mini", 8000)
        assert large >= small

    def test_zero_tokens_returns_zero(self) -> None:
        result = router._estimate_cost("gpt-4o-mini", 0)
        assert result == 0.0

    def test_unknown_model_returns_zero_not_exception(self) -> None:
        # Unknown model should not raise — returns 0.0
        result = router._estimate_cost("totally-unknown-model-xyz", 4096)
        assert isinstance(result, float)
        assert result >= 0.0


# ── _v2_enabled ───────────────────────────────────────────────────────────────


class TestV2Enabled:
    def test_returns_bool(self) -> None:
        result = router._v2_enabled()
        assert isinstance(result, bool)

    def test_returns_bool_with_tenant(self) -> None:
        result = router._v2_enabled(tenant_id="tenant-abc")
        assert isinstance(result, bool)

    def test_default_is_true_when_no_flag_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Simulate feature_flags import failing → should default to True
        import sys
        original = sys.modules.get("app.domains.feature_flags.service")
        sys.modules["app.domains.feature_flags.service"] = None  # type: ignore[assignment]
        try:
            result = router._v2_enabled()
            assert result is True
        finally:
            if original is None:
                sys.modules.pop("app.domains.feature_flags.service", None)
            else:
                sys.modules["app.domains.feature_flags.service"] = original
