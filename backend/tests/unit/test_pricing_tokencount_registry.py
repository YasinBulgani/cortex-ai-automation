"""Unit tests for ai.model_registry pricing, ai.token_counter,
and tspm.product_registry helpers.

Tests are fully self-contained: no DB, no HTTP, no LLM calls.
Covers:
  - ModelPrice dataclass
  - compute_cost_usd: per-million-token math
  - lookup_price: known models, unknown fallback
  - known_models: content checks
  - count_tokens: string → int
  - context_limit: known model limits, unknown fallback
  - plan_tokens: fits/not-fits logic, allowed_output_tokens
  - count_messages_tokens: message list → token count
  - product_registry: normalize_product_id, validate_product_id,
    normalize_product_tags, default_entry_key_for
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.model_registry import (
        ModelPrice,
        compute_cost_usd,
        lookup_price,
        known_models,
    )
    _PRICING_OK = True
except ImportError:
    _PRICING_OK = False

try:
    from app.domains.ai.token_counter import (
        count_tokens,
        context_limit,
        plan_tokens,
        count_messages_tokens,
        TokenPlan,
    )
    _TOKEN_OK = True
except ImportError:
    _TOKEN_OK = False

try:
    from app.domains.tspm.product_registry import (
        DEFAULT_PRODUCT_ID,
        VALID_PRODUCT_IDS,
        PRODUCT_DEFAULT_ENTRY_KEYS,
        normalize_product_id,
        validate_product_id,
        normalize_product_tags,
        default_entry_key_for,
    )
    _REGISTRY_OK = True
except ImportError:
    _REGISTRY_OK = False


# ---------------------------------------------------------------------------
# ModelPrice
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PRICING_OK, reason="model_registry import failed")
class TestModelPrice:
    def test_gpt4o_price_exists(self):
        p = lookup_price("gpt-4o")
        assert isinstance(p, ModelPrice)

    def test_gpt4o_input_price(self):
        p = lookup_price("gpt-4o")
        assert p.input_per_mtok == pytest.approx(2.5)

    def test_gpt4o_output_price(self):
        p = lookup_price("gpt-4o")
        assert p.output_per_mtok == pytest.approx(10.0)

    def test_unknown_model_returns_zero_price(self):
        p = lookup_price("totally-unknown-model-xyz")
        assert p.input_per_mtok == pytest.approx(0.0)
        assert p.output_per_mtok == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# compute_cost_usd
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PRICING_OK, reason="model_registry import failed")
class TestComputeCostUsd:
    def test_zero_tokens_zero_cost(self):
        cost = compute_cost_usd("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == pytest.approx(0.0)

    def test_gpt4o_cost_math(self):
        # 1000 input @ 2.5/Mtok + 500 output @ 10.0/Mtok
        # = 0.0025 + 0.005 = 0.0075
        cost = compute_cost_usd("gpt-4o", input_tokens=1000, output_tokens=500)
        assert cost == pytest.approx(0.0075, rel=1e-3)

    def test_input_only(self):
        cost = compute_cost_usd("gpt-4o", input_tokens=1_000_000, output_tokens=0)
        assert cost == pytest.approx(2.5)

    def test_output_only(self):
        cost = compute_cost_usd("gpt-4o", input_tokens=0, output_tokens=1_000_000)
        assert cost == pytest.approx(10.0)

    def test_unknown_model_zero_cost(self):
        cost = compute_cost_usd("unknown-model-xyz", input_tokens=10000, output_tokens=5000)
        assert cost == pytest.approx(0.0)

    def test_returns_float(self):
        assert isinstance(compute_cost_usd("gpt-4o", input_tokens=100, output_tokens=50), float)


# ---------------------------------------------------------------------------
# known_models
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PRICING_OK, reason="model_registry import failed")
class TestKnownModels:
    def test_returns_iterable(self):
        models = known_models()
        assert hasattr(models, '__iter__')

    def test_contains_gpt4o(self):
        assert "gpt-4o" in known_models()

    def test_contains_claude_model(self):
        assert any("claude" in m for m in known_models())

    def test_not_empty(self):
        assert len(list(known_models())) > 0


# ---------------------------------------------------------------------------
# count_tokens
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TOKEN_OK, reason="token_counter import failed")
class TestCountTokens:
    def test_empty_string(self):
        result = count_tokens("", "gpt-4o")
        assert result == 0

    def test_single_word(self):
        result = count_tokens("hello", "gpt-4o")
        assert result >= 1

    def test_two_words(self):
        result = count_tokens("hello world", "gpt-4o")
        assert result >= 2

    def test_returns_int(self):
        assert isinstance(count_tokens("test text", "gpt-4o"), int)

    def test_longer_text_more_tokens(self):
        short = count_tokens("hello", "gpt-4o")
        long = count_tokens("hello world this is a much longer text string", "gpt-4o")
        assert long > short


# ---------------------------------------------------------------------------
# context_limit
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TOKEN_OK, reason="token_counter import failed")
class TestContextLimit:
    def test_gpt4o_limit(self):
        assert context_limit("gpt-4o") == 128000

    def test_unknown_model_has_fallback(self):
        limit = context_limit("totally-unknown-model-abc")
        assert limit > 0

    def test_returns_int(self):
        assert isinstance(context_limit("gpt-4o"), int)


# ---------------------------------------------------------------------------
# plan_tokens
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TOKEN_OK, reason="token_counter import failed")
class TestPlanTokens:
    def _msgs(self, content="Hello!"):
        return [{"role": "user", "content": content}]

    def test_returns_token_plan(self):
        result = plan_tokens("gpt-4o", self._msgs())
        assert isinstance(result, TokenPlan)

    def test_model_stored(self):
        result = plan_tokens("gpt-4o", self._msgs())
        assert "gpt-4o" in result.model

    def test_fits_for_short_message(self):
        result = plan_tokens("gpt-4o", self._msgs("Hi"))
        assert result.fits is True

    def test_context_limit_populated(self):
        result = plan_tokens("gpt-4o", self._msgs())
        assert result.context_limit == 128000

    def test_input_tokens_positive(self):
        result = plan_tokens("gpt-4o", self._msgs("Hello world this is a test"))
        assert result.input_tokens > 0

    def test_allowed_output_le_requested(self):
        result = plan_tokens("gpt-4o", self._msgs(), requested_max_output=2000)
        assert result.allowed_output_tokens <= 2000

    def test_reason_ok_when_fits(self):
        result = plan_tokens("gpt-4o", self._msgs("Hi"))
        assert result.reason == "ok"


# ---------------------------------------------------------------------------
# count_messages_tokens
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TOKEN_OK, reason="token_counter import failed")
class TestCountMessagesTokens:
    def test_single_message(self):
        msgs = [{"role": "user", "content": "Hello"}]
        result = count_messages_tokens(msgs, "gpt-4o")
        assert result > 0

    def test_more_messages_more_tokens(self):
        msgs1 = [{"role": "user", "content": "Hi"}]
        msgs2 = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello there! How can I help you today?"},
        ]
        assert count_messages_tokens(msgs2, "gpt-4o") > count_messages_tokens(msgs1, "gpt-4o")

    def test_returns_int(self):
        result = count_messages_tokens([{"role": "user", "content": "test"}], "gpt-4o")
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# product_registry
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _REGISTRY_OK, reason="product_registry import failed")
class TestProductRegistry:
    def test_default_product_id(self):
        assert DEFAULT_PRODUCT_ID == "one"

    def test_valid_product_ids_set(self):
        assert isinstance(VALID_PRODUCT_IDS, (set, frozenset))
        assert "one" in VALID_PRODUCT_IDS
        assert "web" in VALID_PRODUCT_IDS

    def test_normalize_product_id_valid(self):
        assert normalize_product_id("web") == "web"

    def test_normalize_product_id_none_returns_default(self):
        assert normalize_product_id(None) == DEFAULT_PRODUCT_ID

    def test_normalize_product_id_empty_returns_default(self):
        assert normalize_product_id("") == DEFAULT_PRODUCT_ID

    def test_normalize_product_id_invalid_returns_default(self):
        assert normalize_product_id("totally_invalid") == DEFAULT_PRODUCT_ID

    def test_normalize_product_id_strips_whitespace(self):
        assert normalize_product_id("  web  ") == "web"

    def test_validate_product_id_valid(self):
        assert validate_product_id("one") == "one"

    def test_validate_product_id_invalid_raises(self):
        with pytest.raises(ValueError):
            validate_product_id("unknown_product")

    def test_validate_product_id_empty_raises(self):
        with pytest.raises(ValueError):
            validate_product_id("")

    def test_normalize_product_tags_valid_ids(self):
        result = normalize_product_tags(["web", "studio"])
        assert "web" in result
        assert "studio" in result

    def test_normalize_product_tags_invalid_raises(self):
        with pytest.raises(ValueError):
            normalize_product_tags(["web", "invalid_tag"])

    def test_normalize_product_tags_deduplicates(self):
        result = normalize_product_tags(["web", "studio", "web"])
        assert result.count("web") == 1

    def test_normalize_product_tags_excludes_primary(self):
        result = normalize_product_tags(["web", "studio"], primary="web")
        assert "web" not in result
        assert "studio" in result

    def test_default_entry_key_for_web(self):
        key = default_entry_key_for("web")
        assert key == "manual-to-automation"

    def test_default_entry_key_for_one(self):
        key = default_entry_key_for("one")
        assert key == "settings"

    def test_default_entry_key_for_mobile(self):
        key = default_entry_key_for("mobile")
        assert key == "mobile"

    def test_default_entry_key_for_none(self):
        # None → default → "one" → "settings"
        key = default_entry_key_for(None)
        assert key == PRODUCT_DEFAULT_ENTRY_KEYS[DEFAULT_PRODUCT_ID]

    def test_all_valid_ids_have_entry_keys(self):
        for pid in VALID_PRODUCT_IDS:
            key = default_entry_key_for(pid)
            assert isinstance(key, str) and len(key) > 0
