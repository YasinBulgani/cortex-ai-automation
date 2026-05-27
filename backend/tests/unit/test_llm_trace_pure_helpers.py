"""Unit tests for ai.llm_trace pure helper functions.

All tests are self-contained: no DB, no HTTP.
Covers:
  - _safe_row_get: safe index access with default fallback
  - _infer_provider: model-name prefix → provider string
  - _estimate_tokens: rough token count from prompt+response lengths
  - _status_from: success/timeout/error string from bool + message
  - _normalize_metadata: dict copy with optional streaming flag
  - _deserialize_metadata: JSON string / dict / invalid → dict
  - _empty_trace_stats: default stats dict shape
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.llm_trace import (
        _safe_row_get,
        _infer_provider,
        _estimate_tokens,
        _status_from,
        _normalize_metadata,
        _deserialize_metadata,
        _empty_trace_stats,
    )
    _LT_OK = True
except ImportError:
    _LT_OK = False


# ---------------------------------------------------------------------------
# _safe_row_get
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestSafeRowGet:
    def test_valid_index(self):
        row = [10, 20, 30]
        assert _safe_row_get(row, 1) == 20

    def test_first_element(self):
        row = ["a", "b", "c"]
        assert _safe_row_get(row, 0) == "a"

    def test_last_element(self):
        row = [1, 2, 3]
        assert _safe_row_get(row, 2) == 3

    def test_out_of_range_returns_default(self):
        row = [1, 2, 3]
        assert _safe_row_get(row, 99) is None

    def test_out_of_range_custom_default(self):
        row = [1, 2, 3]
        assert _safe_row_get(row, 99, default="fallback") == "fallback"

    def test_none_row_returns_default(self):
        assert _safe_row_get(None, 0) is None

    def test_none_row_custom_default(self):
        assert _safe_row_get(None, 0, default=42) == 42

    def test_tuple_row(self):
        row = ("x", "y", "z")
        assert _safe_row_get(row, 1) == "y"

    def test_dict_row_with_int_key(self):
        # dict[int, val] would work but most dict access falls through
        # non-indexable object returns default
        assert _safe_row_get("abc", 1) == "b"  # strings are indexable


# ---------------------------------------------------------------------------
# _infer_provider
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestInferProvider:
    def test_gpt_prefix_returns_openai(self):
        assert _infer_provider("gpt-4o") == "openai"

    def test_gpt_prefix_case_insensitive(self):
        assert _infer_provider("GPT-4") == "openai"

    def test_claude_prefix_returns_anthropic(self):
        assert _infer_provider("claude-3-5-sonnet") == "anthropic"

    def test_claude_uppercase(self):
        assert _infer_provider("CLAUDE-3") == "anthropic"

    def test_unknown_model_returns_ollama(self):
        assert _infer_provider("llama3:8b") == "ollama"

    def test_empty_string_returns_none(self):
        assert _infer_provider("") is None

    def test_none_returns_none(self):
        assert _infer_provider(None) is None  # type: ignore[arg-type]

    def test_returns_string_or_none(self):
        result = _infer_provider("gpt-4o")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _estimate_tokens
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestEstimateTokens:
    def test_returns_tuple_of_three(self):
        result = _estimate_tokens("sys", "user", "resp")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_total_is_sum_of_prompt_and_completion(self):
        p, c, total = _estimate_tokens("aaa", "bbb", "cccc")
        assert total == p + c

    def test_empty_strings(self):
        p, c, total = _estimate_tokens("", "", "")
        assert p == 0
        assert c == 0
        assert total == 0

    def test_long_prompt_gives_more_tokens(self):
        short_p, _, _ = _estimate_tokens("hi", "hi", "resp")
        long_p, _, _ = _estimate_tokens("a" * 300, "b" * 300, "resp")
        assert long_p > short_p

    def test_long_response_gives_more_completion_tokens(self):
        _, short_c, _ = _estimate_tokens("sys", "user", "ok")
        _, long_c, _ = _estimate_tokens("sys", "user", "r" * 300)
        assert long_c > short_c

    def test_none_inputs_treated_as_empty(self):
        p, c, total = _estimate_tokens(None, None, None)  # type: ignore[arg-type]
        assert p >= 0
        assert c >= 0

    def test_all_ints(self):
        p, c, total = _estimate_tokens("system", "user", "response")
        assert isinstance(p, int)
        assert isinstance(c, int)
        assert isinstance(total, int)


# ---------------------------------------------------------------------------
# _status_from
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestStatusFrom:
    def test_success_true(self):
        assert _status_from(True, None) == "success"

    def test_success_true_with_message(self):
        assert _status_from(True, "some message") == "success"

    def test_failure_no_message(self):
        assert _status_from(False, None) == "error"

    def test_failure_generic_message(self):
        assert _status_from(False, "connection refused") == "error"

    def test_timeout_message(self):
        assert _status_from(False, "Request timeout exceeded") == "timeout"

    def test_timeout_lowercase(self):
        assert _status_from(False, "timeout after 30s") == "timeout"

    def test_returns_string(self):
        assert isinstance(_status_from(True, None), str)

    def test_empty_error_message_returns_error(self):
        assert _status_from(False, "") == "error"


# ---------------------------------------------------------------------------
# _normalize_metadata
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestNormalizeMetadata:
    def test_none_returns_empty_dict(self):
        result = _normalize_metadata(None, is_streaming=False)
        assert isinstance(result, dict)

    def test_existing_dict_preserved(self):
        metadata = {"key": "value"}
        result = _normalize_metadata(metadata, is_streaming=False)
        assert result["key"] == "value"

    def test_streaming_adds_key(self):
        result = _normalize_metadata({}, is_streaming=True)
        assert result.get("streaming") is True

    def test_non_streaming_no_streaming_key(self):
        result = _normalize_metadata({}, is_streaming=False)
        assert "streaming" not in result

    def test_does_not_mutate_original(self):
        original = {"a": 1}
        _normalize_metadata(original, is_streaming=True)
        assert "streaming" not in original

    def test_existing_streaming_key_not_overridden(self):
        # setdefault → only set if not already present
        metadata = {"streaming": False}
        result = _normalize_metadata(metadata, is_streaming=True)
        assert result["streaming"] is False

    def test_returns_dict(self):
        assert isinstance(_normalize_metadata({"x": 1}, is_streaming=False), dict)


# ---------------------------------------------------------------------------
# _deserialize_metadata
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestDeserializeMetadata:
    def test_none_returns_empty_dict(self):
        assert _deserialize_metadata(None) == {}

    def test_empty_string_returns_empty(self):
        assert _deserialize_metadata("") == {}

    def test_valid_dict_passthrough(self):
        d = {"key": "val"}
        assert _deserialize_metadata(d) == d

    def test_json_string_parsed(self):
        result = _deserialize_metadata('{"a": 1}')
        assert result == {"a": 1}

    def test_invalid_json_returns_empty(self):
        assert _deserialize_metadata("not json") == {}

    def test_json_list_returns_empty(self):
        # JSON array is not a dict → return {}
        assert _deserialize_metadata("[1, 2, 3]") == {}

    def test_int_input_returns_empty(self):
        assert _deserialize_metadata(42) == {}

    def test_returns_dict(self):
        assert isinstance(_deserialize_metadata({}), dict)

    def test_nested_json_string(self):
        result = _deserialize_metadata('{"outer": {"inner": 1}}')
        assert result == {"outer": {"inner": 1}}


# ---------------------------------------------------------------------------
# _empty_trace_stats
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LT_OK, reason="llm_trace import failed")
class TestEmptyTraceStats:
    def test_returns_dict(self):
        assert isinstance(_empty_trace_stats(), dict)

    def test_total_calls_zero(self):
        assert _empty_trace_stats()["total_calls"] == 0

    def test_total_traces_zero(self):
        assert _empty_trace_stats()["total_traces"] == 0

    def test_successful_zero(self):
        assert _empty_trace_stats()["successful"] == 0

    def test_failed_zero(self):
        assert _empty_trace_stats()["failed"] == 0

    def test_success_rate_zero(self):
        assert _empty_trace_stats()["success_rate"] == pytest.approx(0.0)

    def test_avg_latency_zero(self):
        assert _empty_trace_stats()["avg_latency_ms"] == 0

    def test_top_agents_is_list(self):
        assert isinstance(_empty_trace_stats()["top_agents"], list)

    def test_top_models_is_list(self):
        assert isinstance(_empty_trace_stats()["top_models"], list)

    def test_total_cost_usd_zero(self):
        assert _empty_trace_stats()["total_cost_usd"] == pytest.approx(0.0)

    def test_each_call_returns_fresh_dict(self):
        # Mutable fields don't bleed between calls
        s1 = _empty_trace_stats()
        s2 = _empty_trace_stats()
        s1["top_agents"].append("agent1")
        assert s2["top_agents"] == []
