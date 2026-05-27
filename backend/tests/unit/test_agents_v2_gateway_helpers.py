"""Unit tests for app.domains.agents.v2.tools.ai_gateway — pure helpers.

Tests are fully self-contained: no HTTP, no async, no AI calls.
Covers: parse_json_safe, GatewayUsage.add, GatewayResponse.parsed_json,
        _estimate_tokens (fallback path without tiktoken).
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.v2.tools.ai_gateway import (
        parse_json_safe,
        GatewayUsage,
        GatewayResponse,
        _estimate_tokens,
        AIGatewayError,
        AIGatewayTimeout,
        AIGatewayUnavailable,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="agents.v2 ai_gateway import failed")


# ---------------------------------------------------------------------------
# parse_json_safe
# ---------------------------------------------------------------------------

class TestParseJsonSafe:
    def test_plain_json_dict(self):
        result = parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_json_list(self):
        result = parse_json_safe('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_fenced_json(self):
        raw = '```json\n{"key": "value"}\n```'
        result = parse_json_safe(raw)
        assert result == {"key": "value"}

    def test_fenced_without_lang(self):
        raw = '```\n{"x": 1}\n```'
        result = parse_json_safe(raw)
        assert result == {"x": 1}

    def test_embedded_json_extracted(self):
        raw = 'Some text before {"answer": 42} and after'
        result = parse_json_safe(raw)
        assert result == {"answer": 42}

    def test_empty_string_returns_none(self):
        assert parse_json_safe("") is None

    def test_none_returns_none(self):
        assert parse_json_safe(None) is None  # type: ignore[arg-type]

    def test_invalid_json_returns_none(self):
        assert parse_json_safe("not valid json at all") is None

    def test_returns_list_from_embedded(self):
        raw = 'Result: [1, 2, 3] done'
        result = parse_json_safe(raw)
        assert result == [1, 2, 3]

    def test_nested_json(self):
        raw = '{"nested": {"key": "value", "num": 42}}'
        result = parse_json_safe(raw)
        assert result["nested"]["num"] == 42


# ---------------------------------------------------------------------------
# GatewayUsage.add
# ---------------------------------------------------------------------------

class TestGatewayUsageAdd:
    def test_add_combines_tokens(self):
        u1 = GatewayUsage(input_tokens=10, output_tokens=20, total_tokens=30, cost_usd=0.01)
        u2 = GatewayUsage(input_tokens=5, output_tokens=10, total_tokens=15, cost_usd=0.005)
        result = u1.add(u2)
        assert result.input_tokens == 15
        assert result.output_tokens == 30
        assert result.total_tokens == 45
        assert result.cost_usd == pytest.approx(0.015)

    def test_add_zero_usage(self):
        u1 = GatewayUsage(input_tokens=100, output_tokens=50, total_tokens=150, cost_usd=0.1)
        u2 = GatewayUsage()
        result = u1.add(u2)
        assert result.input_tokens == 100

    def test_add_returns_new_instance(self):
        u1 = GatewayUsage(input_tokens=10)
        u2 = GatewayUsage(input_tokens=5)
        result = u1.add(u2)
        assert result is not u1
        assert result is not u2

    def test_default_values_zero(self):
        usage = GatewayUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cost_usd == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# GatewayResponse.parsed_json
# ---------------------------------------------------------------------------

class TestGatewayResponseParsedJson:
    def _make_response(self, content: str) -> GatewayResponse:
        return GatewayResponse(
            content=content,
            provider_used="test",
            model_used="test-model",
            latency_ms=100,
        )

    def test_valid_json_content(self):
        resp = self._make_response('{"key": "value"}')
        result = resp.parsed_json()
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self):
        resp = self._make_response("plain text response")
        result = resp.parsed_json()
        assert result is None

    def test_empty_content_returns_none(self):
        resp = self._make_response("")
        result = resp.parsed_json()
        assert result is None

    def test_fenced_json_in_content(self):
        resp = self._make_response('```json\n{"answer": 1}\n```')
        result = resp.parsed_json()
        assert result == {"answer": 1}


# ---------------------------------------------------------------------------
# _estimate_tokens
# ---------------------------------------------------------------------------

class TestEstimateTokens:
    def test_empty_string_returns_zero(self):
        assert _estimate_tokens("") == 0

    def test_non_empty_string_positive(self):
        result = _estimate_tokens("hello world test")
        assert result > 0

    def test_longer_text_more_tokens(self):
        short = _estimate_tokens("hello")
        long_text = _estimate_tokens("hello " * 50)
        assert long_text > short

    def test_returns_int(self):
        assert isinstance(_estimate_tokens("test text"), int)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_ai_gateway_timeout_is_gateway_error(self):
        assert issubclass(AIGatewayTimeout, AIGatewayError)

    def test_ai_gateway_unavailable_is_gateway_error(self):
        assert issubclass(AIGatewayUnavailable, AIGatewayError)

    def test_ai_gateway_error_is_runtime_error(self):
        assert issubclass(AIGatewayError, RuntimeError)

    def test_can_raise_and_catch_timeout(self):
        with pytest.raises(AIGatewayError):
            raise AIGatewayTimeout("timed out")

    def test_can_raise_and_catch_unavailable(self):
        with pytest.raises(AIGatewayError):
            raise AIGatewayUnavailable("unavailable")
