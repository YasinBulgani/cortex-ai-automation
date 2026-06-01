"""Unit tests for evals.reporting pure helper functions.

Tests are fully self-contained: no DB, no HTTP, no LLM.
Covers:
  - _as_float: numeric coercion with default
  - _as_int: integer coercion with default
  - _parse_dt: ISO string parsing, timezone normalization, invalid input
  - _fmt_ts: datetime → compact timestamp string
  - _fmt_metric: float → 4-decimal string
  - _suite_badge: PASS/FAIL/SKIPPED HTML span
  - _row_class: CSS class for table row
  - _md_escape: Markdown pipe/newline escaping
  - _status_text: suite-level PASS/FAIL/SKIP text
  - _metric_summary: mean_ aggregate keys → formatted string
  - _case_runtime_summary: provider/model/attempts string
  - SuiteResult: case_pass_rate, count_passed computed properties
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

try:
    from app.domains.evals.reporting import (
        _as_float,
        _as_int,
        _parse_dt,
        _fmt_ts,
        _fmt_metric,
        _suite_badge,
        _row_class,
        _md_escape,
        _status_text,
        _metric_summary,
        _case_runtime_summary,
    )
    from app.domains.evals.schemas import SuiteResult, CaseResult, ScorerOutput as ScoreResult
    _EVALS_OK = True
except ImportError:
    _EVALS_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _suite(passed=True, aggregate=None, cases=None):
    return SuiteResult(
        suite_name="Test Suite",
        adapter_name="playwright",
        passed=passed,
        aggregate=aggregate or {},
        cases=cases or [],
    )


# ---------------------------------------------------------------------------
# _as_float
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestAsFloat:
    def test_int_to_float(self):
        assert _as_float(5) == pytest.approx(5.0)

    def test_float_passthrough(self):
        assert _as_float(3.14) == pytest.approx(3.14)

    def test_string_numeric(self):
        assert _as_float("2.5") == pytest.approx(2.5)

    def test_none_returns_default(self):
        assert _as_float(None) == pytest.approx(0.0)

    def test_none_custom_default(self):
        assert _as_float(None, 9.9) == pytest.approx(9.9)

    def test_invalid_string_returns_default(self):
        assert _as_float("not-a-number") == pytest.approx(0.0)

    def test_invalid_string_custom_default(self):
        assert _as_float("bad", 1.5) == pytest.approx(1.5)

    def test_zero_stays_zero(self):
        assert _as_float(0) == pytest.approx(0.0)

    def test_returns_float_type(self):
        assert isinstance(_as_float(1), float)


# ---------------------------------------------------------------------------
# _as_int
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestAsInt:
    def test_int_passthrough(self):
        assert _as_int(42) == 42

    def test_float_truncated(self):
        assert _as_int(3.9) == 3

    def test_string_int(self):
        assert _as_int("10") == 10

    def test_none_returns_default(self):
        assert _as_int(None) == 0

    def test_none_custom_default(self):
        assert _as_int(None, -1) == -1

    def test_invalid_string_returns_default(self):
        assert _as_int("abc") == 0

    def test_zero(self):
        assert _as_int(0) == 0

    def test_returns_int_type(self):
        assert isinstance(_as_int(5), int)


# ---------------------------------------------------------------------------
# _parse_dt
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestParseDt:
    def test_iso_string_no_tz(self):
        result = _parse_dt("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_iso_string_no_tz_gets_utc(self):
        result = _parse_dt("2024-01-15T10:30:00")
        assert result.tzinfo is not None

    def test_iso_string_with_z(self):
        result = _parse_dt("2024-06-01T00:00:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_iso_string_with_offset(self):
        result = _parse_dt("2024-01-15T12:00:00+03:00")
        assert result is not None
        # Should be UTC-normalized
        assert result.tzinfo == timezone.utc

    def test_none_returns_none(self):
        assert _parse_dt(None) is None  # type: ignore[arg-type]

    def test_empty_string_returns_none(self):
        assert _parse_dt("") is None

    def test_invalid_string_returns_none(self):
        assert _parse_dt("not-a-date") is None

    def test_returns_datetime(self):
        result = _parse_dt("2024-01-15T10:30:00")
        assert isinstance(result, datetime)


# ---------------------------------------------------------------------------
# _fmt_ts
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestFmtTs:
    def test_format_is_compact(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert "20240115" in result
        assert "103000" in result

    def test_returns_string(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert isinstance(_fmt_ts(dt), str)

    def test_no_spaces_or_colons(self):
        dt = datetime(2024, 6, 15, 9, 5, 3, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert " " not in result
        assert ":" not in result


# ---------------------------------------------------------------------------
# _fmt_metric
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestFmtMetric:
    def test_zero_formatted(self):
        result = _fmt_metric(0.0)
        assert "0" in result

    def test_four_decimal_places(self):
        result = _fmt_metric(0.8765)
        assert "." in result
        decimal_part = result.split(".")[1]
        assert len(decimal_part) == 4

    def test_one_formatted(self):
        result = _fmt_metric(1.0)
        assert "1.0000" in result

    def test_returns_string(self):
        assert isinstance(_fmt_metric(0.5), str)


# ---------------------------------------------------------------------------
# _suite_badge
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestSuiteBadge:
    def test_pass_badge(self):
        badge = _suite_badge(_suite(passed=True))
        assert "PASS" in badge
        assert "b-pass" in badge

    def test_fail_badge(self):
        badge = _suite_badge(_suite(passed=False))
        assert "FAIL" in badge
        assert "b-fail" in badge

    def test_skipped_badge(self):
        badge = _suite_badge(_suite(aggregate={"skipped": 1.0}))
        assert "SKIPPED" in badge
        assert "b-skip" in badge

    def test_returns_html_span(self):
        badge = _suite_badge(_suite(passed=True))
        assert badge.startswith("<span")
        assert badge.endswith("</span>")


# ---------------------------------------------------------------------------
# _row_class
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestRowClass:
    def test_passed_true_not_skipped(self):
        assert _row_class(True, False) == "pass"

    def test_passed_false_not_skipped(self):
        assert _row_class(False, False) == "fail"

    def test_skipped_true(self):
        assert _row_class(False, True) == "skip"

    def test_skipped_true_overrides_passed(self):
        # skipped=True should still return "skip" even if passed=True
        assert _row_class(True, True) == "skip"

    def test_returns_string(self):
        assert isinstance(_row_class(True, False), str)


# ---------------------------------------------------------------------------
# _md_escape
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestMdEscape:
    def test_pipe_escaped(self):
        assert "\\|" in _md_escape("a|b")

    def test_multiple_pipes(self):
        result = _md_escape("a|b|c")
        assert result.count("\\|") == 2

    def test_newline_replaced_with_space(self):
        result = _md_escape("a\nb")
        assert "\n" not in result
        assert " " in result

    def test_plain_text_unchanged(self):
        assert _md_escape("hello world") == "hello world"

    def test_strips_whitespace(self):
        result = _md_escape("  hello  ")
        assert result == "hello"

    def test_none_becomes_string(self):
        result = _md_escape(None)
        assert isinstance(result, str)
        assert "None" in result

    def test_int_becomes_string(self):
        result = _md_escape(42)
        assert result == "42"


# ---------------------------------------------------------------------------
# _status_text
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestStatusText:
    def test_pass_text(self):
        assert _status_text(_suite(passed=True)) == "PASS"

    def test_fail_text(self):
        assert _status_text(_suite(passed=False)) == "FAIL"

    def test_skipped_text(self):
        assert _status_text(_suite(aggregate={"skipped": 1.0})) == "SKIP"

    def test_returns_string(self):
        assert isinstance(_status_text(_suite()), str)


# ---------------------------------------------------------------------------
# _metric_summary
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestMetricSummary:
    def test_empty_aggregate_returns_dash(self):
        assert _metric_summary(_suite(aggregate={})) == "-"

    def test_no_mean_keys_returns_dash(self):
        # Only non-mean_ keys
        assert _metric_summary(_suite(aggregate={"accuracy": 0.9})) == "-"

    def test_mean_keys_formatted(self):
        suite = _suite(aggregate={"mean_accuracy": 0.85})
        result = _metric_summary(suite)
        assert "accuracy" in result
        assert "0.850" in result

    def test_multiple_mean_keys(self):
        suite = _suite(aggregate={"mean_f1": 0.72, "mean_accuracy": 0.85})
        result = _metric_summary(suite)
        assert "f1" in result
        assert "accuracy" in result

    def test_returns_string(self):
        assert isinstance(_metric_summary(_suite()), str)


# ---------------------------------------------------------------------------
# _case_runtime_summary
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestCaseRuntimeSummary:
    def test_full_actual(self):
        actual = {
            "provider_used": "openai",
            "model_used": "gpt-4o",
            "attempts": [{"step": 1}, {"step": 2}],
        }
        result = _case_runtime_summary(actual)
        assert "openai" in result
        assert "gpt-4o" in result
        assert "attempts=2" in result

    def test_missing_fields_use_dash(self):
        result = _case_runtime_summary({})
        assert "-" in result
        assert "attempts=0" in result

    def test_none_attempts_treated_as_zero(self):
        result = _case_runtime_summary({"attempts": None})
        assert "attempts=0" in result

    def test_non_list_attempts_treated_as_zero(self):
        result = _case_runtime_summary({"attempts": "not-a-list"})
        assert "attempts=0" in result

    def test_returns_string(self):
        assert isinstance(_case_runtime_summary({}), str)


# ---------------------------------------------------------------------------
# SuiteResult computed properties
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EVALS_OK, reason="evals.reporting import failed")
class TestSuiteResultComputed:
    def _make_case(self, passed: bool, case_id: str = "c1") -> CaseResult:
        return CaseResult(case_id=case_id, passed=passed, actual={})

    def test_case_pass_rate_all_pass(self):
        cases = [self._make_case(True, f"c{i}") for i in range(4)]
        suite = _suite(cases=cases)
        assert suite.case_pass_rate() == pytest.approx(1.0)

    def test_case_pass_rate_half_pass(self):
        cases = [self._make_case(True, "c1"), self._make_case(False, "c2")]
        suite = _suite(cases=cases)
        assert suite.case_pass_rate() == pytest.approx(0.5)

    def test_case_pass_rate_empty(self):
        suite = _suite(cases=[])
        assert suite.case_pass_rate() == pytest.approx(0.0)

    def test_count_passed(self):
        cases = [self._make_case(True, "c1"), self._make_case(True, "c2"), self._make_case(False, "c3")]
        suite = _suite(cases=cases)
        assert suite.count_passed() == 2

    def test_count_passed_empty(self):
        assert _suite(cases=[]).count_passed() == 0
