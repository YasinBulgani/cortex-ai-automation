"""Unit tests for differential privacy pure helper functions.

Tests app/domains/ai_synthetic_data/differential_privacy.py — no DB, no LLM.
Covers: detect_pii_columns, validate_tckn, PrivacyBudgetManager,
        _sign, _generalize_value, _fingerprint_similarity.
"""

from __future__ import annotations

import pytest

from app.domains.ai_synthetic_data.differential_privacy import (
    PrivacyBudgetManager,
    _fingerprint_similarity,
    _generalize_value,
    _sign,
    detect_pii_columns,
    validate_tckn,
)


# ── detect_pii_columns ────────────────────────────────────────────────────────


class TestDetectPiiColumns:
    def test_empty_data_returns_empty(self) -> None:
        assert detect_pii_columns([]) == []

    def test_tckn_column_detected(self) -> None:
        data = [{"tckn": "12345678901", "name": "Ali"}]
        detected = detect_pii_columns(data)
        assert "tckn" in detected

    def test_email_column_detected(self) -> None:
        data = [{"email": "user@example.com", "age": 30}]
        detected = detect_pii_columns(data)
        assert "email" in detected

    def test_telefon_column_detected(self) -> None:
        data = [{"telefon": "0555123456"}]
        detected = detect_pii_columns(data)
        assert "telefon" in detected

    def test_non_pii_column_not_detected(self) -> None:
        data = [{"product_count": 5, "price": 99.99, "category": "electronics"}]
        detected = detect_pii_columns(data)
        assert detected == []

    def test_case_insensitive_detection(self) -> None:
        data = [{"EMAIL": "user@example.com"}]
        detected = detect_pii_columns(data)
        assert "EMAIL" in detected

    def test_iban_column_detected(self) -> None:
        data = [{"iban_number": "TR123456789"}]
        detected = detect_pii_columns(data)
        assert "iban_number" in detected

    def test_ad_soyad_columns_detected(self) -> None:
        data = [{"first_name": "Ali", "last_name": "Yilmaz"}]
        # "name" pattern matches "first_name" and "last_name"
        detected = detect_pii_columns(data)
        assert len(detected) >= 1


# ── validate_tckn ─────────────────────────────────────────────────────────────


class TestValidateTckn:
    def test_valid_tckn(self) -> None:
        # A mathematically valid TCKN
        # 10000000146 is a common test TCKN
        assert validate_tckn("10000000146") is True

    def test_too_short_returns_false(self) -> None:
        assert validate_tckn("1234567890") is False  # 10 digits

    def test_too_long_returns_false(self) -> None:
        assert validate_tckn("123456789012") is False  # 12 digits

    def test_non_digit_returns_false(self) -> None:
        assert validate_tckn("1234567890X") is False

    def test_empty_string_returns_false(self) -> None:
        assert validate_tckn("") is False

    def test_starts_with_zero_returns_false(self) -> None:
        assert validate_tckn("01234567890") is False

    def test_all_zeros_returns_false(self) -> None:
        assert validate_tckn("00000000000") is False

    def test_wrong_checksum_returns_false(self) -> None:
        assert validate_tckn("12345678900") is False  # bad checksum

    def test_none_returns_false(self) -> None:
        assert validate_tckn(None) is False  # type: ignore[arg-type]


# ── PrivacyBudgetManager ──────────────────────────────────────────────────────


class TestPrivacyBudgetManager:
    def test_initial_remaining_equals_total(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=5.0)
        assert mgr.remaining() == 5.0

    def test_not_exhausted_initially(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=5.0)
        assert mgr.is_exhausted() is False

    def test_allocate_within_budget_returns_true(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=10.0)
        assert mgr.allocate(3.0) is True

    def test_allocate_over_budget_returns_false(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=2.0)
        assert mgr.allocate(5.0) is False

    def test_allocate_zero_raises_value_error(self) -> None:
        mgr = PrivacyBudgetManager()
        with pytest.raises(ValueError):
            mgr.allocate(0.0)

    def test_allocate_negative_raises_value_error(self) -> None:
        mgr = PrivacyBudgetManager()
        with pytest.raises(ValueError):
            mgr.allocate(-1.0)

    def test_spend_reduces_remaining(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=10.0)
        mgr.spend(3.0)
        assert mgr.remaining() == pytest.approx(7.0)

    def test_spend_full_exhausts_budget(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=5.0)
        mgr.spend(5.0)
        assert mgr.is_exhausted() is True
        assert mgr.remaining() == 0.0

    def test_spend_over_budget_raises_value_error(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=2.0)
        with pytest.raises(ValueError):
            mgr.spend(3.0)

    def test_spend_zero_raises_value_error(self) -> None:
        mgr = PrivacyBudgetManager()
        with pytest.raises(ValueError):
            mgr.spend(0.0)

    def test_reset_clears_budget(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=5.0)
        mgr.spend(3.0)
        mgr.reset()
        assert mgr.remaining() == 5.0
        assert mgr.is_exhausted() is False

    def test_multiple_spends_accumulate(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=10.0)
        mgr.spend(2.0)
        mgr.spend(3.0)
        assert mgr.remaining() == pytest.approx(5.0)

    def test_allocate_does_not_reduce_remaining(self) -> None:
        mgr = PrivacyBudgetManager(total_budget=10.0)
        mgr.allocate(5.0)
        # allocate() reserves but does not spend
        assert mgr.remaining() == 10.0


# ── _sign ─────────────────────────────────────────────────────────────────────


class TestSign:
    def test_positive_returns_one(self) -> None:
        assert _sign(5.0) == 1.0

    def test_negative_returns_minus_one(self) -> None:
        assert _sign(-3.5) == -1.0

    def test_zero_returns_zero(self) -> None:
        assert _sign(0.0) == 0.0

    def test_very_small_positive(self) -> None:
        assert _sign(1e-15) == 1.0

    def test_very_small_negative(self) -> None:
        assert _sign(-1e-15) == -1.0


# ── _generalize_value ─────────────────────────────────────────────────────────


class TestGeneralizeValue:
    def test_none_returns_none(self) -> None:
        assert _generalize_value(None, "year") is None

    def test_year_extracts_year_from_date(self) -> None:
        result = _generalize_value("1990-05-20", "year")
        assert result == "1990"

    def test_year_no_match_returns_original(self) -> None:
        result = _generalize_value("no-date-here", "year")
        assert result == "no-date-here"

    def test_month_extracts_year_month(self) -> None:
        result = _generalize_value("2024-03-15", "month")
        assert result == "2024-03"

    def test_month_slash_separator(self) -> None:
        result = _generalize_value("2024/06/01", "month")
        assert result == "2024/06"

    def test_category_replaces_with_asterisks(self) -> None:
        result = _generalize_value("John", "category")
        assert result == "J***"

    def test_category_single_char(self) -> None:
        result = _generalize_value("A", "category")
        assert result == "*"

    def test_range_rounds_to_nearest_ten(self) -> None:
        result = _generalize_value("35", "range")
        assert result == "30-40"

    def test_range_zero(self) -> None:
        result = _generalize_value("0", "range")
        assert result == "0-10"

    def test_range_non_numeric_returns_original(self) -> None:
        result = _generalize_value("abc", "range")
        assert result == "abc"

    def test_default_truncates_long_string(self) -> None:
        result = _generalize_value("hello_world", "other")
        assert result == "hel***"

    def test_default_short_string_unchanged(self) -> None:
        result = _generalize_value("ab", "other")
        assert result == "ab"

    def test_integer_input_converted(self) -> None:
        result = _generalize_value(1990, "year")
        assert result == "1990"


# ── _fingerprint_similarity ───────────────────────────────────────────────────


class TestFingerprintSimilarity:
    def test_empty_keys_returns_zero(self) -> None:
        assert _fingerprint_similarity({"a": 1}, {"a": 1}, []) == 0.0

    def test_identical_fingerprints_returns_one(self) -> None:
        fp = {"age": 30, "city": "Istanbul"}
        result = _fingerprint_similarity(fp, fp, ["age", "city"])
        assert result == pytest.approx(1.0)

    def test_completely_different_fingerprints_returns_low(self) -> None:
        fp1 = {"age": 20, "city": "Istanbul"}
        fp2 = {"age": 80, "city": "Ankara"}
        result = _fingerprint_similarity(fp1, fp2, ["age", "city"])
        # city mismatch = 0, age very different → total < 0.5
        assert result < 0.5

    def test_string_equality_counts_as_full_match(self) -> None:
        fp1 = {"city": "Istanbul"}
        fp2 = {"city": "Istanbul"}
        result = _fingerprint_similarity(fp1, fp2, ["city"])
        assert result == 1.0

    def test_string_inequality_counts_as_zero(self) -> None:
        fp1 = {"city": "Istanbul"}
        fp2 = {"city": "Ankara"}
        result = _fingerprint_similarity(fp1, fp2, ["city"])
        assert result == 0.0

    def test_missing_key_skipped(self) -> None:
        fp1 = {"age": 30}
        fp2 = {"other_key": 30}
        # both missing one key from keys list → no matches counted → 0/1
        result = _fingerprint_similarity(fp1, fp2, ["age"])
        # fp2 doesn't have "age" → v2 is None → skipped → 0/1 = 0
        assert result == 0.0

    def test_numeric_close_values_give_high_similarity(self) -> None:
        fp1 = {"score": 100.0}
        fp2 = {"score": 99.0}
        result = _fingerprint_similarity(fp1, fp2, ["score"])
        assert result > 0.9

    def test_numeric_very_different_gives_low_similarity(self) -> None:
        fp1 = {"score": 100.0}
        fp2 = {"score": 1.0}
        result = _fingerprint_similarity(fp1, fp2, ["score"])
        assert result < 0.5

    def test_mixed_numeric_and_string(self) -> None:
        fp1 = {"age": 30, "city": "Istanbul"}
        fp2 = {"age": 30, "city": "Istanbul"}
        result = _fingerprint_similarity(fp1, fp2, ["age", "city"])
        assert result == pytest.approx(1.0)

    def test_result_between_zero_and_one(self) -> None:
        fp1 = {"a": 10, "b": "x"}
        fp2 = {"a": 50, "b": "y"}
        result = _fingerprint_similarity(fp1, fp2, ["a", "b"])
        assert 0.0 <= result <= 1.0
