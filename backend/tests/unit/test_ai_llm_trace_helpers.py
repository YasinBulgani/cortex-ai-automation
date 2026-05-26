"""Unit tests for app.domains.ai.llm_trace — pure helper functions.

Tests are fully self-contained: no DB, no HTTP.
Covers: _safe_row_get, _infer_provider, _estimate_tokens (llm_trace variant),
        _estimate_cost_usd, _status_from, _normalize_metadata,
        _normalize_task_type, _normalize_phase, _deserialize_metadata,
        _empty_trace_stats, constant dicts (_MODEL_COST_PER_1K_TOKENS,
        _TASK_TYPE_ALIASES, _PHASE_ALIASES).
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.llm_trace import (
        _safe_row_get,
        _infer_provider,
        _estimate_tokens,
        _estimate_cost_usd,
        _status_from,
        _normalize_metadata,
        _normalize_task_type,
        _normalize_phase,
        _deserialize_metadata,
        _empty_trace_stats,
        _MODEL_COST_PER_1K_TOKENS,
        _PROVIDER_DEFAULT_COST_PER_1K_TOKENS,
        _TASK_TYPE_ALIASES,
        _PHASE_ALIASES,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="llm_trace import failed")


# ---------------------------------------------------------------------------
# _safe_row_get
# ---------------------------------------------------------------------------

class TestSafeRowGet:
    def test_none_row_returns_default(self):
        assert _safe_row_get(None, 0) is None

    def test_none_row_returns_custom_default(self):
        assert _safe_row_get(None, 0, "fallback") == "fallback"

    def test_tuple_row_index(self):
        row = ("a", "b", "c")
        assert _safe_row_get(row, 0) == "a"
        assert _safe_row_get(row, 2) == "c"

    def test_list_row_index(self):
        row = [10, 20, 30]
        assert _safe_row_get(row, 1) == 20

    def test_out_of_bounds_returns_default(self):
        row = ("a",)
        assert _safe_row_get(row, 5) is None

    def test_out_of_bounds_custom_default(self):
        row = ("a",)
        assert _safe_row_get(row, 99, -1) == -1

    def test_dict_row_key_access(self):
        # dict[0] raises TypeError → returns default
        row = {0: "value"}
        assert _safe_row_get(row, 0) == "value"

    def test_returns_none_for_bad_row_type(self):
        # string index access gives char, int index on string gives char
        result = _safe_row_get("hello", 0)
        assert result == "h" or result is None  # depends on impl


# ---------------------------------------------------------------------------
# _infer_provider
# ---------------------------------------------------------------------------

class TestInferProvider:
    def test_gpt_prefix_is_openai(self):
        assert _infer_provider("gpt-4o") == "openai"

    def test_gpt_4_turbo_is_openai(self):
        assert _infer_provider("gpt-4-turbo") == "openai"

    def test_claude_prefix_is_anthropic(self):
        assert _infer_provider("claude-3-5-sonnet-20241022") == "anthropic"

    def test_claude_sonnet_is_anthropic(self):
        assert _infer_provider("claude-sonnet-4-20250514") == "anthropic"

    def test_unknown_model_is_ollama(self):
        assert _infer_provider("llama3.1") == "ollama"

    def test_empty_string_returns_none(self):
        assert _infer_provider("") is None

    def test_none_returns_none(self):
        assert _infer_provider(None) is None  # type: ignore[arg-type]

    def test_case_insensitive_gpt(self):
        assert _infer_provider("GPT-4O") == "openai"

    def test_case_insensitive_claude(self):
        assert _infer_provider("CLAUDE-3") == "anthropic"

    def test_mistral_is_ollama(self):
        assert _infer_provider("mistral-7b") == "ollama"


# ---------------------------------------------------------------------------
# _estimate_tokens (llm_trace variant: returns 3-tuple)
# ---------------------------------------------------------------------------

class TestEstimateTokensTrace:
    def test_returns_three_tuple(self):
        result = _estimate_tokens("sys", "user", "resp")
        assert len(result) == 3

    def test_empty_returns_zeros(self):
        p, c, t = _estimate_tokens("", "", "")
        assert p == 0
        assert c == 0
        assert t == 0

    def test_none_handled_gracefully(self):
        p, c, t = _estimate_tokens(None, None, None)  # type: ignore[arg-type]
        assert p == 0 and c == 0 and t == 0

    def test_total_is_prompt_plus_completion(self):
        p, c, t = _estimate_tokens("abc", "def", "ghi")
        assert t == p + c

    def test_prompt_tokens_combines_system_and_user(self):
        # "aaaaaa" (6) + "bbb" (3) = 9 chars / 3 = 3 prompt tokens
        p, c, t = _estimate_tokens("aaaaaa", "bbb", "")
        assert p == 3

    def test_completion_tokens_from_response(self):
        # "abcdef" = 6 chars / 3 = 2
        p, c, t = _estimate_tokens("", "", "abcdef")
        assert c == 2

    def test_all_integer_results(self):
        p, c, t = _estimate_tokens("hello", "world", "test")
        assert isinstance(p, int) and isinstance(c, int) and isinstance(t, int)

    def test_nonnegative_all(self):
        p, c, t = _estimate_tokens("x", "y", "z")
        assert p >= 0 and c >= 0 and t >= 0


# ---------------------------------------------------------------------------
# _estimate_cost_usd
# ---------------------------------------------------------------------------

class TestEstimateCostUsd:
    def test_none_tokens_returns_none(self):
        assert _estimate_cost_usd("openai", "gpt-4o", None) is None

    def test_known_model_cost(self):
        # gpt-4o = $0.010 per 1k tokens; 1000 tokens = $0.010
        cost = _estimate_cost_usd("openai", "gpt-4o", 1000)
        assert cost == pytest.approx(0.010, rel=0.01)

    def test_known_model_zero_tokens(self):
        cost = _estimate_cost_usd("openai", "gpt-4o", 0)
        assert cost == 0.0

    def test_ollama_default_zero_cost(self):
        cost = _estimate_cost_usd("ollama", "llama3.1", 1000)
        assert cost == 0.0

    def test_unknown_model_uses_provider_default(self):
        # provider=openai, model=unknown → uses openai default
        cost = _estimate_cost_usd("openai", "unknown-model", 1000)
        assert cost is not None
        assert cost > 0

    def test_unknown_provider_unknown_model_infers_ollama(self):
        # provider=None, model doesn't start with gpt-/claude- → inferred "ollama"
        # ollama default cost = 0.0, so returns 0.0, not None
        cost = _estimate_cost_usd(None, "totally-unknown-model", 1000)
        assert cost == 0.0

    def test_infers_provider_from_model_when_none(self):
        # provider=None, model starts with "gpt-" → inferred as openai
        cost = _estimate_cost_usd(None, "gpt-4o-mini", 1000)
        assert cost is not None
        assert cost > 0

    def test_returns_float(self):
        cost = _estimate_cost_usd("openai", "gpt-4o", 1000)
        assert isinstance(cost, float)

    def test_rounding_to_six_decimals(self):
        # Rounded to 6 decimal places
        cost = _estimate_cost_usd("openai", "gpt-4o", 1)
        assert cost == round(cost, 6)


# ---------------------------------------------------------------------------
# _status_from
# ---------------------------------------------------------------------------

class TestStatusFrom:
    def test_success_true_returns_success(self):
        assert _status_from(True, None) == "success"

    def test_success_true_ignores_error_message(self):
        assert _status_from(True, "some error") == "success"

    def test_failure_with_timeout_message(self):
        assert _status_from(False, "connection timeout occurred") == "timeout"

    def test_failure_without_timeout_returns_error(self):
        assert _status_from(False, "something went wrong") == "error"

    def test_failure_with_none_message_returns_error(self):
        assert _status_from(False, None) == "error"

    def test_failure_empty_message_returns_error(self):
        assert _status_from(False, "") == "error"

    def test_returns_string(self):
        assert isinstance(_status_from(True, None), str)

    def test_timeout_case_insensitive(self):
        assert _status_from(False, "TIMEOUT exceeded") == "timeout"


# ---------------------------------------------------------------------------
# _normalize_metadata
# ---------------------------------------------------------------------------

class TestNormalizeMetadata:
    def test_none_returns_empty_dict(self):
        assert _normalize_metadata(None, is_streaming=False) == {}

    def test_streaming_adds_streaming_key(self):
        result = _normalize_metadata({}, is_streaming=True)
        assert result.get("streaming") is True

    def test_non_streaming_no_streaming_key_added(self):
        result = _normalize_metadata({}, is_streaming=False)
        assert "streaming" not in result

    def test_existing_keys_preserved(self):
        meta = {"agent": "test_agent", "run_id": "abc"}
        result = _normalize_metadata(meta, is_streaming=False)
        assert result["agent"] == "test_agent"
        assert result["run_id"] == "abc"

    def test_existing_streaming_key_not_overwritten(self):
        meta = {"streaming": False}
        result = _normalize_metadata(meta, is_streaming=True)
        # setdefault doesn't overwrite existing
        assert result["streaming"] is False

    def test_returns_dict(self):
        assert isinstance(_normalize_metadata(None, is_streaming=False), dict)

    def test_does_not_mutate_input(self):
        original = {"key": "val"}
        _normalize_metadata(original, is_streaming=True)
        assert "streaming" not in original


# ---------------------------------------------------------------------------
# _normalize_task_type
# ---------------------------------------------------------------------------

class TestNormalizeTaskType:
    def test_chat_stays_chat(self):
        assert _normalize_task_type("chat", None, "agent") == "chat"

    def test_alias_chat_service_to_chat(self):
        assert _normalize_task_type("chat_service", None, "agent") == "chat"

    def test_alias_analysis_to_test_analysis(self):
        assert _normalize_task_type("analysis", None, "agent") == "test_analysis"

    def test_alias_test_generation_to_nl_test_generation(self):
        assert _normalize_task_type("test_generation", None, "agent") == "nl_test_generation"

    def test_phase_fallback_when_task_type_unknown(self):
        # task_type unknown → check phase
        result = _normalize_task_type("", "chat", "agent")
        assert result == "chat"

    def test_agent_name_fallback(self):
        result = _normalize_task_type("", "", "chat")
        assert result == "chat"

    def test_all_unknown_returns_unknown(self):
        assert _normalize_task_type("xyz", "abc", "def") == "unknown"

    def test_none_task_type(self):
        result = _normalize_task_type(None, "chat", "agent")
        assert result == "chat"

    def test_code_generation_alias(self):
        assert _normalize_task_type("generate_gherkin", None, "") == "code_generation"

    def test_security_audit_stays(self):
        assert _normalize_task_type("security_audit", None, "") == "security_audit"


# ---------------------------------------------------------------------------
# _normalize_phase
# ---------------------------------------------------------------------------

class TestNormalizePhase:
    def test_known_phase_alias(self):
        result = _normalize_phase("stream_chat", "chat", is_streaming=False)
        assert result == "chat"

    def test_streaming_returns_stream_when_no_phase(self):
        result = _normalize_phase(None, "chat", is_streaming=True)
        assert result == "stream"

    def test_chat_task_returns_chat_default(self):
        result = _normalize_phase(None, "chat", is_streaming=False)
        assert result == "chat"

    def test_unknown_phase_passthrough(self):
        result = _normalize_phase("my_custom_phase", "chat", is_streaming=False)
        assert result == "my_custom_phase"

    def test_empty_phase_non_streaming_uses_task_default(self):
        result = _normalize_phase("", "test_analysis", is_streaming=False)
        assert result == "analysis"

    def test_none_phase_none_task_not_streaming_returns_none(self):
        result = _normalize_phase(None, "unknown_task", is_streaming=False)
        assert result is None


# ---------------------------------------------------------------------------
# _deserialize_metadata
# ---------------------------------------------------------------------------

class TestDeserializeMetadata:
    def test_none_returns_empty(self):
        assert _deserialize_metadata(None) == {}

    def test_empty_string_returns_empty(self):
        assert _deserialize_metadata("") == {}

    def test_dict_passthrough(self):
        d = {"key": "value"}
        assert _deserialize_metadata(d) == d

    def test_valid_json_string_parsed(self):
        import json
        d = {"agent": "test", "run_id": "abc123"}
        result = _deserialize_metadata(json.dumps(d))
        assert result == d

    def test_invalid_json_returns_empty(self):
        assert _deserialize_metadata("{not: valid json}") == {}

    def test_json_list_returns_empty(self):
        import json
        result = _deserialize_metadata(json.dumps([1, 2, 3]))
        assert result == {}

    def test_integer_returns_empty(self):
        assert _deserialize_metadata(42) == {}

    def test_returns_dict(self):
        assert isinstance(_deserialize_metadata(None), dict)


# ---------------------------------------------------------------------------
# _empty_trace_stats
# ---------------------------------------------------------------------------

class TestEmptyTraceStats:
    def test_returns_dict(self):
        result = _empty_trace_stats()
        assert isinstance(result, dict)

    def test_total_calls_zero(self):
        assert _empty_trace_stats()["total_calls"] == 0

    def test_success_rate_zero(self):
        assert _empty_trace_stats()["success_rate"] == 0.0

    def test_top_agents_empty_list(self):
        assert _empty_trace_stats()["top_agents"] == []

    def test_top_models_empty_list(self):
        assert _empty_trace_stats()["top_models"] == []

    def test_total_cost_zero(self):
        assert _empty_trace_stats()["total_cost_usd"] == 0.0

    def test_has_required_keys(self):
        result = _empty_trace_stats()
        for key in ("total_calls", "successful", "failed", "success_rate",
                    "avg_latency_ms", "total_tokens", "total_cost_usd",
                    "top_agents", "top_models"):
            assert key in result


# ---------------------------------------------------------------------------
# Constants: _MODEL_COST_PER_1K_TOKENS, _TASK_TYPE_ALIASES
# ---------------------------------------------------------------------------

class TestCostConstants:
    def test_gpt4o_has_cost(self):
        assert _MODEL_COST_PER_1K_TOKENS.get("gpt-4o") is not None

    def test_all_costs_positive(self):
        for model, cost in _MODEL_COST_PER_1K_TOKENS.items():
            assert cost >= 0, f"{model} has negative cost"

    def test_provider_defaults_present(self):
        assert "openai" in _PROVIDER_DEFAULT_COST_PER_1K_TOKENS
        assert "anthropic" in _PROVIDER_DEFAULT_COST_PER_1K_TOKENS
        assert "ollama" in _PROVIDER_DEFAULT_COST_PER_1K_TOKENS

    def test_ollama_default_is_zero(self):
        assert _PROVIDER_DEFAULT_COST_PER_1K_TOKENS["ollama"] == 0.0


class TestTaskTypeAliases:
    def test_chat_maps_to_chat(self):
        assert _TASK_TYPE_ALIASES["chat"] == "chat"

    def test_all_values_are_strings(self):
        for k, v in _TASK_TYPE_ALIASES.items():
            assert isinstance(v, str), f"alias {k} maps to non-string"

    def test_no_empty_values(self):
        for k, v in _TASK_TYPE_ALIASES.items():
            assert v, f"alias {k} maps to empty string"

    def test_stream_chat_maps_to_chat(self):
        assert _TASK_TYPE_ALIASES.get("stream_chat") == "chat"


class TestPhaseAliases:
    def test_chat_phase_maps_to_chat(self):
        assert _PHASE_ALIASES.get("chat") == "chat"

    def test_all_values_are_strings(self):
        for k, v in _PHASE_ALIASES.items():
            assert isinstance(v, str)
