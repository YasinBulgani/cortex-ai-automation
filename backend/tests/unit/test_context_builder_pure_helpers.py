"""Unit tests for ai.context_builder pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _approx_tokens: approximate token count from text length
  - _expand_query: synonym/bilingual keyword expansion
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.context_builder import (
        _approx_tokens,
        _expand_query,
    )
    _CB_OK = True
except ImportError:
    _CB_OK = False


# ---------------------------------------------------------------------------
# _approx_tokens
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestApproxTokens:
    def test_empty_string_returns_1(self):
        # max(1, 0//4) = max(1, 0) = 1
        assert _approx_tokens("") == 1

    def test_none_returns_1(self):
        assert _approx_tokens(None) == 1  # type: ignore[arg-type]

    def test_four_chars_returns_1(self):
        assert _approx_tokens("abcd") == 1

    def test_eight_chars_returns_2(self):
        assert _approx_tokens("a" * 8) == 2

    def test_400_chars_returns_100(self):
        assert _approx_tokens("x" * 400) == 100

    def test_proportional_to_length(self):
        t1 = _approx_tokens("a" * 100)
        t2 = _approx_tokens("a" * 200)
        assert t2 > t1

    def test_returns_int(self):
        assert isinstance(_approx_tokens("hello world"), int)

    def test_minimum_is_1(self):
        # Even 1-char text returns >= 1
        assert _approx_tokens("a") >= 1

    def test_unicode_text(self):
        result = _approx_tokens("Merhaba dünya!")
        assert result >= 1


# ---------------------------------------------------------------------------
# _expand_query
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestExpandQuery:
    def test_login_expands_to_synonyms(self):
        result = _expand_query(["login"])
        assert "login" in result
        # Turkish/EN synonyms
        assert "giriş" in result or "auth" in result

    def test_empty_list_returns_empty(self):
        assert _expand_query([]) == []

    def test_no_synonym_word_kept_as_is(self):
        result = _expand_query(["uniqueword123"])
        assert "uniqueword123" in result

    def test_no_duplicate_keywords(self):
        result = _expand_query(["login", "login"])
        assert result.count("login") == 1

    def test_no_duplicate_synonyms(self):
        # "login" and "auth" both expand to each other
        result = _expand_query(["login", "auth"])
        assert result.count("auth") == 1
        assert result.count("login") == 1

    def test_case_normalized(self):
        result = _expand_query(["LOGIN"])
        assert "login" in result

    def test_transfer_expands(self):
        result = _expand_query(["transfer"])
        assert "transfer" in result
        assert "havale" in result or "eft" in result

    def test_returns_list(self):
        assert isinstance(_expand_query(["login"]), list)

    def test_multiple_keywords_all_in_result(self):
        result = _expand_query(["login", "password"])
        assert "login" in result
        assert "password" in result

    def test_şifre_expands(self):
        result = _expand_query(["şifre"])
        assert "şifre" in result
        assert "password" in result or "parola" in result

    def test_empty_string_keyword_skipped(self):
        result = _expand_query(["", "login"])
        assert "" not in result

    def test_hesap_expands_to_account(self):
        result = _expand_query(["hesap"])
        assert "account" in result

    def test_order_preserved_original_first(self):
        result = _expand_query(["login"])
        # "login" should be first since it was in the input
        assert result[0] == "login"
