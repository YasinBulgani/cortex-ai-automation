"""Unit tests for app.domains.ai.output_shield — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no feature flags.
Covers: _luhn (valid/invalid card numbers), _scan_credit_cards (hit detection),
        _redact (placeholder replacement), ShieldHit / ShieldResult dataclasses.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.output_shield import (
        _luhn,
        _scan_credit_cards,
        _redact,
        ShieldHit,
        ShieldResult,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="output_shield import failed")


# ---------------------------------------------------------------------------
# _luhn
# ---------------------------------------------------------------------------

class TestLuhn:
    def test_valid_visa_test_number(self):
        # Luhn-valid test Visa: 4111111111111111
        assert _luhn("4111111111111111") is True

    def test_valid_mastercard_test_number(self):
        # 5500005555555559 is Luhn valid
        assert _luhn("5500005555555559") is True

    def test_invalid_number(self):
        assert _luhn("1234567890123456") is False

    def test_too_short_returns_false(self):
        # < 13 digits
        assert _luhn("41111111111") is False

    def test_too_long_returns_false(self):
        # > 19 digits
        assert _luhn("12345678901234567890") is False

    def test_with_spaces_stripped(self):
        # Spaces are ignored (not digits)
        assert _luhn("4111 1111 1111 1111") is True

    def test_with_dashes_stripped(self):
        assert _luhn("4111-1111-1111-1111") is True

    def test_returns_bool(self):
        assert isinstance(_luhn("4111111111111111"), bool)

    def test_amex_valid(self):
        # 378282246310005 is Luhn valid (Amex test number)
        assert _luhn("378282246310005") is True


# ---------------------------------------------------------------------------
# _scan_credit_cards
# ---------------------------------------------------------------------------

class TestScanCreditCards:
    def test_no_card_number_returns_empty(self):
        hits = _scan_credit_cards("No sensitive data here.")
        assert hits == []

    def test_detects_valid_luhn_card(self):
        hits = _scan_credit_cards("Card: 4111111111111111")
        assert len(hits) >= 1

    def test_hit_category_is_pii_leak(self):
        hits = _scan_credit_cards("4111111111111111")
        assert hits[0].category == "pii_leak"

    def test_hit_pattern_name_credit_card(self):
        hits = _scan_credit_cards("4111111111111111")
        assert "credit_card" in hits[0].pattern_name

    def test_hit_score_high(self):
        hits = _scan_credit_cards("4111111111111111")
        assert hits[0].score >= 0.9

    def test_invalid_luhn_not_detected(self):
        # 1234567890123456 is not Luhn valid
        hits = _scan_credit_cards("1234567890123456")
        assert len(hits) == 0

    def test_returns_list(self):
        assert isinstance(_scan_credit_cards("no card"), list)

    def test_card_with_dashes_detected(self):
        hits = _scan_credit_cards("4111-1111-1111-1111")
        assert len(hits) >= 1

    def test_multiple_cards_detected(self):
        text = "First: 4111111111111111 Second: 378282246310005"
        hits = _scan_credit_cards(text)
        assert len(hits) == 2


# ---------------------------------------------------------------------------
# _redact
# ---------------------------------------------------------------------------

class TestRedact:
    def _hit(self, excerpt: str, category: str = "pii_leak") -> ShieldHit:
        return ShieldHit(
            category=category,
            pattern_name="test_pattern",
            score=0.9,
            excerpt=excerpt,
        )

    def test_replaces_excerpt_with_redacted(self):
        hits = [self._hit("4111111111111111")]
        result = _redact("Card: 4111111111111111 is invalid", hits)
        assert "4111111111111111" not in result
        assert "[REDACTED:pii_leak]" in result

    def test_no_hits_text_unchanged(self):
        result = _redact("clean text", [])
        assert result == "clean text"

    def test_short_excerpt_not_replaced(self):
        # len("ab") == 2, not > 2 → skip
        hits = [self._hit("ab")]
        result = _redact("text ab here", hits)
        assert "ab" in result

    def test_returns_string(self):
        assert isinstance(_redact("text", []), str)

    def test_category_in_redacted_label(self):
        hits = [self._hit("secret", "pii_leak")]
        result = _redact("this is secret", hits)
        assert "[REDACTED:pii_leak]" in result

    def test_multiple_hits_all_redacted(self):
        hits = [self._hit("secret"), self._hit("password")]
        result = _redact("secret and password here", hits)
        assert "secret" not in result
        assert "password" not in result

    def test_empty_excerpt_skipped(self):
        hits = [self._hit("")]
        result = _redact("text here", hits)
        assert result == "text here"


# ---------------------------------------------------------------------------
# ShieldHit dataclass
# ---------------------------------------------------------------------------

class TestShieldHit:
    def test_can_instantiate(self):
        hit = ShieldHit(category="pii_leak", pattern_name="cc", score=0.9, excerpt="1234")
        assert hit.category == "pii_leak"
        assert hit.score == 0.9

    def test_fields_accessible(self):
        hit = ShieldHit(category="sqli", pattern_name="drop_table", score=0.8, excerpt="DROP TABLE")
        assert hit.pattern_name == "drop_table"
        assert hit.excerpt == "DROP TABLE"


# ---------------------------------------------------------------------------
# ShieldResult dataclass
# ---------------------------------------------------------------------------

class TestShieldResult:
    def test_can_instantiate_allow(self):
        result = ShieldResult(decision="allow", score=0.1)
        assert result.decision == "allow"
        assert result.score == 0.1

    def test_default_hits_empty_list(self):
        result = ShieldResult(decision="allow", score=0.0)
        assert result.hits == []

    def test_default_sanitized_is_none(self):
        result = ShieldResult(decision="allow", score=0.0)
        assert result.sanitized is None

    def test_to_dict_returns_dict(self):
        result = ShieldResult(decision="allow", score=0.1)
        d = result.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_has_decision_key(self):
        result = ShieldResult(decision="block", score=0.9)
        assert result.to_dict()["decision"] == "block"

    def test_to_dict_score_rounded(self):
        result = ShieldResult(decision="allow", score=0.12345678)
        assert result.to_dict()["score"] == round(0.12345678, 3)

    def test_to_dict_hits_list(self):
        hit = ShieldHit(category="pii", pattern_name="cc", score=0.9, excerpt="1234")
        result = ShieldResult(decision="block", score=0.9, hits=[hit])
        d = result.to_dict()
        assert len(d["hits"]) == 1
        assert d["hits"][0]["category"] == "pii"

    def test_to_dict_excerpt_truncated_to_120(self):
        long_excerpt = "x" * 200
        hit = ShieldHit(category="pii", pattern_name="cc", score=0.9, excerpt=long_excerpt)
        result = ShieldResult(decision="block", score=0.9, hits=[hit])
        d = result.to_dict()
        assert len(d["hits"][0]["excerpt"]) <= 120
