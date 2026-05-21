from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.domains.ai import gateway_client
from app.domains.ai import router as ai_router


class _Settings:
    ai_provider = "openai"
    openai_api_key = "sk-test"
    anthropic_api_key = ""
    ollama_base_url = "http://localhost:11434/v1"


def test_gateway_headers_require_internal_key(monkeypatch) -> None:
    monkeypatch.delenv("GATEWAY_INTERNAL_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GATEWAY_INTERNAL_KEY"):
        gateway_client._gateway_headers()


def test_gateway_headers_use_configured_internal_key(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_INTERNAL_KEY", "secret-key")

    headers = gateway_client._gateway_headers()

    assert headers["X-Internal-Key"] == "secret-key"


def test_set_active_provider_requires_admin(monkeypatch) -> None:
    monkeypatch.setattr("app.deps._user_permissions", lambda user: set())

    with pytest.raises(HTTPException) as exc:
        ai_router.set_active_provider({"provider": "openai"}, user=object())

    assert exc.value.status_code == 403


def test_set_active_provider_rejects_runtime_switch(monkeypatch) -> None:
    monkeypatch.setattr("app.deps._user_permissions", lambda user: {"admin.*"})
    monkeypatch.setattr("app.config.get_settings", lambda: _Settings())

    with pytest.raises(HTTPException) as exc:
        ai_router.set_active_provider({"provider": "ollama"}, user=object())

    assert exc.value.status_code == 409


def test_set_active_provider_returns_current_provider_for_admin(monkeypatch) -> None:
    monkeypatch.setattr("app.deps._user_permissions", lambda user: {"admin.*"})
    monkeypatch.setattr("app.config.get_settings", lambda: _Settings())

    result = ai_router.set_active_provider({"provider": "openai"}, user=object())

    assert result["active"] == "openai"
    assert result["runtime_switch_supported"] is False
