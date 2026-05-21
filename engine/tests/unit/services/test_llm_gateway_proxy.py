"""Proxy mode tests for LLMGateway (Faz 4.C — ADR-0002).

Covers the new `use_gateway_proxy` feature flag and `_call_ai_gateway` path.
Direct-mode behavior is covered by test_llm_gateway.py.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.llm_gateway import LLMGateway, LLMResponse


_FAKE_CONFIG = Path("/nonexistent_config_dir")


@pytest.fixture
def proxy_gateway(monkeypatch):
    """LLMGateway with proxy mode forced on."""
    monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
    monkeypatch.setenv("AI_GATEWAY_BASE_URL", "http://test-gateway:8080")
    monkeypatch.setenv("GATEWAY_INTERNAL_KEY", "test-key-123")
    return LLMGateway(
        openai_api_key=None,
        anthropic_api_key=None,
        enable_cache=False,  # cache off — test each call isolated
        enable_pii_sanitization=False,  # PII tests handled elsewhere
        budget_limit_usd=10.0,
        rate_limit_per_hour=100,
        use_gateway_proxy=True,
    )


class TestProxyModeActivation:
    def test_env_flag_enables_proxy(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        monkeypatch.setenv("ENGINE_LLM_USE_GATEWAY", "1")
        gw = LLMGateway()
        assert gw.use_gateway_proxy is True

    def test_env_flag_off_by_default(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.delenv("ENGINE_LLM_USE_GATEWAY", raising=False)
        gw = LLMGateway()
        assert gw.use_gateway_proxy is False

    def test_production_defaults_to_proxy(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("ENGINE_LLM_USE_GATEWAY", raising=False)
        gw = LLMGateway()
        assert gw.use_gateway_proxy is True

    def test_explicit_arg_overrides_env(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("ENGINE_LLM_USE_GATEWAY", "1")
        gw = LLMGateway(use_gateway_proxy=False)
        assert gw.use_gateway_proxy is False

    def test_production_rejects_direct_override_without_escape_hatch(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("ENGINE_LLM_ALLOW_DIRECT_PROVIDERS", raising=False)

        with pytest.raises(RuntimeError, match="direct LLM provider mode is disabled"):
            LLMGateway(use_gateway_proxy=False)


class TestProxyCall:
    def _mock_httpx_response(self, content="hello", tokens=42, model="gpt-4o"):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "content": content,
            "provider_used": "groq",
            "model_used": model,
            "tokens_used": tokens,
            "latency_ms": 150,
            "cached": False,
        }
        return mock_resp

    def test_proxy_routes_to_ai_gateway(self, proxy_gateway):
        with patch("httpx.post", return_value=self._mock_httpx_response()) as mock_post:
            resp = proxy_gateway.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
                temperature=0.2,
                max_tokens=100,
            )

        assert isinstance(resp, LLMResponse)
        assert resp.content == "hello"
        assert resp.tokens_used == 42
        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        assert url == "http://test-gateway:8080/ai/complete"

    def test_proxy_includes_internal_key(self, proxy_gateway):
        with patch("httpx.post", return_value=self._mock_httpx_response()) as mock_post:
            proxy_gateway.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o-mini",
            )

        headers = mock_post.call_args.kwargs["headers"]
        assert headers["X-Internal-Key"] == "test-key-123"

    def test_proxy_payload_shape(self, proxy_gateway):
        with patch("httpx.post", return_value=self._mock_httpx_response()) as mock_post:
            proxy_gateway.complete(
                messages=[
                    {"role": "system", "content": "you are helpful"},
                    {"role": "user", "content": "1+1?"},
                ],
                model="qwen2.5-coder:7b",
                temperature=0.1,
                max_tokens=50,
            )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["task_type"] == "generate_playwright"  # model → task mapping
        assert payload["temperature"] == 0.1
        assert payload["max_tokens"] == 50
        assert payload["model_override"] == "qwen2.5-coder:7b"
        assert payload["messages"] == [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "1+1?"},
        ]

    def test_proxy_raises_on_http_error(self, proxy_gateway):
        import httpx

        err_resp = MagicMock()
        err_resp.raise_for_status.side_effect = httpx.HTTPError("502 bad gateway")
        with patch("httpx.post", return_value=err_resp):
            with pytest.raises(RuntimeError, match="AI Gateway erişilemiyor"):
                proxy_gateway.complete(
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o",
                )

    def test_proxy_updates_usage_stats(self, proxy_gateway):
        with patch("httpx.post", return_value=self._mock_httpx_response(tokens=100)):
            proxy_gateway.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
            )

        assert proxy_gateway.stats.total_calls == 1
        assert proxy_gateway.stats.total_tokens == 100

    def test_proxy_unknown_model_falls_back_to_chat_task(self, proxy_gateway):
        with patch("httpx.post", return_value=self._mock_httpx_response()) as mock_post:
            proxy_gateway.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="some-unknown-model-xyz",
            )

        payload = mock_post.call_args.kwargs["json"]
        assert payload["task_type"] == "chat"


class TestDirectModeStillWorks:
    """Regression: default (non-proxy) path must not reach httpx."""

    def test_default_mode_does_not_call_ai_gateway(self, monkeypatch):
        monkeypatch.setattr("services.llm_gateway._CONFIG_DIR", _FAKE_CONFIG)
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.delenv("ENGINE_LLM_USE_GATEWAY", raising=False)
        gw = LLMGateway(openai_api_key="sk-test")

        # Mock the internal OpenAI client so no real HTTP call is made
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "direct-mode-ok"
        mock_usage = MagicMock(total_tokens=10, prompt_tokens=5, completion_tokens=5)
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice],
            usage=mock_usage,
        )
        gw._openai = mock_client

        with patch("httpx.post") as mock_post:
            resp = gw.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
            )

        assert resp.content == "direct-mode-ok"
        mock_post.assert_not_called()
