"""
Unit tests for StreamingLLMService.

All LLM calls are mocked via monkeypatch so these tests run without any
network access or real model credentials.
"""
from __future__ import annotations

import json
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.ai.streaming_service import StreamingLLMService, get_streaming_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fake_stream(*tokens: str) -> AsyncIterator[str]:
    """Yields a sequence of token strings, simulating async_stream_llm."""
    for t in tokens:
        yield t


async def _collect(gen: AsyncIterator[dict]) -> list[dict]:
    """Drain an async generator into a list."""
    result = []
    async for item in gen:
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------

class TestStreamScenarioGeneration:
    """Tests for stream_scenario_generation."""

    @pytest.mark.asyncio
    async def test_yields_token_events(self, monkeypatch):
        tokens = ["Hello", " world"]
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream(*tokens),
        )
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(
            svc.stream_scenario_generation("Login flow", project_id="p1")
        )
        token_events = [e for e in events if e["type"] == "token"]
        assert [e["content"] for e in token_events] == tokens

    @pytest.mark.asyncio
    async def test_final_event_is_complete(self, monkeypatch):
        scenarios_json = json.dumps({"scenarios": [{"name": "S1"}]})
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream(scenarios_json),
        )
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_scenario_generation("desc"))
        last = events[-1]
        assert last["type"] == "complete"
        assert last["scenarios"] == [{"name": "S1"}]

    @pytest.mark.asyncio
    async def test_malformed_json_yields_raw_complete(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream("not-json"),
        )
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_scenario_generation("desc"))
        last = events[-1]
        assert last["type"] == "complete"
        assert "raw" in last

    @pytest.mark.asyncio
    async def test_llm_error_mid_stream_yields_error_event(self, monkeypatch):
        async def _boom(*a, **kw):
            raise RuntimeError("LLM unavailable")
            yield  # make it a generator

        monkeypatch.setattr("app.domains.ai.service.async_stream_llm", _boom)
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_scenario_generation("desc"))
        assert events[-1]["type"] == "error"
        assert "LLM unavailable" in events[-1]["message"]

    @pytest.mark.asyncio
    async def test_rag_context_appended_when_present(self, monkeypatch):
        captured: dict = {}

        async def _capturing_stream(system, user, **kw):
            captured["system"] = system
            yield json.dumps({"scenarios": []})

        monkeypatch.setattr("app.domains.ai.service.async_stream_llm", _capturing_stream)
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value="example scenario"),
        )
        svc = StreamingLLMService()
        await _collect(svc.stream_scenario_generation("desc", project_id="p1"))
        assert "example scenario" in captured.get("system", "")


# ---------------------------------------------------------------------------
# Test analysis
# ---------------------------------------------------------------------------

class TestStreamTestAnalysis:
    @pytest.mark.asyncio
    async def test_yields_tokens_and_complete(self, monkeypatch):
        payload = json.dumps({"summary": "All passed"})
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream(payload),
        )
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_test_analysis("run data"))
        types = [e["type"] for e in events]
        assert "token" in types
        assert events[-1]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_error_handling(self, monkeypatch):
        async def _fail(*a, **kw):
            raise ConnectionError("timeout")
            yield

        monkeypatch.setattr("app.domains.ai.service.async_stream_llm", _fail)
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_test_analysis("run data"))
        assert events[-1]["type"] == "error"

    @pytest.mark.asyncio
    async def test_message_truncated_to_500_chars(self, monkeypatch):
        async def _fail(*a, **kw):
            raise ValueError("x" * 600)
            yield

        monkeypatch.setattr("app.domains.ai.service.async_stream_llm", _fail)
        monkeypatch.setattr(
            "app.domains.ai.service._get_rag_context_async",
            AsyncMock(return_value=""),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_test_analysis("run data"))
        assert len(events[-1]["message"]) <= 500


# ---------------------------------------------------------------------------
# Test data generation
# ---------------------------------------------------------------------------

class TestStreamTestDataGeneration:
    @pytest.mark.asyncio
    async def test_columns_passed_in_user_content(self, monkeypatch):
        captured: dict = {}

        async def _cap(system, user, **kw):
            captured["user"] = user
            yield json.dumps({"rows": []})

        monkeypatch.setattr("app.domains.ai.service.async_stream_llm", _cap)
        svc = StreamingLLMService()
        await _collect(
            svc.stream_test_data_generation(
                "login data",
                columns=[{"name": "username", "type": "string"}],
            )
        )
        assert "username" in captured.get("user", "")

    @pytest.mark.asyncio
    async def test_complete_event_contains_data_key(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream(json.dumps({"rows": [1, 2, 3]})),
        )
        svc = StreamingLLMService()
        events = await _collect(svc.stream_test_data_generation("desc"))
        assert events[-1]["type"] == "complete"
        assert "data" in events[-1]


# ---------------------------------------------------------------------------
# General streaming
# ---------------------------------------------------------------------------

class TestStreamGeneral:
    @pytest.mark.asyncio
    async def test_no_parse_json_returns_text(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream("hello", " there"),
        )
        svc = StreamingLLMService()
        events = await _collect(
            svc.stream_general("sys", "user", parse_json=False)
        )
        assert events[-1]["type"] == "complete"
        assert events[-1]["text"] == "hello there"

    @pytest.mark.asyncio
    async def test_parse_json_true_returns_data(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream(json.dumps({"key": "value"})),
        )
        svc = StreamingLLMService()
        events = await _collect(
            svc.stream_general("sys", "user", parse_json=True)
        )
        last = events[-1]
        assert last["type"] == "complete"
        assert last.get("data", {}).get("key") == "value"

    @pytest.mark.asyncio
    async def test_parse_json_malformed_falls_back_to_raw(self, monkeypatch):
        monkeypatch.setattr(
            "app.domains.ai.service.async_stream_llm",
            lambda *a, **kw: _fake_stream("{{bad json"),
        )
        svc = StreamingLLMService()
        events = await _collect(
            svc.stream_general("sys", "user", parse_json=True)
        )
        assert events[-1]["type"] == "complete"
        assert "raw" in events[-1]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestGetStreamingService:
    def test_returns_instance(self):
        svc = get_streaming_service()
        assert isinstance(svc, StreamingLLMService)

    def test_singleton_same_object(self):
        a = get_streaming_service()
        b = get_streaming_service()
        assert a is b
