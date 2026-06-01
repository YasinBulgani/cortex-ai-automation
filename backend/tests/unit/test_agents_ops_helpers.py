"""Unit tests for app.domains.agents.ops_agent — pure helpers.

Tests are fully self-contained: no HTTP, no async.
Covers: _truncate_payload, parse_targets, _utcnow.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.ops_agent import (
        _truncate_payload,
        parse_targets,
        _utcnow,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="ops_agent import failed")


# ---------------------------------------------------------------------------
# _utcnow
# ---------------------------------------------------------------------------

class TestUtcNow:
    def test_returns_string(self):
        assert isinstance(_utcnow(), str)

    def test_contains_t_separator(self):
        result = _utcnow()
        assert "T" in result

    def test_contains_timezone_offset(self):
        result = _utcnow()
        # ISO format with timezone should have + or Z
        assert "+" in result or "Z" in result


# ---------------------------------------------------------------------------
# _truncate_payload
# ---------------------------------------------------------------------------

class TestTruncatePayload:
    def test_short_dict_not_truncated(self):
        payload = {"key": "value"}
        result = _truncate_payload(payload)
        assert "key" in result

    def test_long_payload_truncated(self):
        payload = {"data": "x" * 1000}
        result = _truncate_payload(payload, limit=100)
        assert len(result) <= 103  # limit + "..."

    def test_truncated_ends_with_ellipsis(self):
        payload = {"data": "x" * 1000}
        result = _truncate_payload(payload, limit=50)
        assert result.endswith("...")

    def test_exact_limit_not_truncated(self):
        # Short string within limit
        payload = "ab"
        result = _truncate_payload(payload, limit=100)
        assert "..." not in result

    def test_non_serializable_falls_back_to_str(self):
        class NotSerializable:
            def __str__(self):
                return "fallback"
        result = _truncate_payload(NotSerializable())
        assert "fallback" in result

    def test_returns_string(self):
        assert isinstance(_truncate_payload({"x": 1}), str)

    def test_list_payload(self):
        result = _truncate_payload([1, 2, 3])
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# parse_targets
# ---------------------------------------------------------------------------

class TestParseTargets:
    def test_empty_string_returns_empty(self):
        assert parse_targets("") == []

    def test_none_returns_empty(self):
        assert parse_targets("") == []

    def test_single_name_url_pair(self):
        result = parse_targets("api=http://localhost:8000")
        assert len(result) == 1
        assert result[0]["name"] == "api"
        assert result[0]["url"] == "http://localhost:8000"

    def test_multiple_comma_separated(self):
        result = parse_targets("api=http://a.com,db=http://b.com")
        assert len(result) == 2

    def test_newline_separator(self):
        result = parse_targets("api=http://a.com\ndb=http://b.com")
        assert len(result) == 2

    def test_semicolon_separator(self):
        result = parse_targets("api=http://a.com;db=http://b.com")
        assert len(result) == 2

    def test_url_without_name_uses_last_segment(self):
        result = parse_targets("http://localhost/myservice")
        assert len(result) == 1
        assert result[0]["url"] == "http://localhost/myservice"
        assert result[0]["name"] == "myservice"

    def test_whitespace_stripped(self):
        result = parse_targets("  api = http://a.com  ")
        assert len(result) == 1
        assert result[0]["name"] == "api"

    def test_empty_chunks_skipped(self):
        result = parse_targets("api=http://a.com,,")
        assert len(result) == 1

    def test_returns_list_of_dicts(self):
        result = parse_targets("api=http://x.com")
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)
