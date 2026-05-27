"""Unit tests for api_testing/feedback_loop.py pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/api_testing/feedback_loop.py:
    _find_expected_status, _guess_root_cause, _extract_path
"""

from __future__ import annotations

import types

import pytest

from app.domains.api_testing.feedback_loop import (
    _extract_path,
    _find_expected_status,
    _guess_root_cause,
)


# ── _find_expected_status ─────────────────────────────────────────────────────


class TestFindExpectedStatus:
    def test_finds_integer_status(self) -> None:
        assertions = [{"type": "status_code", "expected": 200}]
        assert _find_expected_status(assertions) == 200

    def test_finds_string_status(self) -> None:
        assertions = [{"type": "status_code", "expected": "404"}]
        assert _find_expected_status(assertions) == 404

    def test_skips_non_status_code_assertions(self) -> None:
        assertions = [
            {"type": "response_time", "expected": 500},
            {"type": "status_code", "expected": 201},
        ]
        assert _find_expected_status(assertions) == 201

    def test_empty_list_returns_none(self) -> None:
        assert _find_expected_status([]) is None

    def test_no_status_code_type_returns_none(self) -> None:
        assertions = [{"type": "content_type", "expected": "application/json"}]
        assert _find_expected_status(assertions) is None

    def test_non_digit_string_skipped(self) -> None:
        assertions = [{"type": "status_code", "expected": "ok"}]
        assert _find_expected_status(assertions) is None

    def test_returns_first_match(self) -> None:
        assertions = [
            {"type": "status_code", "expected": 200},
            {"type": "status_code", "expected": 201},
        ]
        assert _find_expected_status(assertions) == 200

    def test_returns_int(self) -> None:
        assertions = [{"type": "status_code", "expected": 200}]
        result = _find_expected_status(assertions)
        assert isinstance(result, int)


# ── _guess_root_cause ─────────────────────────────────────────────────────────


def _make_detail(status_code=None, error_message=""):
    """Create a minimal ApiExecutionDetail-like object."""
    return types.SimpleNamespace(status_code=status_code, error_message=error_message)


class TestGuessRootCause:
    def test_401_returns_auth_failure(self) -> None:
        detail = _make_detail(status_code=401)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "auth" in result.lower()

    def test_403_returns_authorization_failure(self) -> None:
        detail = _make_detail(status_code=403)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "authorization" in result.lower() or "permission" in result.lower()

    def test_404_returns_not_found(self) -> None:
        detail = _make_detail(status_code=404)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "not found" in result.lower() or "404" in (result or "")

    def test_409_returns_conflict(self) -> None:
        detail = _make_detail(status_code=409)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "conflict" in result.lower()

    def test_422_returns_validation(self) -> None:
        detail = _make_detail(status_code=422)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "validation" in result.lower()

    def test_429_returns_rate_limit(self) -> None:
        detail = _make_detail(status_code=429)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "rate" in result.lower()

    def test_500_returns_server_error(self) -> None:
        detail = _make_detail(status_code=500)
        result = _guess_root_cause(detail)
        assert result is not None
        assert "server" in result.lower()

    def test_502_returns_service_unavailable(self) -> None:
        detail = _make_detail(status_code=502)
        result = _guess_root_cause(detail)
        assert result is not None

    def test_503_returns_service_unavailable(self) -> None:
        detail = _make_detail(status_code=503)
        result = _guess_root_cause(detail)
        assert result is not None

    def test_timeout_in_error_returns_timeout(self) -> None:
        detail = _make_detail(status_code=None, error_message="request timeout occurred")
        result = _guess_root_cause(detail)
        assert result is not None
        assert "timeout" in result.lower()

    def test_connection_error_returns_connection(self) -> None:
        detail = _make_detail(status_code=None, error_message="connection refused")
        result = _guess_root_cause(detail)
        assert result is not None
        assert "connection" in result.lower()

    def test_unknown_status_returns_none(self) -> None:
        detail = _make_detail(status_code=418)
        assert _guess_root_cause(detail) is None


# ── _extract_path ─────────────────────────────────────────────────────────────


class TestExtractPath:
    def test_full_url_returns_path(self) -> None:
        result = _extract_path("http://example.com/api/users")
        assert result == "/api/users"

    def test_url_with_query_strips_query(self) -> None:
        result = _extract_path("http://example.com/api/users?page=1&limit=10")
        assert result == "/api/users"

    def test_url_with_port(self) -> None:
        result = _extract_path("http://example.com:8080/api/v1/test")
        assert result == "/api/v1/test"

    def test_empty_url_returns_slash(self) -> None:
        assert _extract_path("") == "/"

    def test_https_url(self) -> None:
        result = _extract_path("https://api.example.com/v2/auth/login")
        assert result == "/v2/auth/login"

    def test_url_with_fragment(self) -> None:
        # Fragment comes after # — urlparse handles this
        result = _extract_path("http://example.com/path")
        assert result == "/path"

    def test_root_path(self) -> None:
        result = _extract_path("http://example.com/")
        assert result == "/"

    def test_returns_string(self) -> None:
        assert isinstance(_extract_path("http://example.com/test"), str)
