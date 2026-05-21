"""Shared fixtures for agent unit tests.

All external dependencies (OpenAI client, KnowledgeStore, LLM trace, settings)
are mocked so tests can run without Docker, DB, or any LLM backend.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fake settings — mirrors the relevant fields of app.config.Settings
# ---------------------------------------------------------------------------

def _make_fake_settings(**overrides) -> SimpleNamespace:
    defaults = {
        "ai_provider": "ollama",
        "ollama_base_url": "http://localhost:11434/v1",
        "ollama_api_key": "ollama",
        "ollama_model_analyst": "qwen2.5:32b",
        "ollama_model_fast": "mistral:latest",
        "ollama_model_coder": "qwen2.5-coder:7b",
        "openai_api_key": "sk-test-key",
        "openai_base_url": "https://api.openai.com/v1",
        "openai_model": "gpt-4o",
        "anthropic_api_key": "",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture()
def fake_settings():
    """Return a default fake settings object (ollama provider)."""
    return _make_fake_settings()


@pytest.fixture()
def fake_settings_openai():
    """Return a fake settings object configured for openai provider."""
    return _make_fake_settings(ai_provider="openai")


# ---------------------------------------------------------------------------
# Mock OpenAI client & chat completion response
# ---------------------------------------------------------------------------

def _build_completion_response(content: str = '{"ok": true}'):
    """Build a mock object mimicking openai.ChatCompletion response."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture()
def mock_openai_client():
    """Patch openai.OpenAI so no real HTTP calls are made.

    Returns a tuple (client_instance, create_mock) so tests can configure
    the return value of chat.completions.create.
    """
    client_instance = MagicMock()
    create_mock = client_instance.chat.completions.create
    create_mock.return_value = _build_completion_response()

    with patch("openai.OpenAI", return_value=client_instance):
        yield client_instance, create_mock


@pytest.fixture()
def mock_knowledge_store():
    """Patch KnowledgeStore so learn() / get_project_context() won't hit DB."""
    store_instance = MagicMock()
    store_instance.ingest = MagicMock()
    store_instance.retrieve = MagicMock(return_value=[])

    with patch(
        "app.domains.ai.knowledge_store.KnowledgeStore",
        return_value=store_instance,
    ):
        yield store_instance


@pytest.fixture()
def mock_llm_trace():
    """Patch log_llm_call so trace writes are no-ops."""
    with patch("app.domains.ai.llm_trace.log_llm_call") as m:
        yield m


@pytest.fixture()
def mock_trace_json_parse():
    """Patch _trace_json_parse on BaseAgent (DB write)."""
    with patch(
        "app.domains.agents.banking_team.base_agent.BaseAgent._trace_json_parse"
    ) as m:
        yield m


# ---------------------------------------------------------------------------
# Helpers re-exported for convenience inside tests
# ---------------------------------------------------------------------------

def build_completion(content: str = '{"ok": true}'):
    """Convenience for tests that need to set .return_value inline."""
    return _build_completion_response(content)
