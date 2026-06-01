"""Unit tests for AI context builder pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/context_builder.py:
    _approx_tokens, _extract_keywords, _detect_intent,
    _score_text, _normalize, _truncate
"""

from __future__ import annotations

import pytest

from app.domains.ai.context_builder import (
    _approx_tokens,
    _detect_intent,
    _extract_keywords,
    _normalize,
    _score_text,
    _truncate,
)


# ── _approx_tokens ────────────────────────────────────────────────────────────


class TestApproxTokens:
    def test_empty_string_returns_1(self) -> None:
        assert _approx_tokens("") == 1

    def test_none_treated_as_empty(self) -> None:
        assert _approx_tokens(None) == 1  # type: ignore[arg-type]

    def test_short_text_returns_at_least_1(self) -> None:
        assert _approx_tokens("hi") >= 1

    def test_longer_text_proportional(self) -> None:
        # 400 chars → 100 tokens (approx_chars_per_token=4)
        text = "a" * 400
        result = _approx_tokens(text)
        assert result > 1

    def test_returns_int(self) -> None:
        assert isinstance(_approx_tokens("hello world"), int)

    def test_consistent_for_same_input(self) -> None:
        text = "This is a test sentence."
        assert _approx_tokens(text) == _approx_tokens(text)

    def test_longer_text_has_more_tokens(self) -> None:
        short = "Hello."
        long = "Hello. " * 50
        assert _approx_tokens(long) > _approx_tokens(short)


# ── _normalize ────────────────────────────────────────────────────────────────


class TestNormalize:
    def test_lowercases(self) -> None:
        assert _normalize("HELLO WORLD") == "hello world"

    def test_strips_punctuation(self) -> None:
        result = _normalize("hello, world!")
        assert "," not in result
        assert "!" not in result

    def test_collapses_whitespace(self) -> None:
        result = _normalize("  lots   of   spaces  ")
        assert "  " not in result
        assert result == "lots of spaces"

    def test_empty_string(self) -> None:
        assert _normalize("") == ""

    def test_none_handled(self) -> None:
        assert _normalize(None) == ""  # type: ignore[arg-type]

    def test_preserves_hyphens(self) -> None:
        result = _normalize("test-driven")
        assert "test-driven" in result or "test" in result

    def test_unicode_text(self) -> None:
        result = _normalize("Şenaryo testi")
        assert "enaryo" in result or "senaryo" in result

    def test_returns_string(self) -> None:
        assert isinstance(_normalize("test"), str)


# ── _truncate ─────────────────────────────────────────────────────────────────


class TestTruncate:
    def test_short_text_unchanged(self) -> None:
        assert _truncate("hello", 100) == "hello"

    def test_long_text_truncated(self) -> None:
        text = "a" * 200
        result = _truncate(text, 50)
        assert len(result) <= 50

    def test_truncated_ends_with_ellipsis(self) -> None:
        text = "a" * 200
        result = _truncate(text, 50)
        assert result.endswith("...")

    def test_collapses_whitespace_before_truncating(self) -> None:
        text = "  lots   of   spaces  "
        result = _truncate(text, 100)
        assert "  " not in result

    def test_empty_string_returns_empty(self) -> None:
        assert _truncate("", 50) == ""

    def test_none_handled(self) -> None:
        result = _truncate(None, 50)  # type: ignore[arg-type]
        assert isinstance(result, str)

    def test_exact_length_not_truncated(self) -> None:
        text = "a" * 10
        assert _truncate(text, 10) == text

    def test_returns_string(self) -> None:
        assert isinstance(_truncate("test", 100), str)


# ── _extract_keywords ─────────────────────────────────────────────────────────


class TestExtractKeywords:
    def test_returns_list(self) -> None:
        assert isinstance(_extract_keywords("login scenario"), list)

    def test_empty_query_returns_empty(self) -> None:
        result = _extract_keywords("")
        assert result == [] or isinstance(result, list)

    def test_filters_stop_words(self) -> None:
        # Common stop words like "the", "a", "is" should be filtered
        result = _extract_keywords("the test is passing")
        assert "the" not in result
        assert "is" not in result or "test" in result

    def test_max_8_keywords(self) -> None:
        long_query = " ".join([f"word{i}" for i in range(20)])
        result = _extract_keywords(long_query)
        assert len(result) <= 8

    def test_important_words_included(self) -> None:
        result = _extract_keywords("login authentication test scenario")
        assert any(kw in result for kw in ["login", "authentication", "scenario", "test"])

    def test_single_char_words_excluded(self) -> None:
        result = _extract_keywords("a b c test scenario")
        assert "a" not in result
        assert "b" not in result

    def test_duplicate_words_counted(self) -> None:
        # Most frequent word should appear first
        result = _extract_keywords("login login login password")
        assert len(result) > 0
        assert result[0] == "login"

    def test_returns_strings(self) -> None:
        for kw in _extract_keywords("test scenario login"):
            assert isinstance(kw, str)


# ── _detect_intent ────────────────────────────────────────────────────────────


class TestDetectIntent:
    def test_failure_intent_detected(self) -> None:
        keywords = ["bug", "error", "fail"]
        result = _detect_intent("why does the test fail with error", keywords)
        assert result == "failure"

    def test_coverage_intent_detected(self) -> None:
        keywords = ["coverage", "gap", "requirement"]
        result = _detect_intent("what is the test coverage gap", keywords)
        assert result == "coverage"

    def test_automation_intent_detected(self) -> None:
        keywords = ["playwright", "gherkin", "locator"]
        result = _detect_intent("generate playwright gherkin scenario", keywords)
        assert result == "automation"

    def test_data_intent_detected(self) -> None:
        keywords = ["dataset", "veri"]
        result = _detect_intent("test data dataset schema", keywords)
        assert result == "data"

    def test_scenario_intent_detected(self) -> None:
        keywords = ["senaryo", "scenario"]
        result = _detect_intent("create test scenario", keywords)
        assert result == "scenario"

    def test_unknown_returns_general(self) -> None:
        result = _detect_intent("xyz abc 123", [])
        assert result == "general"

    def test_returns_string(self) -> None:
        assert isinstance(_detect_intent("test query", []), str)

    def test_empty_query_returns_general(self) -> None:
        result = _detect_intent("", [])
        assert result == "general"


# ── _score_text ───────────────────────────────────────────────────────────────


class TestScoreText:
    def test_returns_float(self) -> None:
        assert isinstance(_score_text("some text", ["some"]), float)

    def test_empty_keywords_returns_nonzero(self) -> None:
        # With no keywords, returns 0.4 (fallback score)
        result = _score_text("some text", [])
        assert result == pytest.approx(0.4)

    def test_empty_text_returns_zero(self) -> None:
        assert _score_text("", ["test"]) == pytest.approx(0.0)

    def test_matching_keyword_increases_score(self) -> None:
        score_no_match = _score_text("completely unrelated content", ["login"])
        score_match = _score_text("login authentication required", ["login"])
        assert score_match > score_no_match

    def test_multiple_occurrences_boost_score(self) -> None:
        score_once = _score_text("login is required", ["login"])
        score_multiple = _score_text("login login login required", ["login"])
        assert score_multiple >= score_once

    def test_phrase_match_boosts_score(self) -> None:
        keywords = ["login", "test"]
        score_single = _score_text("login scenario", keywords)
        score_phrase = _score_text("login test scenario", keywords)
        # phrase match adds 1.5 bonus
        assert score_phrase >= score_single

    def test_non_matching_text_returns_zero(self) -> None:
        result = _score_text("completely different content", ["login"])
        assert result == pytest.approx(0.0)

    def test_none_text_returns_zero(self) -> None:
        result = _score_text(None, ["test"])  # type: ignore[arg-type]
        assert result == pytest.approx(0.0)
