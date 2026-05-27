"""Unit tests for ai.output_shield and ai.quality_judge pure helper functions.

All tests are self-contained: no DB, no HTTP, no feature flags.
Covers:
  - output_shield._luhn: Luhn algorithm for credit card validation
  - output_shield._redact: excerpt replacement with [REDACTED:category] markers
  - quality_judge._clip: float clamping to [0.0, 10.0]
  - quality_judge._parse_judge_json: JSON extraction from LLM judge output
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.output_shield import _luhn, _redact
    from app.domains.ai.output_shield import ShieldHit
    _OS_OK = True
except ImportError:
    _OS_OK = False

try:
    from app.domains.ai.quality_judge import _clip, _parse_judge_json
    _QJ_OK = True
except ImportError:
    _QJ_OK = False


# ---------------------------------------------------------------------------
# _luhn
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _OS_OK, reason="output_shield import failed")
class TestLuhn:
    def test_valid_visa_test_card(self):
        # 4111111111111111 is a well-known test Visa card
        assert _luhn("4111111111111111") is True

    def test_valid_mastercard_test(self):
        # 5500005555555559 is a standard test MC card
        assert _luhn("5500005555555559") is True

    def test_invalid_card(self):
        assert _luhn("1234567890123456") is False

    def test_too_short_returns_false(self):
        assert _luhn("1234") is False

    def test_too_long_returns_false(self):
        assert _luhn("1" * 20) is False

    def test_single_digit_off_fails(self):
        # Valid card with one digit changed
        assert _luhn("4111111111111112") is False

    def test_returns_bool(self):
        assert isinstance(_luhn("4111111111111111"), bool)

    def test_all_zeros_length_13_to_19(self):
        # All zeros satisfy Luhn (checksum = 0)
        assert _luhn("0" * 13) is True

    def test_with_spaces_strips_non_digits(self):
        # "4111 1111 1111 1111" → treats only digit chars
        assert _luhn("4111 1111 1111 1111") is True

    def test_with_dashes(self):
        assert _luhn("4111-1111-1111-1111") is True


# ---------------------------------------------------------------------------
# _redact
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _OS_OK, reason="output_shield import failed")
class TestRedact:
    def _make_hit(self, category: str, excerpt: str) -> ShieldHit:
        return ShieldHit(category=category, pattern_name="test", score=0.9, excerpt=excerpt)

    def test_single_hit_redacted(self):
        text = "My card is 4111111111111111"
        hit = self._make_hit("pii_leak", "4111111111111111")
        result = _redact(text, [hit])
        assert "4111111111111111" not in result
        assert "[REDACTED:pii_leak]" in result

    def test_multiple_hits_redacted(self):
        text = "Name: John, SSN: 123-45-6789"
        hits = [
            self._make_hit("pii_name", "John"),
            self._make_hit("pii_ssn", "123-45-6789"),
        ]
        result = _redact(text, hits)
        assert "John" not in result
        assert "123-45-6789" not in result

    def test_no_hits_text_unchanged(self):
        text = "Clean text with no PII"
        result = _redact(text, [])
        assert result == text

    def test_short_excerpt_not_replaced(self):
        # excerpt len <= 2 → not replaced
        text = "ab test"
        hit = self._make_hit("pii", "ab")
        result = _redact(text, [hit])
        assert result == text

    def test_returns_string(self):
        assert isinstance(_redact("text", []), str)

    def test_category_in_redacted_marker(self):
        text = "token: abc123xyz"
        hit = self._make_hit("secret_leak", "abc123xyz")
        result = _redact(text, [hit])
        assert "secret_leak" in result


# ---------------------------------------------------------------------------
# _clip (quality_judge)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QJ_OK, reason="quality_judge import failed")
class TestClip:
    def test_value_in_range(self):
        assert _clip(5.0) == pytest.approx(5.0)

    def test_zero_ok(self):
        assert _clip(0.0) == pytest.approx(0.0)

    def test_ten_ok(self):
        assert _clip(10.0) == pytest.approx(10.0)

    def test_below_zero_clamped(self):
        assert _clip(-1.0) == pytest.approx(0.0)

    def test_above_ten_clamped(self):
        assert _clip(11.0) == pytest.approx(10.0)

    def test_string_number_coerced(self):
        assert _clip("7.5") == pytest.approx(7.5)

    def test_invalid_string_returns_zero(self):
        assert _clip("bad") == pytest.approx(0.0)

    def test_none_returns_zero(self):
        assert _clip(None) == pytest.approx(0.0)

    def test_returns_float(self):
        assert isinstance(_clip(5), float)

    def test_rounding_to_2_decimal(self):
        result = _clip(7.555555)
        assert result == pytest.approx(round(7.555555, 2))


# ---------------------------------------------------------------------------
# _parse_judge_json (quality_judge)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QJ_OK, reason="quality_judge import failed")
class TestParseJudgeJson:
    def test_plain_json_parsed(self):
        result = _parse_judge_json('{"score": 8, "reason": "good"}')
        assert result == {"score": 8, "reason": "good"}

    def test_json_fence_parsed(self):
        raw = '```json\n{"score": 7}\n```'
        result = _parse_judge_json(raw)
        assert result == {"score": 7}

    def test_embedded_in_prose(self):
        raw = 'Assessment: {"score": 9, "pass": true} done.'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result.get("score") == 9

    def test_not_json_returns_none(self):
        assert _parse_judge_json("no json here") is None

    def test_empty_string_returns_none(self):
        assert _parse_judge_json("") is None

    def test_returns_dict_or_none(self):
        result = _parse_judge_json('{"x": 1}')
        assert isinstance(result, dict)

    def test_nested_json(self):
        result = _parse_judge_json('{"metrics": {"accuracy": 0.9}}')
        assert result == {"metrics": {"accuracy": 0.9}}

    def test_partial_extraction(self):
        raw = 'prefix {"a": 1} suffix'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result.get("a") == 1
