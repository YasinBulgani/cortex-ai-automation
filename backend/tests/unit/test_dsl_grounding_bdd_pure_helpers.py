"""Unit tests for tspm.dsl_grounding_for_bdd pure helper functions.

All tests are self-contained: no DB, no embedding, no HTTP.
Covers:
  - _normalize: punctuation removal + whitespace normalization
  - _strip_placeholders: {param} removal
  - _tokenize_for_match: token set with length filter + placeholder skip
  - _token_overlap_score: Jaccard-like overlap between token sets
  - _extract_capitalized_phrases: consecutive capitalized word groups
  - _keyword_to_bucket: BDD keyword → given/when/then/None
  - _cache_key: deterministic string from text/top_k/lang
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.dsl_grounding_for_bdd import (
        _normalize,
        _strip_placeholders,
        _tokenize_for_match,
        _token_overlap_score,
        _extract_capitalized_phrases,
        _keyword_to_bucket,
        _cache_key,
    )
    _BDD_OK = True
except ImportError:
    _BDD_OK = False


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestNormalize:
    def test_lowercases_text(self):
        assert "hello world" in _normalize("Hello World")

    def test_removes_comma(self):
        result = _normalize("hello, world")
        assert "," not in result

    def test_removes_period(self):
        result = _normalize("end.")
        assert "." not in result

    def test_removes_question_mark(self):
        result = _normalize("ok?")
        assert "?" not in result

    def test_collapses_whitespace(self):
        result = _normalize("a   b    c")
        assert "  " not in result

    def test_strips_leading_trailing_whitespace(self):
        result = _normalize("  hello  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_returns_string(self):
        assert isinstance(_normalize("text"), str)

    def test_parentheses_removed(self):
        result = _normalize("test (value)")
        assert "(" not in result
        assert ")" not in result


# ---------------------------------------------------------------------------
# _strip_placeholders
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestStripPlaceholders:
    def test_removes_placeholder(self):
        result = _strip_placeholders("Click {button}")
        assert "{button}" not in result

    def test_multiple_placeholders(self):
        result = _strip_placeholders("Login as {user} with {password}")
        assert "{user}" not in result
        assert "{password}" not in result

    def test_no_placeholder_unchanged(self):
        result = _strip_placeholders("Click Login")
        assert result == "Click Login"

    def test_empty_string(self):
        assert _strip_placeholders("") == ""

    def test_returns_string(self):
        assert isinstance(_strip_placeholders("test"), str)

    def test_placeholder_replaced_with_space(self):
        result = _strip_placeholders("A{x}B")
        assert "A" in result
        assert "B" in result


# ---------------------------------------------------------------------------
# _tokenize_for_match
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestTokenizeForMatch:
    def test_returns_set(self):
        assert isinstance(_tokenize_for_match("hello world"), set)

    def test_short_tokens_excluded(self):
        # "ok" (len 2) should be excluded
        result = _tokenize_for_match("ok done")
        assert "ok" not in result

    def test_min_length_3(self):
        result = _tokenize_for_match("abc xy z")
        assert "abc" in result
        assert "xy" not in result
        assert "z" not in result

    def test_placeholders_excluded(self):
        result = _tokenize_for_match("click {button}")
        for tok in result:
            assert not (tok.startswith("{") and tok.endswith("}"))

    def test_empty_string_returns_empty_set(self):
        assert _tokenize_for_match("") == set()

    def test_all_short_returns_empty(self):
        assert _tokenize_for_match("a b c") == set()

    def test_lowercased_tokens(self):
        result = _tokenize_for_match("Click LOGIN")
        assert "click" in result
        assert "login" in result


# ---------------------------------------------------------------------------
# _token_overlap_score
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestTokenOverlapScore:
    def test_full_overlap_returns_one(self):
        q = {"click", "login"}
        alias = "click login"
        assert _token_overlap_score(q, alias) == pytest.approx(1.0)

    def test_no_overlap_returns_zero(self):
        q = {"navigate", "home"}
        alias = "submit form"
        assert _token_overlap_score(q, alias) == pytest.approx(0.0)

    def test_empty_q_returns_zero(self):
        assert _token_overlap_score(set(), "click login") == pytest.approx(0.0)

    def test_empty_alias_returns_zero(self):
        assert _token_overlap_score({"click"}, "") == pytest.approx(0.0)

    def test_partial_overlap(self):
        q = {"click", "login", "form"}
        alias = "click login"
        score = _token_overlap_score(q, alias)
        assert 0.0 < score <= 1.0

    def test_returns_float(self):
        assert isinstance(_token_overlap_score({"test"}, "test case"), float)

    def test_score_in_range(self):
        q = {"hello", "world", "test"}
        alias = "hello world"
        score = _token_overlap_score(q, alias)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _extract_capitalized_phrases
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestExtractCapitalizedPhrases:
    def test_single_capitalized_word(self):
        # Single uppercase word len>1
        result = _extract_capitalized_phrases("the Login button")
        assert "Login" in result

    def test_phrase_of_two_words(self):
        result = _extract_capitalized_phrases("the Click Submit")
        assert "Click Submit" in result

    def test_all_lowercase_returns_empty(self):
        assert _extract_capitalized_phrases("click submit") == []

    def test_mixed_groups(self):
        result = _extract_capitalized_phrases("The Login Page exists")
        assert any("Login" in p for p in result)

    def test_consecutive_capitalized_words_grouped(self):
        result = _extract_capitalized_phrases("User Clicks The Button")
        # All words capitalized → one phrase
        assert len(result) == 1
        assert "User Clicks The Button" in result

    def test_empty_string(self):
        assert _extract_capitalized_phrases("") == []

    def test_returns_list(self):
        assert isinstance(_extract_capitalized_phrases("Hello"), list)

    def test_single_char_not_captured(self):
        # Single char won't be in any phrase (len > 1 required)
        result = _extract_capitalized_phrases("A B C")
        assert result == []

    def test_punctuation_stripped_before_check(self):
        # "Login." → cleaned="Login" → capitalized
        result = _extract_capitalized_phrases("Click Login.")
        assert any("Login" in p for p in result)


# ---------------------------------------------------------------------------
# _keyword_to_bucket
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestKeywordToBucket:
    def test_given_keyword_tr(self):
        assert _keyword_to_bucket("diyelim ki") == "given"

    def test_given_keyword_en(self):
        assert _keyword_to_bucket("given") == "given"

    def test_when_keyword_en(self):
        assert _keyword_to_bucket("when") == "when"

    def test_when_keyword_tr(self):
        assert _keyword_to_bucket("eğer") == "when"

    def test_then_keyword_en(self):
        assert _keyword_to_bucket("then") == "then"

    def test_then_keyword_tr(self):
        assert _keyword_to_bucket("o zaman") == "then"

    def test_and_keyword_returns_none(self):
        assert _keyword_to_bucket("and") is None

    def test_but_keyword_returns_none(self):
        assert _keyword_to_bucket("but") is None

    def test_unknown_keyword_returns_none(self):
        assert _keyword_to_bucket("unknown_keyword") is None

    def test_empty_string_returns_none(self):
        assert _keyword_to_bucket("") is None

    def test_colon_suffix_stripped(self):
        # "given:" → strip trailing ":" → "given"
        assert _keyword_to_bucket("given:") == "given"

    def test_uppercase_handled(self):
        result = _keyword_to_bucket("GIVEN")
        assert result == "given"


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="dsl_grounding_for_bdd import failed")
class TestCacheKey:
    def test_returns_string(self):
        assert isinstance(_cache_key("text", 5, "tr"), str)

    def test_includes_top_k(self):
        result = _cache_key("text", 10, "tr")
        assert "10" in result

    def test_includes_lang(self):
        result = _cache_key("text", 5, "tr")
        assert "tr" in result

    def test_includes_text_snippet(self):
        result = _cache_key("navigate home", 5, None)
        assert "navigate home" in result

    def test_deterministic(self):
        k1 = _cache_key("same text", 5, "tr")
        k2 = _cache_key("same text", 5, "tr")
        assert k1 == k2

    def test_different_top_k_different_key(self):
        assert _cache_key("text", 3, "tr") != _cache_key("text", 5, "tr")

    def test_different_lang_different_key(self):
        assert _cache_key("text", 5, "tr") != _cache_key("text", 5, "en")

    def test_different_text_different_key(self):
        assert _cache_key("text A", 5, None) != _cache_key("text B", 5, None)

    def test_none_lang_handled(self):
        result = _cache_key("text", 5, None)
        assert isinstance(result, str)

    def test_long_text_truncated_at_512(self):
        # Both keys should be equal if text differs only after 512 chars
        base = "a" * 512
        k1 = _cache_key(base + "X", 5, None)
        k2 = _cache_key(base + "Y", 5, None)
        assert k1 == k2
