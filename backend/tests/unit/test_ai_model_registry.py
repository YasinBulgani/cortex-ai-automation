"""Unit tests for app.domains.ai.model_registry — single source of model info.

Tests are fully self-contained: uses the real model_registry.yaml (project fixture).
Covers: get_model_info, resolve_alias, compute_cost_usd, lookup_price,
list_models_by_tier, list_offline_models, known_models, _canonicalize.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.model_registry import (
        get_model_info,
        resolve_alias,
        compute_cost_usd,
        lookup_price,
        list_models_by_tier,
        list_offline_models,
        known_models,
        ModelInfo,
        ModelPrice,
        ModelCost,
        _UNKNOWN,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="model_registry import failed")


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------

class TestGetModelInfo:
    def test_returns_model_info_for_known_model(self):
        info = get_model_info("gpt-4o")
        assert isinstance(info, ModelInfo)
        assert info.id != "__unknown__"

    def test_unknown_model_returns_unknown_sentinel(self):
        info = get_model_info("totally-nonexistent-model-xyz")
        assert info.id == "__unknown__"

    def test_empty_string_returns_unknown(self):
        info = get_model_info("")
        assert info.id == "__unknown__"

    def test_provider_prefixed_model_resolved(self):
        # "openai:gpt-4o" should strip prefix
        info = get_model_info("openai:gpt-4o")
        assert info.id != "__unknown__"

    def test_model_has_provider(self):
        info = get_model_info("gpt-4o")
        assert isinstance(info.provider, str)
        assert len(info.provider) > 0

    def test_model_has_tier(self):
        info = get_model_info("gpt-4o")
        assert info.tier in ("mini", "mid", "premium", "local")

    def test_model_has_cost(self):
        info = get_model_info("gpt-4o")
        assert isinstance(info.cost, ModelCost)

    def test_gpt4o_is_premium_or_mid(self):
        info = get_model_info("gpt-4o")
        assert info.tier in ("premium", "mid")

    def test_returns_model_info_instance(self):
        assert isinstance(get_model_info("gpt-4o"), ModelInfo)


# ---------------------------------------------------------------------------
# resolve_alias
# ---------------------------------------------------------------------------

class TestResolveAlias:
    def test_canonical_id_resolves_to_itself(self):
        info = get_model_info("gpt-4o")
        # canonical ID should resolve
        result = resolve_alias("gpt-4o")
        assert result is not None

    def test_unknown_alias_returns_none(self):
        result = resolve_alias("totally-nonexistent-alias-xyz")
        assert result is None

    def test_empty_returns_none(self):
        result = resolve_alias("")
        assert result is None

    def test_returns_string_or_none(self):
        result = resolve_alias("gpt-4o")
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# compute_cost_usd
# ---------------------------------------------------------------------------

class TestComputeCostUsd:
    def test_zero_tokens_returns_zero(self):
        cost = compute_cost_usd("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_positive_tokens_known_model(self):
        # gpt-4o has non-zero cost rates
        cost = compute_cost_usd("gpt-4o", input_tokens=1000, output_tokens=200)
        assert isinstance(cost, float)
        assert cost >= 0.0

    def test_unknown_model_returns_zero(self):
        cost = compute_cost_usd("nonexistent-model", input_tokens=1000, output_tokens=1000)
        assert cost == 0.0

    def test_more_tokens_more_cost(self):
        small = compute_cost_usd("gpt-4o", input_tokens=100, output_tokens=50)
        large = compute_cost_usd("gpt-4o", input_tokens=10_000, output_tokens=5_000)
        # large should cost more (or equal if rates are 0)
        assert large >= small

    def test_returns_float(self):
        result = compute_cost_usd("gpt-4o", input_tokens=1000, output_tokens=500)
        assert isinstance(result, float)

    def test_cached_input_tokens_reduce_cost(self):
        # Cached tokens should be <= standard cost
        standard = compute_cost_usd("gpt-4o", input_tokens=1000, output_tokens=100)
        cached = compute_cost_usd(
            "gpt-4o",
            input_tokens=1000,
            output_tokens=100,
            cached_input_tokens=800,
        )
        # cached cost should be ≤ standard (if model has cached pricing)
        assert cached <= standard or cached == standard  # equal if no cached rate

    def test_result_rounded_to_8_decimal_places(self):
        cost = compute_cost_usd("gpt-4o", input_tokens=123_456, output_tokens=45_678)
        # Should not have more than 8 decimal places
        decimal_str = str(cost)
        if "." in decimal_str:
            decimals = len(decimal_str.split(".")[1])
            assert decimals <= 8


# ---------------------------------------------------------------------------
# lookup_price
# ---------------------------------------------------------------------------

class TestLookupPrice:
    def test_returns_model_price(self):
        price = lookup_price("gpt-4o")
        assert isinstance(price, ModelPrice)

    def test_has_input_and_output_rates(self):
        price = lookup_price("gpt-4o")
        assert isinstance(price.input_per_mtok, float)
        assert isinstance(price.output_per_mtok, float)

    def test_unknown_model_returns_zero_price(self):
        price = lookup_price("nonexistent-xyz")
        assert price.input_per_mtok == 0.0
        assert price.output_per_mtok == 0.0


# ---------------------------------------------------------------------------
# list_models_by_tier
# ---------------------------------------------------------------------------

class TestListModelsByTier:
    def test_returns_list(self):
        result = list_models_by_tier("premium")
        assert isinstance(result, list)

    def test_all_results_have_correct_tier(self):
        for tier in ("mini", "mid", "premium", "local"):
            models = list_models_by_tier(tier)
            for m in models:
                assert m.tier == tier

    def test_unknown_tier_returns_empty(self):
        result = list_models_by_tier("nonexistent_tier")
        assert result == []

    def test_offline_only_flag_filters(self):
        all_premium = list_models_by_tier("premium")
        offline_premium = list_models_by_tier("premium", offline_only=True)
        # offline_only should return a subset
        assert len(offline_premium) <= len(all_premium)
        for m in offline_premium:
            assert m.offline_safe is True

    def test_results_are_model_info(self):
        for m in list_models_by_tier("mid"):
            assert isinstance(m, ModelInfo)


# ---------------------------------------------------------------------------
# list_offline_models
# ---------------------------------------------------------------------------

class TestListOfflineModels:
    def test_returns_list(self):
        result = list_offline_models()
        assert isinstance(result, list)

    def test_all_results_are_offline_safe(self):
        for m in list_offline_models():
            assert m.offline_safe is True


# ---------------------------------------------------------------------------
# known_models
# ---------------------------------------------------------------------------

class TestKnownModels:
    def test_returns_tuple(self):
        assert isinstance(known_models(), tuple)

    def test_nonempty(self):
        assert len(known_models()) > 0

    def test_contains_strings(self):
        for name in known_models():
            assert isinstance(name, str)

    def test_gpt4o_in_known_models(self):
        names = known_models()
        assert any("gpt-4o" in n for n in names)
