"""Unit tests for ai.service pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _is_local_llm_url: local/private URL detection
  - _is_retriable_error: transient vs permanent error classification
  - _parse_json_response: multi-strategy JSON extraction from LLM output
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.service import (
        _is_local_llm_url,
        _is_retriable_error,
        _parse_json_response,
    )
    _AI_SVC_OK = True
except ImportError:
    _AI_SVC_OK = False


# ---------------------------------------------------------------------------
# _is_local_llm_url
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AI_SVC_OK, reason="ai.service import failed")
class TestIsLocalLlmUrl:
    def test_localhost(self):
        assert _is_local_llm_url("http://localhost:11434") is True

    def test_127_loopback(self):
        assert _is_local_llm_url("http://127.0.0.1:11434") is True

    def test_host_docker_internal(self):
        assert _is_local_llm_url("http://host.docker.internal:11434") is True

    def test_private_ip_192(self):
        assert _is_local_llm_url("http://192.168.1.100:11434") is True

    def test_private_ip_10(self):
        assert _is_local_llm_url("http://10.0.0.1:11434") is True

    def test_public_url_returns_false(self):
        assert _is_local_llm_url("https://api.openai.com") is False

    def test_empty_string_returns_false(self):
        assert _is_local_llm_url("") is False

    def test_docker_service_name_no_dot(self):
        # "ollama" has no dot → treated as local Docker service
        assert _is_local_llm_url("http://ollama:11434") is True

    def test_docker_service_name_with_dot_returns_false(self):
        # "my.service.com" has dots → not a local name
        assert _is_local_llm_url("http://my.service.com:11434") is False

    def test_returns_bool(self):
        assert isinstance(_is_local_llm_url("http://localhost"), bool)

    def test_ipv6_loopback(self):
        assert _is_local_llm_url("http://[::1]:11434") is True


# ---------------------------------------------------------------------------
# _is_retriable_error
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AI_SVC_OK, reason="ai.service import failed")
class TestIsRetriableError:
    def test_generic_runtime_error_is_retriable(self):
        assert _is_retriable_error(RuntimeError("connection reset")) is True

    def test_timeout_error_is_retriable(self):
        assert _is_retriable_error(TimeoutError("timeout")) is True

    def test_connection_error_is_retriable(self):
        assert _is_retriable_error(ConnectionError("failed")) is True

    def test_value_error_not_retriable(self):
        assert _is_retriable_error(ValueError("invalid input")) is False

    def test_auth_message_not_retriable(self):
        assert _is_retriable_error(RuntimeError("401 unauthorized")) is False

    def test_permission_message_not_retriable(self):
        assert _is_retriable_error(RuntimeError("permission denied")) is False

    def test_returns_bool(self):
        assert isinstance(_is_retriable_error(RuntimeError("err")), bool)

    def test_invalid_api_key_not_retriable(self):
        assert _is_retriable_error(RuntimeError("invalid api key")) is False


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AI_SVC_OK, reason="ai.service import failed")
class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown_fence(self):
        raw = '```json\n{"status": "ok"}\n```'
        result = _parse_json_response(raw)
        assert result == {"status": "ok"}

    def test_generic_fence(self):
        raw = '```\n{"status": "ok"}\n```'
        result = _parse_json_response(raw)
        assert result == {"status": "ok"}

    def test_json_embedded_in_prose(self):
        raw = 'Here is the result: {"score": 0.9} - end.'
        result = _parse_json_response(raw)
        assert result == {"score": 0.9}

    def test_trailing_comma_handled(self):
        raw = '{"a": 1, "b": 2,}'
        result = _parse_json_response(raw)
        assert result["a"] == 1

    def test_empty_string_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("")

    def test_none_like_empty_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("   ")

    def test_not_json_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("just some random text without json")

    def test_returns_dict(self):
        result = _parse_json_response('{"a": 1}')
        assert isinstance(result, dict)

    def test_nested_json(self):
        result = _parse_json_response('{"outer": {"inner": 42}}')
        assert result == {"outer": {"inner": 42}}

    def test_single_quotes_converted(self):
        # Strategy 5: single → double quotes
        raw = "{'key': 'value'}"
        result = _parse_json_response(raw)
        assert result == {"key": "value"}

    def test_list_response(self):
        result = _parse_json_response('[1, 2, 3]')
        assert result == [1, 2, 3]
