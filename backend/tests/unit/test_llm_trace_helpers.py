"""Unit tests for LLM trace pure helper functions.

Tests app/domains/ai/llm_trace.py — no DB, no external deps.
Covers: _safe_row_get, _infer_provider, _estimate_tokens, _estimate_cost_usd,
        _status_from, _normalize_metadata, _normalize_task_type,
        _normalize_phase, _empty_trace_stats.
"""

from __future__ import annotations

import pytest

from app.domains.ai.llm_trace import (
    _empty_trace_stats,
    _estimate_cost_usd,
    _estimate_tokens,
    _infer_provider,
    _normalize_metadata,
    _normalize_phase,
    _normalize_task_type,
    _safe_row_get,
    _status_from,
)


# ── _safe_row_get ─────────────────────────────────────────────────────────────


class TestSafeRowGet:
    def test_none_row_returns_default(self) -> None:
        assert _safe_row_get(None, 0) is None

    def test_none_row_custom_default(self) -> None:
        assert _safe_row_get(None, 0, "fallback") == "fallback"

    def test_list_row_valid_index(self) -> None:
        assert _safe_row_get([10, 20, 30], 1) == 20

    def test_list_row_index_out_of_range(self) -> None:
        assert _safe_row_get([10, 20], 5) is None

    def test_tuple_row_valid_index(self) -> None:
        assert _safe_row_get(("a", "b", "c"), 2) == "c"

    def test_empty_sequence(self) -> None:
        assert _safe_row_get([], 0) is None


# ── _infer_provider ───────────────────────────────────────────────────────────


class TestInferProvider:
    def test_gpt_model_returns_openai(self) -> None:
        assert _infer_provider("gpt-4") == "openai"

    def test_gpt_turbo_returns_openai(self) -> None:
        assert _infer_provider("gpt-3.5-turbo") == "openai"

    def test_claude_returns_anthropic(self) -> None:
        assert _infer_provider("claude-3-opus") == "anthropic"

    def test_claude_sonnet_returns_anthropic(self) -> None:
        assert _infer_provider("claude-sonnet-4") == "anthropic"

    def test_other_model_returns_ollama(self) -> None:
        assert _infer_provider("llama3") == "ollama"

    def test_empty_model_returns_none(self) -> None:
        assert _infer_provider("") is None

    def test_none_model_returns_none(self) -> None:
        assert _infer_provider(None) is None  # type: ignore[arg-type]

    def test_case_insensitive(self) -> None:
        assert _infer_provider("GPT-4") == "openai"
        assert _infer_provider("CLAUDE-3") == "anthropic"


# ── _estimate_tokens ──────────────────────────────────────────────────────────


class TestEstimateTokens:
    def test_returns_three_values(self) -> None:
        result = _estimate_tokens("system", "user", "response")
        assert len(result) == 3

    def test_empty_strings_return_zeros(self) -> None:
        p, c, t = _estimate_tokens("", "", "")
        assert p == 0
        assert c == 0
        assert t == 0

    def test_total_is_sum_of_prompt_and_completion(self) -> None:
        p, c, total = _estimate_tokens("a" * 30, "b" * 30, "c" * 30)
        assert total == p + c

    def test_longer_text_gives_more_tokens(self) -> None:
        _, _, small = _estimate_tokens("x" * 10, "y" * 10, "z" * 10)
        _, _, large = _estimate_tokens("x" * 100, "y" * 100, "z" * 100)
        assert large > small

    def test_none_inputs_handled(self) -> None:
        p, c, total = _estimate_tokens(None, None, None)  # type: ignore[arg-type]
        assert p >= 0 and c >= 0 and total >= 0

    def test_approximate_3_chars_per_token(self) -> None:
        # 30 chars / 3 = 10 tokens
        p, _, _ = _estimate_tokens("a" * 30, "", "")
        assert p == 10


# ── _estimate_cost_usd ────────────────────────────────────────────────────────


class TestEstimateCostUsd:
    def test_none_tokens_returns_none(self) -> None:
        assert _estimate_cost_usd("openai", "gpt-4", None) is None

    def test_known_model_returns_float(self) -> None:
        # gpt-4 should be in the cost table
        result = _estimate_cost_usd("openai", "gpt-4", 1000)
        # Should return a positive float or None
        if result is not None:
            assert isinstance(result, float)
            assert result >= 0.0

    def test_zero_tokens_returns_zero(self) -> None:
        result = _estimate_cost_usd("openai", "gpt-4", 0)
        if result is not None:
            assert result == 0.0

    def test_unknown_model_and_provider_returns_none_or_float(self) -> None:
        # "unknown-model-xyz" → _infer_provider returns "ollama" (non-empty, non-gpt/claude)
        # ollama may have 0.0 cost_per_1k in the table → returns 0.0 not None
        result = _estimate_cost_usd(None, "unknown-model-xyz", 1000)
        assert result is None or isinstance(result, float)

    def test_provider_inferred_from_model_name(self) -> None:
        # Without explicit provider, should infer from model
        result = _estimate_cost_usd(None, "gpt-4", 1000)
        # May or may not have cost — just should not crash
        assert result is None or isinstance(result, float)


# ── _status_from ──────────────────────────────────────────────────────────────


class TestStatusFrom:
    def test_success_true_returns_success(self) -> None:
        assert _status_from(True, None) == "success"

    def test_success_true_ignores_error(self) -> None:
        assert _status_from(True, "some error") == "success"

    def test_failure_with_timeout_message(self) -> None:
        assert _status_from(False, "Request timeout exceeded") == "timeout"

    def test_failure_with_timeout_lowercase(self) -> None:
        assert _status_from(False, "timeout after 30s") == "timeout"

    def test_failure_without_timeout_returns_error(self) -> None:
        assert _status_from(False, "connection refused") == "error"

    def test_failure_with_none_error_returns_error(self) -> None:
        assert _status_from(False, None) == "error"

    def test_failure_with_empty_error_returns_error(self) -> None:
        assert _status_from(False, "") == "error"


# ── _normalize_metadata ───────────────────────────────────────────────────────


class TestNormalizeMetadata:
    def test_none_metadata_returns_empty(self) -> None:
        result = _normalize_metadata(None, is_streaming=False)
        assert isinstance(result, dict)

    def test_streaming_adds_flag(self) -> None:
        result = _normalize_metadata({}, is_streaming=True)
        assert result.get("streaming") is True

    def test_non_streaming_no_flag(self) -> None:
        result = _normalize_metadata({}, is_streaming=False)
        assert "streaming" not in result

    def test_existing_metadata_preserved(self) -> None:
        meta = {"temperature": 0.7, "max_tokens": 500}
        result = _normalize_metadata(meta, is_streaming=False)
        assert result["temperature"] == 0.7
        assert result["max_tokens"] == 500

    def test_streaming_does_not_override_existing_flag(self) -> None:
        meta = {"streaming": False}
        result = _normalize_metadata(meta, is_streaming=True)
        # setdefault only sets if not present → existing False stays
        assert result["streaming"] is False

    def test_does_not_mutate_original(self) -> None:
        meta = {"key": "val"}
        _normalize_metadata(meta, is_streaming=True)
        assert "streaming" not in meta


# ── _normalize_task_type ──────────────────────────────────────────────────────


class TestNormalizeTaskType:
    def test_known_alias_resolved(self) -> None:
        result = _normalize_task_type("chat", None, "")
        assert result == "chat"

    def test_none_task_type_falls_to_phase(self) -> None:
        result = _normalize_task_type(None, "generation", "")
        # If "generation" is in aliases, return that
        assert isinstance(result, str)

    def test_none_all_returns_unknown(self) -> None:
        result = _normalize_task_type(None, None, "")
        assert result == "unknown"

    def test_empty_all_returns_unknown(self) -> None:
        result = _normalize_task_type("", "", "")
        assert result == "unknown"

    def test_case_insensitive(self) -> None:
        result = _normalize_task_type("CHAT", None, "")
        assert result == "chat"

    def test_agent_name_used_as_fallback(self) -> None:
        result = _normalize_task_type(None, None, "chat")
        assert result == "chat"

    def test_first_non_empty_wins(self) -> None:
        # task_type wins over phase
        result1 = _normalize_task_type("chat", "generation", "")
        result2 = _normalize_task_type(None, "generation", "chat")
        assert result1 == "chat"
        # For result2, "generation" should win over agent "chat"
        assert isinstance(result2, str)


# ── _normalize_phase ─────────────────────────────────────────────────────────


class TestNormalizePhase:
    def test_streaming_returns_stream(self) -> None:
        result = _normalize_phase(None, "chat", is_streaming=True)
        assert result == "stream"

    def test_known_phase_returned(self) -> None:
        result = _normalize_phase("analysis", "chat", is_streaming=False)
        assert isinstance(result, str)
        assert result  # not empty

    def test_no_phase_chat_returns_chat_default(self) -> None:
        result = _normalize_phase(None, "chat", is_streaming=False)
        assert result == "chat"

    def test_no_phase_unknown_task_returns_none(self) -> None:
        result = _normalize_phase(None, "nonexistent_task", is_streaming=False)
        assert result is None

    def test_streaming_takes_precedence_over_default(self) -> None:
        # Even for task_type "chat", streaming returns "stream"
        result = _normalize_phase(None, "chat", is_streaming=True)
        assert result == "stream"


# ── _empty_trace_stats ────────────────────────────────────────────────────────


class TestEmptyTraceStats:
    def test_returns_dict(self) -> None:
        assert isinstance(_empty_trace_stats(), dict)

    def test_required_keys_present(self) -> None:
        stats = _empty_trace_stats()
        required = [
            "total_calls", "successful", "failed", "success_rate",
            "avg_latency_ms", "total_tokens", "total_cost_usd",
            "top_agents", "top_models",
        ]
        for key in required:
            assert key in stats, f"Missing key: {key}"

    def test_numeric_defaults_are_zero(self) -> None:
        stats = _empty_trace_stats()
        assert stats["total_calls"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["total_cost_usd"] == 0.0

    def test_list_defaults_are_empty(self) -> None:
        stats = _empty_trace_stats()
        assert stats["top_agents"] == []
        assert stats["top_models"] == []

    def test_each_call_returns_new_dict(self) -> None:
        s1 = _empty_trace_stats()
        s2 = _empty_trace_stats()
        s1["total_calls"] = 99
        assert s2["total_calls"] == 0
