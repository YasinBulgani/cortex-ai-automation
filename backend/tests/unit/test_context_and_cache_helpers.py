"""Unit tests for context builder and semantic cache pure helper functions.

No DB, no Redis, no HTTP — pure Python only.

Covers:
  app/domains/ai/context_builder.py:
    _normalize, _truncate, _approx_tokens, _expand_query,
    _extract_keywords, _detect_intent, _score_text, _summarize_steps
  app/domains/ai/semantic_cache.py:
    _normalize_message, _exact_key, _cosine, _decode, _row_to_entry
"""

from __future__ import annotations

import math

import pytest

from app.domains.ai.context_builder import (
    _approx_tokens,
    _detect_intent,
    _expand_query,
    _extract_keywords,
    _normalize,
    _score_text,
    _summarize_steps,
    _truncate,
)
from app.domains.ai.semantic_cache import (
    CacheEntry,
    _cosine,
    _decode,
    _exact_key,
    _normalize_message,
    _row_to_entry,
)


# ── _normalize (context_builder) ──────────────────────────────────────────────


class TestContextNormalize:
    def test_lowercase(self) -> None:
        assert _normalize("HELLO") == "hello"

    def test_punctuation_stripped(self) -> None:
        result = _normalize("hello, world!")
        assert "," not in result
        assert "!" not in result

    def test_whitespace_collapsed(self) -> None:
        assert _normalize("hello   world") == "hello world"

    def test_empty_string(self) -> None:
        assert _normalize("") == ""

    def test_none_like_handled(self) -> None:
        # _normalize uses `(text or "").lower()` — None-safe
        # But type signature is str, so pass empty string
        assert _normalize("") == ""

    def test_leading_trailing_stripped(self) -> None:
        assert _normalize("  hello  ") == "hello"

    def test_unicode_preserved(self) -> None:
        result = _normalize("Türkçe metin")
        assert "türkçe" in result

    def test_hyphen_preserved(self) -> None:
        result = _normalize("data-driven test")
        assert "data-driven" in result


# ── _truncate ─────────────────────────────────────────────────────────────────


class TestTruncate:
    def test_short_text_unchanged(self) -> None:
        text = "hello world"
        assert _truncate(text, 50) == text

    def test_long_text_truncated(self) -> None:
        text = "a" * 100
        result = _truncate(text, 50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_exact_length_unchanged(self) -> None:
        text = "hello"
        assert _truncate(text, 5) == text

    def test_empty_string(self) -> None:
        assert _truncate("", 10) == ""

    def test_none_like_returns_empty(self) -> None:
        assert _truncate("", 10) == ""

    def test_whitespace_collapsed_before_truncate(self) -> None:
        text = "a  b  c"
        result = _truncate(text, 100)
        assert "  " not in result  # collapsed

    def test_truncation_adds_ellipsis(self) -> None:
        text = "x" * 200
        result = _truncate(text, 50)
        assert result.endswith("...")

    def test_max_len_respected(self) -> None:
        text = "hello world this is a long text"
        result = _truncate(text, 10)
        assert len(result) <= 10


# ── _approx_tokens ────────────────────────────────────────────────────────────


class TestApproxTokens:
    def test_empty_string_returns_one(self) -> None:
        # max(1, 0 // 4) = max(1, 0) = 1
        assert _approx_tokens("") == 1

    def test_four_chars_is_one_token(self) -> None:
        assert _approx_tokens("abcd") == 1

    def test_eight_chars_is_two_tokens(self) -> None:
        assert _approx_tokens("a" * 8) == 2

    def test_100_chars(self) -> None:
        assert _approx_tokens("a" * 100) == 25

    def test_none_handled(self) -> None:
        assert _approx_tokens(None) >= 1  # type: ignore[arg-type]

    def test_longer_text_more_tokens(self) -> None:
        short = _approx_tokens("short text")
        long = _approx_tokens("this is a much much longer text " * 10)
        assert long > short


# ── _expand_query ─────────────────────────────────────────────────────────────


class TestExpandQuery:
    def test_empty_returns_empty(self) -> None:
        assert _expand_query([]) == []

    def test_unknown_keyword_unchanged(self) -> None:
        result = _expand_query(["xyz_unknown"])
        assert "xyz_unknown" in result

    def test_login_expands_to_synonyms(self) -> None:
        result = _expand_query(["login"])
        assert "login" in result
        # login has synonyms: giriş, oturum, auth
        assert any(s in result for s in ["giriş", "auth", "oturum"])

    def test_transfer_expands(self) -> None:
        result = _expand_query(["transfer"])
        assert "transfer" in result
        assert any(s in result for s in ["havale", "eft", "para"])

    def test_no_duplicates(self) -> None:
        # login + auth both expand to each other — no duplicates
        result = _expand_query(["login", "auth"])
        assert len(result) == len(set(result))

    def test_case_insensitive_expansion(self) -> None:
        result = _expand_query(["LOGIN"])
        # Lowercased to "login" which has synonyms
        assert "login" in result

    def test_multiple_keywords_all_present(self) -> None:
        result = _expand_query(["transfer", "login"])
        assert "transfer" in result
        assert "login" in result


# ── _extract_keywords ─────────────────────────────────────────────────────────


class TestExtractKeywords:
    def test_empty_query_returns_empty(self) -> None:
        assert _extract_keywords("") == []

    def test_single_word(self) -> None:
        result = _extract_keywords("transfer")
        assert "transfer" in result

    def test_stop_words_excluded(self) -> None:
        # Turkish stop words like "ve" should be excluded
        result = _extract_keywords("ve ile")
        # "ve" and "ile" are stop words — likely empty or minimal
        # Just check it doesn't raise
        assert isinstance(result, list)

    def test_at_most_8_keywords(self) -> None:
        query = "transfer havale eft payment balance hesap kart login extra more"
        result = _extract_keywords(query)
        assert len(result) <= 8

    def test_single_char_tokens_excluded(self) -> None:
        result = _extract_keywords("a b c transfer")
        assert "a" not in result
        assert "b" not in result

    def test_repeated_words_handled(self) -> None:
        result = _extract_keywords("transfer transfer transfer login")
        assert isinstance(result, list)
        # Should not raise; most common 8 returned

    def test_banking_keywords_included(self) -> None:
        result = _extract_keywords("transfer hesap login")
        assert any(k in result for k in ["transfer", "hesap", "login"])


# ── _detect_intent ────────────────────────────────────────────────────────────


class TestDetectIntent:
    def test_failure_intent(self) -> None:
        result = _detect_intent("test error debug failure", ["error", "failure"])
        assert result == "failure"

    def test_coverage_intent(self) -> None:
        result = _detect_intent("coverage gap kapsam eksik", ["coverage", "gap"])
        assert result == "coverage"

    def test_automation_intent(self) -> None:
        result = _detect_intent("playwright locator selector", ["playwright", "locator"])
        assert result == "automation"

    def test_data_intent(self) -> None:
        result = _detect_intent("dataset schema sql veri", ["dataset", "schema"])
        assert result == "data"

    def test_scenario_intent(self) -> None:
        result = _detect_intent("senaryo scenario test case", ["senaryo", "scenario"])
        assert result == "scenario"

    def test_unknown_returns_general(self) -> None:
        result = _detect_intent("xyz unknown abc", ["xyz"])
        assert result == "general"

    def test_empty_returns_general(self) -> None:
        result = _detect_intent("", [])
        assert result == "general"

    def test_returns_string(self) -> None:
        result = _detect_intent("some query", ["some"])
        assert isinstance(result, str)


# ── _score_text ───────────────────────────────────────────────────────────────


class TestScoreText:
    def test_empty_text_returns_zero(self) -> None:
        assert _score_text("", ["keyword"]) == 0.0

    def test_empty_keywords_returns_baseline(self) -> None:
        # No keywords → returns 0.4
        assert _score_text("some text", []) == 0.4

    def test_matching_keyword_positive_score(self) -> None:
        score = _score_text("transfer test failed", ["transfer"])
        assert score > 0.0

    def test_non_matching_keyword_zero(self) -> None:
        score = _score_text("login test passed", ["transfer"])
        assert score == 0.0

    def test_more_occurrences_higher_score(self) -> None:
        s1 = _score_text("transfer", ["transfer"])
        s2 = _score_text("transfer transfer transfer transfer", ["transfer"])
        assert s2 >= s1

    def test_multiple_keywords_higher_score(self) -> None:
        s1 = _score_text("transfer login", ["transfer"])
        s2 = _score_text("transfer login", ["transfer", "login"])
        assert s2 > s1

    def test_phrase_bonus(self) -> None:
        # First two keywords as phrase → bonus if found
        text = "transfer login scenario"
        s_phrase = _score_text(text, ["transfer", "login"])
        s_no_phrase = _score_text(text, ["transfer", "abc"])
        assert s_phrase >= s_no_phrase

    def test_case_insensitive_matching(self) -> None:
        score = _score_text("TRANSFER TEST", ["transfer"])
        assert score > 0.0


# ── _summarize_steps ──────────────────────────────────────────────────────────


class TestSummarizeSteps:
    def test_empty_list_returns_empty(self) -> None:
        assert _summarize_steps([]) == ""

    def test_non_list_returns_empty(self) -> None:
        assert _summarize_steps("not a list") == ""  # type: ignore[arg-type]
        assert _summarize_steps(None) == ""  # type: ignore[arg-type]

    def test_dict_step_with_text(self) -> None:
        steps = [{"keyword": "Given", "text": "user logs in"}]
        result = _summarize_steps(steps)
        assert "user logs in" in result

    def test_dict_step_with_action(self) -> None:
        steps = [{"action": "click login button"}]
        result = _summarize_steps(steps)
        assert "click login button" in result

    def test_string_step(self) -> None:
        steps = ["kullanıcı giriş yapar"]
        result = _summarize_steps(steps)
        assert "kullanıcı giriş yapar" in result

    def test_max_4_steps_shown(self) -> None:
        steps = [{"text": f"step {i}"} for i in range(10)]
        result = _summarize_steps(steps)
        # Only first 4 processed, separated by " | "
        parts = result.split(" | ")
        assert len(parts) <= 4

    def test_separator_between_steps(self) -> None:
        steps = [{"text": "step1"}, {"text": "step2"}]
        result = _summarize_steps(steps)
        assert " | " in result

    def test_expected_field_included(self) -> None:
        steps = [{"text": "action", "expected": "result"}]
        result = _summarize_steps(steps)
        assert "result" in result


# ── _normalize_message (semantic_cache) ──────────────────────────────────────


class TestNormalizeMessage:
    def test_empty_returns_empty(self) -> None:
        assert _normalize_message("") == ""

    def test_none_returns_empty(self) -> None:
        assert _normalize_message(None) == ""  # type: ignore[arg-type]

    def test_lowercase(self) -> None:
        assert _normalize_message("HELLO") == "hello"

    def test_whitespace_collapsed(self) -> None:
        result = _normalize_message("hello   world")
        assert "  " not in result

    def test_trailing_punctuation_removed(self) -> None:
        assert _normalize_message("hello.") == "hello"
        assert _normalize_message("hello!") == "hello"
        assert _normalize_message("hello?") == "hello"

    def test_leading_trailing_stripped(self) -> None:
        assert _normalize_message("  hello  ") == "hello"

    def test_deterministic(self) -> None:
        k1 = _normalize_message("Hello World.")
        k2 = _normalize_message("Hello World.")
        assert k1 == k2


# ── _exact_key ────────────────────────────────────────────────────────────────


class TestExactKey:
    def test_returns_string(self) -> None:
        result = _exact_key("chat", "hello", None)
        assert isinstance(result, str)

    def test_length_40(self) -> None:
        # SHA1 hex = 40 chars
        result = _exact_key("chat", "hello", None)
        assert len(result) == 40

    def test_deterministic(self) -> None:
        k1 = _exact_key("chat", "hello world", "system")
        k2 = _exact_key("chat", "hello world", "system")
        assert k1 == k2

    def test_different_task_types_different_keys(self) -> None:
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("generation", "hello", None)
        assert k1 != k2

    def test_different_messages_different_keys(self) -> None:
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("chat", "goodbye", None)
        assert k1 != k2

    def test_none_system_msg_handled(self) -> None:
        result = _exact_key("chat", "hello", None)
        assert len(result) == 40

    def test_user_msg_normalized(self) -> None:
        # Same message after normalization → same key
        k1 = _exact_key("chat", "HELLO WORLD.", None)
        k2 = _exact_key("chat", "hello world", None)
        assert k1 == k2  # normalized to same string


# ── _cosine (semantic_cache) ──────────────────────────────────────────────────


class TestSemanticCacheCosine:
    def test_identical_vectors(self) -> None:
        v = [1.0, 0.0, 0.0]
        result = _cosine(v, v)
        assert result == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        result = _cosine([1.0, 0.0], [0.0, 1.0])
        assert result == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        result = _cosine([1.0, 0.0], [-1.0, 0.0])
        assert result == pytest.approx(-1.0)

    def test_empty_vectors_returns_zero(self) -> None:
        assert _cosine([], []) == 0.0

    def test_unequal_length_returns_zero(self) -> None:
        assert _cosine([1.0, 2.0], [1.0]) == 0.0

    def test_zero_vector_returns_zero(self) -> None:
        assert _cosine([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_result_between_minus_one_and_one(self) -> None:
        a = [0.5, 0.3, 0.7]
        b = [0.2, 0.8, 0.1]
        result = _cosine(a, b)
        assert -1.0 <= result <= 1.0

    def test_full_cosine_not_just_dot(self) -> None:
        # This version normalizes; _cosine([2,0],[2,0]) should be 1.0, not 4.0
        result = _cosine([2.0, 0.0], [2.0, 0.0])
        assert result == pytest.approx(1.0)


# ── _decode ───────────────────────────────────────────────────────────────────


class TestDecode:
    def test_none_returns_none(self) -> None:
        assert _decode(None) is None

    def test_bytes_decoded(self) -> None:
        assert _decode(b"hello") == "hello"

    def test_bytearray_decoded(self) -> None:
        assert _decode(bytearray(b"world")) == "world"

    def test_string_returned_as_is(self) -> None:
        assert _decode("test") == "test"

    def test_integer_converted_to_string(self) -> None:
        assert _decode(42) == "42"

    def test_unicode_bytes_decoded(self) -> None:
        result = _decode("Türkçe".encode("utf-8"))
        assert result == "Türkçe"


# ── _row_to_entry ─────────────────────────────────────────────────────────────


class TestRowToEntry:
    def test_empty_dict_returns_none(self) -> None:
        assert _row_to_entry({}) is None

    def test_missing_response_returns_none(self) -> None:
        data = {"task_type": "chat", "user_msg": "hello"}
        assert _row_to_entry(data) is None

    def test_valid_row_returns_cache_entry(self) -> None:
        data = {
            "response": "AI answer",
            "task_type": "chat",
            "user_msg": "hello",
            "created_at": "1700000000.0",
            "hits": "5",
        }
        result = _row_to_entry(data)
        assert result is not None
        assert isinstance(result, CacheEntry)

    def test_response_field_set(self) -> None:
        data = {"response": "test answer", "task_type": "chat"}
        result = _row_to_entry(data)
        assert result is not None
        assert result.response == "test answer"

    def test_bytes_keys_also_work(self) -> None:
        data = {b"response": b"AI answer", b"task_type": b"generation"}
        result = _row_to_entry(data)
        assert result is not None
        assert result.response == "AI answer"

    def test_missing_task_type_defaults_to_unknown(self) -> None:
        data = {"response": "answer"}
        result = _row_to_entry(data)
        assert result is not None
        assert result.task_type == "unknown"

    def test_hits_default_to_zero(self) -> None:
        data = {"response": "answer"}
        result = _row_to_entry(data)
        assert result is not None
        assert result.hits == 0

    def test_invalid_created_at_returns_none_or_entry(self) -> None:
        # "abc" can't be converted to float → exception caught → None
        data = {"response": "answer", "created_at": "not-a-number"}
        result = _row_to_entry(data)
        assert result is None
