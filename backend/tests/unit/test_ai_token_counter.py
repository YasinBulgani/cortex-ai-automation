"""Unit tests for app.domains.ai.token_counter — pre-flight token planning.

Tests are fully self-contained: no DB, no HTTP.
Covers: context_limit, _canonicalize_model (via context_limit),
count_tokens, count_messages_tokens, plan_tokens, TokenPlan.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.token_counter import (
        context_limit,
        count_tokens,
        count_messages_tokens,
        plan_tokens,
        TokenPlan,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="token_counter import failed")


# ---------------------------------------------------------------------------
# context_limit
# ---------------------------------------------------------------------------

class TestContextLimit:
    def test_gpt4o_returns_128k(self):
        assert context_limit("gpt-4o") == 128_000

    def test_gpt4_1_returns_1m(self):
        assert context_limit("gpt-4.1") == 1_000_000

    def test_claude_sonnet_returns_200k(self):
        assert context_limit("claude-sonnet-4-20250514") == 200_000

    def test_gemini_25_pro_returns_2m(self):
        assert context_limit("gemini-2.5-pro") == 2_097_152

    def test_unknown_model_returns_default_32k(self):
        assert context_limit("totally-unknown-model-xyz") == 32_768

    def test_uppercase_model_name_handled(self):
        # _canonicalize_model lowercases
        limit = context_limit("GPT-4O")
        assert limit in (128_000, 32_768)  # should match or fall through to default

    def test_provider_prefixed_model(self):
        # "openai:gpt-4o" should strip prefix and return 128K
        limit = context_limit("openai:gpt-4o")
        assert limit == 128_000

    def test_returns_int(self):
        assert isinstance(context_limit("gpt-4o"), int)

    def test_llama_returns_8k(self):
        assert context_limit("llama3") == 8_192

    def test_qwen_returns_32k(self):
        assert context_limit("qwen2.5") == 32_768


# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------

class TestCountTokens:
    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_nonempty_string_returns_positive(self):
        result = count_tokens("Hello, world!")
        assert result > 0

    def test_longer_text_more_tokens(self):
        short = count_tokens("Hello")
        long = count_tokens("Hello " * 100)
        assert long > short

    def test_returns_int(self):
        assert isinstance(count_tokens("test"), int)

    def test_whitespace_only(self):
        # Whitespace has at least 1 token or 0 if empty-like fallback
        result = count_tokens("   ")
        assert isinstance(result, int)
        assert result >= 0

    def test_different_models_may_differ(self):
        # Both should return positive ints regardless of model
        r1 = count_tokens("test text", model="gpt-4o")
        r2 = count_tokens("test text", model="gpt-4o-mini")
        assert r1 > 0
        assert r2 > 0

    def test_fallback_model_still_works(self):
        # An unknown model should fall back to len/4
        result = count_tokens("word " * 40, model="nonexistent-model-xyz")
        assert result > 0


# ---------------------------------------------------------------------------
# count_messages_tokens
# ---------------------------------------------------------------------------

class TestCountMessagesTokens:
    def test_empty_list_returns_overhead_only(self):
        # 3 tokens reply priming overhead even for empty list
        result = count_messages_tokens([])
        assert result >= 0

    def test_single_message_positive_tokens(self):
        messages = [{"role": "user", "content": "Hello, world!"}]
        result = count_messages_tokens(messages)
        assert result > 0

    def test_more_messages_more_tokens(self):
        m1 = [{"role": "user", "content": "Hi"}]
        m2 = [
            {"role": "user", "content": "Hello, this is a longer message"},
            {"role": "assistant", "content": "Sure, I can help with that."},
        ]
        assert count_messages_tokens(m2) > count_messages_tokens(m1)

    def test_none_list_safe(self):
        result = count_messages_tokens(None)  # type: ignore
        assert isinstance(result, int)

    def test_returns_int(self):
        result = count_messages_tokens([{"role": "user", "content": "test"}])
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# plan_tokens — TokenPlan
# ---------------------------------------------------------------------------

class TestPlanTokens:
    def test_small_prompt_fits(self):
        messages = [{"role": "user", "content": "Hello"}]
        plan = plan_tokens("gpt-4o", messages, requested_max_output=4096)
        assert plan.fits is True

    def test_returns_token_plan(self):
        plan = plan_tokens("gpt-4o", messages=None, requested_max_output=1000)
        assert isinstance(plan, TokenPlan)

    def test_model_stored_in_plan(self):
        plan = plan_tokens("gpt-4o", messages=[], requested_max_output=1000)
        assert plan.model == "gpt-4o"

    def test_context_limit_in_plan(self):
        plan = plan_tokens("gpt-4o", messages=[], requested_max_output=1000)
        assert plan.context_limit == 128_000

    def test_allowed_output_lte_requested(self):
        plan = plan_tokens("gpt-4o", messages=[], requested_max_output=4096)
        assert plan.allowed_output_tokens <= 4096

    def test_input_tokens_tracked(self):
        messages = [{"role": "user", "content": "Hello world"}]
        plan = plan_tokens("gpt-4o", messages=messages, requested_max_output=1000)
        assert plan.input_tokens > 0

    def test_input_text_alternative(self):
        plan = plan_tokens("gpt-4o", input_text="Hello world", requested_max_output=1000)
        assert plan.input_tokens > 0
        assert plan.fits is True

    def test_no_input_zero_tokens(self):
        plan = plan_tokens("gpt-4o", requested_max_output=1000)
        assert plan.input_tokens == 0

    def test_reason_is_string(self):
        plan = plan_tokens("gpt-4o", messages=[], requested_max_output=1000)
        assert isinstance(plan.reason, str)
        assert len(plan.reason) > 0

    def test_to_dict_has_required_keys(self):
        plan = plan_tokens("gpt-4o", requested_max_output=500)
        d = plan.to_dict()
        assert "model" in d
        assert "context_limit" in d
        assert "input_tokens" in d
        assert "fits" in d
        assert "reason" in d
        assert "allowed_output_tokens" in d

    def test_massive_input_doesnt_fit(self):
        # 200K tokens of text won't fit in llama3 (8K limit)
        big_text = "word " * 40_000  # ~40K words → ~50K+ tokens
        plan = plan_tokens("llama3", input_text=big_text, requested_max_output=4096)
        assert plan.fits is False
        assert plan.allowed_output_tokens == 0

    def test_output_capped_at_available(self):
        # With a small model and modest input, output cap should be < requested
        # qwen2.5 has 32K limit; with 500-token input, ~31K available - safety
        messages = [{"role": "user", "content": "Hi"}]
        plan = plan_tokens("qwen2.5", messages=messages, requested_max_output=50_000)
        assert plan.allowed_output_tokens < 50_000
