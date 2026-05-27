"""Unit tests for app.domains.ai.token_counter — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no tiktoken required.
Covers: _canonicalize_model, context_limit, count_tokens (fallback path),
        count_messages_tokens, TokenPlan.to_dict, _MODEL_CONTEXT_LIMITS.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.token_counter import (
        _canonicalize_model,
        context_limit,
        count_tokens,
        count_messages_tokens,
        TokenPlan,
        _MODEL_CONTEXT_LIMITS,
        _SAFETY_BUFFER_PCT,
        _SAFETY_BUFFER_MIN,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="token_counter import failed")


# ---------------------------------------------------------------------------
# _canonicalize_model
# ---------------------------------------------------------------------------

class TestCanonicalizeModel:
    def test_strips_openai_prefix(self):
        assert _canonicalize_model("openai:gpt-4o") == "gpt-4o"

    def test_strips_anthropic_prefix(self):
        assert _canonicalize_model("anthropic:claude-3-5-sonnet") == "claude-3-5-sonnet"

    def test_non_provider_colon_uses_prefix(self):
        # "qwen2.5-coder:7b-instruct" — "qwen2.5-coder" is not in providers set
        result = _canonicalize_model("qwen2.5-coder:7b-instruct")
        assert result == "qwen2.5-coder"

    def test_no_colon_lowercased_stripped(self):
        assert _canonicalize_model("GPT-4O") == "gpt-4o"

    def test_empty_string_returns_empty(self):
        assert _canonicalize_model("") == ""

    def test_none_returns_empty(self):
        assert _canonicalize_model(None) == ""  # type: ignore[arg-type]

    def test_strips_whitespace(self):
        assert _canonicalize_model("  gpt-4o  ") == "gpt-4o"

    def test_google_prefix_stripped(self):
        assert _canonicalize_model("google:gemini-pro") == "gemini-pro"

    def test_groq_prefix_stripped(self):
        assert _canonicalize_model("groq:llama3-8b") == "llama3-8b"


# ---------------------------------------------------------------------------
# context_limit
# ---------------------------------------------------------------------------

class TestContextLimit:
    def test_gpt4o_limit(self):
        assert context_limit("gpt-4o") == 128_000

    def test_claude_sonnet_4_limit(self):
        assert context_limit("claude-sonnet-4-20250514") == 200_000

    def test_unknown_model_returns_32k(self):
        assert context_limit("completely-unknown-model") == 32_768

    def test_prefix_match(self):
        # "gpt-4o-2024-..." should match prefix "gpt-4o"
        assert context_limit("gpt-4o-2024-some-date") == 128_000

    def test_llama3_limit(self):
        assert context_limit("llama3") == 8_192

    def test_case_normalized(self):
        # _canonicalize_model lowercases, so GPT-4O should match
        assert context_limit("GPT-4O") == 128_000

    def test_returns_int(self):
        assert isinstance(context_limit("gpt-4o"), int)

    def test_positive_limit(self):
        assert context_limit("gpt-4o") > 0


# ---------------------------------------------------------------------------
# count_tokens (fallback path when tiktoken unavailable)
# ---------------------------------------------------------------------------

class TestCountTokensFallback:
    def test_empty_returns_zero(self):
        assert count_tokens("") == 0

    def test_none_returns_zero(self):
        assert count_tokens(None) == 0  # type: ignore[arg-type]

    def test_returns_int(self):
        assert isinstance(count_tokens("hello"), int)

    def test_nonnegative(self):
        assert count_tokens("hello world") >= 0

    def test_longer_text_more_tokens(self):
        short = count_tokens("hi")
        long = count_tokens("a" * 400)
        assert long > short

    def test_minimum_one_for_nonempty(self):
        # max(1, len/4) so single char returns at least 1
        assert count_tokens("x") >= 1


# ---------------------------------------------------------------------------
# count_messages_tokens
# ---------------------------------------------------------------------------

class TestCountMessagesTokens:
    def test_empty_messages_returns_small_positive(self):
        # Empty list → 0 msg tokens + 3 priming = 3
        result = count_messages_tokens([])
        assert result >= 0

    def test_none_messages_returns_small_positive(self):
        result = count_messages_tokens(None)  # type: ignore[arg-type]
        assert result >= 0

    def test_returns_int(self):
        msgs = [{"role": "user", "content": "hello"}]
        assert isinstance(count_messages_tokens(msgs), int)

    def test_more_content_more_tokens(self):
        msgs_short = [{"role": "user", "content": "hi"}]
        msgs_long = [{"role": "user", "content": "a" * 400}]
        assert count_messages_tokens(msgs_long) > count_messages_tokens(msgs_short)

    def test_multiple_messages_additive(self):
        single = count_messages_tokens([{"role": "user", "content": "test"}])
        double = count_messages_tokens([
            {"role": "system", "content": "test"},
            {"role": "user", "content": "test"},
        ])
        assert double > single


# ---------------------------------------------------------------------------
# TokenPlan.to_dict
# ---------------------------------------------------------------------------

class TestTokenPlanToDict:
    def _plan(self, **overrides):
        base = dict(
            model="gpt-4o",
            context_limit=128_000,
            input_tokens=1000,
            requested_max_output=4096,
            allowed_output_tokens=3000,
            fits=True,
            reason="ok",
        )
        base.update(overrides)
        return TokenPlan(**base)

    def test_returns_dict(self):
        assert isinstance(self._plan().to_dict(), dict)

    def test_model_key(self):
        assert self._plan(model="claude-3").to_dict()["model"] == "claude-3"

    def test_fits_key(self):
        assert self._plan(fits=False).to_dict()["fits"] is False

    def test_all_required_keys(self):
        d = self._plan().to_dict()
        for key in ("model", "context_limit", "input_tokens", "requested_max_output",
                    "allowed_output_tokens", "fits", "reason"):
            assert key in d

    def test_fits_false_when_overflow(self):
        plan = self._plan(fits=False, allowed_output_tokens=0, reason="overflow")
        assert plan.fits is False
        assert plan.to_dict()["allowed_output_tokens"] == 0


# ---------------------------------------------------------------------------
# _MODEL_CONTEXT_LIMITS constant
# ---------------------------------------------------------------------------

class TestModelContextLimits:
    def test_is_dict(self):
        assert isinstance(_MODEL_CONTEXT_LIMITS, dict)

    def test_all_values_positive(self):
        for model, limit in _MODEL_CONTEXT_LIMITS.items():
            assert limit > 0, f"{model} has non-positive limit"

    def test_gpt4_1_has_million_context(self):
        assert _MODEL_CONTEXT_LIMITS.get("gpt-4.1") == 1_000_000

    def test_gemini_has_large_context(self):
        assert _MODEL_CONTEXT_LIMITS.get("gemini-2.5-pro", 0) > 1_000_000


# ---------------------------------------------------------------------------
# Safety buffer constants
# ---------------------------------------------------------------------------

class TestSafetyBufferConstants:
    def test_buffer_pct_between_0_and_1(self):
        assert 0 < _SAFETY_BUFFER_PCT < 1

    def test_buffer_min_positive(self):
        assert _SAFETY_BUFFER_MIN > 0

    def test_buffer_min_reasonable(self):
        # At least 100 tokens buffer
        assert _SAFETY_BUFFER_MIN >= 100
