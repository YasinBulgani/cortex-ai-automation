"""Unit tests for evals reporting helper functions.

Tests app/domains/evals/reporting.py pure helper functions —
no filesystem I/O, no external dependencies.
Covers: _as_float, _as_int, _parse_dt, _fmt_metric, _fmt_ts,
        _suite_health, _runtime_matrix, _suite_badge, _row_class,
        _status_text, _metric_summary, _md_escape, _case_runtime_summary.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domains.evals.reporting import (
    _as_float,
    _as_int,
    _case_runtime_summary,
    _fmt_metric,
    _fmt_ts,
    _md_escape,
    _metric_summary,
    _row_class,
    _runtime_matrix,
    _status_text,
    _suite_badge,
    _suite_health,
)
from app.domains.evals.schemas import CaseResult, ScorerOutput, SuiteResult


# ── _as_float ─────────────────────────────────────────────────────────────────


class TestAsFloat:
    def test_float_input(self) -> None:
        assert _as_float(1.5) == 1.5

    def test_int_input(self) -> None:
        assert _as_float(3) == 3.0

    def test_string_float(self) -> None:
        assert _as_float("2.5") == 2.5

    def test_string_int(self) -> None:
        assert _as_float("10") == 10.0

    def test_none_returns_default(self) -> None:
        assert _as_float(None) == 0.0

    def test_none_custom_default(self) -> None:
        assert _as_float(None, default=-1.0) == -1.0

    def test_invalid_string_returns_default(self) -> None:
        assert _as_float("abc") == 0.0

    def test_empty_string_returns_default(self) -> None:
        assert _as_float("") == 0.0

    def test_zero(self) -> None:
        assert _as_float(0) == 0.0

    def test_negative(self) -> None:
        assert _as_float(-3.14) == pytest.approx(-3.14)


# ── _as_int ───────────────────────────────────────────────────────────────────


class TestAsInt:
    def test_int_input(self) -> None:
        assert _as_int(5) == 5

    def test_float_truncated(self) -> None:
        assert _as_int(3.9) == 3

    def test_string_int(self) -> None:
        assert _as_int("42") == 42

    def test_none_returns_default(self) -> None:
        assert _as_int(None) == 0

    def test_none_custom_default(self) -> None:
        assert _as_int(None, default=99) == 99

    def test_invalid_string_returns_default(self) -> None:
        assert _as_int("xyz") == 0

    def test_zero(self) -> None:
        assert _as_int(0) == 0

    def test_negative(self) -> None:
        assert _as_int(-7) == -7


# ── _parse_dt ─────────────────────────────────────────────────────────────────


class TestParseDt:
    def _import(self):
        from app.domains.evals.reporting import _parse_dt
        return _parse_dt

    def test_iso_with_z(self) -> None:
        from app.domains.evals.reporting import _parse_dt
        result = _parse_dt("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_iso_with_offset(self) -> None:
        from app.domains.evals.reporting import _parse_dt
        result = _parse_dt("2024-03-20T14:00:00+03:00")
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 11  # 14:00+03:00 → 11:00 UTC

    def test_iso_without_tz(self) -> None:
        from app.domains.evals.reporting import _parse_dt
        result = _parse_dt("2024-06-01T08:00:00")
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_empty_string_returns_none(self) -> None:
        from app.domains.evals.reporting import _parse_dt
        assert _parse_dt("") is None

    def test_invalid_string_returns_none(self) -> None:
        from app.domains.evals.reporting import _parse_dt
        assert _parse_dt("not-a-date") is None

    def test_none_handled(self) -> None:
        from app.domains.evals.reporting import _parse_dt
        assert _parse_dt(None) is None  # type: ignore[arg-type]


# ── _fmt_metric ───────────────────────────────────────────────────────────────


class TestFmtMetric:
    def test_four_decimal_places(self) -> None:
        assert _fmt_metric(0.9) == "0.9000"

    def test_zero(self) -> None:
        assert _fmt_metric(0.0) == "0.0000"

    def test_one(self) -> None:
        assert _fmt_metric(1.0) == "1.0000"

    def test_rounds(self) -> None:
        assert _fmt_metric(0.12345) == "0.1235"  # rounds up

    def test_negative(self) -> None:
        assert _fmt_metric(-0.5) == "-0.5000"


# ── _fmt_ts ───────────────────────────────────────────────────────────────────


class TestFmtTs:
    def test_format(self) -> None:
        dt = datetime(2024, 3, 15, 9, 5, 2, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert result == "20240315-090502"

    def test_format_midnight(self) -> None:
        dt = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        result = _fmt_ts(dt)
        assert result == "20251231-000000"


# ── _row_class ────────────────────────────────────────────────────────────────


class TestRowClass:
    def test_passed_not_skipped(self) -> None:
        assert _row_class(True, False) == "pass"

    def test_failed_not_skipped(self) -> None:
        assert _row_class(False, False) == "fail"

    def test_skipped_overrides_passed(self) -> None:
        assert _row_class(True, True) == "skip"

    def test_skipped_overrides_failed(self) -> None:
        assert _row_class(False, True) == "skip"


# ── _md_escape ────────────────────────────────────────────────────────────────


class TestMdEscape:
    def test_pipe_escaped(self) -> None:
        result = _md_escape("a|b|c")
        assert result == r"a\|b\|c"

    def test_newline_replaced(self) -> None:
        result = _md_escape("line1\nline2")
        assert result == "line1 line2"

    def test_whitespace_stripped(self) -> None:
        result = _md_escape("  hello  ")
        assert result == "hello"

    def test_plain_text_unchanged(self) -> None:
        result = _md_escape("simple text")
        assert result == "simple text"

    def test_non_string_converted(self) -> None:
        result = _md_escape(42)
        assert result == "42"

    def test_empty(self) -> None:
        result = _md_escape("")
        assert result == ""


# ── _case_runtime_summary ─────────────────────────────────────────────────────


class TestCaseRuntimeSummary:
    def test_full_actual(self) -> None:
        actual = {
            "provider_used": "openai",
            "model_used": "gpt-4",
            "attempts": [1, 2, 3],
        }
        result = _case_runtime_summary(actual)
        assert "openai" in result
        assert "gpt-4" in result
        assert "attempts=3" in result

    def test_missing_fields_uses_dash(self) -> None:
        result = _case_runtime_summary({})
        assert "- / -" in result
        assert "attempts=0" in result

    def test_none_attempts(self) -> None:
        actual = {"provider_used": "anthropic", "model_used": "claude", "attempts": None}
        result = _case_runtime_summary(actual)
        assert "attempts=0" in result

    def test_non_list_attempts(self) -> None:
        actual = {"provider_used": "p", "model_used": "m", "attempts": "not-a-list"}
        result = _case_runtime_summary(actual)
        assert "attempts=0" in result


# ── SuiteResult helpers ───────────────────────────────────────────────────────


def _make_suite(
    name: str = "my-suite",
    passed: bool = True,
    cases: list | None = None,
    aggregate: dict | None = None,
    threshold_failures: list | None = None,
    adapter_name: str = "openai",
) -> SuiteResult:
    return SuiteResult(
        suite_name=name,
        adapter_name=adapter_name,
        passed=passed,
        cases=cases or [],
        aggregate=aggregate or {},
        threshold_failures=threshold_failures or [],
    )


class TestSuiteBadge:
    def test_passed_suite(self) -> None:
        suite = _make_suite(passed=True)
        badge = _suite_badge(suite)
        assert "PASS" in badge
        assert "b-pass" in badge

    def test_failed_suite(self) -> None:
        suite = _make_suite(passed=False)
        badge = _suite_badge(suite)
        assert "FAIL" in badge
        assert "b-fail" in badge

    def test_skipped_suite(self) -> None:
        suite = _make_suite(passed=True, aggregate={"skipped": 1.0})
        badge = _suite_badge(suite)
        assert "SKIP" in badge
        assert "b-skip" in badge


class TestStatusText:
    def test_passed(self) -> None:
        suite = _make_suite(passed=True)
        assert _status_text(suite) == "PASS"

    def test_failed(self) -> None:
        suite = _make_suite(passed=False)
        assert _status_text(suite) == "FAIL"

    def test_skipped(self) -> None:
        suite = _make_suite(passed=True, aggregate={"skipped": 1.0})
        assert _status_text(suite) == "SKIP"


class TestMetricSummary:
    def test_mean_metrics_included(self) -> None:
        suite = _make_suite(aggregate={"mean_precision": 0.9, "mean_recall": 0.8})
        result = _metric_summary(suite)
        assert "precision=0.900" in result
        assert "recall=0.800" in result

    def test_non_mean_keys_excluded(self) -> None:
        suite = _make_suite(aggregate={"case_pass_rate": 0.9, "skipped": 0.0})
        result = _metric_summary(suite)
        assert result == "-"

    def test_empty_aggregate(self) -> None:
        suite = _make_suite(aggregate={})
        assert _metric_summary(suite) == "-"

    def test_sorted_output(self) -> None:
        suite = _make_suite(aggregate={"mean_z_score": 0.5, "mean_a_score": 0.7})
        result = _metric_summary(suite)
        a_pos = result.index("a_score")
        z_pos = result.index("z_score")
        assert a_pos < z_pos  # sorted alphabetically


# ── _suite_health ─────────────────────────────────────────────────────────────


class TestSuiteHealth:
    def test_empty_rows_returns_empty(self) -> None:
        assert _suite_health([]) == []

    def test_single_passing_suite(self) -> None:
        rows = [
            {
                "suites": [
                    {
                        "name": "auth-suite",
                        "adapter": "openai",
                        "passed": True,
                        "case_pass_rate": 1.0,
                        "total_latency_ms": 500,
                        "threshold_failures": [],
                    }
                ]
            }
        ]
        result = _suite_health(rows)
        assert len(result) == 1
        assert result[0]["name"] == "auth-suite"
        assert result[0]["status"] == "pass"
        assert result[0]["runs"] == 1

    def test_single_failing_suite(self) -> None:
        rows = [
            {
                "suites": [
                    {
                        "name": "search-suite",
                        "adapter": "anthropic",
                        "passed": False,
                        "case_pass_rate": 0.5,
                        "total_latency_ms": 1000,
                        "threshold_failures": ["precision below threshold"],
                    }
                ]
            }
        ]
        result = _suite_health(rows)
        assert len(result) == 1
        assert result[0]["status"] == "fail"
        assert result[0]["latest_threshold_failures"] == ["precision below threshold"]

    def test_multiple_runs_same_suite(self) -> None:
        rows = [
            {
                "suites": [
                    {
                        "name": "suite-a",
                        "adapter": "x",
                        "passed": True,
                        "case_pass_rate": 1.0,
                        "total_latency_ms": 100,
                    }
                ]
            },
            {
                "suites": [
                    {
                        "name": "suite-a",
                        "adapter": "x",
                        "passed": True,
                        "case_pass_rate": 1.0,
                        "total_latency_ms": 200,
                    }
                ]
            },
        ]
        result = _suite_health(rows)
        assert len(result) == 1
        assert result[0]["runs"] == 2
        assert result[0]["pass_rate"] == 1.0

    def test_warn_when_not_all_runs_passed(self) -> None:
        rows = [
            {
                "suites": [
                    {
                        "name": "flaky-suite",
                        "adapter": "y",
                        "passed": True,
                        "case_pass_rate": 1.0,
                        "total_latency_ms": 100,
                    }
                ]
            },
            {
                "suites": [
                    {
                        "name": "flaky-suite",
                        "adapter": "y",
                        "passed": False,
                        "case_pass_rate": 0.9,
                        "total_latency_ms": 100,
                    }
                ]
            },
        ]
        # Latest passed=False → status fail (latest_passed overrides)
        result = _suite_health(rows)
        assert result[0]["status"] == "fail"

    def test_fail_suites_sorted_first(self) -> None:
        rows = [
            {
                "suites": [
                    {
                        "name": "good-suite",
                        "adapter": "a",
                        "passed": True,
                        "case_pass_rate": 1.0,
                        "total_latency_ms": 100,
                    },
                    {
                        "name": "bad-suite",
                        "adapter": "b",
                        "passed": False,
                        "case_pass_rate": 0.0,
                        "total_latency_ms": 100,
                    },
                ]
            }
        ]
        result = _suite_health(rows)
        assert result[0]["name"] == "bad-suite"  # fail first

    def test_non_dict_suites_skipped(self) -> None:
        rows = [{"suites": ["not-a-dict", None]}]
        result = _suite_health(rows)
        assert result == []

    def test_missing_suites_key(self) -> None:
        result = _suite_health([{"something_else": []}])
        assert result == []


# ── _runtime_matrix ───────────────────────────────────────────────────────────


class TestRuntimeMatrix:
    def test_none_report_returns_empty(self) -> None:
        assert _runtime_matrix(None) == []

    def test_empty_report_returns_empty(self) -> None:
        assert _runtime_matrix({}) == []

    def test_single_provider_model(self) -> None:
        report = {
            "suites": [
                {
                    "cases": [
                        {
                            "actual": {
                                "provider_used": "openai",
                                "model_used": "gpt-4",
                                "attempts": [1, 2],
                            }
                        }
                    ]
                }
            ]
        }
        result = _runtime_matrix(report)
        assert len(result) == 1
        assert result[0]["provider"] == "openai"
        assert result[0]["model"] == "gpt-4"
        assert result[0]["cases"] == 1
        assert result[0]["attempts"] == 2

    def test_multiple_providers_aggregated(self) -> None:
        report = {
            "suites": [
                {
                    "cases": [
                        {
                            "actual": {
                                "provider_used": "openai",
                                "model_used": "gpt-4",
                                "attempts": [1],
                            }
                        },
                        {
                            "actual": {
                                "provider_used": "anthropic",
                                "model_used": "claude-3",
                                "attempts": [1, 2, 3],
                            }
                        },
                    ]
                }
            ]
        }
        result = _runtime_matrix(report)
        assert len(result) == 2

    def test_same_provider_different_cases_accumulated(self) -> None:
        report = {
            "suites": [
                {
                    "cases": [
                        {
                            "actual": {
                                "provider_used": "openai",
                                "model_used": "gpt-4",
                                "attempts": [1],
                            }
                        },
                        {
                            "actual": {
                                "provider_used": "openai",
                                "model_used": "gpt-4",
                                "attempts": [1, 2],
                            }
                        },
                    ]
                }
            ]
        }
        result = _runtime_matrix(report)
        assert len(result) == 1
        assert result[0]["cases"] == 2
        assert result[0]["attempts"] == 3

    def test_missing_actual_key(self) -> None:
        report = {"suites": [{"cases": [{"no_actual": True}]}]}
        result = _runtime_matrix(report)
        # Should not crash; actual defaults to {}
        assert len(result) == 1
        assert result[0]["provider"] == "-"

    def test_sorted_by_cases_desc(self) -> None:
        report = {
            "suites": [
                {
                    "cases": [
                        {"actual": {"provider_used": "a", "model_used": "m1", "attempts": [1]}},
                        {"actual": {"provider_used": "b", "model_used": "m2", "attempts": [1]}},
                        {"actual": {"provider_used": "a", "model_used": "m1", "attempts": [1]}},
                    ]
                }
            ]
        }
        result = _runtime_matrix(report)
        # Provider "a" has 2 cases, "b" has 1 → "a" comes first
        assert result[0]["provider"] == "a"
        assert result[0]["cases"] == 2
