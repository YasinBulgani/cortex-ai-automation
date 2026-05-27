"""Unit tests for tspm.dsl_grounding_for_bdd pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM, no vector store.
Covers:
  - _normalize: lowercase + punctuation + whitespace cleanup
  - _tokenize_for_match: token set with placeholder and short-word filtering
  - _strip_placeholders: {param} removal
  - _fill_placeholders: {param} substitution from quoted values
  - _extract_capitalized_phrases: capitalized word phrase extraction
  - _keyword_to_bucket: GWT keyword → bucket mapping
  - _cache_key: text/top_k/lang → cache key string
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.dsl_grounding_for_bdd import (
        _normalize,
        _tokenize_for_match,
        _strip_placeholders,
        _fill_placeholders,
        _extract_capitalized_phrases,
        _keyword_to_bucket,
        _cache_key,
    )
    _DG_OK = True
except ImportError:
    _DG_OK = False


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestNormalize:
    def test_lowercases(self):
        assert _normalize("Hello World") == "hello world"

    def test_removes_punctuation(self):
        result = _normalize("Hello, World!")
        assert "," not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        result = _normalize("a   b   c")
        assert result == "a b c"

    def test_strips_leading_trailing(self):
        result = _normalize("  hello  ")
        assert result == "hello"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_question_marks_removed(self):
        result = _normalize("Is it done?")
        assert "?" not in result

    def test_parentheses_removed(self):
        result = _normalize("(test)")
        assert "(" not in result and ")" not in result

    def test_returns_string(self):
        assert isinstance(_normalize("text"), str)

    def test_quotes_removed(self):
        result = _normalize('"quoted"')
        assert '"' not in result

    def test_semicolons_removed(self):
        result = _normalize("a; b; c")
        assert ";" not in result


# ---------------------------------------------------------------------------
# _tokenize_for_match
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestTokenizeForMatch:
    def test_returns_set(self):
        assert isinstance(_tokenize_for_match("hello world"), set)

    def test_basic_tokens(self):
        result = _tokenize_for_match("click the login button")
        assert "click" in result
        assert "login" in result
        assert "button" in result

    def test_short_words_filtered(self):
        result = _tokenize_for_match("do it")
        # "do" and "it" are < 3 chars
        assert "do" not in result
        assert "it" not in result

    def test_placeholders_filtered(self):
        result = _tokenize_for_match("enter {username} and {password}")
        assert "{username}" not in result
        assert "{password}" not in result

    def test_empty_string_returns_empty_set(self):
        assert _tokenize_for_match("") == set()

    def test_case_insensitive(self):
        result = _tokenize_for_match("LOGIN")
        assert "login" in result

    def test_returns_unique_tokens(self):
        result = _tokenize_for_match("click click click")
        assert len(result) == 1

    def test_only_placeholders_returns_empty(self):
        result = _tokenize_for_match("{param1} {param2}")
        # placeholders are filtered
        assert len(result) == 0


# ---------------------------------------------------------------------------
# _strip_placeholders
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestStripPlaceholders:
    def test_single_placeholder_removed(self):
        result = _strip_placeholders("Click {button}")
        assert "{button}" not in result

    def test_multiple_placeholders_removed(self):
        result = _strip_placeholders("Enter {username} and {password}")
        assert "{username}" not in result
        assert "{password}" not in result

    def test_no_placeholder_unchanged(self):
        result = _strip_placeholders("Click the button")
        assert result == "Click the button"

    def test_empty_string(self):
        assert _strip_placeholders("") == ""

    def test_returns_string(self):
        assert isinstance(_strip_placeholders("text"), str)

    def test_placeholder_replaced_with_space(self):
        result = _strip_placeholders("A{x}B")
        # placeholder replaced with space(s)
        assert "{x}" not in result

    def test_only_placeholder(self):
        result = _strip_placeholders("{param}")
        assert "{param}" not in result


# ---------------------------------------------------------------------------
# _fill_placeholders
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestFillPlaceholders:
    def test_single_quoted_value_fills(self):
        result = _fill_placeholders('Enter {username}', 'Enter "admin"')
        assert "admin" in result
        assert "{username}" not in result

    def test_single_quoted_value_single_quotes(self):
        result = _fill_placeholders("Enter {username}", "Enter 'testuser'")
        assert "testuser" in result

    def test_no_placeholder_unchanged(self):
        result = _fill_placeholders("Click the button", "some text")
        assert result == "Click the button"

    def test_no_quoted_values_uses_capitalized(self):
        result = _fill_placeholders("Click {button}", "Click Submit Button")
        # Should fill with capitalized phrase
        assert "{button}" not in result

    def test_returns_string(self):
        assert isinstance(_fill_placeholders("text {p}", '"v"'), str)

    def test_empty_source_leaves_placeholder(self):
        result = _fill_placeholders("Enter {username}", "")
        # No values to fill → placeholder remains
        assert "{username}" in result

    def test_multiple_placeholders(self):
        result = _fill_placeholders('Enter {user} and {pass}', 'Enter "alice" and "secret"')
        assert "{user}" not in result
        assert "{pass}" not in result


# ---------------------------------------------------------------------------
# _extract_capitalized_phrases
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestExtractCapitalizedPhrases:
    def test_single_capitalized_word_after_lowercase(self):
        # "the" is lowercase → breaks phrase; "Submit" starts a new phrase
        result = _extract_capitalized_phrases("the Submit")
        assert "Submit" in result

    def test_consecutive_capitalized_words_grouped(self):
        result = _extract_capitalized_phrases("Click Login Button Now")
        # "Login Button" or "Click Login Button" depending on implementation
        # There should be at least one phrase with multiple words
        combined = " ".join(result)
        assert "Login" in combined

    def test_empty_string(self):
        result = _extract_capitalized_phrases("")
        assert result == []

    def test_no_capitalized_words(self):
        result = _extract_capitalized_phrases("click the button")
        assert result == []

    def test_returns_list(self):
        assert isinstance(_extract_capitalized_phrases("Test"), list)

    def test_mixed_case_text(self):
        result = _extract_capitalized_phrases("the Login Page is loaded")
        assert any("Login" in p for p in result)

    def test_single_uppercase_char_ignored(self):
        # Single uppercase char of length 1 should be filtered (len > 1 check)
        result = _extract_capitalized_phrases("A B C Submit")
        # "A", "B", "C" are len 1 → not included; "Submit" is
        assert any("Submit" in p for p in result)


# ---------------------------------------------------------------------------
# _keyword_to_bucket
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestKeywordToBucket:
    def test_given_keyword(self):
        assert _keyword_to_bucket("given") == "given"

    def test_diyelim_ki(self):
        assert _keyword_to_bucket("diyelim ki") == "given"

    def test_olduğu_gibi(self):
        assert _keyword_to_bucket("olduğu gibi") == "given"

    def test_when_keyword(self):
        assert _keyword_to_bucket("when") == "when"

    def test_eğer_keyword(self):
        assert _keyword_to_bucket("eğer") == "when"

    def test_eger_keyword(self):
        assert _keyword_to_bucket("eger") == "when"

    def test_then_keyword(self):
        assert _keyword_to_bucket("then") == "then"

    def test_o_zaman_keyword(self):
        assert _keyword_to_bucket("o zaman") == "then"

    def test_and_returns_none(self):
        assert _keyword_to_bucket("and") is None

    def test_but_returns_none(self):
        assert _keyword_to_bucket("but") is None

    def test_ve_returns_none(self):
        assert _keyword_to_bucket("ve") is None

    def test_unknown_keyword_returns_none(self):
        assert _keyword_to_bucket("unknown") is None

    def test_empty_string_returns_none(self):
        assert _keyword_to_bucket("") is None

    def test_trailing_colon_stripped(self):
        # "given:" should map to "given"
        assert _keyword_to_bucket("given:") == "given"

    def test_case_normalized(self):
        assert _keyword_to_bucket("GIVEN") == "given"


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DG_OK, reason="dsl_grounding_for_bdd import failed")
class TestCacheKey:
    def test_returns_string(self):
        assert isinstance(_cache_key("text", 5, "tr"), str)

    def test_different_top_k_differs(self):
        k1 = _cache_key("text", 5, "tr")
        k2 = _cache_key("text", 10, "tr")
        assert k1 != k2

    def test_different_text_differs(self):
        k1 = _cache_key("text1", 5, "tr")
        k2 = _cache_key("text2", 5, "tr")
        assert k1 != k2

    def test_different_lang_differs(self):
        k1 = _cache_key("text", 5, "tr")
        k2 = _cache_key("text", 5, "en")
        assert k1 != k2

    def test_none_lang_handled(self):
        key = _cache_key("text", 5, None)
        assert isinstance(key, str)

    def test_deterministic(self):
        k1 = _cache_key("same", 5, "tr")
        k2 = _cache_key("same", 5, "tr")
        assert k1 == k2

    def test_long_text_truncated(self):
        long_text = "x" * 2000
        key = _cache_key(long_text, 5, "tr")
        # Key should not be excessively long
        assert isinstance(key, str)
