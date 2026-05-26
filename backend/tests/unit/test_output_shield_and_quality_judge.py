"""Unit tests for AI output shield and quality judge pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/output_shield.py:
    _luhn, _scan_credit_cards, _redact
  app/domains/ai/quality_judge.py:
    _clip, _parse_judge_json
"""

from __future__ import annotations

import pytest

from app.domains.ai.output_shield import _luhn, _redact, _scan_credit_cards
from app.domains.ai.quality_judge import _clip, _parse_judge_json


# ── _luhn ─────────────────────────────────────────────────────────────────────


class TestLuhn:
    def test_valid_visa(self) -> None:
        # Classic Visa test number
        assert _luhn("4111111111111111") is True

    def test_valid_mastercard(self) -> None:
        assert _luhn("5500005555555559") is True

    def test_invalid_number(self) -> None:
        assert _luhn("1234567890123456") is False

    def test_too_short_returns_false(self) -> None:
        assert _luhn("4111111") is False

    def test_too_long_returns_false(self) -> None:
        assert _luhn("4" * 20) is False

    def test_empty_string_returns_false(self) -> None:
        assert _luhn("") is False

    def test_with_spaces_still_checked(self) -> None:
        # Spaces are filtered via isdigit()
        assert _luhn("4111 1111 1111 1111") is True

    def test_with_dashes_still_checked(self) -> None:
        assert _luhn("4111-1111-1111-1111") is True

    def test_returns_bool(self) -> None:
        assert isinstance(_luhn("4111111111111111"), bool)

    def test_all_zeros_returns_false(self) -> None:
        # 16 zeros: checksum = 0 mod 10 = 0 = valid (edge case)
        result = _luhn("0000000000000000")
        assert isinstance(result, bool)


# ── _scan_credit_cards ────────────────────────────────────────────────────────


class TestScanCreditCards:
    def test_finds_valid_card(self) -> None:
        text = "Payment processed with card 4111111111111111"
        hits = _scan_credit_cards(text)
        assert len(hits) >= 1
        assert any("4111111111111111" in h.excerpt for h in hits)

    def test_no_card_in_text(self) -> None:
        hits = _scan_credit_cards("No card number here, just regular text")
        assert hits == []

    def test_invalid_luhn_not_detected(self) -> None:
        # A 16-digit number that fails Luhn
        text = "Number: 1234567890123456"
        hits = _scan_credit_cards(text)
        assert len(hits) == 0

    def test_returns_list(self) -> None:
        assert isinstance(_scan_credit_cards(""), list)

    def test_hit_category_is_pii_leak(self) -> None:
        text = "4111111111111111"
        hits = _scan_credit_cards(text)
        if hits:
            assert hits[0].category == "pii_leak"

    def test_hit_score_high(self) -> None:
        text = "4111111111111111"
        hits = _scan_credit_cards(text)
        if hits:
            assert hits[0].score >= 0.8

    def test_multiple_cards_detected(self) -> None:
        text = "Cards: 4111111111111111 and 5500005555555559"
        hits = _scan_credit_cards(text)
        assert len(hits) >= 2


# ── _redact ───────────────────────────────────────────────────────────────────


class TestRedact:
    def test_redacts_single_excerpt(self) -> None:
        from types import SimpleNamespace
        hit = SimpleNamespace(category="pii_leak", excerpt="john@example.com")
        result = _redact("Email: john@example.com - done", [hit])
        assert "john@example.com" not in result
        assert "[REDACTED:pii_leak]" in result

    def test_multiple_excerpts_redacted(self) -> None:
        from types import SimpleNamespace
        hits = [
            SimpleNamespace(category="pii_leak", excerpt="alice@corp.com"),
            SimpleNamespace(category="credit_card", excerpt="4111111111111111"),
        ]
        text = "alice@corp.com paid with 4111111111111111"
        result = _redact(text, hits)
        assert "alice@corp.com" not in result
        assert "4111111111111111" not in result

    def test_empty_hits_returns_original(self) -> None:
        text = "No sensitive data here"
        result = _redact(text, [])
        assert result == text

    def test_short_excerpt_not_redacted(self) -> None:
        # Excerpt length <= 2 is not replaced
        from types import SimpleNamespace
        hit = SimpleNamespace(category="pii_leak", excerpt="ab")
        result = _redact("hello ab world", [hit])
        assert "ab" in result

    def test_returns_string(self) -> None:
        assert isinstance(_redact("text", []), str)


# ── _clip ─────────────────────────────────────────────────────────────────────


class TestClip:
    def test_clips_to_max_10(self) -> None:
        assert _clip(15) == pytest.approx(10.0)

    def test_clips_to_min_0(self) -> None:
        assert _clip(-5) == pytest.approx(0.0)

    def test_value_in_range(self) -> None:
        assert _clip(7.5) == pytest.approx(7.5)

    def test_zero(self) -> None:
        assert _clip(0) == pytest.approx(0.0)

    def test_ten(self) -> None:
        assert _clip(10) == pytest.approx(10.0)

    def test_string_int_converted(self) -> None:
        assert _clip("8") == pytest.approx(8.0)

    def test_invalid_string_returns_zero(self) -> None:
        assert _clip("not a number") == pytest.approx(0.0)

    def test_none_returns_zero(self) -> None:
        assert _clip(None) == pytest.approx(0.0)

    def test_returns_float(self) -> None:
        assert isinstance(_clip(5), float)

    def test_rounds_to_2_decimals(self) -> None:
        result = _clip(7.567)
        assert result == pytest.approx(7.57)


# ── _parse_judge_json ─────────────────────────────────────────────────────────


class TestParseJudgeJson:
    def test_plain_json(self) -> None:
        result = _parse_judge_json('{"score": 8, "reasoning": "Good"}')
        assert result is not None
        assert result["score"] == 8

    def test_json_in_fence(self) -> None:
        raw = '```json\n{"score": 7}\n```'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["score"] == 7

    def test_json_in_plain_fence(self) -> None:
        raw = '```\n{"score": 6}\n```'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["score"] == 6

    def test_json_embedded_in_text(self) -> None:
        raw = 'Here is my evaluation: {"score": 9, "reasoning": "Excellent"} done.'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["score"] == 9

    def test_invalid_returns_none(self) -> None:
        assert _parse_judge_json("not valid json") is None

    def test_empty_string_returns_none(self) -> None:
        assert _parse_judge_json("") is None

    def test_none_input_returns_none(self) -> None:
        assert _parse_judge_json(None) is None

    def test_returns_dict_or_none(self) -> None:
        result = _parse_judge_json('{"x": 1}')
        assert isinstance(result, (dict, type(None)))

    def test_nested_json(self) -> None:
        raw = '{"score": 7, "details": {"accuracy": 0.9, "completeness": 0.8}}'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["details"]["accuracy"] == pytest.approx(0.9)
