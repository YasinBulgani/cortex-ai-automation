"""LLM Gateway unit tests — PII sanitization, cache, rate limiting, budget."""
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.llm_gateway import LLMGateway, LLMResponse, MODEL_COSTS

_FAKE_CONFIG = Path("/nonexistent_config_dir")


@pytest.fixture
def gateway(monkeypatch):
    """Gateway with yaml config override disabled."""
    monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
    return LLMGateway(
        openai_api_key=None,
        anthropic_api_key=None,
        enable_cache=True,
        enable_pii_sanitization=True,
        budget_limit_usd=10.0,
        rate_limit_per_hour=5,
        cache_ttl_seconds=60,
    )


class TestPIISanitization:
    def test_masks_tc_kimlik(self, gateway):
        msgs = [{"role": "user", "content": "TC: 12345678901"}]
        result = gateway._sanitize_messages(msgs)
        assert "[TC_KIMLIK]" in result[0]["content"]
        assert "12345678901" not in result[0]["content"]

    def test_masks_iban_uppercase(self, gateway):
        msgs = [{"role": "user", "content": "IBAN: TR330006100519786457841326"}]
        result = gateway._sanitize_messages(msgs)
        assert "[IBAN]" in result[0]["content"]

    def test_masks_iban_lowercase(self, gateway):
        msgs = [{"role": "user", "content": "iban: tr330006100519786457841326"}]
        result = gateway._sanitize_messages(msgs)
        assert "[IBAN]" in result[0]["content"]

    def test_masks_email(self, gateway):
        msgs = [{"role": "user", "content": "email: test@bank.com"}]
        result = gateway._sanitize_messages(msgs)
        assert "[EMAIL]" in result[0]["content"]

    def test_masks_phone(self, gateway):
        msgs = [{"role": "user", "content": "tel: 0532 123 45 67"}]
        result = gateway._sanitize_messages(msgs)
        assert "[TELEFON]" in result[0]["content"]

    def test_handles_missing_content_key(self, gateway):
        msgs = [{"role": "system"}]
        result = gateway._sanitize_messages(msgs)
        assert result[0]["content"] == ""


class TestCacheWithTTL:
    def test_cache_hit(self, gateway):
        key = gateway._cache_key([{"role": "user", "content": "test"}], "gpt-4o", 0.2)
        fake_resp = LLMResponse("cached", "gpt-4o", 100, False, 0.01, 50)
        gateway._cache[key] = (fake_resp, time.monotonic())

        result = gateway._get_from_cache(key)
        assert result is not None
        assert result.content == "cached"

    def test_cache_expired(self, gateway):
        key = "expired_key"
        fake_resp = LLMResponse("old", "gpt-4o", 100, False, 0.01, 50)
        gateway._cache[key] = (fake_resp, time.monotonic() - 120)

        result = gateway._get_from_cache(key)
        assert result is None
        assert key not in gateway._cache

    def test_cache_miss(self, gateway):
        result = gateway._get_from_cache("nonexistent")
        assert result is None


class TestRateLimiting:
    def test_allows_within_limit(self, gateway):
        for _ in range(5):
            gateway._enforce_rate_limit()

    def test_blocks_over_limit(self, gateway):
        for _ in range(5):
            gateway._enforce_rate_limit()
        with pytest.raises(RuntimeError, match="Rate limit"):
            gateway._enforce_rate_limit()

    def test_old_timestamps_cleaned(self, gateway):
        gateway._call_timestamps = [time.monotonic() - 4000] * 10
        gateway._enforce_rate_limit()
        assert len(gateway._call_timestamps) == 1


class TestBudgetLimit:
    def test_budget_exceeded_raises(self, gateway):
        gateway.stats.total_cost_usd = 15.0
        with pytest.raises(RuntimeError, match="bütçe limiti"):
            gateway.complete([{"role": "user", "content": "test"}])


class TestAvailability:
    def test_no_keys_unavailable(self, gateway):
        assert gateway.available is False

    def test_openai_available(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        gw = LLMGateway(openai_api_key="sk-test")
        assert gw.has_openai is True
        assert gw.available is True

    def test_anthropic_available(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        gw = LLMGateway(anthropic_api_key="sk-ant-test")
        assert gw.has_anthropic is True
        assert gw.available is True


class TestApiKeyGuard:
    def test_openai_no_key_raises(self, gateway):
        with pytest.raises(RuntimeError, match="OpenAI API anahtarı"):
            gateway._call_openai([], "gpt-4o", 0.2, 100)

    def test_anthropic_no_key_raises(self, gateway):
        with pytest.raises(RuntimeError, match="Anthropic API anahtarı"):
            gateway._call_anthropic([], "claude-3-5-sonnet-latest", 0.2, 100)


class TestCostCalculation:
    def test_known_model_cost(self):
        cost = LLMGateway._calculate_cost("gpt-4o", 1000, 500)
        expected = 1000 * MODEL_COSTS["gpt-4o"]["input"] + 500 * MODEL_COSTS["gpt-4o"]["output"]
        assert abs(cost - expected) < 1e-10

    def test_unknown_model_fallback(self):
        cost = LLMGateway._calculate_cost("unknown-model", 1000, 500)
        assert cost >= 0


class TestStats:
    def test_stats_to_dict(self, gateway):
        d = gateway.stats.to_dict()
        assert "total_calls" in d
        assert d["total_calls"] == 0

    def test_update_stats(self, gateway):
        resp = LLMResponse("test", "gpt-4o", 500, False, 0.005, 100)
        gateway._update_stats(resp)
        assert gateway.stats.total_calls == 1
        assert gateway.stats.total_tokens == 500
