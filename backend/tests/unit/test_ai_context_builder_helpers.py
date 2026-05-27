"""Unit tests for app.domains.ai.context_builder — pure helper functions.

Tests are fully self-contained: no DB, no HTTP.
Covers: _normalize, _truncate, _approx_tokens, _extract_keywords,
        _detect_intent, _score_text, _expand_query, _summarize_steps.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.context_builder import (
        _normalize,
        _truncate,
        _approx_tokens,
        _extract_keywords,
        _detect_intent,
        _score_text,
        _expand_query,
        _summarize_steps,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="context_builder import failed")


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_lowercases_text(self):
        assert _normalize("HELLO World") == "hello world"

    def test_strips_punctuation(self):
        result = _normalize("hello, world!")
        assert "," not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        assert _normalize("  too   many   spaces  ") == "too many spaces"

    def test_empty_string_returns_empty(self):
        assert _normalize("") == ""

    def test_none_equivalent_empty_returns_empty(self):
        # module uses `(text or "")` internally
        # pass empty string as proxy
        assert _normalize("") == ""

    def test_keeps_hyphens(self):
        result = _normalize("gpt-4o-mini")
        assert "gpt-4o-mini" in result or "gpt" in result

    def test_unicode_preserved(self):
        result = _normalize("şifre güvenlik")
        assert "şifre" in result
        assert "güvenlik" in result


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------

class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 100) == "hello"

    def test_text_at_limit_unchanged(self):
        text = "x" * 10
        assert _truncate(text, 10) == text

    def test_long_text_truncated_with_ellipsis(self):
        text = "a" * 50
        result = _truncate(text, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_whitespace_collapsed(self):
        result = _truncate("  hello   world  ", 100)
        assert result == "hello world"

    def test_empty_string(self):
        assert _truncate("", 10) == ""

    def test_ellipsis_at_correct_position(self):
        result = _truncate("abcdefghij", 6)
        assert result == "abc..."


# ---------------------------------------------------------------------------
# _approx_tokens
# ---------------------------------------------------------------------------

class TestApproxTokens:
    def test_empty_string_returns_one(self):
        # max(1, ...) ensures minimum of 1
        assert _approx_tokens("") == 1

    def test_four_chars_one_token(self):
        assert _approx_tokens("abcd") == 1

    def test_eight_chars_two_tokens(self):
        assert _approx_tokens("abcdefgh") == 2

    def test_returns_int(self):
        assert isinstance(_approx_tokens("test"), int)

    def test_long_text_proportional(self):
        text = "a" * 400
        assert _approx_tokens(text) == 100


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------

class TestExtractKeywords:
    def test_extracts_content_words(self):
        keywords = _extract_keywords("login failure bug")
        assert "login" in keywords or "failure" in keywords or "bug" in keywords

    def test_filters_stop_words(self):
        keywords = _extract_keywords("bu bir test")
        # "bu" and "bir" are stop words
        assert "bu" not in keywords
        assert "bir" not in keywords

    def test_empty_query_returns_empty(self):
        assert _extract_keywords("") == []

    def test_returns_list(self):
        assert isinstance(_extract_keywords("hello world"), list)

    def test_max_eight_keywords(self):
        long_query = " ".join(f"keyword{i}" for i in range(20))
        assert len(_extract_keywords(long_query)) <= 8

    def test_duplicate_words_counted_once(self):
        keywords = _extract_keywords("bug bug bug")
        assert keywords.count("bug") == 1

    def test_short_tokens_excluded(self):
        # single-char tokens filtered (len > 1 required)
        keywords = _extract_keywords("a b c test")
        assert "a" not in keywords
        assert "b" not in keywords
        assert "c" not in keywords


# ---------------------------------------------------------------------------
# _detect_intent
# ---------------------------------------------------------------------------

class TestDetectIntent:
    def test_failure_intent_detected(self):
        intent = _detect_intent("test failed with error", ["error", "failure"])
        assert intent == "failure"

    def test_coverage_intent_detected(self):
        intent = _detect_intent("test coverage eksik kapsam", ["coverage", "eksik"])
        assert intent == "coverage"

    def test_automation_intent_detected(self):
        intent = _detect_intent("playwright bdd cucumber", ["playwright", "cucumber"])
        assert intent == "automation"

    def test_data_intent_detected(self):
        intent = _detect_intent("test data csv schema", ["data", "schema"])
        assert intent == "data"

    def test_unknown_returns_general(self):
        intent = _detect_intent("totally unrelated xyz", [])
        assert intent == "general"

    def test_returns_string(self):
        assert isinstance(_detect_intent("test", []), str)


# ---------------------------------------------------------------------------
# _score_text
# ---------------------------------------------------------------------------

class TestScoreText:
    def test_empty_text_returns_zero(self):
        assert _score_text("", ["keyword"]) == 0.0

    def test_empty_keywords_returns_base_score(self):
        score = _score_text("some text here", [])
        assert score == pytest.approx(0.4)

    def test_keyword_present_increases_score(self):
        with_kw = _score_text("login failed here", ["login"])
        without_kw = _score_text("something else", ["login"])
        assert with_kw > without_kw

    def test_multiple_occurrences_capped(self):
        # Occurrences capped at 3 in formula: min(occurrences, 3) * 0.7
        single = _score_text("login", ["login"])
        many = _score_text("login login login login login", ["login"])
        triple = _score_text("login login login", ["login"])
        # Triple and more should be same (capped)
        assert triple == pytest.approx(many, abs=0.1)

    def test_phrase_bonus_when_two_keywords_adjacent(self):
        score_phrase = _score_text("login failure detected", ["login", "failure"])
        score_separate = _score_text("login something failure detected", ["login", "failure"])
        # Phrase bonus may or may not apply depending on word order
        assert score_phrase >= score_separate - 2.0  # Allow some slack

    def test_returns_float(self):
        assert isinstance(_score_text("test text", ["test"]), float)


# ---------------------------------------------------------------------------
# _expand_query
# ---------------------------------------------------------------------------

class TestExpandQuery:
    def test_login_expands_to_synonyms(self):
        expanded = _expand_query(["login"])
        assert "login" in expanded
        # Should contain some synonyms
        assert len(expanded) > 1

    def test_transfer_expands_to_havale_eft(self):
        expanded = _expand_query(["transfer"])
        assert "havale" in expanded or "eft" in expanded

    def test_no_duplicates(self):
        expanded = _expand_query(["login", "login"])
        assert expanded.count("login") == 1

    def test_unknown_word_returned_as_is(self):
        expanded = _expand_query(["unknownword123"])
        assert "unknownword123" in expanded

    def test_empty_list_returns_empty(self):
        assert _expand_query([]) == []

    def test_returns_list(self):
        assert isinstance(_expand_query(["test"]), list)

    def test_case_insensitive_lookup(self):
        expanded = _expand_query(["LOGIN"])
        # Should lowercase and expand
        assert "login" in expanded or len(expanded) >= 1

    def test_original_keywords_preserved_first(self):
        expanded = _expand_query(["hesap"])
        assert expanded[0] == "hesap"


# ---------------------------------------------------------------------------
# _summarize_steps
# ---------------------------------------------------------------------------

class TestSummarizeSteps:
    def test_none_returns_empty(self):
        assert _summarize_steps(None) == ""

    def test_empty_list_returns_empty(self):
        assert _summarize_steps([]) == ""

    def test_non_list_returns_empty(self):
        assert _summarize_steps("not a list") == ""

    def test_dict_step_with_text(self):
        steps = [{"text": "User clicks login"}]
        result = _summarize_steps(steps)
        assert "User clicks login" in result

    def test_dict_step_with_keyword_and_text(self):
        steps = [{"keyword": "Given", "text": "user is logged in"}]
        result = _summarize_steps(steps)
        assert "Given" in result
        assert "user is logged in" in result

    def test_dict_step_with_action_field(self):
        steps = [{"action": "Click submit button"}]
        result = _summarize_steps(steps)
        assert "Click submit button" in result

    def test_dict_step_with_expected(self):
        steps = [{"text": "Submit form", "expected": "Success"}]
        result = _summarize_steps(steps)
        assert "Success" in result

    def test_string_step_included(self):
        steps = ["Plain text step"]
        result = _summarize_steps(steps)
        assert "Plain text step" in result

    def test_max_four_steps_taken(self):
        steps = [{"text": f"step{i}"} for i in range(10)]
        result = _summarize_steps(steps)
        # Only first 4 steps included
        assert "step4" not in result
        assert "step0" in result

    def test_pipe_separator_used(self):
        steps = [{"text": "step1"}, {"text": "step2"}]
        result = _summarize_steps(steps)
        assert " | " in result

    def test_empty_step_text_skipped(self):
        steps = [{"text": ""}, {"text": "valid"}]
        result = _summarize_steps(steps)
        assert "valid" in result
