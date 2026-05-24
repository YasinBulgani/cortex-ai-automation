"""Unit tests for API Testing feedback loop pure helper functions.

Tests app/domains/api_testing/feedback_loop.py — no DB, no LLM.
Covers: _find_expected_status, _extract_path, _build_stats_summary.
"""

from __future__ import annotations

import pytest

from app.domains.api_testing.feedback_loop import (
    _build_stats_summary,
    _extract_path,
    _find_expected_status,
)


# ── _find_expected_status ─────────────────────────────────────────────────────


class TestFindExpectedStatus:
    def test_empty_list_returns_none(self) -> None:
        assert _find_expected_status([]) is None

    def test_finds_int_status(self) -> None:
        assertions = [{"type": "status_code", "expected": 200}]
        assert _find_expected_status(assertions) == 200

    def test_finds_string_digit_status(self) -> None:
        assertions = [{"type": "status_code", "expected": "201"}]
        assert _find_expected_status(assertions) == 201

    def test_non_status_code_assertion_ignored(self) -> None:
        assertions = [
            {"type": "header", "expected": "application/json"},
            {"type": "json_path", "expected": "value"},
        ]
        assert _find_expected_status(assertions) is None

    def test_first_status_code_returned(self) -> None:
        assertions = [
            {"type": "status_code", "expected": 200},
            {"type": "status_code", "expected": 201},
        ]
        assert _find_expected_status(assertions) == 200

    def test_non_digit_string_ignored(self) -> None:
        assertions = [{"type": "status_code", "expected": "two-hundred"}]
        assert _find_expected_status(assertions) is None

    def test_list_expected_not_returned(self) -> None:
        assertions = [{"type": "status_code", "expected": [200, 201]}]
        # Expected is a list, not int or digit string → returns None
        assert _find_expected_status(assertions) is None

    def test_mixed_assertions_finds_status(self) -> None:
        assertions = [
            {"type": "json_path", "expected": "$.id"},
            {"type": "status_code", "expected": 404},
            {"type": "header", "expected": "application/json"},
        ]
        assert _find_expected_status(assertions) == 404

    def test_none_expected_skipped(self) -> None:
        assertions = [{"type": "status_code", "expected": None}]
        assert _find_expected_status(assertions) is None


# ── _extract_path ─────────────────────────────────────────────────────────────


class TestExtractPath:
    def test_empty_url_returns_slash(self) -> None:
        assert _extract_path("") == "/"

    def test_none_url_returns_slash(self) -> None:
        assert _extract_path(None) == "/"  # type: ignore[arg-type]

    def test_full_url_extracts_path(self) -> None:
        assert _extract_path("http://api.example.com/v1/users") == "/v1/users"

    def test_https_url(self) -> None:
        assert _extract_path("https://api.bank.com/api/v2/accounts") == "/api/v2/accounts"

    def test_url_with_query_string(self) -> None:
        result = _extract_path("http://api.example.com/users?page=1&limit=10")
        assert result == "/users"

    def test_url_with_port(self) -> None:
        result = _extract_path("http://localhost:8000/api/test")
        assert result == "/api/test"

    def test_root_path(self) -> None:
        assert _extract_path("http://api.example.com/") == "/"

    def test_no_path_returns_slash(self) -> None:
        result = _extract_path("http://api.example.com")
        assert result == "/"

    def test_nested_path(self) -> None:
        result = _extract_path("https://api.example.com/v3/users/123/accounts/456")
        assert result == "/v3/users/123/accounts/456"

    def test_path_with_trailing_slash(self) -> None:
        result = _extract_path("https://api.example.com/users/")
        assert result == "/users/"


# ── _build_stats_summary ──────────────────────────────────────────────────────


class TestBuildStatsSummary:
    def test_empty_stats_returns_none(self) -> None:
        result = _build_stats_summary({}, run_id="run-001")
        assert result is None

    def test_single_endpoint_summary(self) -> None:
        stats = {
            "GET /api/users": {
                "count": 5,
                "passed": 4,
                "failed": 1,
                "total_ms": 500.0,
            }
        }
        result = _build_stats_summary(stats, run_id="run-001")
        assert result is not None
        assert "RUN SUMMARY" in result
        assert "run-001" in result
        assert "GET /api/users" in result
        assert "80%" in result  # 4/5 pass rate
        assert "100ms" in result  # 500/5 avg ms

    def test_all_passing(self) -> None:
        stats = {
            "POST /api/login": {
                "count": 3,
                "passed": 3,
                "failed": 0,
                "total_ms": 300.0,
            }
        }
        result = _build_stats_summary(stats, run_id="run-002")
        assert "100%" in result

    def test_all_failing(self) -> None:
        stats = {
            "GET /api/broken": {
                "count": 2,
                "passed": 0,
                "failed": 2,
                "total_ms": 100.0,
            }
        }
        result = _build_stats_summary(stats, run_id="run-003")
        assert "0%" in result

    def test_multiple_endpoints_sorted(self) -> None:
        stats = {
            "POST /api/payments": {"count": 1, "passed": 1, "failed": 0, "total_ms": 100.0},
            "GET /api/accounts": {"count": 2, "passed": 2, "failed": 0, "total_ms": 200.0},
        }
        result = _build_stats_summary(stats, run_id="r")
        assert result is not None
        # Sorted alphabetically: GET /api/accounts before POST /api/payments
        get_pos = result.index("GET /api/accounts")
        post_pos = result.index("POST /api/payments")
        assert get_pos < post_pos

    def test_run_id_in_header(self) -> None:
        stats = {"GET /": {"count": 1, "passed": 1, "failed": 0, "total_ms": 50.0}}
        result = _build_stats_summary(stats, run_id="test-run-xyz")
        assert "test-run-xyz" in result

    def test_zero_count_handled(self) -> None:
        stats = {
            "GET /api/empty": {"count": 0, "passed": 0, "failed": 0, "total_ms": 0.0}
        }
        # Should not crash with division by zero
        result = _build_stats_summary(stats, run_id="r")
        assert result is not None
        assert "0%" in result
