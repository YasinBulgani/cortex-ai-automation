"""Unit tests for AI synthetic data advanced generator pure helpers.

Tests app/domains/ai_synthetic_data/advanced_generators.py — no external deps.
Covers: _is_numeric, _column_type, _mean, _stdev, _pearson_corr,
        generate_tckn, validate_tckn, generate_iban,
        DataQualityChecker.check_fk_integrity.
"""

from __future__ import annotations

import math
import pytest

from app.domains.ai_synthetic_data.advanced_generators import (
    DataQualityChecker,
    _column_type,
    _is_numeric,
    _mean,
    _pearson_corr,
    _stdev,
    generate_iban,
    generate_tckn,
    validate_tckn,
)


# ── _is_numeric ───────────────────────────────────────────────────────────────


class TestIsNumeric:
    def test_int_is_numeric(self) -> None:
        assert _is_numeric(42) is True

    def test_float_is_numeric(self) -> None:
        assert _is_numeric(3.14) is True

    def test_zero_is_numeric(self) -> None:
        assert _is_numeric(0) is True

    def test_negative_is_numeric(self) -> None:
        assert _is_numeric(-5) is True

    def test_bool_is_not_numeric(self) -> None:
        assert _is_numeric(True) is False
        assert _is_numeric(False) is False

    def test_string_is_not_numeric(self) -> None:
        assert _is_numeric("42") is False

    def test_none_is_not_numeric(self) -> None:
        assert _is_numeric(None) is False

    def test_list_is_not_numeric(self) -> None:
        assert _is_numeric([1, 2]) is False


# ── _column_type ──────────────────────────────────────────────────────────────


class TestColumnType:
    def test_empty_returns_categorical(self) -> None:
        assert _column_type([]) == "categorical"

    def test_all_none_returns_categorical(self) -> None:
        assert _column_type([None, None]) == "categorical"

    def test_all_numeric_returns_numeric(self) -> None:
        assert _column_type([1, 2, 3, 4, 5]) == "numeric"

    def test_all_strings_returns_categorical(self) -> None:
        assert _column_type(["a", "b", "c"]) == "categorical"

    def test_over_70pct_numeric_returns_numeric(self) -> None:
        # 8 numeric out of 10 = 80% > 70%
        result = _column_type([1, 2, 3, 4, 5, 6, 7, 8, "a", "b"])
        assert result == "numeric"

    def test_under_70pct_numeric_returns_categorical(self) -> None:
        # 5 numeric out of 10 = 50% < 70%
        result = _column_type([1, 2, 3, 4, 5, "a", "b", "c", "d", "e"])
        assert result == "categorical"

    def test_with_none_values(self) -> None:
        # None values excluded: 3 numeric out of 3 = 100%
        result = _column_type([1, 2, None, 3])
        assert result == "numeric"


# ── _mean ─────────────────────────────────────────────────────────────────────


class TestMean:
    def test_empty_returns_zero(self) -> None:
        assert _mean([]) == 0.0

    def test_single_value(self) -> None:
        assert _mean([5.0]) == 5.0

    def test_multiple_values(self) -> None:
        assert _mean([1.0, 2.0, 3.0, 4.0, 5.0]) == pytest.approx(3.0)

    def test_negative_values(self) -> None:
        assert _mean([-2.0, 0.0, 2.0]) == pytest.approx(0.0)

    def test_zero_list(self) -> None:
        assert _mean([0.0, 0.0, 0.0]) == 0.0


# ── _stdev ────────────────────────────────────────────────────────────────────


class TestStdev:
    def test_empty_returns_zero(self) -> None:
        assert _stdev([]) == 0.0

    def test_single_value_returns_zero(self) -> None:
        assert _stdev([5.0]) == 0.0

    def test_two_values(self) -> None:
        result = _stdev([1.0, 3.0])
        assert result > 0.0

    def test_identical_values_return_zero(self) -> None:
        assert _stdev([5.0, 5.0, 5.0]) == pytest.approx(0.0)

    def test_sample_stdev_positive(self) -> None:
        # For list with spread, stddev is positive
        result = _stdev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        assert result > 1.5  # definitely > 0 with spread


# ── _pearson_corr ─────────────────────────────────────────────────────────────


class TestPearsonCorr:
    def test_empty_returns_zero(self) -> None:
        assert _pearson_corr([], []) == 0.0

    def test_too_few_returns_zero(self) -> None:
        assert _pearson_corr([1.0, 2.0], [1.0, 2.0]) == 0.0

    def test_perfect_positive_correlation(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        result = _pearson_corr(xs, ys)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_perfect_negative_correlation(self) -> None:
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        result = _pearson_corr(xs, ys)
        assert result == pytest.approx(-1.0, abs=1e-6)

    def test_zero_correlation(self) -> None:
        # Constant y → std=0 → returns 0.0
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [3.0, 3.0, 3.0, 3.0, 3.0]
        result = _pearson_corr(xs, ys)
        assert result == 0.0

    def test_result_in_minus_one_to_one(self) -> None:
        xs = [1.0, 5.0, 3.0, 2.0, 4.0]
        ys = [4.0, 1.0, 3.0, 5.0, 2.0]
        result = _pearson_corr(xs, ys)
        assert -1.0 <= result <= 1.0


# ── generate_tckn + validate_tckn ────────────────────────────────────────────


class TestGenerateAndValidateTckn:
    def test_generated_tckn_is_valid(self) -> None:
        for _ in range(20):
            tckn = generate_tckn()
            assert validate_tckn(tckn), f"Generated TCKN {tckn} failed validation"

    def test_generated_tckn_is_11_digits(self) -> None:
        tckn = generate_tckn()
        assert len(tckn) == 11
        assert tckn.isdigit()

    def test_generated_tckn_not_starting_with_zero(self) -> None:
        for _ in range(10):
            tckn = generate_tckn()
            assert tckn[0] != "0"

    def test_invalid_tckn_rejected(self) -> None:
        assert validate_tckn("12345678900") is False

    def test_wrong_length_rejected(self) -> None:
        assert validate_tckn("1234567890") is False
        assert validate_tckn("123456789012") is False

    def test_non_digit_rejected(self) -> None:
        assert validate_tckn("1234567890X") is False

    def test_leading_zero_rejected(self) -> None:
        assert validate_tckn("01234567890") is False


# ── generate_iban ─────────────────────────────────────────────────────────────


class TestGenerateIban:
    def test_starts_with_tr(self) -> None:
        iban = generate_iban()
        assert iban.startswith("TR")

    def test_correct_length(self) -> None:
        iban = generate_iban()
        # TR(2) + check(2) + bank(5) + account(16) = 25 chars total
        assert len(iban) == 25

    def test_all_digits_after_tr(self) -> None:
        iban = generate_iban()
        assert iban[2:].isdigit()

    def test_custom_bank_code(self) -> None:
        iban = generate_iban(bank_code="00010")
        assert "00010" in iban

    def test_bank_code_zero_padded(self) -> None:
        iban = generate_iban(bank_code="10")
        assert "00010" in iban  # padded to 5 digits

    def test_multiple_calls_produce_different_ibans(self) -> None:
        ibans = {generate_iban() for _ in range(10)}
        assert len(ibans) > 1  # should be unique most of the time


# ── DataQualityChecker.check_fk_integrity ────────────────────────────────────


class TestDataQualityCheckerFkIntegrity:
    def test_empty_dataset_returns_valid(self) -> None:
        result = DataQualityChecker.check_fk_integrity({})
        assert result["valid"] is True
        assert result["orphan_accounts"] == []
        assert result["orphan_transactions"] == []

    def test_valid_fk_references(self) -> None:
        dataset = {
            "customers": [{"musteri_id": 1}, {"musteri_id": 2}],
            "accounts": [
                {"hesap_id": 101, "musteri_id": 1},
                {"hesap_id": 102, "musteri_id": 2},
            ],
            "transactions": [
                {"islem_id": 1001, "hesap_id": 101},
                {"islem_id": 1002, "hesap_id": 102},
            ],
        }
        result = DataQualityChecker.check_fk_integrity(dataset)
        assert result["valid"] is True
        assert result["orphan_accounts"] == []
        assert result["orphan_transactions"] == []

    def test_orphan_account_detected(self) -> None:
        dataset = {
            "customers": [{"musteri_id": 1}],
            "accounts": [{"hesap_id": 101, "musteri_id": 999}],  # 999 not in customers
            "transactions": [],
        }
        result = DataQualityChecker.check_fk_integrity(dataset)
        assert result["valid"] is False
        assert 101 in result["orphan_accounts"]

    def test_orphan_transaction_detected(self) -> None:
        dataset = {
            "customers": [{"musteri_id": 1}],
            "accounts": [{"hesap_id": 101, "musteri_id": 1}],
            "transactions": [{"islem_id": 1001, "hesap_id": 999}],  # 999 not in accounts
        }
        result = DataQualityChecker.check_fk_integrity(dataset)
        assert result["valid"] is False
        assert 1001 in result["orphan_transactions"]

    def test_counts_correct(self) -> None:
        dataset = {
            "customers": [{"musteri_id": 1}, {"musteri_id": 2}],
            "accounts": [{"hesap_id": 101, "musteri_id": 1}],
            "transactions": [{"islem_id": 1001, "hesap_id": 101}],
        }
        result = DataQualityChecker.check_fk_integrity(dataset)
        assert result["total_customers"] == 2
        assert result["total_accounts"] == 1
        assert result["total_transactions"] == 1
