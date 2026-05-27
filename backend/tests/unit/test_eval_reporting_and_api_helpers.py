"""Unit tests for eval reporting and API testing pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/evals/reporting.py:
    _fmt_ts, _fmt_metric, _as_float, _as_int, _parse_dt,
    _md_escape, _status_text, _row_class
  app/domains/api_testing/assertion_suggester.py:
    _make_suggestion, _existing_assertion_types
  app/domains/api_testing/feedback_loop.py:
    _extract_path, _find_expected_status, _guess_root_cause
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.domains.evals.reporting import (
    _as_float,
    _as_int,
    _fmt_metric,
    _fmt_ts,
    _md_escape,
    _parse_dt,
    _row_class,
    _status_text,
)
from app.domains.api_testing.assertion_suggester import (
    _existing_assertion_types,
    _make_suggestion,
)
from app.domains.api_testing.feedback_loop import (
    _extract_path,
    _find_expected_status,
    _guess_root_cause,
)


# ── _fmt_ts ───────────────────────────────────────────────────────────────────


class TestFmtTs:
    def test_returns_string(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert isinstance(result, str)

    def test_format_yyyymmdd_hhmmss(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert result == "20240115-103045"

    def test_midnight(self) -> None:
        dt = datetime(2024, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert result == "20241231-000000"

    def test_single_digit_month_zero_padded(self) -> None:
        dt = datetime(2024, 3, 5, 9, 5, 7, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert result == "20240305-090507"


# ── _fmt_metric ───────────────────────────────────────────────────────────────


class TestFmtMetric:
    def test_four_decimal_places(self) -> None:
        result = _fmt_metric(0.12345)
        assert result == "0.1235"  # rounded to 4 decimals

    def test_zero(self) -> None:
        assert _fmt_metric(0.0) == "0.0000"

    def test_one(self) -> None:
        assert _fmt_metric(1.0) == "1.0000"

    def test_returns_string(self) -> None:
        assert isinstance(_fmt_metric(0.5), str)

    def test_negative_value(self) -> None:
        result = _fmt_metric(-0.25)
        assert result == "-0.2500"


# ── _as_float ─────────────────────────────────────────────────────────────────


class TestAsFloat:
    def test_float_passthrough(self) -> None:
        assert _as_float(3.14) == pytest.approx(3.14)

    def test_int_converted(self) -> None:
        assert _as_float(5) == pytest.approx(5.0)

    def test_string_converted(self) -> None:
        assert _as_float("2.5") == pytest.approx(2.5)

    def test_invalid_returns_default(self) -> None:
        assert _as_float("not-a-float") == 0.0

    def test_none_returns_default(self) -> None:
        assert _as_float(None) == 0.0

    def test_custom_default(self) -> None:
        assert _as_float("bad", default=99.9) == pytest.approx(99.9)

    def test_zero(self) -> None:
        assert _as_float(0) == 0.0


# ── _as_int ───────────────────────────────────────────────────────────────────


class TestAsInt:
    def test_int_passthrough(self) -> None:
        assert _as_int(42) == 42

    def test_float_truncated(self) -> None:
        assert _as_int(3.9) == 3

    def test_string_converted(self) -> None:
        assert _as_int("7") == 7

    def test_invalid_returns_default(self) -> None:
        assert _as_int("abc") == 0

    def test_none_returns_default(self) -> None:
        assert _as_int(None) == 0

    def test_custom_default(self) -> None:
        assert _as_int("x", default=-1) == -1

    def test_negative_string(self) -> None:
        assert _as_int("-5") == -5


# ── _parse_dt ─────────────────────────────────────────────────────────────────


class TestParseDt:
    def test_iso_format(self) -> None:
        result = _parse_dt("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_z_suffix_parsed(self) -> None:
        result = _parse_dt("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.tzinfo is not None

    def test_utc_offset_parsed(self) -> None:
        result = _parse_dt("2024-01-15T10:30:00+00:00")
        assert result is not None

    def test_empty_returns_none(self) -> None:
        assert _parse_dt("") is None

    def test_invalid_returns_none(self) -> None:
        assert _parse_dt("not-a-date") is None

    def test_returns_utc_aware(self) -> None:
        result = _parse_dt("2024-06-01T00:00:00Z")
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_naive_datetime_gets_utc(self) -> None:
        # No timezone info → should become UTC aware
        result = _parse_dt("2024-06-01T00:00:00")
        assert result is not None
        assert result.tzinfo is not None


# ── _md_escape ────────────────────────────────────────────────────────────────


class TestMdEscape:
    def test_pipe_escaped(self) -> None:
        result = _md_escape("a|b")
        assert "\\|" in result
        assert "|" not in result.replace("\\|", "")

    def test_newline_replaced_with_space(self) -> None:
        result = _md_escape("line1\nline2")
        assert "\n" not in result
        assert "line1" in result
        assert "line2" in result

    def test_plain_text_unchanged(self) -> None:
        assert _md_escape("hello world") == "hello world"

    def test_strips_whitespace(self) -> None:
        assert _md_escape("  hello  ") == "hello"

    def test_non_string_converted(self) -> None:
        result = _md_escape(42)
        assert result == "42"

    def test_none_converted(self) -> None:
        result = _md_escape(None)
        assert result == "None"


# ── _status_text ──────────────────────────────────────────────────────────────


class TestStatusText:
    def test_passed_suite(self) -> None:
        from app.domains.evals.schemas import SuiteResult
        res = SuiteResult(suite_name="test", adapter_name="pytest", passed=True)
        assert _status_text(res) == "PASS"

    def test_failed_suite(self) -> None:
        from app.domains.evals.schemas import SuiteResult
        res = SuiteResult(suite_name="test", adapter_name="pytest", passed=False)
        assert _status_text(res) == "FAIL"

    def test_skipped_suite(self) -> None:
        from app.domains.evals.schemas import SuiteResult
        res = SuiteResult(suite_name="test", adapter_name="pytest",
                          aggregate={"skipped": 1.0}, passed=False)
        assert _status_text(res) == "SKIP"


# ── _row_class ────────────────────────────────────────────────────────────────


class TestRowClass:
    def test_pass_row(self) -> None:
        assert _row_class(passed=True, skipped=False) == "pass"

    def test_fail_row(self) -> None:
        assert _row_class(passed=False, skipped=False) == "fail"

    def test_skip_row(self) -> None:
        assert _row_class(passed=False, skipped=True) == "skip"

    def test_skip_overrides_passed(self) -> None:
        # If skipped=True, result is "skip" regardless of passed
        assert _row_class(passed=True, skipped=True) == "skip"

    def test_returns_string(self) -> None:
        assert isinstance(_row_class(True, False), str)


# ── _make_suggestion ──────────────────────────────────────────────────────────


class TestMakeSuggestion:
    def test_returns_dict(self) -> None:
        result = _make_suggestion("status_code", "status_code", "eq", 200, "reason", "CRITICAL", "functional")
        assert isinstance(result, dict)

    def test_all_keys_present(self) -> None:
        result = _make_suggestion("header", "Content-Type", "contains", "application/json",
                                  "Check header", "HIGH", "functional")
        assert "type" in result
        assert "field" in result
        assert "operator" in result
        assert "expected" in result
        assert "reason" in result
        assert "priority" in result
        assert "category" in result

    def test_values_match_inputs(self) -> None:
        result = _make_suggestion("perf", "response_time", "lt", 500, "fast", "MEDIUM", "performance")
        assert result["type"] == "perf"
        assert result["field"] == "response_time"
        assert result["operator"] == "lt"
        assert result["expected"] == 500
        assert result["reason"] == "fast"
        assert result["priority"] == "MEDIUM"
        assert result["category"] == "performance"


# ── _existing_assertion_types ─────────────────────────────────────────────────


class TestExistingAssertionTypes:
    def test_empty_list_returns_empty(self) -> None:
        result = _existing_assertion_types([])
        assert result == {}

    def test_single_assertion_indexed(self) -> None:
        assertions = [{"type": "status_code", "expected": 200}]
        result = _existing_assertion_types(assertions)
        assert "status_code" in result
        assert len(result["status_code"]) == 1

    def test_multiple_same_type_grouped(self) -> None:
        assertions = [
            {"type": "header", "field": "Content-Type"},
            {"type": "header", "field": "Authorization"},
        ]
        result = _existing_assertion_types(assertions)
        assert "header" in result
        assert len(result["header"]) == 2

    def test_different_types_separate_keys(self) -> None:
        assertions = [
            {"type": "status_code", "expected": 200},
            {"type": "performance", "field": "response_time"},
        ]
        result = _existing_assertion_types(assertions)
        assert "status_code" in result
        assert "performance" in result

    def test_missing_type_key_uses_empty_string(self) -> None:
        assertions = [{"expected": 200}]
        result = _existing_assertion_types(assertions)
        assert "" in result


# ── _extract_path ─────────────────────────────────────────────────────────────


class TestExtractPath:
    def test_full_url(self) -> None:
        result = _extract_path("http://api.example.com/v1/users")
        assert result == "/v1/users"

    def test_with_query_string(self) -> None:
        result = _extract_path("https://api.example.com/users?page=1")
        assert result == "/users"

    def test_empty_url_returns_root(self) -> None:
        assert _extract_path("") == "/"

    def test_root_path(self) -> None:
        result = _extract_path("https://api.example.com/")
        assert result == "/"

    def test_path_with_params(self) -> None:
        result = _extract_path("https://api.example.com/users/123/orders")
        assert result == "/users/123/orders"

    def test_returns_string(self) -> None:
        assert isinstance(_extract_path("http://example.com"), str)


# ── _find_expected_status ─────────────────────────────────────────────────────


class TestFindExpectedStatus:
    def test_finds_status_code_assertion(self) -> None:
        assertions = [{"type": "status_code", "expected": 200}]
        assert _find_expected_status(assertions) == 200

    def test_empty_list_returns_none(self) -> None:
        assert _find_expected_status([]) is None

    def test_no_status_code_type_returns_none(self) -> None:
        assertions = [{"type": "header", "expected": "application/json"}]
        assert _find_expected_status(assertions) is None

    def test_string_status_code_converted(self) -> None:
        assertions = [{"type": "status_code", "expected": "404"}]
        assert _find_expected_status(assertions) == 404

    def test_multiple_assertions_first_status_returned(self) -> None:
        assertions = [
            {"type": "header", "expected": "application/json"},
            {"type": "status_code", "expected": 201},
        ]
        assert _find_expected_status(assertions) == 201


# ── _guess_root_cause ─────────────────────────────────────────────────────────


class TestGuessRootCause:
    def _detail(self, status_code=None, error_message=""):
        return SimpleNamespace(status_code=status_code, error_message=error_message)

    def test_401_authentication(self) -> None:
        result = _guess_root_cause(self._detail(401))
        assert "authentication" in result.lower()

    def test_403_authorization(self) -> None:
        result = _guess_root_cause(self._detail(403))
        assert "authorization" in result.lower()

    def test_404_not_found(self) -> None:
        result = _guess_root_cause(self._detail(404))
        assert "not found" in result.lower()

    def test_422_validation(self) -> None:
        result = _guess_root_cause(self._detail(422))
        assert "validation" in result.lower()

    def test_429_rate_limit(self) -> None:
        result = _guess_root_cause(self._detail(429))
        assert "rate limit" in result.lower()

    def test_500_server_error(self) -> None:
        result = _guess_root_cause(self._detail(500))
        assert "server" in result.lower()

    def test_timeout_error_message(self) -> None:
        result = _guess_root_cause(self._detail(None, "timeout occurred"))
        assert "timeout" in result.lower()

    def test_connection_refused(self) -> None:
        result = _guess_root_cause(self._detail(None, "connection refused"))
        assert "connection" in result.lower()

    def test_unknown_status_returns_none(self) -> None:
        result = _guess_root_cause(self._detail(200))
        assert result is None
