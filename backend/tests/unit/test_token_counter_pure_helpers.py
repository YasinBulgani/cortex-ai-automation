"""Unit tests for ai.token_counter pure helper functions.

All tests are self-contained: no HTTP, no LLM, no tiktoken required.
Covers:
  - _canonicalize_model: provider prefix / tag stripping
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.token_counter import _canonicalize_model
    _TC_OK = True
except ImportError:
    _TC_OK = False


# ---------------------------------------------------------------------------
# _canonicalize_model
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="token_counter import failed")
class TestCanonicalizeModel:
    def test_plain_model_name(self):
        result = _canonicalize_model("gpt-4o")
        assert result == "gpt-4o"

    def test_strips_leading_trailing_whitespace(self):
        result = _canonicalize_model("  gpt-4  ")
        assert result == "gpt-4"

    def test_lowercases_model(self):
        result = _canonicalize_model("GPT-4O")
        assert result == "gpt-4o"

    def test_openai_provider_prefix_stripped(self):
        result = _canonicalize_model("openai:gpt-4o")
        assert result == "gpt-4o"

    def test_anthropic_provider_prefix_stripped(self):
        result = _canonicalize_model("anthropic:claude-3-sonnet")
        assert result == "claude-3-sonnet"

    def test_google_provider_prefix_stripped(self):
        result = _canonicalize_model("google:gemini-pro")
        assert result == "gemini-pro"

    def test_groq_provider_prefix_stripped(self):
        result = _canonicalize_model("groq:llama3-8b")
        assert result == "llama3-8b"

    def test_ollama_provider_prefix_stripped(self):
        result = _canonicalize_model("ollama:mistral")
        assert result == "mistral"

    def test_vllm_provider_prefix_stripped(self):
        result = _canonicalize_model("vllm:llama3")
        assert result == "llama3"

    def test_azure_provider_prefix_stripped(self):
        result = _canonicalize_model("azure:gpt-35-turbo")
        assert result == "gpt-35-turbo"

    def test_unknown_prefix_becomes_model(self):
        # Unknown provider prefix → prefix itself is returned (not the rest)
        result = _canonicalize_model("mycompany:custom-model")
        assert result == "mycompany"

    def test_empty_string_returns_empty(self):
        result = _canonicalize_model("")
        assert result == ""

    def test_none_equivalent_empty(self):
        result = _canonicalize_model(None)  # type: ignore[arg-type]
        assert result == ""

    def test_returns_string(self):
        assert isinstance(_canonicalize_model("gpt-4"), str)

    def test_multiple_colons_uses_first_split(self):
        # Only first ":" is used for provider:rest split
        result = _canonicalize_model("openai:gpt-4:extra")
        # After split on first ":", rest = "gpt-4:extra"
        assert result == "gpt-4:extra"
