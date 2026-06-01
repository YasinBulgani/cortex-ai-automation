"""Unit tests for app.domains.ai.model_registry — pure helper functions.

Tests are fully self-contained: no DB, no HTTP.
Covers: _parse_cost, _parse_model, _parse_family, _canonicalize,
        ModelCost / ModelInfo / ModelPrice dataclasses.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.model_registry import (
        _parse_cost,
        _parse_model,
        _parse_family,
        _canonicalize,
        ModelCost,
        ModelInfo,
        _UNKNOWN,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="model_registry import failed")


# ---------------------------------------------------------------------------
# _parse_cost
# ---------------------------------------------------------------------------

class TestParseCost:
    def test_none_returns_default(self):
        cost = _parse_cost(None)
        assert isinstance(cost, ModelCost)
        assert cost.input_per_mtok == 0.0
        assert cost.output_per_mtok == 0.0

    def test_empty_dict_returns_default(self):
        cost = _parse_cost({})
        assert cost.input_per_mtok == 0.0
        assert cost.output_per_mtok == 0.0

    def test_parses_input_output(self):
        cost = _parse_cost({"input": 3.0, "output": 15.0})
        assert cost.input_per_mtok == pytest.approx(3.0)
        assert cost.output_per_mtok == pytest.approx(15.0)

    def test_cached_input_present(self):
        cost = _parse_cost({"input": 3.0, "output": 15.0, "cached_input": 0.3})
        assert cost.cached_input_per_mtok == pytest.approx(0.3)

    def test_cached_input_absent_is_none(self):
        cost = _parse_cost({"input": 1.0})
        assert cost.cached_input_per_mtok is None

    def test_zero_values(self):
        cost = _parse_cost({"input": 0.0, "output": 0.0})
        assert cost.input_per_mtok == 0.0
        assert cost.output_per_mtok == 0.0

    def test_returns_modelcost_instance(self):
        assert isinstance(_parse_cost({"input": 1.0}), ModelCost)


# ---------------------------------------------------------------------------
# _parse_model
# ---------------------------------------------------------------------------

class TestParseModel:
    def _entry(self, **overrides):
        base = {
            "id": "test-model",
            "provider": "openai",
            "tier": "premium",
            "context_window": 128000,
            "max_output": 4096,
            "supports_json": True,
            "supports_tools": True,
            "offline_safe": False,
            "status": "prod",
            "kind": "chat",
            "cost": {"input": 5.0, "output": 15.0},
        }
        base.update(overrides)
        return base

    def test_returns_model_info(self):
        result = _parse_model(self._entry(), {})
        assert isinstance(result, ModelInfo)

    def test_id_parsed(self):
        result = _parse_model(self._entry(id="gpt-4o"), {})
        assert result.id == "gpt-4o"

    def test_provider_from_entry(self):
        result = _parse_model(self._entry(provider="anthropic"), {})
        assert result.provider == "anthropic"

    def test_provider_from_defaults(self):
        entry = {"id": "some-model", "tier": "mid"}
        result = _parse_model(entry, {"provider": "ollama"})
        assert result.provider == "ollama"

    def test_tier_parsed(self):
        result = _parse_model(self._entry(tier="mini"), {})
        assert result.tier == "mini"

    def test_context_window_parsed(self):
        result = _parse_model(self._entry(context_window=32000), {})
        assert result.context_window == 32000

    def test_aliases_lowercased_tuple(self):
        entry = self._entry(aliases=["GPT-4O", "gpt4o"])
        result = _parse_model(entry, {})
        assert "gpt-4o" in result.aliases
        assert "gpt4o" in result.aliases

    def test_no_aliases_empty_tuple(self):
        result = _parse_model(self._entry(), {})
        assert result.aliases == ()

    def test_cost_parsed(self):
        result = _parse_model(self._entry(cost={"input": 10.0, "output": 30.0}), {})
        assert result.cost.input_per_mtok == pytest.approx(10.0)

    def test_p95_from_sla(self):
        entry = self._entry()
        entry["sla"] = {"p95_ms": 2500}
        result = _parse_model(entry, {})
        assert result.p95_ms == 2500

    def test_p95_default_zero(self):
        result = _parse_model(self._entry(), {})
        assert result.p95_ms == 0

    def test_offline_safe_from_defaults(self):
        entry = {"id": "local-model", "provider": "ollama", "tier": "local"}
        result = _parse_model(entry, {"offline_safe": True})
        assert result.offline_safe is True


# ---------------------------------------------------------------------------
# _parse_family
# ---------------------------------------------------------------------------

class TestParseFamily:
    def test_returns_tuple(self):
        result = _parse_family({"prefix": "gpt-", "tier": "premium"})
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_prefix_lowercased(self):
        prefix, info = _parse_family({"prefix": "GPT-"})
        assert prefix == "gpt-"

    def test_info_is_model_info(self):
        prefix, info = _parse_family({"prefix": "claude-"})
        assert isinstance(info, ModelInfo)

    def test_provider_is_family(self):
        prefix, info = _parse_family({"prefix": "claude-"})
        assert info.provider == "family"

    def test_tier_from_raw(self):
        prefix, info = _parse_family({"prefix": "gpt-", "tier": "premium"})
        assert info.tier == "premium"

    def test_tier_default_mid(self):
        prefix, info = _parse_family({"prefix": "some-"})
        assert info.tier == "mid"

    def test_cost_parsed(self):
        prefix, info = _parse_family({
            "prefix": "gpt-",
            "cost": {"input": 5.0, "output": 20.0}
        })
        assert info.cost.input_per_mtok == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# _canonicalize
# ---------------------------------------------------------------------------

class TestCanonicalize:
    def test_strips_openai_prefix(self):
        assert _canonicalize("openai:gpt-4o") == "gpt-4o"

    def test_strips_anthropic_prefix(self):
        assert _canonicalize("anthropic:claude-3-5-sonnet") == "claude-3-5-sonnet"

    def test_ollama_colon_preserved_if_not_provider(self):
        # "qwen2.5-coder:7b-instruct" — "qwen2.5-coder" is not a provider prefix
        result = _canonicalize("qwen2.5-coder:7b-instruct")
        assert result == "qwen2.5-coder:7b-instruct"

    def test_no_prefix_returns_lowercased(self):
        assert _canonicalize("GPT-4O") == "gpt-4o"

    def test_empty_string_returns_empty(self):
        assert _canonicalize("") == ""

    def test_none_returns_empty(self):
        assert _canonicalize(None) == ""  # type: ignore[arg-type]

    def test_strips_whitespace(self):
        assert _canonicalize("  gpt-4o  ") == "gpt-4o"

    def test_google_prefix_stripped(self):
        result = _canonicalize("google:gemini-pro")
        assert result == "gemini-pro"


# ---------------------------------------------------------------------------
# ModelCost / ModelInfo dataclasses
# ---------------------------------------------------------------------------

class TestModelCostDataclass:
    def test_default_values(self):
        cost = ModelCost()
        assert cost.input_per_mtok == 0.0
        assert cost.output_per_mtok == 0.0
        assert cost.cached_input_per_mtok is None

    def test_immutable(self):
        cost = ModelCost(input_per_mtok=5.0)
        with pytest.raises((AttributeError, TypeError)):
            cost.input_per_mtok = 10.0  # type: ignore[misc]


class TestModelInfoDataclass:
    def test_required_fields(self):
        info = ModelInfo(id="test", provider="openai", tier="premium")
        assert info.id == "test"
        assert info.provider == "openai"
        assert info.tier == "premium"

    def test_default_context_window(self):
        info = ModelInfo(id="x", provider="p", tier="t")
        assert info.context_window == 0

    def test_default_supports_json_true(self):
        info = ModelInfo(id="x", provider="p", tier="t")
        assert info.supports_json is True

    def test_unknown_singleton(self):
        assert _UNKNOWN.id == "__unknown__"
        assert _UNKNOWN.provider == "unknown"
