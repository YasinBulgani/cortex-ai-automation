"""Smart Model Router unit testleri — tier karar matrisini kanitlar."""
from __future__ import annotations

import pytest

from app.domains.ai import smart_model_router as router
from app.domains.ai.smart_model_router import (
    Tier,
    classify_endpoints,
    route_for_endpoints,
    route_model,
)


@pytest.fixture(autouse=True)
def _reset_circuit(monkeypatch):
    router._circuit_state.clear()
    # Rate-limit monitor state'ini de temizle (test'ler arasi sizma onle)
    try:
        from app.domains.ai.rate_limit_monitor import clear_rate_limit
        clear_rate_limit()
    except Exception:
        pass
    monkeypatch.setattr(router.settings, "anthropic_api_key", "test-key", raising=False)
    monkeypatch.setattr(router.settings, "openai_api_key", "test-key", raising=False)
    monkeypatch.setattr(router.settings, "ai_routing_mode", "balanced", raising=False)
    monkeypatch.setattr(router.settings, "openai_mini_model", "gpt-4o-mini", raising=False)
    monkeypatch.setattr(router.settings, "openai_mid_model", "gpt-4o", raising=False)
    monkeypatch.setattr(router.settings, "anthropic_premium_model", "claude-sonnet-4-20250514", raising=False)
    monkeypatch.setattr(router.settings, "ollama_fallback_model", "qwen2.5:32b", raising=False)
    # Feature flag'i her testte aktif tut
    try:
        from app.domains.feature_flags.service import feature_flags
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.clear()
        feature_flags.set_flag(
            "ai.router.v2",
            FlagUpdate(enabled=True, percent=100),
            actor="test",
        )
    except Exception:
        pass
    yield
    router._circuit_state.clear()
    try:
        from app.domains.ai.rate_limit_monitor import clear_rate_limit
        clear_rate_limit()
    except Exception:
        pass


class TestBaseRouting:

    def test_security_audit_critical_is_premium_low_temp(self):
        rec = route_model("security_audit", risk_level="critical")
        assert rec.tier is Tier.PREMIUM
        assert rec.temperature <= 0.10

    def test_security_audit_default_is_premium(self):
        rec = route_model("security_audit", risk_level="medium")
        assert rec.tier is Tier.PREMIUM

    def test_test_generation_financial_is_premium(self):
        rec = route_model("test_generation", has_financial=True, risk_level="medium")
        assert rec.tier is Tier.PREMIUM

    def test_test_generation_pii_is_premium(self):
        rec = route_model("test_generation", has_pii=True, risk_level="medium")
        assert rec.tier is Tier.PREMIUM

    def test_test_generation_high_risk_is_premium(self):
        rec = route_model("test_generation", risk_level="high")
        assert rec.tier is Tier.PREMIUM

    def test_test_generation_low_simple_is_mini(self):
        rec = route_model("test_generation", complexity="low", risk_level="low")
        assert rec.tier is Tier.MINI

    def test_test_generation_medium_default_is_mid(self):
        rec = route_model("test_generation", complexity="medium", risk_level="medium")
        assert rec.tier is Tier.MID

    def test_chain_builder_is_premium(self):
        rec = route_model("chain_builder")
        assert rec.tier is Tier.PREMIUM

    def test_quality_judge_is_premium_low_temp(self):
        rec = route_model("quality_judge")
        assert rec.tier is Tier.PREMIUM
        assert rec.temperature <= 0.10

    def test_spec_analysis_few_endpoints_is_mini(self):
        rec = route_model("spec_analysis", endpoint_count=3)
        assert rec.tier is Tier.MINI

    def test_spec_analysis_many_endpoints_is_mid(self):
        rec = route_model("spec_analysis", endpoint_count=12)
        assert rec.tier is Tier.MID

    def test_spec_analysis_financial_upgrades_to_mid(self):
        rec = route_model("spec_analysis", endpoint_count=2, has_financial=True)
        assert rec.tier is Tier.MID

    def test_code_generation_is_mid(self):
        rec = route_model("code_generation")
        assert rec.tier is Tier.MID

    def test_chat_is_mini(self):
        rec = route_model("chat")
        assert rec.tier is Tier.MINI

    def test_unknown_task_type_defaults_to_mini(self):
        rec = route_model("arbitrary_task_xyz")
        assert rec.tier is Tier.MINI


class TestTierResolution:

    def test_mini_resolves_to_gpt_4o_mini(self):
        assert router._resolve(Tier.MINI) == "gpt-4o-mini"

    def test_mid_resolves_to_gpt_4o(self):
        assert router._resolve(Tier.MID) == "gpt-4o"

    def test_premium_with_anthropic_key_is_claude(self):
        assert router._resolve(Tier.PREMIUM) == "claude-sonnet-4-20250514"

    def test_premium_without_anthropic_key_falls_to_mid(self, monkeypatch):
        monkeypatch.setattr(router.settings, "anthropic_api_key", "", raising=False)
        assert router._resolve(Tier.PREMIUM) == "gpt-4o"

    def test_local_resolves_to_ollama(self):
        assert router._resolve(Tier.LOCAL) == "qwen2.5:32b"


class TestGlobalMode:

    def test_cost_optimized_demotes_premium_to_mid(self, monkeypatch):
        monkeypatch.setattr(router.settings, "ai_routing_mode", "cost_optimized", raising=False)
        rec = route_model("test_generation", has_financial=True)
        assert rec.tier is Tier.MID
        assert "cost_optimized" in rec.reason

    def test_cost_optimized_keeps_quality_judge_premium(self, monkeypatch):
        monkeypatch.setattr(router.settings, "ai_routing_mode", "cost_optimized", raising=False)
        rec = route_model("quality_judge")
        assert rec.tier is Tier.PREMIUM

    def test_quality_first_upgrades_mini_to_mid(self, monkeypatch):
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        rec = route_model("chat")
        assert rec.tier is Tier.MID

    def test_quality_first_upgrades_mid_to_premium(self, monkeypatch):
        monkeypatch.setattr(router.settings, "ai_routing_mode", "quality_first", raising=False)
        rec = route_model("code_generation")
        assert rec.tier is Tier.PREMIUM

    def test_balanced_is_default(self):
        rec = route_model("test_generation", has_financial=True)
        assert rec.tier is Tier.PREMIUM


class TestCircuitBreaker:

    def _trip(self, model_name: str) -> None:
        for _ in range(router._CIRCUIT_THRESHOLD):
            router.record_circuit_failure(model_name)

    def test_premium_circuit_open_falls_to_mid(self):
        self._trip("claude-sonnet-4-20250514")
        rec = route_model("chain_builder")
        assert rec.tier is Tier.MID
        assert "circuit open" in rec.reason.lower()

    def test_mid_circuit_open_falls_to_mini(self):
        self._trip("gpt-4o")
        rec = route_model("code_generation")
        assert rec.tier is Tier.MINI

    def test_record_success_resets_circuit(self):
        router.record_circuit_failure("gpt-4o")
        router.record_circuit_failure("gpt-4o")
        router.record_circuit_failure("gpt-4o")
        assert router.should_fallback("gpt-4o") is True
        router.record_circuit_success("gpt-4o")
        assert router.should_fallback("gpt-4o") is False


class TestClassifyEndpoints:

    def test_transfer_marks_financial_critical(self):
        eps = [{"method": "POST", "path": "/api/v1/transfers"}]
        cl = classify_endpoints(eps)
        assert cl["has_financial"] is True
        assert cl["risk_level"] == "critical"

    def test_auth_marks_critical(self):
        eps = [{"method": "POST", "path": "/auth/login"}]
        cl = classify_endpoints(eps)
        assert cl["risk_level"] == "critical"

    def test_account_marks_pii_high(self):
        eps = [{"method": "GET", "path": "/accounts/me"}]
        cl = classify_endpoints(eps)
        assert cl["has_pii"] is True
        assert cl["risk_level"] == "high"

    def test_complexity_grows_with_count(self):
        assert classify_endpoints([{"method": "GET", "path": "/a"}])["complexity"] == "low"
        eps_5 = [{"method": "GET", "path": f"/p{i}"} for i in range(5)]
        assert classify_endpoints(eps_5)["complexity"] == "medium"
        eps_20 = [{"method": "GET", "path": f"/p{i}"} for i in range(20)]
        assert classify_endpoints(eps_20)["complexity"] == "high"

    def test_route_for_endpoints_financial_lifts_to_premium(self):
        eps = [{"method": "POST", "path": "/api/v1/transfers"}]
        rec = route_for_endpoints("test_generation", eps)
        assert rec.tier is Tier.PREMIUM


class TestCostEstimate:

    def test_mini_cheaper_than_premium(self):
        rec_mini = route_model("chat")
        rec_premium = route_model("security_audit", risk_level="critical")
        assert rec_mini.estimated_cost_usd < rec_premium.estimated_cost_usd

    def test_cost_is_non_negative(self):
        rec = route_model("test_generation", has_financial=True)
        assert rec.estimated_cost_usd >= 0.0


class TestFeatureFlag:

    def test_flag_disabled_returns_safe_mini(self, feature_flags):
        from app.domains.feature_flags.schemas import FlagUpdate
        feature_flags.set_flag(
            "ai.router.v2",
            FlagUpdate(enabled=False, percent=0),
            actor="test",
        )

        rec = route_model("security_audit", risk_level="critical")
        # Normalde PREMIUM dondururdu; flag kapaliyken MINI
        assert rec.tier is Tier.MINI
        assert "feature_flag" in rec.reason


class TestBackwardCompat:

    def test_legacy_get_strong_model(self):
        assert router._get_strong_model() == "claude-sonnet-4-20250514"

    def test_legacy_get_fast_model(self):
        assert router._get_fast_model() == "gpt-4o-mini"
