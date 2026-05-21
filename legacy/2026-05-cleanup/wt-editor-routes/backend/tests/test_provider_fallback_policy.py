from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.domains.ai import service as ai_service
from app.domains.agents.banking_team import base_agent


def _settings(**overrides):
    defaults = {
        "ai_provider": "anthropic",
        "allow_provider_fallback": False,
        "anthropic_api_key": "",
        "anthropic_model": "claude-sonnet-4-20250514",
        "openai_api_key": "sk-test",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4o",
        "ollama_base_url": "http://localhost:11434/v1",
        "ollama_api_key": "ollama",
        "ollama_model_fast": "mistral:latest",
        "ollama_model_analyst": "qwen2.5:32b",
        "ollama_model_coder": "qwen2.5-coder:7b",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_call_llm_raises_when_selected_provider_missing_key() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=False, anthropic_api_key="")

    with patch.object(ai_service, "settings", fake):
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            ai_service.call_llm("system", "user")


def test_call_llm_falls_back_only_when_enabled() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=True, anthropic_api_key="")

    with patch.object(ai_service, "settings", fake):
        with patch.object(ai_service, "_call_openai", return_value="ok") as mock_openai:
            result = ai_service.call_llm("system", "user")

    assert result == "ok"
    mock_openai.assert_called_once()


def test_base_agent_provider_resolution_raises_without_explicit_fallback() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=False, anthropic_api_key="")

    with patch.object(base_agent, "settings", fake):
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            base_agent._resolve_effective_provider()


def test_base_agent_provider_resolution_uses_openai_when_enabled() -> None:
    fake = _settings(ai_provider="anthropic", allow_provider_fallback=True, anthropic_api_key="")

    with patch.object(base_agent, "settings", fake):
        assert base_agent._resolve_effective_provider() == "openai"
