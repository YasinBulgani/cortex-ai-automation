"""AI Gateway client — unit testleri (httpx mock'lu)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.domains.agents.v2.tools.ai_gateway import (
    AIGatewayError,
    AsyncAIGatewayClient,
    calculate_cost_usd,
    parse_json_safe,
)
from app.domains.ai.structured_output import StructuredOutputValidationError


# ═══════════════════════════════════════════════════════════════════════════
# JSON parser
# ═══════════════════════════════════════════════════════════════════════════


class TestJSONParser:
    def test_direct_json(self):
        assert parse_json_safe('{"a": 1}') == {"a": 1}

    def test_markdown_fence_json(self):
        assert parse_json_safe('```json\n{"a": 1}\n```') == {"a": 1}

    def test_partial_json_extraction(self):
        text = "İşte sonuç:\n\n{\"a\": 1, \"b\": 2}\n\nTeşekkürler"
        assert parse_json_safe(text) == {"a": 1, "b": 2}

    def test_array(self):
        assert parse_json_safe("[1, 2, 3]") == [1, 2, 3]

    def test_invalid_returns_none(self):
        assert parse_json_safe("bu JSON değil") is None

    def test_empty_string_returns_none(self):
        assert parse_json_safe("") is None


# ═══════════════════════════════════════════════════════════════════════════
# Cost calculator
# ═══════════════════════════════════════════════════════════════════════════


class TestCostCalculator:
    def test_local_model_zero_cost(self):
        assert calculate_cost_usd("qwen2.5:14b-instruct-q4_K_M", 10_000, 5_000) == 0.0

    def test_cloud_model_cost(self):
        # gpt-4o-mini: 0.15 input / 0.60 output per 1M
        cost = calculate_cost_usd("gpt-4o-mini", 1_000_000, 500_000)
        assert cost == pytest.approx(0.15 + 0.30)

    def test_unknown_model_zero(self):
        assert calculate_cost_usd("some-random-model", 1000, 500) == 0.0

    def test_claude_premium(self):
        # claude-3.5-sonnet: 3 / 15
        cost = calculate_cost_usd("claude-3.5-sonnet", 100_000, 50_000)
        assert cost == pytest.approx(0.3 + 0.75)


# ═══════════════════════════════════════════════════════════════════════════
# Client retry behavior
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_client_retries_on_503():
    """503 aldıkça retry etmeli, nihayetinde başarılı olmalı."""
    client = AsyncAIGatewayClient()

    # Mock HTTPX transport: ilk 2 çağrı 503, 3. çağrı OK
    call_count = {"n": 0}

    def _mock_handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] < 3:
            return httpx.Response(503, json={"detail": "busy"})
        return httpx.Response(
            200,
            json={
                "content": '{"ok": true}',
                "provider_used": "mock",
                "model_used": "qwen2.5:14b-instruct-q4_K_M",
                "latency_ms": 100,
                "tokens_used": 10,
                "correlation_id": "abc",
            },
        )

    transport = httpx.MockTransport(_mock_handler)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers={"X-Internal-Key": client.internal_key},
        transport=transport,
    )

    # Retry backoff küçük olsun
    import app.domains.agents.v2.tools.ai_gateway as gw_mod
    old_backoff = gw_mod.RETRY_BACKOFF
    gw_mod.RETRY_BACKOFF = 0.01
    try:
        resp = await client.complete(
            user_message="test",
            task_type="chat",
        )
    finally:
        gw_mod.RETRY_BACKOFF = old_backoff
        await client.close()

    assert resp.content == '{"ok": true}'
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_client_raises_on_400():
    """400 hatası retry edilmez, hemen fırlat."""
    client = AsyncAIGatewayClient()

    def _mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "bad request"})

    transport = httpx.MockTransport(_mock_handler)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers={"X-Internal-Key": client.internal_key},
        transport=transport,
    )
    try:
        with pytest.raises(AIGatewayError):
            await client.complete(user_message="test", task_type="chat")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_parses_json_response():
    """content'te JSON varsa .parsed_json() geri getirmeli."""
    client = AsyncAIGatewayClient()

    def _mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": '{"domain": "banking", "feature_area": "login"}',
                "provider_used": "mock",
                "model_used": "qwen2.5:14b-instruct-q4_K_M",
                "latency_ms": 50,
                "tokens_used": 20,
            },
        )

    transport = httpx.MockTransport(_mock_handler)
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers={"X-Internal-Key": client.internal_key},
        transport=transport,
    )
    try:
        resp = await client.complete(
            user_message="analyze",
            task_type="analyze_document",
        )
    finally:
        await client.close()

    parsed = resp.parsed_json()
    assert parsed == {"domain": "banking", "feature_area": "login"}
    # Local model → cost 0
    assert resp.usage.cost_usd == 0.0


@pytest.mark.asyncio
async def test_client_budget_preflight_blocks_before_http(monkeypatch):
    from app.config import settings
    from app.domains.ai.budget import BudgetStatus

    monkeypatch.setattr(settings, "ai_budget_preflight_required", True)
    monkeypatch.setattr(
        "app.domains.ai.budget.check_budget",
        lambda tenant_id, additional_cost_usd=0.0: BudgetStatus(
            allowed=False,
            reason="hard_cap",
            today_usd=10.0,
            daily_cap_usd=10.0,
            notify_at_pct=80,
            hard_cap=True,
        ),
    )

    client = AsyncAIGatewayClient()

    def _mock_handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP should not be called when budget blocks")

    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers={"X-Internal-Key": client.internal_key},
        transport=httpx.MockTransport(_mock_handler),
    )
    try:
        with pytest.raises(AIGatewayError, match="Budget preflight blocked"):
            await client.complete(
                user_message="test",
                task_type="chat",
                tenant_id="tenant-1",
                model_override="gpt-4o-mini",
            )
    finally:
        monkeypatch.setattr(settings, "ai_budget_preflight_required", False)
        await client.close()


@pytest.mark.asyncio
async def test_client_fail_closed_on_structured_output_violation(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ai_structured_output_fail_closed", True)
    client = AsyncAIGatewayClient()

    def _mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": '{"not": "the expected schema"}',
                "provider_used": "mock",
                "model_used": "qwen2.5:14b-instruct-q4_K_M",
                "latency_ms": 50,
                "tokens_used": 20,
            },
        )

    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        headers={"X-Internal-Key": client.internal_key},
        transport=httpx.MockTransport(_mock_handler),
    )
    try:
        with pytest.raises(StructuredOutputValidationError):
            await client.complete(
                user_message="generate",
                task_type="generate_test_cases",
            )
    finally:
        monkeypatch.setattr(settings, "ai_structured_output_fail_closed", False)
        await client.close()
