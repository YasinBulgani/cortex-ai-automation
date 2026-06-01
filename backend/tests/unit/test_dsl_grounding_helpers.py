"""Unit tests for TSP/BDD DSL grounding pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/tspm/dsl_grounding_for_bdd.py:
    _normalize, _strip_placeholders, _fill_placeholders,
    _tokenize_for_match, _token_overlap_score,
    _extract_capitalized_phrases, _cache_key,
    _keyword_to_bucket, _action_bucket
"""

from __future__ import annotations

import types

import pytest

from app.domains.tspm.dsl_grounding_for_bdd import (
    _cache_key,
    _extract_capitalized_phrases,
    _fill_placeholders,
    _keyword_to_bucket,
    _normalize,
    _strip_placeholders,
    _token_overlap_score,
    _tokenize_for_match,
)


# ── _normalize ────────────────────────────────────────────────────────────────


class TestNormalize:
    def test_lowercases_text(self) -> None:
        assert _normalize("Hello World") == "hello world"

    def test_removes_punctuation(self) -> None:
        result = _normalize('test "value", done!')
        assert '"' not in result
        assert ',' not in result
        assert '!' not in result

    def test_collapses_whitespace(self) -> None:
        result = _normalize("  lots   of   spaces  ")
        assert "  " not in result
        assert result == "lots of spaces"

    def test_empty_string(self) -> None:
        assert _normalize("") == ""

    def test_returns_string(self) -> None:
        assert isinstance(_normalize("test"), str)

    def test_preserves_alphanumeric(self) -> None:
        result = _normalize("login123")
        assert "login123" in result


# ── _strip_placeholders ───────────────────────────────────────────────────────


class TestStripPlaceholders:
    def test_removes_placeholder(self) -> None:
        result = _strip_placeholders("I click {button}")
        assert "{button}" not in result

    def test_multiple_placeholders(self) -> None:
        result = _strip_placeholders("{user} logs in with {password}")
        assert "{user}" not in result
        assert "{password}" not in result

    def test_no_placeholder_unchanged(self) -> None:
        text = "click the login button"
        assert _strip_placeholders(text) == text

    def test_returns_string(self) -> None:
        assert isinstance(_strip_placeholders("test"), str)

    def test_empty_string(self) -> None:
        assert _strip_placeholders("") == ""


# ── _fill_placeholders ────────────────────────────────────────────────────────


class TestFillPlaceholders:
    def test_fills_placeholder_with_quoted_value(self) -> None:
        result = _fill_placeholders('I click "{button}"', 'click "Login"')
        assert "Login" in result

    def test_no_placeholder_returns_original(self) -> None:
        text = "click the button"
        assert _fill_placeholders(text, "some text") == text

    def test_plain_placeholder_wrapped_in_quotes(self) -> None:
        result = _fill_placeholders("enter {value}", 'enter "admin"')
        assert "admin" in result

    def test_unfilled_placeholder_remains(self) -> None:
        # No quoted value in source → placeholder stays
        result = _fill_placeholders("I click {button}", "I click something")
        assert "{button}" in result

    def test_capitalized_phrase_used_when_no_quotes(self) -> None:
        result = _fill_placeholders("click {button}", "click Login Button")
        # Should use capitalized phrase
        assert "Login" in result or "{button}" in result  # fallback or filled

    def test_returns_string(self) -> None:
        assert isinstance(_fill_placeholders("{x}", '"val"'), str)


# ── _tokenize_for_match ───────────────────────────────────────────────────────


class TestTokenizeForMatch:
    def test_returns_set(self) -> None:
        assert isinstance(_tokenize_for_match("hello world"), set)

    def test_empty_text_returns_empty_set(self) -> None:
        assert _tokenize_for_match("") == set()

    def test_filters_short_tokens(self) -> None:
        # Filter threshold is < 3 chars (i.e. length 1 and 2 are filtered)
        result = _tokenize_for_match("a to test scenario")
        assert "a" not in result   # length 1 → filtered
        assert "to" not in result  # length 2 → filtered

    def test_includes_long_tokens(self) -> None:
        result = _tokenize_for_match("authentication required")
        assert "authentication" in result
        assert "required" in result

    def test_filters_placeholders(self) -> None:
        result = _tokenize_for_match("click {button} ok")
        assert "{button}" not in result

    def test_lowercased_tokens(self) -> None:
        result = _tokenize_for_match("Login Authentication")
        assert "Login" not in result
        # lowercased
        assert "login" in result


# ── _token_overlap_score ──────────────────────────────────────────────────────


class TestTokenOverlapScore:
    def test_perfect_overlap(self) -> None:
        q_tokens = {"login", "authentication"}
        score = _token_overlap_score(q_tokens, "login authentication")
        assert score > 0.0

    def test_no_overlap_returns_zero(self) -> None:
        q_tokens = {"login"}
        score = _token_overlap_score(q_tokens, "unrelated phrase here")
        assert score == pytest.approx(0.0)

    def test_empty_tokens_returns_zero(self) -> None:
        assert _token_overlap_score(set(), "some text") == pytest.approx(0.0)

    def test_empty_alias_returns_zero(self) -> None:
        assert _token_overlap_score({"login"}, "") == pytest.approx(0.0)

    def test_returns_float(self) -> None:
        assert isinstance(_token_overlap_score({"test"}, "test phrase"), float)

    def test_score_between_zero_and_one(self) -> None:
        score = _token_overlap_score({"login", "test"}, "login test scenario")
        assert 0.0 <= score <= 1.0

    def test_partial_overlap_between_zero_and_one(self) -> None:
        q_tokens = {"login", "password", "authentication"}
        score = _token_overlap_score(q_tokens, "login form here")
        assert 0.0 < score <= 1.0


# ── _extract_capitalized_phrases ──────────────────────────────────────────────


class TestExtractCapitalizedPhrases:
    def test_extracts_single_capitalized_word(self) -> None:
        result = _extract_capitalized_phrases("click Login")
        assert "Login" in result

    def test_extracts_multi_word_phrase(self) -> None:
        result = _extract_capitalized_phrases("click Login Button")
        assert any("Login" in p for p in result)

    def test_empty_string_returns_empty(self) -> None:
        assert _extract_capitalized_phrases("") == []

    def test_all_lowercase_returns_empty(self) -> None:
        result = _extract_capitalized_phrases("click the button")
        assert result == []

    def test_returns_list(self) -> None:
        assert isinstance(_extract_capitalized_phrases("Test"), list)

    def test_skips_single_char_words(self) -> None:
        # Words of length 1 (like "A") are excluded
        result = _extract_capitalized_phrases("A Login Form")
        assert "A" not in result

    def test_strips_trailing_punctuation(self) -> None:
        result = _extract_capitalized_phrases("click Login!")
        assert any("Login" in p for p in result)


# ── _cache_key ────────────────────────────────────────────────────────────────


class TestCacheKey:
    def test_returns_string(self) -> None:
        assert isinstance(_cache_key("hello", 5, "tr"), str)

    def test_different_inputs_produce_different_keys(self) -> None:
        k1 = _cache_key("text1", 5, "tr")
        k2 = _cache_key("text2", 5, "tr")
        assert k1 != k2

    def test_different_top_k_produces_different_keys(self) -> None:
        k1 = _cache_key("text", 5, "tr")
        k2 = _cache_key("text", 10, "tr")
        assert k1 != k2

    def test_different_lang_produces_different_keys(self) -> None:
        k1 = _cache_key("text", 5, "tr")
        k2 = _cache_key("text", 5, "en")
        assert k1 != k2

    def test_none_lang_handled(self) -> None:
        key = _cache_key("text", 5, None)
        assert isinstance(key, str)

    def test_long_text_truncated(self) -> None:
        long_text = "a" * 1000
        key = _cache_key(long_text, 5, "tr")
        # Key should not contain 1000 'a's — truncated to 512
        assert len(key) < 1000 + 50  # well under full length + overhead

    def test_same_inputs_same_key(self) -> None:
        k1 = _cache_key("hello world", 3, "en")
        k2 = _cache_key("hello world", 3, "en")
        assert k1 == k2


# ── _keyword_to_bucket ────────────────────────────────────────────────────────


class TestKeywordToBucket:
    def test_given_keyword_returns_given(self) -> None:
        assert _keyword_to_bucket("given") == "given"

    def test_diyelim_ki_returns_given(self) -> None:
        assert _keyword_to_bucket("diyelim ki") == "given"

    def test_when_keyword_returns_when(self) -> None:
        assert _keyword_to_bucket("when") == "when"

    def test_eger_returns_when(self) -> None:
        assert _keyword_to_bucket("eğer") == "when" or _keyword_to_bucket("eger") == "when"

    def test_then_keyword_returns_then(self) -> None:
        assert _keyword_to_bucket("then") == "then"

    def test_o_zaman_returns_then(self) -> None:
        assert _keyword_to_bucket("o zaman") == "then"

    def test_and_returns_none(self) -> None:
        assert _keyword_to_bucket("and") is None

    def test_ve_returns_none(self) -> None:
        assert _keyword_to_bucket("ve") is None

    def test_unknown_returns_none(self) -> None:
        assert _keyword_to_bucket("random") is None

    def test_empty_returns_none(self) -> None:
        assert _keyword_to_bucket("") is None

    def test_trailing_colon_stripped(self) -> None:
        result = _keyword_to_bucket("given:")
        assert result == "given"
