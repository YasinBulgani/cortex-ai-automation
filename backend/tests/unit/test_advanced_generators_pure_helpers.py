"""Unit tests for ai_synthetic_data.advanced_generators pure helper functions.

All tests are self-contained: no DB, no HTTP, no external dependencies.
Covers:
  - _is_numeric: numeric value detection
  - _column_type: numeric/categorical inference from sample values
  - _mean: arithmetic mean
  - _stdev: sample standard deviation
  - _pearson_corr: Pearson correlation coefficient
  - _row_fingerprint: MD5 row hash
  - _hash_similarity: row similarity score
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai_synthetic_data.advanced_generators import (
        _is_numeric,
        _column_type,
        _mean,
        _stdev,
        _pearson_corr,
        _row_fingerprint,
        _hash_similarity,
    )
    _AG_OK = True
except ImportError:
    _AG_OK = False


# ---------------------------------------------------------------------------
# _is_numeric
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestIsNumeric:
    def test_int_is_numeric(self):
        assert _is_numeric(42) is True

    def test_float_is_numeric(self):
        assert _is_numeric(3.14) is True

    def test_negative_is_numeric(self):
        assert _is_numeric(-7.5) is True

    def test_zero_is_numeric(self):
        assert _is_numeric(0) is True

    def test_bool_is_not_numeric(self):
        # bool is subclass of int but should not be treated as numeric
        assert _is_numeric(True) is False
        assert _is_numeric(False) is False

    def test_string_is_not_numeric(self):
        assert _is_numeric("42") is False

    def test_none_is_not_numeric(self):
        assert _is_numeric(None) is False

    def test_list_is_not_numeric(self):
        assert _is_numeric([1, 2, 3]) is False

    def test_returns_bool(self):
        assert isinstance(_is_numeric(1), bool)


# ---------------------------------------------------------------------------
# _column_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestColumnType:
    def test_all_numeric_returns_numeric(self):
        assert _column_type([1, 2, 3, 4, 5]) == "numeric"

    def test_all_strings_returns_categorical(self):
        assert _column_type(["a", "b", "c"]) == "categorical"

    def test_empty_list_returns_categorical(self):
        assert _column_type([]) == "categorical"

    def test_all_none_returns_categorical(self):
        assert _column_type([None, None]) == "categorical"

    def test_mixed_mostly_numeric_returns_numeric(self):
        # 8 numeric, 1 string → 89% numeric > 70%
        values = [1, 2, 3, 4, 5, 6, 7, 8, "x"]
        assert _column_type(values) == "numeric"

    def test_mixed_mostly_categorical_returns_categorical(self):
        # 1 numeric, 9 strings → 10% numeric < 70%
        values = [1, "a", "b", "c", "d", "e", "f", "g", "h", "i"]
        assert _column_type(values) == "categorical"

    def test_booleans_not_counted_as_numeric(self):
        # Booleans are excluded from numeric count
        values = [True, False, True, False, True]
        assert _column_type(values) == "categorical"

    def test_returns_string(self):
        assert isinstance(_column_type([1, 2, 3]), str)

    def test_floats_are_numeric(self):
        assert _column_type([1.1, 2.2, 3.3]) == "numeric"


# ---------------------------------------------------------------------------
# _mean
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestMean:
    def test_basic_mean(self):
        assert _mean([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_single_value(self):
        assert _mean([5.0]) == pytest.approx(5.0)

    def test_empty_list_returns_zero(self):
        assert _mean([]) == pytest.approx(0.0)

    def test_negative_values(self):
        assert _mean([-2.0, -4.0]) == pytest.approx(-3.0)

    def test_returns_float(self):
        assert isinstance(_mean([1.0, 2.0]), float)

    def test_all_zeros(self):
        assert _mean([0.0, 0.0, 0.0]) == pytest.approx(0.0)

    def test_large_values(self):
        assert _mean([1000.0, 2000.0, 3000.0]) == pytest.approx(2000.0)


# ---------------------------------------------------------------------------
# _stdev
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestStdev:
    def test_basic_stdev(self):
        # Sample std of [1,2,3] = sqrt(1) = 1
        assert _stdev([1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_empty_list_returns_zero(self):
        assert _stdev([]) == pytest.approx(0.0)

    def test_single_value_returns_zero(self):
        assert _stdev([5.0]) == pytest.approx(0.0)

    def test_identical_values_returns_zero(self):
        assert _stdev([3.0, 3.0, 3.0]) == pytest.approx(0.0)

    def test_returns_float(self):
        assert isinstance(_stdev([1.0, 2.0, 3.0]), float)

    def test_larger_spread_larger_stdev(self):
        narrow = _stdev([1.0, 2.0, 3.0])
        wide = _stdev([1.0, 10.0, 20.0])
        assert wide > narrow


# ---------------------------------------------------------------------------
# _pearson_corr
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestPearsonCorr:
    def test_perfect_positive_correlation(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _pearson_corr(xs, ys) == pytest.approx(1.0)

    def test_perfect_negative_correlation(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert _pearson_corr(xs, ys) == pytest.approx(-1.0)

    def test_no_correlation_with_zero_variance(self):
        xs = [1.0, 1.0, 1.0, 1.0, 1.0]
        ys = [1.0, 2.0, 3.0, 4.0, 5.0]
        # sx == 0 → returns 0.0
        assert _pearson_corr(xs, ys) == pytest.approx(0.0)

    def test_fewer_than_3_returns_zero(self):
        assert _pearson_corr([1.0, 2.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_empty_returns_zero(self):
        assert _pearson_corr([], []) == pytest.approx(0.0)

    def test_result_in_range_minus_one_to_one(self):
        xs = [1.0, 3.0, 5.0, 7.0, 2.0]
        ys = [2.0, 4.0, 6.0, 1.0, 3.0]
        result = _pearson_corr(xs, ys)
        assert -1.0 <= result <= 1.0

    def test_returns_float(self):
        xs = [1.0, 2.0, 3.0, 4.0, 5.0]
        ys = [2.0, 4.0, 6.0, 8.0, 10.0]
        assert isinstance(_pearson_corr(xs, ys), float)


# ---------------------------------------------------------------------------
# _row_fingerprint
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestRowFingerprint:
    def test_deterministic(self):
        row = {"a": 1, "b": "hello"}
        cols = ["a", "b"]
        assert _row_fingerprint(row, cols) == _row_fingerprint(row, cols)

    def test_different_rows_different_fingerprint(self):
        r1 = {"a": 1, "b": "hello"}
        r2 = {"a": 2, "b": "world"}
        cols = ["a", "b"]
        assert _row_fingerprint(r1, cols) != _row_fingerprint(r2, cols)

    def test_returns_hex_string(self):
        result = _row_fingerprint({"a": 1}, ["a"])
        assert all(c in "0123456789abcdef" for c in result)

    def test_column_order_sorted_internally(self):
        # Same row, different col orders → same fingerprint (sorted internally)
        row = {"a": 1, "b": 2}
        fp1 = _row_fingerprint(row, ["a", "b"])
        fp2 = _row_fingerprint(row, ["b", "a"])
        assert fp1 == fp2

    def test_missing_column_handled(self):
        # Missing column → str(None) = "None"
        result = _row_fingerprint({"a": 1}, ["a", "missing"])
        assert isinstance(result, str)

    def test_returns_md5_length_string(self):
        result = _row_fingerprint({"x": "y"}, ["x"])
        assert len(result) == 32


# ---------------------------------------------------------------------------
# _hash_similarity
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AG_OK, reason="advanced_generators import failed")
class TestHashSimilarity:
    def test_identical_fingerprints_returns_one(self):
        row = {"a": 1, "b": "hello"}
        fp = _row_fingerprint(row, ["a", "b"])
        assert _hash_similarity(fp, fp, ["a", "b"], row, row) == pytest.approx(1.0)

    def test_identical_rows_returns_one(self):
        row = {"a": 1, "b": "same"}
        cols = ["a", "b"]
        fp = _row_fingerprint(row, cols)
        assert _hash_similarity(fp, fp, cols, row, row) == pytest.approx(1.0)

    def test_completely_different_rows_returns_zero(self):
        r1 = {"a": 1, "b": "hello"}
        r2 = {"a": 9, "b": "world"}
        cols = ["a", "b"]
        fp1 = _row_fingerprint(r1, cols)
        fp2 = _row_fingerprint(r2, cols)
        result = _hash_similarity(fp1, fp2, cols, r1, r2)
        assert 0.0 <= result <= 1.0

    def test_numeric_close_values_partial_match(self):
        r1 = {"price": 100.0}
        r2 = {"price": 101.0}  # 1% diff < 5% → 0.8 match
        cols = ["price"]
        fp1 = _row_fingerprint(r1, cols)
        fp2 = _row_fingerprint(r2, cols)
        result = _hash_similarity(fp1, fp2, cols, r1, r2)
        assert result > 0.5

    def test_empty_cols_returns_zero(self):
        result = _hash_similarity("fp1", "fp2", [], {}, {})
        assert result == pytest.approx(0.0)

    def test_result_in_range_0_to_1(self):
        r1 = {"x": 1, "y": "a"}
        r2 = {"x": 2, "y": "b"}
        cols = ["x", "y"]
        fp1 = _row_fingerprint(r1, cols)
        fp2 = _row_fingerprint(r2, cols)
        result = _hash_similarity(fp1, fp2, cols, r1, r2)
        assert 0.0 <= result <= 1.0
