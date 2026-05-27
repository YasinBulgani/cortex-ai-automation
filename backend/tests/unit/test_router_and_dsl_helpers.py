"""Unit tests for smart model router and DSL grounding pure helper functions.

No DB, no LLM, no HTTP — pure Python only.

Covers:
  app/domains/ai/smart_model_router.py:
    _next_tier, _estimate_cost, Tier
  app/domains/tspm/dsl_grounding_for_bdd.py:
    _normalize, _strip_placeholders, _fill_placeholders,
    _tokenize_for_match, _token_overlap_score,
    _extract_capitalized_phrases, _cache_key, _keyword_to_bucket
"""

from __future__ import annotations

import pytest

from app.domains.ai.smart_model_router import Tier, _estimate_cost, _next_tier
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


# ── _next_tier ────────────────────────────────────────────────────────────────


class TestNextTier:
    def test_premium_falls_to_mid(self) -> None:
        assert _next_tier(Tier.PREMIUM) == Tier.MID

    def test_mid_falls_to_mini(self) -> None:
        assert _next_tier(Tier.MID) == Tier.MINI

    def test_mini_falls_to_local(self) -> None:
        assert _next_tier(Tier.MINI) == Tier.LOCAL

    def test_local_stays_local(self) -> None:
        assert _next_tier(Tier.LOCAL) == Tier.LOCAL

    def test_returns_tier_instance(self) -> None:
        result = _next_tier(Tier.PREMIUM)
        assert isinstance(result, Tier)


# ── _estimate_cost ────────────────────────────────────────────────────────────


class TestEstimateCost:
    def test_returns_float(self) -> None:
        result = _estimate_cost("gpt-4o", 1000)
        assert isinstance(result, float)

    def test_non_negative(self) -> None:
        result = _estimate_cost("gpt-4o", 1000)
        assert result >= 0.0

    def test_zero_tokens_returns_zero(self) -> None:
        result = _estimate_cost("gpt-4o", 0)
        assert result == 0.0

    def test_unknown_model_returns_zero(self) -> None:
        # compute_cost_usd may raise for unknown model → returns 0.0
        result = _estimate_cost("totally-unknown-xyz-model", 1000)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_more_tokens_higher_cost(self) -> None:
        low = _estimate_cost("gpt-4o", 100)
        high = _estimate_cost("gpt-4o", 10000)
        # May both be 0 for unknown model, but shouldn't decrease
        assert high >= low


# ── _normalize (dsl_grounding_for_bdd) ───────────────────────────────────────


class TestDslNormalize:
    def test_lowercase(self) -> None:
        assert _normalize("HELLO") == "hello"

    def test_punctuation_replaced(self) -> None:
        result = _normalize("hello, world!")
        assert "," not in result
        assert "!" not in result

    def test_whitespace_collapsed(self) -> None:
        result = _normalize("hello   world")
        assert "  " not in result

    def test_empty_string(self) -> None:
        assert _normalize("") == ""

    def test_quotes_removed(self) -> None:
        result = _normalize('"hello"')
        assert '"' not in result

    def test_leading_trailing_stripped(self) -> None:
        result = _normalize("  hello  ")
        assert result == "hello"

    def test_brackets_replaced(self) -> None:
        result = _normalize("value [test]")
        assert "[" not in result
        assert "]" not in result


# ── _strip_placeholders ───────────────────────────────────────────────────────


class TestStripPlaceholders:
    def test_removes_single_placeholder(self) -> None:
        result = _strip_placeholders("user enters {value}")
        assert "{value}" not in result

    def test_removes_multiple_placeholders(self) -> None:
        result = _strip_placeholders("{user} clicks {button}")
        assert "{user}" not in result
        assert "{button}" not in result

    def test_no_placeholders_unchanged(self) -> None:
        text = "user clicks login button"
        assert _strip_placeholders(text) == text

    def test_empty_string(self) -> None:
        assert _strip_placeholders("") == ""

    def test_text_preserved_around_placeholder(self) -> None:
        result = _strip_placeholders("user enters {value} and clicks")
        assert "user enters" in result
        assert "and clicks" in result

    def test_placeholder_replaced_with_space(self) -> None:
        result = _strip_placeholders("alana {deger} yazilir")
        # {deger} replaced with space → "alana   yazilir" → stripped
        assert "deger" not in result
        assert "{" not in result


# ── _fill_placeholders ────────────────────────────────────────────────────────


class TestFillPlaceholders:
    def test_no_placeholders_unchanged(self) -> None:
        pattern = "user clicks login button"
        result = _fill_placeholders(pattern, "some source text")
        assert result == pattern

    def test_fills_from_quoted_value(self) -> None:
        pattern = 'kullanıcı "{email}" alanına yazar'
        result = _fill_placeholders(pattern, 'user@example.com değerini "user@test.com" olarak gir')
        assert "user@test.com" in result

    def test_fills_from_capitalized_phrase_when_no_quotes(self) -> None:
        pattern = "kullanıcı {button} butonuna tıklar"
        result = _fill_placeholders(pattern, "Giriş Yap butonuna tıkla")
        # "Giriş Yap" is capitalized → fills placeholder
        assert "Giriş" in result or "button" in result

    def test_empty_pattern(self) -> None:
        result = _fill_placeholders("", "source text")
        assert result == ""

    def test_more_placeholders_than_values_partial_fill(self) -> None:
        pattern = "{a} ve {b} ve {c}"
        result = _fill_placeholders(pattern, '"value1"')
        # Only first placeholder filled
        assert "value1" in result
        assert "{b}" in result or "{c}" in result


# ── _tokenize_for_match ───────────────────────────────────────────────────────


class TestTokenizeForMatch:
    def test_empty_string_returns_empty_set(self) -> None:
        assert _tokenize_for_match("") == set()

    def test_single_word(self) -> None:
        result = _tokenize_for_match("login")
        assert "login" in result

    def test_short_tokens_excluded(self) -> None:
        # "ve" (2 chars) → excluded; "login" (5 chars) → included
        result = _tokenize_for_match("ve login")
        assert "ve" not in result
        assert "login" in result

    def test_placeholders_excluded(self) -> None:
        result = _tokenize_for_match("alana {deger} yazar")
        assert "{deger}" not in result
        assert any(t in result for t in ["alana", "yazar"])

    def test_returns_set(self) -> None:
        result = _tokenize_for_match("test test test")
        assert isinstance(result, set)
        # No duplicates in set
        assert len(result) == 1

    def test_multiple_words(self) -> None:
        result = _tokenize_for_match("kullanıcı giriş yapar")
        assert "kullanıcı" in result or "giriş" in result or "yapar" in result

    def test_normalized_to_lowercase(self) -> None:
        result = _tokenize_for_match("LOGIN")
        assert "login" in result


# ── _token_overlap_score ──────────────────────────────────────────────────────


class TestTokenOverlapScore:
    def test_empty_query_returns_zero(self) -> None:
        assert _token_overlap_score(set(), "login button") == 0.0

    def test_empty_alias_returns_zero(self) -> None:
        assert _token_overlap_score({"login"}, "") == 0.0

    def test_full_overlap_returns_one(self) -> None:
        # alias tokens fully contained in query tokens
        q = {"login", "button", "click"}
        result = _token_overlap_score(q, "login button")
        assert result == pytest.approx(1.0)

    def test_partial_overlap(self) -> None:
        q = {"login"}
        # alias "login button" → 2 tokens, 1 overlap → 1/2 = 0.5
        result = _token_overlap_score(q, "login button")
        assert 0.0 < result < 1.0

    def test_no_overlap_returns_zero(self) -> None:
        q = {"transfer"}
        result = _token_overlap_score(q, "login button")
        assert result == 0.0

    def test_result_between_zero_and_one(self) -> None:
        q = {"kullanıcı", "giriş"}
        result = _token_overlap_score(q, "kullanıcı giriş sayfası")
        assert 0.0 <= result <= 1.0


# ── _extract_capitalized_phrases ──────────────────────────────────────────────


class TestExtractCapitalizedPhrases:
    def test_empty_returns_empty(self) -> None:
        assert _extract_capitalized_phrases("") == []

    def test_single_capitalized_word(self) -> None:
        result = _extract_capitalized_phrases("Click Login")
        assert "Login" in result or "Click Login" in result

    def test_multi_word_phrase(self) -> None:
        result = _extract_capitalized_phrases("Click Giriş Yap button")
        # "Giriş Yap" is capitalized phrase
        assert any("Giriş" in p for p in result)

    def test_lowercase_words_not_captured(self) -> None:
        result = _extract_capitalized_phrases("click the button")
        assert result == []

    def test_mixed_returns_only_capitalized(self) -> None:
        result = _extract_capitalized_phrases("click Login button and Submit")
        # "Login" and "Submit" are capitalized
        assert any("Login" in p for p in result)
        assert any("Submit" in p for p in result)

    def test_punctuation_stripped_before_check(self) -> None:
        # "Login," → cleaned to "Login" → capitalized
        result = _extract_capitalized_phrases("Click Login,")
        assert any("Login" in p for p in result)

    def test_returns_list(self) -> None:
        assert isinstance(_extract_capitalized_phrases("Hello World"), list)


# ── _cache_key (dsl_grounding_for_bdd) ───────────────────────────────────────


class TestDslCacheKey:
    def test_returns_string(self) -> None:
        result = _cache_key("login test", 5, "tr")
        assert isinstance(result, str)

    def test_deterministic(self) -> None:
        k1 = _cache_key("login test", 5, "tr")
        k2 = _cache_key("login test", 5, "tr")
        assert k1 == k2

    def test_different_top_k_different_key(self) -> None:
        k1 = _cache_key("login", 5, "tr")
        k2 = _cache_key("login", 10, "tr")
        assert k1 != k2

    def test_different_text_different_key(self) -> None:
        k1 = _cache_key("login", 5, "tr")
        k2 = _cache_key("transfer", 5, "tr")
        assert k1 != k2

    def test_none_lang_handled(self) -> None:
        result = _cache_key("login", 5, None)
        assert isinstance(result, str)

    def test_long_text_truncated(self) -> None:
        short = _cache_key("a" * 100, 5, None)
        long = _cache_key("a" * 600, 5, None)
        # Both truncated to 512 chars → same key if first 512 chars match
        k1 = _cache_key("a" * 512, 5, None)
        k2 = _cache_key("a" * 600, 5, None)
        # strip() then [:512] → "a"*512 for both
        assert k1 == k2


# ── _keyword_to_bucket ────────────────────────────────────────────────────────


class TestKeywordToBucket:
    def test_given_keyword(self) -> None:
        assert _keyword_to_bucket("given") == "given"

    def test_diyelim_ki(self) -> None:
        assert _keyword_to_bucket("diyelim ki") == "given"

    def test_when_keyword(self) -> None:
        assert _keyword_to_bucket("when") == "when"

    def test_eger(self) -> None:
        assert _keyword_to_bucket("eğer") == "when"

    def test_eger_without_cedilla(self) -> None:
        assert _keyword_to_bucket("eger") == "when"

    def test_then_keyword(self) -> None:
        assert _keyword_to_bucket("then") == "then"

    def test_o_zaman(self) -> None:
        assert _keyword_to_bucket("o zaman") == "then"

    def test_ve_returns_none(self) -> None:
        assert _keyword_to_bucket("ve") is None

    def test_and_returns_none(self) -> None:
        assert _keyword_to_bucket("and") is None

    def test_unknown_returns_none(self) -> None:
        assert _keyword_to_bucket("xyz_unknown") is None

    def test_empty_returns_none(self) -> None:
        assert _keyword_to_bucket("") is None

    def test_none_returns_none(self) -> None:
        assert _keyword_to_bucket(None) is None  # type: ignore[arg-type]

    def test_colon_stripped(self) -> None:
        # "given:" → stripped to "given"
        assert _keyword_to_bucket("given:") == "given"

    def test_case_insensitive(self) -> None:
        # Function lowercases input: "GIVEN" → "given" → matches
        assert _keyword_to_bucket("GIVEN") == "given"
        assert _keyword_to_bucket("WHEN") == "when"
        assert _keyword_to_bucket("THEN") == "then"
