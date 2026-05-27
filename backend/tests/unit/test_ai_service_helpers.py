"""Unit tests for AI service pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/service.py:
    _is_local_llm_url, _is_retriable_error, _estimate_trace_tokens,
    _parse_json_response
"""

from __future__ import annotations

import pytest

from app.domains.ai.service import (
    _estimate_trace_tokens,
    _is_local_llm_url,
    _is_retriable_error,
    _parse_json_response,
)


# ── _is_local_llm_url ─────────────────────────────────────────────────────────


class TestIsLocalLlmUrl:
    def test_localhost_is_local(self) -> None:
        assert _is_local_llm_url("http://localhost:11434") is True

    def test_127_0_0_1_is_local(self) -> None:
        assert _is_local_llm_url("http://127.0.0.1:8080") is True

    def test_loopback_ipv6_is_local(self) -> None:
        # IPv6 loopback requires bracket notation in URLs
        assert _is_local_llm_url("http://[::1]:11434") is True

    def test_0_0_0_0_is_local(self) -> None:
        assert _is_local_llm_url("http://0.0.0.0:8080") is True

    def test_docker_internal_is_local(self) -> None:
        assert _is_local_llm_url("http://host.docker.internal:11434") is True

    def test_docker_service_name_no_dot_is_local(self) -> None:
        # Docker Compose service names like "ollama" or "vllm" have no dots
        assert _is_local_llm_url("http://ollama:11434") is True
        assert _is_local_llm_url("http://vllm:8000") is True

    def test_private_ip_192_168_is_local(self) -> None:
        assert _is_local_llm_url("http://192.168.1.100:11434") is True

    def test_private_ip_10_is_local(self) -> None:
        assert _is_local_llm_url("http://10.0.0.1:11434") is True

    def test_public_ip_not_local(self) -> None:
        assert _is_local_llm_url("http://8.8.8.8:11434") is False

    def test_external_hostname_not_local(self) -> None:
        assert _is_local_llm_url("https://api.openai.com") is False

    def test_empty_string_not_local(self) -> None:
        assert _is_local_llm_url("") is False

    def test_returns_bool(self) -> None:
        assert isinstance(_is_local_llm_url("http://localhost"), bool)

    def test_anthropic_api_not_local(self) -> None:
        assert _is_local_llm_url("https://api.anthropic.com") is False


# ── _is_retriable_error ───────────────────────────────────────────────────────


class TestIsRetriableError:
    def test_generic_runtime_error_is_retriable(self) -> None:
        assert _is_retriable_error(RuntimeError("connection timeout")) is True

    def test_timeout_error_is_retriable(self) -> None:
        assert _is_retriable_error(TimeoutError("request timed out")) is True

    def test_connection_error_is_retriable(self) -> None:
        assert _is_retriable_error(ConnectionError("connection refused")) is True

    def test_auth_error_not_retriable(self) -> None:
        # Messages containing "unauthorized" or "403" should not be retried
        assert _is_retriable_error(RuntimeError("401 Unauthorized")) is False

    def test_value_error_not_retriable(self) -> None:
        assert _is_retriable_error(ValueError("invalid input")) is False

    def test_key_error_not_retriable(self) -> None:
        assert _is_retriable_error(KeyError("missing key")) is False

    def test_returns_bool(self) -> None:
        assert isinstance(_is_retriable_error(Exception("test")), bool)

    def test_permission_denied_not_retriable(self) -> None:
        assert _is_retriable_error(RuntimeError("permission denied")) is False

    def test_generic_exception_is_retriable(self) -> None:
        # Base Exception without non-retriable keywords
        assert _is_retriable_error(Exception("server error 500")) is True


# ── _estimate_trace_tokens ────────────────────────────────────────────────────


class TestEstimateTraceTokens:
    def test_returns_tuple_of_three(self) -> None:
        result = _estimate_trace_tokens("system", "user", "response")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_total_is_sum_of_prompt_and_completion(self) -> None:
        prompt, completion, total = _estimate_trace_tokens("sys", "usr", "resp")
        assert total == prompt + completion

    def test_empty_strings_return_zeros(self) -> None:
        prompt, completion, total = _estimate_trace_tokens("", "", "")
        assert prompt == 0
        assert completion == 0
        assert total == 0

    def test_all_values_non_negative(self) -> None:
        prompt, completion, total = _estimate_trace_tokens("s" * 100, "u" * 100, "r" * 100)
        assert prompt >= 0
        assert completion >= 0
        assert total >= 0

    def test_longer_text_more_tokens(self) -> None:
        _, _, short = _estimate_trace_tokens("s", "u", "r")
        _, _, long = _estimate_trace_tokens("s" * 1000, "u" * 1000, "r" * 1000)
        assert long > short

    def test_prompt_includes_system_and_user(self) -> None:
        # prompt_tokens = (len(system) + len(user_content)) // 3
        system = "a" * 300  # 100 tokens
        user = "b" * 300  # another 100 tokens
        prompt, _, _ = _estimate_trace_tokens(system, user, "")
        assert prompt == 200  # (300 + 300) // 3

    def test_completion_from_response_only(self) -> None:
        # completion_tokens = len(response) // 3
        _, completion, _ = _estimate_trace_tokens("", "", "r" * 300)
        assert completion == 100  # 300 // 3


# ── _parse_json_response ──────────────────────────────────────────────────────


class TestParseJsonResponse:
    def test_plain_json_dict_parsed(self) -> None:
        result = _parse_json_response('{"score": 8, "label": "good"}')
        assert result["score"] == 8
        assert result["label"] == "good"

    def test_json_in_markdown_fence_parsed(self) -> None:
        raw = '```json\n{"score": 7, "reason": "ok"}\n```'
        result = _parse_json_response(raw)
        assert result["score"] == 7

    def test_json_in_plain_fence_parsed(self) -> None:
        raw = '```\n{"score": 6}\n```'
        result = _parse_json_response(raw)
        assert result["score"] == 6

    def test_json_embedded_in_text_parsed(self) -> None:
        raw = 'Here is my analysis: {"score": 9, "comment": "excellent"} done.'
        result = _parse_json_response(raw)
        assert result["score"] == 9

    def test_empty_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _parse_json_response("")

    def test_whitespace_only_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _parse_json_response("   ")

    def test_returns_dict(self) -> None:
        result = _parse_json_response('{"x": 1}')
        assert isinstance(result, dict)

    def test_nested_json_parsed(self) -> None:
        raw = '{"outer": {"inner": 42}}'
        result = _parse_json_response(raw)
        assert result["outer"]["inner"] == 42

    def test_json_array_parsed(self) -> None:
        raw = '[{"id": 1}, {"id": 2}]'
        result = _parse_json_response(raw)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_unicode_content_preserved(self) -> None:
        raw = '{"message": "Başarılı test"}'
        result = _parse_json_response(raw)
        assert "Başarılı" in result["message"]
