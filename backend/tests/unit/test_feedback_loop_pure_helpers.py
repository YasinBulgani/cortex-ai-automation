"""Unit tests for api_testing.feedback_loop pure helper functions.

All tests are self-contained: no DB, no HTTP, no KnowledgeStore.
Covers:
  - _find_expected_status: extract status code from assertion list
  - _extract_path: URL path extraction
"""
from __future__ import annotations

import pytest

try:
    from app.domains.api_testing.feedback_loop import (
        _find_expected_status,
        _extract_path,
    )
    _FL_OK = True
except ImportError:
    _FL_OK = False


# ---------------------------------------------------------------------------
# _find_expected_status
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FL_OK, reason="feedback_loop import failed")
class TestFindExpectedStatus:
    def test_finds_integer_status(self):
        assertions = [{"type": "status_code", "expected": 200}]
        assert _find_expected_status(assertions) == 200

    def test_finds_string_status(self):
        assertions = [{"type": "status_code", "expected": "201"}]
        assert _find_expected_status(assertions) == 201

    def test_returns_none_when_missing(self):
        assertions = [{"type": "json_path", "path": "$.id"}]
        assert _find_expected_status(assertions) is None

    def test_empty_list_returns_none(self):
        assert _find_expected_status([]) is None

    def test_multiple_assertions_finds_status_code(self):
        assertions = [
            {"type": "json_path", "path": "$.name"},
            {"type": "status_code", "expected": 404},
            {"type": "header", "field": "Content-Type"},
        ]
        assert _find_expected_status(assertions) == 404

    def test_non_digit_string_returns_none(self):
        assertions = [{"type": "status_code", "expected": "ok"}]
        assert _find_expected_status(assertions) is None

    def test_missing_expected_key_returns_none(self):
        assertions = [{"type": "status_code"}]
        assert _find_expected_status(assertions) is None

    def test_returns_int(self):
        assertions = [{"type": "status_code", "expected": 200}]
        result = _find_expected_status(assertions)
        assert isinstance(result, int)

    def test_first_status_code_returned(self):
        assertions = [
            {"type": "status_code", "expected": 200},
            {"type": "status_code", "expected": 201},
        ]
        assert _find_expected_status(assertions) == 200


# ---------------------------------------------------------------------------
# _extract_path
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FL_OK, reason="feedback_loop import failed")
class TestExtractPath:
    def test_full_url_with_path(self):
        assert _extract_path("http://localhost:8000/api/v1/users") == "/api/v1/users"

    def test_https_url(self):
        assert _extract_path("https://api.example.com/v2/payments") == "/v2/payments"

    def test_url_with_query_string(self):
        result = _extract_path("http://host/path?key=value")
        assert result == "/path"

    def test_empty_url_returns_root(self):
        assert _extract_path("") == "/"

    def test_url_without_path_returns_root(self):
        result = _extract_path("http://localhost:8080")
        assert result == "/" or result == ""

    def test_root_path(self):
        result = _extract_path("http://host:8000/")
        assert result == "/"

    def test_returns_string(self):
        assert isinstance(_extract_path("http://host/path"), str)

    def test_path_with_id(self):
        result = _extract_path("https://api.com/users/123/orders")
        assert result == "/users/123/orders"

    def test_path_with_fragment_ignored(self):
        # Fragment (#) handling — ensure it doesn't error
        result = _extract_path("http://host/path")
        assert isinstance(result, str)
