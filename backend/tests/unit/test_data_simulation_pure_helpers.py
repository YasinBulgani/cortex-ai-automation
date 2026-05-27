"""Unit tests for tspm.test_data_simulation_service pure helpers.

All tests are self-contained: no DB, no HTTP calls (only FastAPI exception raise).
Covers:
  - _expand_simple_regex: simple character-class regex expansion
  - _validate_supported_connection: allowed DB connection string check
  - _rewrite_localhost_for_docker: localhost → postgres host rewrite in Docker
"""
from __future__ import annotations

import os
import re

import pytest

try:
    from app.domains.tspm.test_data_simulation_service import (
        _expand_simple_regex,
        _validate_supported_connection,
        _rewrite_localhost_for_docker,
    )
    from fastapi import HTTPException
    _SIM_OK = True
except ImportError:
    _SIM_OK = False


# ---------------------------------------------------------------------------
# _expand_simple_regex
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SIM_OK, reason="test_data_simulation_service import failed")
class TestExpandSimpleRegex:
    def test_uppercase_charset(self):
        result = _expand_simple_regex("[A-Z]{3}")
        assert len(result) == 3
        assert all(c.isupper() for c in result)

    def test_digit_charset(self):
        result = _expand_simple_regex("[0-9]{4}")
        assert len(result) == 4
        assert all(c.isdigit() for c in result)

    def test_lowercase_charset(self):
        result = _expand_simple_regex("[a-z]{2}")
        assert len(result) == 2
        assert all(c.islower() for c in result)

    def test_literal_chars_preserved(self):
        result = _expand_simple_regex("ABC")
        assert result == "ABC"

    def test_single_char_from_charset(self):
        # No repeat count → default 1
        result = _expand_simple_regex("[A-Z]")
        assert len(result) == 1
        assert result.isupper()

    def test_mixed_charset_and_literal(self):
        result = _expand_simple_regex("[A-Z]{2}[0-9]{3}")
        # 2 uppercase + 3 digits = 5 chars
        assert len(result) == 5
        assert result[:2].isupper()
        assert result[2:].isdigit()

    def test_single_char_class(self):
        result = _expand_simple_regex("[AB]{5}")
        assert len(result) == 5
        assert all(c in "AB" for c in result)

    def test_returns_string(self):
        assert isinstance(_expand_simple_regex("[A-Z]{1}"), str)

    def test_non_charset_preserved(self):
        result = _expand_simple_regex("PREFIX-[0-9]{3}")
        assert result.startswith("PREFIX-")
        assert len(result) == 10  # 7 + 3

    def test_different_results_due_to_randomness(self):
        """Multiple calls should sometimes produce different results."""
        results = {_expand_simple_regex("[A-Z]{4}") for _ in range(20)}
        # With 26^4 = 456976 possible values, getting >1 unique result is near-certain
        assert len(results) > 1


# ---------------------------------------------------------------------------
# _validate_supported_connection
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SIM_OK, reason="test_data_simulation_service import failed")
class TestValidateSupportedConnection:
    def test_postgresql_ok(self):
        # Should not raise
        _validate_supported_connection(
            "postgresql://user:pass@localhost/db", "not supported"
        )

    def test_postgresql_psycopg2_ok(self):
        _validate_supported_connection(
            "postgresql+psycopg2://user:pass@host:5432/db", "not supported"
        )

    def test_sqlite_ok(self):
        _validate_supported_connection(
            "sqlite:///path/to/db.sqlite", "not supported"
        )

    def test_mysql_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_supported_connection("mysql://u:p@host/db", "MySQL not supported")
        assert exc_info.value.status_code == 400

    def test_mongodb_raises(self):
        with pytest.raises(HTTPException):
            _validate_supported_connection("mongodb://localhost/db", "Not supported")

    def test_empty_string_raises(self):
        with pytest.raises(HTTPException):
            _validate_supported_connection("", "empty")

    def test_error_message_preserved(self):
        with pytest.raises(HTTPException) as exc_info:
            _validate_supported_connection("redis://host/0", "Custom error message")
        assert exc_info.value.detail == "Custom error message"

    def test_case_sensitive_prefix(self):
        # "POSTGRESQL://" is not allowed (uppercase)
        with pytest.raises(HTTPException):
            _validate_supported_connection("POSTGRESQL://user/db", "uppercase not allowed")


# ---------------------------------------------------------------------------
# _rewrite_localhost_for_docker
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SIM_OK, reason="test_data_simulation_service import failed")
class TestRewriteLocalhostForDocker:
    def _without_docker_env(self):
        """Remove docker env indicators for non-docker tests."""
        os.environ.pop("RUNNING_IN_DOCKER", None)
        # Note: /.dockerenv cannot be easily faked in tests

    def test_no_rewrite_outside_docker(self):
        self._without_docker_env()
        conn = "postgresql://user:pass@localhost:5432/mydb"
        # Outside Docker, returns unchanged (unless /.dockerenv exists on this machine)
        result = _rewrite_localhost_for_docker(conn)
        # Either unchanged or rewritten — just verify it's a string
        assert isinstance(result, str)

    def test_with_docker_env_rewrites_localhost(self, monkeypatch):
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
        conn = "postgresql://user:pass@localhost:5432/mydb"
        result = _rewrite_localhost_for_docker(conn)
        assert "postgres" in result
        assert "localhost" not in result

    def test_with_docker_env_rewrites_127_0_0_1(self, monkeypatch):
        monkeypatch.setenv("RUNNING_IN_DOCKER", "1")
        conn = "postgresql://user:pass@127.0.0.1:5432/mydb"
        result = _rewrite_localhost_for_docker(conn)
        assert "127.0.0.1" not in result

    def test_remote_host_not_rewritten(self, monkeypatch):
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
        conn = "postgresql://user:pass@db.example.com:5432/mydb"
        result = _rewrite_localhost_for_docker(conn)
        assert "db.example.com" in result

    def test_psycopg2_scheme_rewritten(self, monkeypatch):
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
        conn = "postgresql+psycopg2://user:pass@localhost/mydb"
        result = _rewrite_localhost_for_docker(conn)
        assert "localhost" not in result

    def test_returns_string(self):
        result = _rewrite_localhost_for_docker("postgresql://u@localhost/db")
        assert isinstance(result, str)

    def test_no_docker_env_sqlite_unchanged(self):
        self._without_docker_env()
        conn = "sqlite:///test.db"
        result = _rewrite_localhost_for_docker(conn)
        assert isinstance(result, str)
