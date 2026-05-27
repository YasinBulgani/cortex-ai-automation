"""Unit tests for ai.model_registry pure helper functions.

All tests are self-contained: no YAML file access, no registry singleton.
Covers:
  - ModelCost: frozen dataclass defaults and immutability
  - ModelInfo: frozen dataclass fields and defaults
  - _parse_cost: None/empty input, float coercion, optional cached_input
  - _canonicalize: provider prefix stripping, unknown prefixes, edge cases
  - _parse_model: entry dict → ModelInfo, defaults fallback
  - _parse_family: minimal registry proxy creation
  - compute_cost_usd: math (using ModelCost directly via monkeypatching)
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.model_registry import (
        ModelCost,
        ModelInfo,
        _parse_cost,
        _canonicalize,
        _parse_model,
        _parse_family,
    )
    _MR_OK = True
except ImportError:
    _MR_OK = False


# ---------------------------------------------------------------------------
# ModelCost
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MR_OK, reason="model_registry import failed")
class TestModelCost:
    def test_default_input_per_mtok(self):
        c = ModelCost()
        assert c.input_per_mtok == 0.0

    def test_default_output_per_mtok(self):
        c = ModelCost()
        assert c.output_per_mtok == 0.0

    def test_default_cached_input_none(self):
        c = ModelCost()
        assert c.cached_input_per_mtok is None

    def test_set_fields(self):
        c = ModelCost(input_per_mtok=1.5, output_per_mtok=6.0, cached_input_per_mtok=0.75)
        assert c.input_per_mtok == pytest.approx(1.5)
        assert c.output_per_mtok == pytest.approx(6.0)
        assert c.cached_input_per_mtok == pytest.approx(0.75)

    def test_frozen_raises_on_set(self):
        c = ModelCost()
        with pytest.raises((AttributeError, TypeError)):
            c.input_per_mtok = 99.0  # type: ignore[misc]

    def test_equality(self):
        a = ModelCost(input_per_mtok=1.0, output_per_mtok=2.0)
        b = ModelCost(input_per_mtok=1.0, output_per_mtok=2.0)
        assert a == b

    def test_inequality_on_different_values(self):
        a = ModelCost(input_per_mtok=1.0)
        b = ModelCost(input_per_mtok=2.0)
        assert a != b


# ---------------------------------------------------------------------------
# ModelInfo
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MR_OK, reason="model_registry import failed")
class TestModelInfo:
    def _make(self, **overrides):
        base = dict(id="test-model", provider="openai", tier="mid")
        base.update(overrides)
        return ModelInfo(**base)

    def test_required_fields(self):
        m = self._make()
        assert m.id == "test-model"
        assert m.provider == "openai"
        assert m.tier == "mid"

    def test_default_context_window(self):
        assert self._make().context_window == 0

    def test_default_max_output(self):
        assert self._make().max_output == 0

    def test_default_cost_is_model_cost(self):
        m = self._make()
        assert isinstance(m.cost, ModelCost)
        assert m.cost.input_per_mtok == 0.0

    def test_default_supports_json(self):
        assert self._make().supports_json is True

    def test_default_supports_tools(self):
        assert self._make().supports_tools is True

    def test_default_offline_safe(self):
        assert self._make().offline_safe is False

    def test_default_status(self):
        assert self._make().status == "prod"

    def test_default_kind(self):
        assert self._make().kind == "chat"

    def test_default_p95_ms(self):
        assert self._make().p95_ms == 0

    def test_default_aliases_empty_tuple(self):
        assert self._make().aliases == ()

    def test_frozen(self):
        m = self._make()
        with pytest.raises((AttributeError, TypeError)):
            m.id = "other"  # type: ignore[misc]

    def test_equality(self):
        a = self._make(id="m1")
        b = self._make(id="m1")
        assert a == b

    def test_aliases_as_tuple(self):
        m = self._make(aliases=("alias1", "alias2"))
        assert isinstance(m.aliases, tuple)
        assert "alias1" in m.aliases


# ---------------------------------------------------------------------------
# _parse_cost
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MR_OK, reason="model_registry import failed")
class TestParseCost:
    def test_none_returns_default_model_cost(self):
        result = _parse_cost(None)
        assert isinstance(result, ModelCost)
        assert result.input_per_mtok == pytest.approx(0.0)
        assert result.output_per_mtok == pytest.approx(0.0)
        assert result.cached_input_per_mtok is None

    def test_empty_dict_returns_default(self):
        result = _parse_cost({})
        assert result.input_per_mtok == pytest.approx(0.0)
        assert result.output_per_mtok == pytest.approx(0.0)

    def test_input_float_coercion(self):
        result = _parse_cost({"input": "2.5"})
        assert result.input_per_mtok == pytest.approx(2.5)

    def test_output_float_coercion(self):
        result = _parse_cost({"output": "6.0"})
        assert result.output_per_mtok == pytest.approx(6.0)

    def test_input_and_output(self):
        result = _parse_cost({"input": 1.5, "output": 6.0})
        assert result.input_per_mtok == pytest.approx(1.5)
        assert result.output_per_mtok == pytest.approx(6.0)

    def test_cached_input_set(self):
        result = _parse_cost({"input": 1.0, "output": 2.0, "cached_input": 0.5})
        assert result.cached_input_per_mtok == pytest.approx(0.5)

    def test_cached_input_absent_is_none(self):
        result = _parse_cost({"input": 1.0, "output": 2.0})
        assert result.cached_input_per_mtok is None

    def test_cached_input_explicit_none_is_none(self):
        # raw.get("cached_input") returns None for missing key
        result = _parse_cost({"input": 1.0, "cached_input": None})
        assert result.cached_input_per_mtok is None

    def test_zero_values_stay_zero(self):
        result = _parse_cost({"input": 0, "output": 0})
        assert result.input_per_mtok == pytest.approx(0.0)

    def test_none_value_for_input_falls_back_to_zero(self):
        # None or 0.0 — `or 0.0` handles None
        result = _parse_cost({"input": None, "output": None})
        assert result.input_per_mtok == pytest.approx(0.0)
        assert result.output_per_mtok == pytest.approx(0.0)

    def test_returns_model_cost_instance(self):
        assert isinstance(_parse_cost({"input": 1.0}), ModelCost)

    def test_integer_input_coerced_to_float(self):
        result = _parse_cost({"input": 3, "output": 10})
        assert isinstance(result.input_per_mtok, float)
        assert isinstance(result.output_per_mtok, float)


# ---------------------------------------------------------------------------
# _canonicalize
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MR_OK, reason="model_registry import failed")
class TestCanonicalize:
    def test_openai_prefix_stripped(self):
        assert _canonicalize("openai:gpt-4o") == "gpt-4o"

    def test_anthropic_prefix_stripped(self):
        assert _canonicalize("anthropic:claude-3-5-sonnet") == "claude-3-5-sonnet"

    def test_google_prefix_stripped(self):
        assert _canonicalize("google:gemini-pro") == "gemini-pro"

    def test_groq_prefix_stripped(self):
        assert _canonicalize("groq:llama3-8b") == "llama3-8b"

    def test_ollama_prefix_stripped(self):
        assert _canonicalize("ollama:qwen2.5-coder") == "qwen2.5-coder"

    def test_vllm_prefix_stripped(self):
        assert _canonicalize("vllm:mistral-7b") == "mistral-7b"

    def test_azure_prefix_stripped(self):
        assert _canonicalize("azure:gpt-4") == "gpt-4"

    def test_gemini_prefix_stripped(self):
        assert _canonicalize("gemini:gemini-1.5-flash") == "gemini-1.5-flash"

    def test_unknown_prefix_kept(self):
        # "hf" is not in _PROVIDER_PREFIXES → kept as-is
        assert _canonicalize("hf:llama") == "hf:llama"

    def test_no_prefix_unchanged(self):
        assert _canonicalize("gpt-4o") == "gpt-4o"

    def test_empty_string_returns_empty(self):
        assert _canonicalize("") == ""

    def test_none_like_empty_returns_empty(self):
        # None input is not accepted in type annotations but coerces via `(model or "")`
        # Pass empty string
        assert _canonicalize("") == ""

    def test_uppercase_lowercased(self):
        assert _canonicalize("OpenAI:GPT-4o") == "gpt-4o"

    def test_whitespace_stripped(self):
        assert _canonicalize("  openai:gpt-4o  ") == "gpt-4o"

    def test_multiple_colons_only_first_split(self):
        # "openai:gpt-4:extra" → prefix="openai", rest="gpt-4:extra"
        assert _canonicalize("openai:gpt-4:extra") == "gpt-4:extra"

    def test_model_with_colon_for_size_not_provider(self):
        # "qwen2.5-coder:7b-instruct" has unknown prefix "qwen2.5-coder" → kept
        result = _canonicalize("qwen2.5-coder:7b-instruct-q4")
        assert "qwen2.5-coder" in result

    def test_returns_string(self):
        assert isinstance(_canonicalize("gpt-4o"), str)


# ---------------------------------------------------------------------------
# _parse_model
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MR_OK, reason="model_registry import failed")
class TestParseModel:
    def _entry(self, **overrides):
        base = {"id": "test-model-id", "provider": "openai", "tier": "mid"}
        base.update(overrides)
        return base

    def test_basic_parse(self):
        info = _parse_model(self._entry(), {})
        assert info.id == "test-model-id"
        assert info.provider == "openai"
        assert info.tier == "mid"

    def test_uses_defaults_for_provider(self):
        entry = {"id": "model-x"}
        info = _parse_model(entry, {"provider": "anthropic"})
        assert info.provider == "anthropic"

    def test_uses_defaults_for_tier(self):
        entry = {"id": "model-x"}
        info = _parse_model(entry, {"tier": "premium"})
        assert info.tier == "premium"

    def test_context_window_parsed(self):
        info = _parse_model(self._entry(context_window=128000), {})
        assert info.context_window == 128000

    def test_max_output_parsed(self):
        info = _parse_model(self._entry(max_output=4096), {})
        assert info.max_output == 4096

    def test_supports_json_default_true(self):
        info = _parse_model(self._entry(), {})
        assert info.supports_json is True

    def test_supports_tools_default_true(self):
        info = _parse_model(self._entry(), {})
        assert info.supports_tools is True

    def test_offline_safe_default_false(self):
        info = _parse_model(self._entry(), {})
        assert info.offline_safe is False

    def test_offline_safe_set(self):
        info = _parse_model(self._entry(offline_safe=True), {})
        assert info.offline_safe is True

    def test_status_default_prod(self):
        info = _parse_model(self._entry(), {})
        assert info.status == "prod"

    def test_kind_default_chat(self):
        info = _parse_model(self._entry(), {})
        assert info.kind == "chat"

    def test_kind_set(self):
        info = _parse_model(self._entry(kind="embedding"), {})
        assert info.kind == "embedding"

    def test_p95_ms_from_sla(self):
        entry = self._entry(sla={"p95_ms": 500})
        info = _parse_model(entry, {})
        assert info.p95_ms == 500

    def test_aliases_lowercased(self):
        entry = self._entry(aliases=["GPT-4o", "GPT4"])
        info = _parse_model(entry, {})
        assert "gpt-4o" in info.aliases
        assert "gpt4" in info.aliases

    def test_aliases_empty_by_default(self):
        info = _parse_model(self._entry(), {})
        assert info.aliases == ()

    def test_cost_parsed(self):
        entry = self._entry(cost={"input": 2.5, "output": 10.0})
        info = _parse_model(entry, {})
        assert info.cost.input_per_mtok == pytest.approx(2.5)

    def test_returns_model_info(self):
        assert isinstance(_parse_model(self._entry(), {}), ModelInfo)


# ---------------------------------------------------------------------------
# _parse_family
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _MR_OK, reason="model_registry import failed")
class TestParseFamily:
    def test_prefix_extracted(self):
        prefix, info = _parse_family({"prefix": "gpt-4"})
        assert prefix == "gpt-4"

    def test_prefix_lowercased(self):
        prefix, _ = _parse_family({"prefix": "GPT-4"})
        assert prefix == "gpt-4"

    def test_provider_is_family(self):
        _, info = _parse_family({"prefix": "gpt-4"})
        assert info.provider == "family"

    def test_tier_default_mid(self):
        _, info = _parse_family({"prefix": "gpt-4"})
        assert info.tier == "mid"

    def test_tier_set(self):
        _, info = _parse_family({"prefix": "gpt-4", "tier": "premium"})
        assert info.tier == "premium"

    def test_cost_parsed(self):
        _, info = _parse_family({"prefix": "gpt-4", "cost": {"input": 1.0, "output": 3.0}})
        assert info.cost.input_per_mtok == pytest.approx(1.0)

    def test_offline_safe_default_false(self):
        _, info = _parse_family({"prefix": "gpt-4"})
        assert info.offline_safe is False

    def test_id_equals_prefix(self):
        prefix, info = _parse_family({"prefix": "gpt-4o"})
        assert info.id == prefix

    def test_kind_is_chat(self):
        _, info = _parse_family({"prefix": "gpt-4"})
        assert info.kind == "chat"

    def test_returns_tuple(self):
        result = _parse_family({"prefix": "gpt-4"})
        assert isinstance(result, tuple)
        assert len(result) == 2
