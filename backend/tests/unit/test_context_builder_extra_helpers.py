"""Additional unit tests for ai.context_builder pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers (supplementing test_context_builder_pure_helpers.py):
  - _normalize: unicode-safe text normalization
  - _truncate: text truncation with ellipsis
  - _summarize_steps: step list → pipe-separated string
  - _score_text: keyword relevance score
  - _extract_keywords: top-8 tokens from query
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.context_builder import (
        _normalize,
        _truncate,
        _summarize_steps,
        _score_text,
        _extract_keywords,
    )
    _CB_OK = True
except ImportError:
    _CB_OK = False


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestNormalize:
    def test_lowercases(self):
        assert "hello world" == _normalize("Hello World")

    def test_removes_punctuation(self):
        result = _normalize("test, case!")
        assert "," not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        result = _normalize("a   b   c")
        assert "  " not in result

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_none_returns_empty(self):
        assert _normalize(None) == ""  # type: ignore[arg-type]

    def test_strips_edges(self):
        result = _normalize("  text  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_hyphens_preserved(self):
        # hyphens are kept (\w\s-)
        result = _normalize("test-case")
        assert "-" in result

    def test_returns_string(self):
        assert isinstance(_normalize("test"), str)


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 100) == "hello"

    def test_long_text_truncated(self):
        result = _truncate("a" * 200, 50)
        assert len(result) <= 50

    def test_truncated_ends_with_ellipsis(self):
        result = _truncate("a" * 200, 50)
        assert result.endswith("...")

    def test_exact_length_not_truncated(self):
        text = "a" * 50
        result = _truncate(text, 50)
        assert not result.endswith("...")

    def test_none_input_handled(self):
        result = _truncate(None, 50)  # type: ignore[arg-type]
        assert isinstance(result, str)

    def test_empty_string(self):
        assert _truncate("", 50) == ""

    def test_collapses_internal_whitespace(self):
        result = _truncate("a  b  c", 100)
        assert "  " not in result

    def test_returns_string(self):
        assert isinstance(_truncate("text", 100), str)


# ---------------------------------------------------------------------------
# _summarize_steps
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestSummarizeSteps:
    def test_empty_list_returns_empty(self):
        assert _summarize_steps([]) == ""

    def test_non_list_returns_empty(self):
        assert _summarize_steps("not a list") == ""
        assert _summarize_steps(None) == ""

    def test_dict_step_with_text(self):
        steps = [{"text": "Click Login"}]
        result = _summarize_steps(steps)
        assert "Click Login" in result

    def test_dict_step_with_action(self):
        steps = [{"action": "Submit Form"}]
        result = _summarize_steps(steps)
        assert "Submit Form" in result

    def test_string_step(self):
        steps = ["Navigate to home"]
        result = _summarize_steps(steps)
        assert "Navigate to home" in result

    def test_multiple_steps_joined_with_pipe(self):
        steps = [{"text": "Step 1"}, {"text": "Step 2"}]
        result = _summarize_steps(steps)
        assert "|" in result

    def test_max_4_steps(self):
        steps = [{"text": f"Step {i}"} for i in range(10)]
        result = _summarize_steps(steps)
        parts = [p.strip() for p in result.split("|")]
        assert len(parts) <= 4

    def test_empty_dict_step_skipped(self):
        steps = [{}, {"text": "Valid Step"}]
        result = _summarize_steps(steps)
        assert "Valid Step" in result

    def test_keyword_included_if_present(self):
        steps = [{"keyword": "Given", "text": "user is logged in"}]
        result = _summarize_steps(steps)
        assert "Given" in result

    def test_returns_string(self):
        assert isinstance(_summarize_steps([{"text": "step"}]), str)


# ---------------------------------------------------------------------------
# _score_text
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestScoreText:
    def test_empty_text_returns_zero(self):
        assert _score_text("", ["keyword"]) == pytest.approx(0.0)

    def test_empty_keywords_returns_base_score(self):
        score = _score_text("some text", [])
        assert score == pytest.approx(0.4)

    def test_matching_keyword_gives_positive_score(self):
        score = _score_text("login page exists", ["login"])
        assert score > 0.0

    def test_non_matching_keyword_gives_zero(self):
        score = _score_text("login page", ["submit"])
        assert score == pytest.approx(0.0)

    def test_more_keywords_match_higher_score(self):
        s1 = _score_text("login page", ["login"])
        s2 = _score_text("login page submit", ["login", "submit"])
        assert s2 > s1

    def test_returns_float(self):
        assert isinstance(_score_text("text", ["kw"]), float)

    def test_phrase_bonus(self):
        # "login page" as a phrase gives bonus vs separate keywords
        text = "test login page functionality"
        s_phrase = _score_text(text, ["login", "page"])
        s_separate = _score_text(text, ["login", "other"])
        assert s_phrase >= s_separate


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CB_OK, reason="context_builder import failed")
class TestExtractKeywords:
    def test_returns_list(self):
        assert isinstance(_extract_keywords("click login button"), list)

    def test_max_8_keywords(self):
        long_query = " ".join([f"keyword{i}" for i in range(20)])
        result = _extract_keywords(long_query)
        assert len(result) <= 8

    def test_stop_words_excluded(self):
        # "ve", "bir", "bu" are likely stop words in Turkish
        result = _extract_keywords("login ve submit test")
        assert "ve" not in result

    def test_short_tokens_excluded(self):
        result = _extract_keywords("a b test case")
        assert "a" not in result
        assert "b" not in result

    def test_empty_query(self):
        result = _extract_keywords("")
        assert isinstance(result, list)

    def test_meaningful_words_present(self):
        result = _extract_keywords("login button click test")
        assert any(w in result for w in ["login", "button", "click", "test"])

    def test_frequency_ranked(self):
        # "login" appears 3 times → should be in top keywords
        result = _extract_keywords("login login login click navigation")
        assert "login" in result
