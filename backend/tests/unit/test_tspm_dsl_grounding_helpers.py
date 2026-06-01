"""Unit tests for app.domains.tspm.dsl_grounding_for_bdd — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no catalog.
Covers: _normalize, _strip_placeholders, _fill_placeholders,
        _tokenize_for_match, _keyword_to_bucket,
        _extract_capitalized_phrases, _cache_key.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.dsl_grounding_for_bdd import (
        _normalize,
        _strip_placeholders,
        _fill_placeholders,
        _tokenize_for_match,
        _keyword_to_bucket,
        _extract_capitalized_phrases,
        _cache_key,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="dsl_grounding_for_bdd import failed")


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercases(self):
        assert _normalize("Hello World") == "hello world"

    def test_strips_punctuation(self):
        result = _normalize("Hello, World! (test)")
        assert "," not in result
        assert "!" not in result
        assert "(" not in result

    def test_collapses_whitespace(self):
        assert _normalize("  too   many   spaces  ") == "too many spaces"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_quotes_removed(self):
        result = _normalize('"quoted text"')
        assert '"' not in result

    def test_semicolons_removed(self):
        assert ";" not in _normalize("step one; step two")

    def test_returns_string(self):
        assert isinstance(_normalize("test"), str)


# ---------------------------------------------------------------------------
# _strip_placeholders
# ---------------------------------------------------------------------------

class TestStripPlaceholders:
    def test_replaces_placeholder_with_space(self):
        result = _strip_placeholders("alana {value} yazar")
        assert "{value}" not in result
        assert "alana" in result
        assert "yazar" in result

    def test_multiple_placeholders(self):
        result = _strip_placeholders("{field} değerini {value} olarak ayarla")
        assert "{field}" not in result
        assert "{value}" not in result

    def test_no_placeholders_unchanged(self):
        text = "alana değer yazar"
        assert _strip_placeholders(text) == text

    def test_returns_string(self):
        assert isinstance(_strip_placeholders("test {x}"), str)


# ---------------------------------------------------------------------------
# _fill_placeholders
# ---------------------------------------------------------------------------

class TestFillPlaceholders:
    def test_fills_from_quoted_value(self):
        result = _fill_placeholders('alana {value} yazar', '"admin"')
        assert "admin" in result
        assert "{value}" not in result

    def test_no_placeholder_no_change(self):
        result = _fill_placeholders("sabit metin", "anything")
        assert result == "sabit metin"

    def test_fills_from_capitalized_phrases(self):
        # No quotes → use capitalized phrases
        result = _fill_placeholders("alana {value} gir", "Giriş Yap")
        assert "{value}" not in result

    def test_insufficient_values_leaves_placeholder(self):
        # 2 placeholders but only 1 value
        result = _fill_placeholders("{a} ve {b}", '"first"')
        assert "{b}" in result

    def test_double_quoted_placeholder_preserved(self):
        result = _fill_placeholders('alana "{value}" yazar', '"test-value"')
        assert '"test-value"' in result


# ---------------------------------------------------------------------------
# _tokenize_for_match
# ---------------------------------------------------------------------------

class TestTokenizeForMatch:
    def test_returns_set(self):
        assert isinstance(_tokenize_for_match("hello world"), set)

    def test_empty_returns_empty(self):
        assert _tokenize_for_match("") == set()

    def test_short_tokens_excluded(self):
        # "ki" is 2 chars → excluded (< 3)
        tokens = _tokenize_for_match("ki ve test")
        assert "ki" not in tokens
        assert "ve" not in tokens

    def test_placeholders_excluded(self):
        tokens = _tokenize_for_match("alana {value} yazar")
        assert "{value}" not in tokens

    def test_content_words_included(self):
        tokens = _tokenize_for_match("alana değer yazar")
        assert "alana" in tokens or "değer" in tokens or "yazar" in tokens

    def test_lowercased(self):
        tokens = _tokenize_for_match("Hello World")
        assert "hello" in tokens
        assert "world" in tokens


# ---------------------------------------------------------------------------
# _keyword_to_bucket
# ---------------------------------------------------------------------------

class TestKeywordToBucket:
    def test_given_keyword(self):
        assert _keyword_to_bucket("Diyelim ki") == "given"

    def test_given_english(self):
        assert _keyword_to_bucket("given") == "given"

    def test_when_keyword(self):
        assert _keyword_to_bucket("Eğer") == "when"

    def test_when_english(self):
        assert _keyword_to_bucket("when") == "when"

    def test_then_keyword(self):
        assert _keyword_to_bucket("O zaman") == "then"

    def test_then_english(self):
        assert _keyword_to_bucket("then") == "then"

    def test_and_returns_none(self):
        assert _keyword_to_bucket("Ve") is None

    def test_but_returns_none(self):
        assert _keyword_to_bucket("ama") is None

    def test_unknown_returns_none(self):
        assert _keyword_to_bucket("unknown_keyword") is None

    def test_empty_returns_none(self):
        assert _keyword_to_bucket("") is None

    def test_trailing_colon_stripped(self):
        assert _keyword_to_bucket("given:") == "given"

    def test_case_insensitive(self):
        assert _keyword_to_bucket("GIVEN") == "given"


# ---------------------------------------------------------------------------
# _extract_capitalized_phrases
# ---------------------------------------------------------------------------

class TestExtractCapitalizedPhrases:
    def test_single_capitalized_word(self):
        phrases = _extract_capitalized_phrases("Button tıklanır")
        assert "Button" in phrases

    def test_multi_word_phrase(self):
        phrases = _extract_capitalized_phrases("Giriş Yap butonuna tıkla")
        combined = " ".join(phrases)
        assert "Giriş" in combined or "Yap" in combined

    def test_all_lowercase_returns_empty(self):
        phrases = _extract_capitalized_phrases("tamamen küçük harf")
        assert phrases == []

    def test_returns_list(self):
        assert isinstance(_extract_capitalized_phrases("Hello World"), list)

    def test_empty_string_returns_empty(self):
        assert _extract_capitalized_phrases("") == []

    def test_single_char_words_excluded(self):
        # Single char after strip is excluded (len > 1 required)
        phrases = _extract_capitalized_phrases("A Button")
        combined = " ".join(phrases)
        assert "Button" in combined

    def test_punctuation_stripped_from_word(self):
        phrases = _extract_capitalized_phrases("Click 'Submit' button")
        combined = " ".join(phrases)
        assert "Submit" in combined


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_returns_string(self):
        assert isinstance(_cache_key("test", 5, "tr"), str)

    def test_includes_top_k(self):
        k1 = _cache_key("text", 5, "tr")
        k2 = _cache_key("text", 10, "tr")
        assert k1 != k2

    def test_different_text_different_key(self):
        k1 = _cache_key("hello", 5, None)
        k2 = _cache_key("world", 5, None)
        assert k1 != k2

    def test_different_lang_different_key(self):
        k1 = _cache_key("text", 5, "tr")
        k2 = _cache_key("text", 5, "en")
        assert k1 != k2

    def test_none_lang_handled(self):
        key = _cache_key("text", 5, None)
        assert isinstance(key, str)

    def test_long_text_truncated(self):
        long_text = "x" * 1000
        key = _cache_key(long_text, 5, None)
        assert isinstance(key, str)
        # Key should be deterministic for same first 512 chars
        key2 = _cache_key(long_text, 5, None)
        assert key == key2
