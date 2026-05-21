from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domains.ai import router as ai_router
from app.domains.ai import service as ai_service


@pytest.mark.anyio
async def test_async_stream_llm_propagates_temperature_and_max_tokens(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_stream(*args, **kwargs):
        captured["temperature"] = kwargs.get("temperature")
        captured["max_tokens"] = kwargs.get("max_tokens")
        if False:
            yield ""  # pragma: no cover

    async def _fake_client():
        return object()

    monkeypatch.setattr(ai_service, "_resolve_effective_provider", lambda: "openai")
    monkeypatch.setattr(ai_service, "_get_async_openai_client", _fake_client)
    monkeypatch.setattr(ai_service, "_async_stream_openai_compatible", _fake_stream)

    items = []
    async for token in ai_service.async_stream_llm(
        "system",
        "user",
        temperature=0.65,
        max_tokens=1234,
    ):
        items.append(token)

    assert items == []
    assert captured["temperature"] == 0.65
    assert captured["max_tokens"] == 1234


@pytest.mark.anyio
async def test_stream_general_applies_rate_limit_and_records_usage(monkeypatch) -> None:
    calls: dict[str, object] = {"checked": None, "recorded": None}

    class _Svc:
        async def stream_general(self, **kwargs):
            yield {"type": "token", "content": "abc"}
            yield {"type": "complete", "text": "abc"}

    monkeypatch.setattr(ai_router, "_check_llm_access", lambda user_id: calls.__setitem__("checked", user_id))
    monkeypatch.setattr(
        ai_router,
        "_record_llm_usage_safe",
        lambda user_id, *parts: calls.__setitem__("recorded", (user_id, parts)),
    )
    monkeypatch.setattr(
        "app.domains.ai.streaming_service.get_streaming_service",
        lambda: _Svc(),
    )

    body = ai_router.GeneralStreamRequest(
        system_prompt="sys",
        user_message="hello",
        parse_json=False,
        temperature=0.4,
        max_tokens=222,
    )
    user = SimpleNamespace(id="user-1")

    response = await ai_router.stream_general_llm(body=body, user=user)
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk)

    assert chunks
    assert calls["checked"] == "user-1"
    recorded_user, recorded_parts = calls["recorded"]
    assert recorded_user == "user-1"
    assert "sys" in recorded_parts
    assert "hello" in recorded_parts
    assert "abc" in recorded_parts
