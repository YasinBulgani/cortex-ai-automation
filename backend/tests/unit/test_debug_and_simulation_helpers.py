"""Unit tests for AI debug service and data simulation pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/tspm/ai_debug_service.py:
    _parse_debug_response, _default_fix_steps, _default_recommended_actions
  app/domains/tspm/test_data_simulation_service.py:
    _validate_supported_connection, _rewrite_localhost_for_docker,
    _expand_simple_regex
"""

from __future__ import annotations

import json

import pytest

from app.domains.tspm.ai_debug_service import (
    _default_fix_steps,
    _default_recommended_actions,
    _parse_debug_response,
)
from app.domains.tspm.test_data_simulation_service import (
    _expand_simple_regex,
    _rewrite_localhost_for_docker,
    _validate_supported_connection,
)


# ── _parse_debug_response ─────────────────────────────────────────────────────


class TestParseDebugResponse:
    def test_valid_json_object(self) -> None:
        raw = json.dumps({
            "analyses": [{"test_id": "t1"}],
            "overall_health": "healthy",
            "key_patterns": ["pattern1"],
            "recommended_actions": ["action1"],
        })
        result = _parse_debug_response(raw)
        assert result["overall_health"] == "healthy"
        assert result["analyses"] == [{"test_id": "t1"}]

    def test_json_in_code_fence(self) -> None:
        data = {"overall_health": "at_risk", "analyses": [], "key_patterns": [], "recommended_actions": []}
        raw = f"```json\n{json.dumps(data)}\n```"
        result = _parse_debug_response(raw)
        assert result["overall_health"] == "at_risk"

    def test_missing_fields_use_defaults(self) -> None:
        raw = json.dumps({"analyses": []})
        result = _parse_debug_response(raw)
        assert result["overall_health"] == "at_risk"  # default
        assert result["key_patterns"] == []
        assert result["recommended_actions"] == []

    def test_embedded_json_extracted(self) -> None:
        # JSON embedded in surrounding text
        data = {"analyses": [], "overall_health": "healthy", "key_patterns": [], "recommended_actions": []}
        raw = f"Analysis result: {json.dumps(data)} end of response"
        result = _parse_debug_response(raw)
        assert result["overall_health"] == "healthy"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises((ValueError, json.JSONDecodeError, Exception)):
            _parse_debug_response("completely invalid text without json")

    def test_returns_dict(self) -> None:
        raw = json.dumps({"overall_health": "critical"})
        result = _parse_debug_response(raw)
        assert isinstance(result, dict)

    def test_required_keys_present(self) -> None:
        raw = json.dumps({"overall_health": "healthy"})
        result = _parse_debug_response(raw)
        assert "analyses" in result
        assert "overall_health" in result
        assert "key_patterns" in result
        assert "recommended_actions" in result


# ── _default_fix_steps ────────────────────────────────────────────────────────


class TestDefaultFixSteps:
    def test_product_bug_functional_steps(self) -> None:
        steps = _default_fix_steps("PRODUCT_BUG", "functional")
        assert isinstance(steps, list)
        assert len(steps) >= 1
        assert any("hata" in s.lower() or "bug" in s.lower() or "stack" in s.lower() for s in steps)

    def test_test_issue_stale_locator_steps(self) -> None:
        steps = _default_fix_steps("TEST_ISSUE", "stale_locator")
        assert isinstance(steps, list)
        assert any("selector" in s.lower() or "locator" in s.lower() for s in steps)

    def test_test_issue_timing_steps(self) -> None:
        steps = _default_fix_steps("TEST_ISSUE", "timing")
        assert isinstance(steps, list)
        assert any("bekle" in s.lower() or "wait" in s.lower() or "timeout" in s.lower() for s in steps)

    def test_environment_infra_down_steps(self) -> None:
        steps = _default_fix_steps("ENVIRONMENT", "infra_down")
        assert len(steps) >= 1
        assert any("servis" in s.lower() or "log" in s.lower() for s in steps)

    def test_flaky_timing_steps(self) -> None:
        steps = _default_fix_steps("FLAKY", "timing")
        assert isinstance(steps, list)
        assert len(steps) >= 1

    def test_race_condition_concurrent_write(self) -> None:
        steps = _default_fix_steps("RACE_CONDITION", "concurrent_write")
        assert any("lock" in s.lower() or "transaction" in s.lower() for s in steps)

    def test_unknown_category_returns_default(self) -> None:
        steps = _default_fix_steps("UNKNOWN_XYZ", "unknown_sub")
        assert isinstance(steps, list)
        assert len(steps) == 3  # default has 3 items

    def test_returns_list(self) -> None:
        result = _default_fix_steps("FLAKY", "async")
        assert isinstance(result, list)


# ── _default_recommended_actions ─────────────────────────────────────────────


class TestDefaultRecommendedActions:
    def test_empty_categories_returns_empty_or_minimal(self) -> None:
        result = _default_recommended_actions({})
        assert isinstance(result, list)

    def test_product_bug_triggers_action(self) -> None:
        result = _default_recommended_actions({"PRODUCT_BUG": 2})
        assert any("product_bug" in a.lower() or "jira" in a.lower() or "2" in a for a in result)

    def test_test_issue_triggers_action(self) -> None:
        result = _default_recommended_actions({"TEST_ISSUE": 3})
        assert any("test" in a.lower() for a in result)

    def test_environment_triggers_action(self) -> None:
        result = _default_recommended_actions({"ENVIRONMENT": 1})
        assert any("ortam" in a.lower() or "servis" in a.lower() or "environment" in a.lower() for a in result)

    def test_flaky_triggers_action(self) -> None:
        result = _default_recommended_actions({"FLAKY": 4})
        assert any("flaky" in a.lower() or "retry" in a.lower() for a in result)

    def test_multiple_categories(self) -> None:
        cats = {"PRODUCT_BUG": 1, "TEST_ISSUE": 2, "FLAKY": 1}
        result = _default_recommended_actions(cats)
        assert len(result) >= 2  # at least one action per category

    def test_returns_list(self) -> None:
        result = _default_recommended_actions({"PRODUCT_BUG": 1})
        assert isinstance(result, list)


# ── _validate_supported_connection ────────────────────────────────────────────


class TestValidateSupportedConnection:
    def test_postgresql_url_passes(self) -> None:
        # Should not raise
        _validate_supported_connection("postgresql://user:pass@localhost/db", "error msg")

    def test_postgresql_psycopg2_url_passes(self) -> None:
        _validate_supported_connection("postgresql+psycopg2://user:pass@localhost/db", "error msg")

    def test_sqlite_url_passes(self) -> None:
        _validate_supported_connection("sqlite:///path/to/db.sqlite", "error msg")

    def test_mysql_url_raises(self) -> None:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_supported_connection("mysql://user:pass@localhost/db", "unsupported")
        assert exc_info.value.status_code == 400

    def test_mongodb_url_raises(self) -> None:
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _validate_supported_connection("mongodb://localhost/db", "unsupported")

    def test_empty_string_raises(self) -> None:
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            _validate_supported_connection("", "empty connection")

    def test_error_message_passed_to_exception(self) -> None:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_supported_connection("redis://localhost", "custom error message")
        assert "custom error message" in str(exc_info.value.detail)


# ── _rewrite_localhost_for_docker ─────────────────────────────────────────────


class TestRewriteLocalhostForDocker:
    def test_non_docker_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Outside Docker, URL should be unchanged."""
        monkeypatch.delenv("RUNNING_IN_DOCKER", raising=False)
        conn = "postgresql://user:pass@localhost:5432/db"
        result = _rewrite_localhost_for_docker(conn)
        assert result == conn

    def test_docker_env_rewrites_localhost(self, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
        """Inside Docker, localhost → postgres."""
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
        conn = "postgresql://user:pass@localhost:5432/db"
        result = _rewrite_localhost_for_docker(conn)
        assert "postgres" in result
        assert "localhost" not in result

    def test_non_localhost_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
        conn = "postgresql://user:pass@db.example.com:5432/mydb"
        result = _rewrite_localhost_for_docker(conn)
        # remote host → unchanged
        assert "db.example.com" in result

    def test_127_0_0_1_also_rewritten(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
        conn = "postgresql://user:pass@127.0.0.1:5432/db"
        result = _rewrite_localhost_for_docker(conn)
        assert "127.0.0.1" not in result


# ── _expand_simple_regex ──────────────────────────────────────────────────────


class TestExpandSimpleRegex:
    def test_literal_string_unchanged(self) -> None:
        # No special regex chars → returned as-is
        result = _expand_simple_regex("hello")
        assert result == "hello"

    def test_charset_produces_single_char(self) -> None:
        # [abc] → one of a, b, c
        result = _expand_simple_regex("[abc]")
        assert result in ("a", "b", "c")

    def test_charset_with_repeat(self) -> None:
        # [0-9]{5} → 5 digit string
        result = _expand_simple_regex("[0-9]{5}")
        assert len(result) == 5
        assert result.isdigit()

    def test_alpha_range_charset(self) -> None:
        # [a-z] → single lowercase letter
        result = _expand_simple_regex("[a-z]")
        assert len(result) == 1
        assert result.islower()

    def test_escape_sequence(self) -> None:
        # \- → literal hyphen
        result = _expand_simple_regex("\\-")
        assert result == "-"

    def test_mixed_pattern(self) -> None:
        # "TR[0-9]{2}" → "TR" + 2 digits
        result = _expand_simple_regex("TR[0-9]{2}")
        assert result.startswith("TR")
        assert len(result) == 4
        assert result[2:].isdigit()

    def test_empty_string(self) -> None:
        assert _expand_simple_regex("") == ""

    def test_repeat_produces_correct_length(self) -> None:
        result = _expand_simple_regex("[A-Z]{3}")
        assert len(result) == 3
        assert result.isupper()
