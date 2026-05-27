"""Unit tests for knowledge store and test runner pure helper functions.

No DB, no HTTP, no external deps.

Covers:
  app/domains/ai/knowledge_store.py:
    _embed_cache_key, _cosine_similarity, mask_sensitive
  app/domains/tspm/test_runner_service.py:
    _convert_steps
"""

from __future__ import annotations

import math

import pytest

from app.domains.ai.knowledge_store import (
    _cosine_similarity,
    _embed_cache_key,
    mask_sensitive,
)
from app.domains.tspm.test_runner_service import _convert_steps


# ── _embed_cache_key ──────────────────────────────────────────────────────────


class TestEmbedCacheKey:
    def test_returns_string(self) -> None:
        result = _embed_cache_key("hello world")
        assert isinstance(result, str)

    def test_length_32(self) -> None:
        result = _embed_cache_key("some text")
        assert len(result) == 32

    def test_hex_characters(self) -> None:
        result = _embed_cache_key("test input")
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self) -> None:
        k1 = _embed_cache_key("same text")
        k2 = _embed_cache_key("same text")
        assert k1 == k2

    def test_different_texts_different_keys(self) -> None:
        k1 = _embed_cache_key("text one")
        k2 = _embed_cache_key("text two")
        assert k1 != k2

    def test_empty_string(self) -> None:
        result = _embed_cache_key("")
        assert len(result) == 32

    def test_long_text_truncated_at_4000(self) -> None:
        # Both texts beyond 4000 chars but share first 4000 chars → same key
        base = "x" * 4000
        k1 = _embed_cache_key(base)
        k2 = _embed_cache_key(base + "extra stuff after 4000")
        assert k1 == k2

    def test_unicode_text(self) -> None:
        result = _embed_cache_key("Türkçe metin ile test ışık çöp")
        assert isinstance(result, str)
        assert len(result) == 32


# ── _cosine_similarity ────────────────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_vectors_returns_one(self) -> None:
        v = [0.6, 0.8]  # normalized: 0.6^2 + 0.8^2 = 1.0
        result = _cosine_similarity(v, v)
        assert result == pytest.approx(1.0)

    def test_orthogonal_vectors_returns_zero(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(0.0)

    def test_opposite_vectors_returns_minus_one(self) -> None:
        a = [0.6, 0.8]
        b = [-0.6, -0.8]
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(-1.0)

    def test_empty_vectors_returns_zero(self) -> None:
        # zip of empty → sum is 0
        result = _cosine_similarity([], [])
        assert result == pytest.approx(0.0)

    def test_simple_dot_product(self) -> None:
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        # dot = 4 + 10 + 18 = 32
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(32.0)

    def test_returns_float(self) -> None:
        result = _cosine_similarity([0.5, 0.5], [0.5, 0.5])
        assert isinstance(result, float)

    def test_partial_overlap_truncates_to_shorter(self) -> None:
        # zip stops at shorter → only first two elements
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0]
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(14.0)  # 1*4 + 2*5 = 14


# ── mask_sensitive ────────────────────────────────────────────────────────────


class TestMaskSensitive:
    def test_email_masked(self) -> None:
        text = "Please contact user@example.com for support"
        result = mask_sensitive(text)
        assert "user@example.com" not in result
        assert "[EMAIL]" in result

    def test_turkish_phone_masked(self) -> None:
        text = "Call me at 05321234567"
        result = mask_sensitive(text)
        assert "05321234567" not in result
        assert "[TEL]" in result

    def test_credit_card_masked(self) -> None:
        text = "Card: 4111 1111 1111 1111"
        result = mask_sensitive(text)
        assert "4111 1111 1111 1111" not in result
        assert "[KART]" in result

    def test_iban_masked(self) -> None:
        text = "My IBAN: TR330006100519786457841326"
        result = mask_sensitive(text)
        assert "TR33" not in result or "[IBAN]" in result

    def test_password_field_masked(self) -> None:
        text = "password=supersecret123"
        result = mask_sensitive(text)
        assert "supersecret123" not in result
        assert "[SIFRE]" in result

    def test_sifre_field_masked(self) -> None:
        text = "şifre: mypassword"
        result = mask_sensitive(text)
        assert "mypassword" not in result
        assert "[SIFRE]" in result

    def test_no_sensitive_data_unchanged(self) -> None:
        text = "This is a regular sentence about test coverage."
        result = mask_sensitive(text)
        assert result == text

    def test_empty_string_unchanged(self) -> None:
        assert mask_sensitive("") == ""

    def test_multiple_emails_all_masked(self) -> None:
        text = "a@example.com and b@test.org are contacts"
        result = mask_sensitive(text)
        assert "a@example.com" not in result
        assert "b@test.org" not in result
        assert result.count("[EMAIL]") == 2

    def test_tc_kimlik_masked(self) -> None:
        # 11-digit number starting with non-zero
        text = "TC: 12345678901"
        result = mask_sensitive(text)
        assert "12345678901" not in result
        assert "[TC_KIMLIK]" in result

    def test_returns_string(self) -> None:
        result = mask_sensitive("test text")
        assert isinstance(result, str)


# ── _convert_steps ────────────────────────────────────────────────────────────


class TestConvertSteps:
    def test_empty_list_returns_empty(self) -> None:
        assert _convert_steps([]) == []

    def test_action_key_step(self) -> None:
        steps = [{"action": "click login button", "expected": "redirected"}]
        result = _convert_steps(steps)
        assert len(result) == 1
        assert result[0]["action"] == "click login button"
        assert result[0]["expected"] == "redirected"

    def test_action_key_without_expected_uses_empty(self) -> None:
        steps = [{"action": "click button"}]
        result = _convert_steps(steps)
        assert result[0]["expected"] == ""

    def test_text_key_with_arrow(self) -> None:
        steps = [{"text": "kullanıcı giriş yapar → başarı mesajı görünür"}]
        result = _convert_steps(steps)
        assert len(result) == 1
        assert result[0]["action"] == "kullanıcı giriş yapar"
        assert result[0]["expected"] == "başarı mesajı görünür"

    def test_text_key_without_arrow(self) -> None:
        steps = [{"text": "kullanıcı login sayfasına gider"}]
        result = _convert_steps(steps)
        assert len(result) == 1
        assert result[0]["action"] == "kullanıcı login sayfasına gider"
        assert result[0]["expected"] == ""

    def test_non_dict_entries_skipped(self) -> None:
        steps = [
            {"action": "click"},
            "not a dict",
            42,
            None,
            {"action": "submit"},
        ]
        result = _convert_steps(steps)
        assert len(result) == 2

    def test_dict_without_action_or_text_skipped(self) -> None:
        steps = [{"keyword": "Given", "value": "user is logged in"}]
        result = _convert_steps(steps)
        assert len(result) == 0

    def test_action_takes_priority_over_text(self) -> None:
        # If "action" key present, uses action path
        steps = [{"action": "click", "text": "this is text too"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "click"

    def test_multiple_steps_all_converted(self) -> None:
        steps = [
            {"action": "step1"},
            {"text": "step2 → expected2"},
            {"text": "step3"},
        ]
        result = _convert_steps(steps)
        assert len(result) == 3
        assert result[0]["action"] == "step1"
        assert result[1]["expected"] == "expected2"
        assert result[2]["expected"] == ""

    def test_arrow_splits_on_first_only(self) -> None:
        # Multiple arrows: splits on first only
        steps = [{"text": "action → expected → extra"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "action"
        assert result[0]["expected"] == "expected → extra"

    def test_whitespace_stripped_around_arrow(self) -> None:
        steps = [{"text": "  do action  →  see result  "}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "do action"
        assert result[0]["expected"] == "see result"
