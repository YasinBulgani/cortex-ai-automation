from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.domains.ai import smart_model_router


def _settings(**overrides):
    defaults = {
        "ai_provider": "anthropic",
        "allow_provider_fallback": False,
        "ai_routing_mode": "balanced",
        "anthropic_api_key": "",
        "anthropic_model": "claude-sonnet-4-20250514",
        "anthropic_premium_model": "claude-sonnet-4-20250514",
        "openai_api_key": "sk-test",
        "openai_model": "gpt-4o",
        "openai_mini_model": "gpt-4o-mini",
        "openai_mid_model": "gpt-4o",
        "ollama_model_analyst": "qwen2.5:32b",
        "ollama_model_fast": "mistral:latest",
        "ollama_model_coder": "qwen2.5-coder:7b",
        "ollama_fallback_model": "qwen2.5:32b",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_router_provider_resolution_raises_without_explicit_fallback() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=False, anthropic_api_key="")

    with patch.object(smart_model_router, "settings", fake):
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            smart_model_router._get_strong_model()


def test_router_provider_resolution_uses_openai_when_enabled() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=True, anthropic_api_key="")

    with patch.object(smart_model_router, "settings", fake):
        assert smart_model_router._get_strong_model() == "gpt-4o"


def test_route_model_uses_anthropic_when_configured() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=False, anthropic_api_key="anth-key")

    with patch.object(smart_model_router, "settings", fake):
        rec = smart_model_router.route_model(task_type="security_audit", risk_level="critical")

    assert rec.model == "claude-sonnet-4-20250514"
