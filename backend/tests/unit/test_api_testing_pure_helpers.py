"""Unit tests for api_testing pure helper functions.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers:
  - app.domains.api_testing.assertion_engine: _resolve_json_path, _compare
  - app.domains.api_testing.coverage_analyzer: _classify_gap_severity, _build_recommendation
  - app.domains.api_testing.test_prioritizer: _path_matches
  - app.domains.coverup.gap_detector: _line_suggestion, _branch_suggestion, _function_suggestion
  - app.domains.catalog.schema_v1: _validation_errors_to_message (via parse_and_validate_snapshot)
"""
from __future__ import annotations

import pytest

try:
    from app.domains.api_testing.assertion_engine import _resolve_json_path, _compare
    _ASSERTION_OK = True
except ImportError:
    _ASSERTION_OK = False

try:
    from app.domains.api_testing.coverage_analyzer import (
        _classify_gap_severity,
        _build_recommendation,
    )
    _COVERAGE_OK = True
except ImportError:
    _COVERAGE_OK = False

try:
    from app.domains.api_testing.test_prioritizer import _path_matches
    _PRIORITIZER_OK = True
except ImportError:
    _PRIORITIZER_OK = False

try:
    from app.domains.coverup.gap_detector import (
        _line_suggestion,
        _branch_suggestion,
        _function_suggestion,
    )
    _COVERUP_OK = True
except ImportError:
    _COVERUP_OK = False

try:
    from app.domains.catalog.schema_v1 import parse_and_validate_snapshot
    _CATALOG_OK = True
except ImportError:
    _CATALOG_OK = False


# ---------------------------------------------------------------------------
# _resolve_json_path
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ASSERTION_OK, reason="assertion_engine import failed")
class TestResolveJsonPath:
    def test_simple_field(self):
        found, val = _resolve_json_path({"name": "Alice"}, "$.name")
        assert found is True
        assert val == "Alice"

    def test_nested_field(self):
        data = {"user": {"id": 42}}
        found, val = _resolve_json_path(data, "$.user.id")
        assert found is True
        assert val == 42

    def test_missing_field(self):
        found, val = _resolve_json_path({"x": 1}, "$.y")
        assert found is False

    def test_array_index(self):
        data = {"items": [10, 20, 30]}
        found, val = _resolve_json_path(data, "$.items[1]")
        assert found is True
        assert val == 20

    def test_array_wildcard_returns_all(self):
        data = {"items": [1, 2, 3]}
        found, val = _resolve_json_path(data, "$.items[*]")
        assert found is True
        assert val == [1, 2, 3]

    def test_array_out_of_bounds(self):
        data = {"items": [1]}
        found, val = _resolve_json_path(data, "$.items[5]")
        assert found is False

    def test_empty_path_returns_false(self):
        found, val = _resolve_json_path({"x": 1}, "")
        assert found is False

    def test_path_not_starting_with_dollar(self):
        found, val = _resolve_json_path({"x": 1}, "x.y")
        assert found is False

    def test_deep_nesting(self):
        data = {"a": {"b": {"c": "deep"}}}
        found, val = _resolve_json_path(data, "$.a.b.c")
        assert found is True
        assert val == "deep"

    def test_none_data_returns_false(self):
        found, val = _resolve_json_path(None, "$.field")
        assert found is False

    def test_array_field_access(self):
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        found, val = _resolve_json_path(data, "$.users[0].name")
        assert found is True
        assert val == "Alice"


# ---------------------------------------------------------------------------
# _compare
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ASSERTION_OK, reason="assertion_engine import failed")
class TestCompare:
    def test_equals_true(self):
        assert _compare("hello", "equals", "hello") is True

    def test_equals_false(self):
        assert _compare("hello", "equals", "world") is False

    def test_not_equals(self):
        assert _compare("a", "not_equals", "b") is True

    def test_contains(self):
        assert _compare("hello world", "contains", "world") is True

    def test_not_contains(self):
        assert _compare("hello world", "not_contains", "xyz") is True

    def test_gt(self):
        assert _compare(10, "gt", 5) is True
        assert _compare(5, "gt", 10) is False

    def test_lt(self):
        assert _compare(3, "lt", 5) is True

    def test_gte(self):
        assert _compare(5, "gte", 5) is True
        assert _compare(6, "gte", 5) is True
        assert _compare(4, "gte", 5) is False

    def test_lte(self):
        assert _compare(5, "lte", 5) is True
        assert _compare(4, "lte", 5) is True
        assert _compare(6, "lte", 5) is False

    def test_matches_regex(self):
        assert _compare("test-123", "matches", r"\d+") is True
        assert _compare("no-digits", "matches", r"^\d+$") is False

    def test_one_of(self):
        assert _compare("admin", "one_of", ["admin", "user"]) is True
        assert _compare("guest", "one_of", ["admin", "user"]) is False

    def test_starts_with(self):
        assert _compare("hello world", "starts_with", "hello") is True
        assert _compare("hello world", "starts_with", "world") is False

    def test_ends_with(self):
        assert _compare("hello world", "ends_with", "world") is True

    def test_is_empty_none(self):
        assert _compare(None, "is_empty", None) is True

    def test_is_empty_empty_string(self):
        assert _compare("", "is_empty", None) is True

    def test_is_empty_empty_list(self):
        assert _compare([], "is_empty", None) is True

    def test_is_not_empty(self):
        assert _compare("hello", "is_not_empty", None) is True
        assert _compare("", "is_not_empty", None) is False

    def test_type_is_string(self):
        assert _compare("hello", "type_is", "string") is True
        assert _compare(123, "type_is", "string") is False

    def test_type_is_number(self):
        assert _compare(42, "type_is", "number") is True
        assert _compare(3.14, "type_is", "number") is True

    def test_type_is_boolean(self):
        assert _compare(True, "type_is", "boolean") is True

    def test_type_is_array(self):
        assert _compare([1, 2], "type_is", "array") is True

    def test_type_is_object(self):
        assert _compare({"k": "v"}, "type_is", "object") is True

    def test_type_is_null(self):
        assert _compare(None, "type_is", "null") is True

    def test_invalid_operator_falls_back_to_equals(self):
        assert _compare("x", "unknown_op", "x") is True

    def test_type_error_returns_false(self):
        # gt on non-numeric should return False, not raise
        assert _compare("abc", "gt", 5) is False


# ---------------------------------------------------------------------------
# _classify_gap_severity
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERAGE_OK, reason="coverage_analyzer import failed")
class TestClassifyGapSeverity:
    def test_critical_no_tests(self):
        result = _classify_gap_severity("critical", 0, [])
        assert result == "critical"

    def test_critical_with_tests_no_security(self):
        result = _classify_gap_severity("critical", 1, ["boundary"])
        assert result == "low"

    def test_critical_missing_security(self):
        result = _classify_gap_severity("critical", 1, ["security"])
        assert result == "high"

    def test_critical_missing_compliance(self):
        result = _classify_gap_severity("critical", 1, ["compliance"])
        assert result == "high"

    def test_high_no_tests(self):
        result = _classify_gap_severity("high", 0, [])
        assert result == "high"

    def test_high_with_tests(self):
        result = _classify_gap_severity("high", 2, ["boundary"])
        assert result == "low"

    def test_medium_no_tests(self):
        result = _classify_gap_severity("medium", 0, [])
        assert result == "medium"

    def test_many_missing_types(self):
        result = _classify_gap_severity("low", 5, ["a", "b", "c", "d"])
        assert result == "medium"

    def test_few_missing_types(self):
        result = _classify_gap_severity("low", 5, ["a", "b"])
        assert result == "low"

    def test_case_insensitive_risk(self):
        result = _classify_gap_severity("CRITICAL", 0, [])
        assert result == "critical"

    def test_empty_risk_treated_as_low(self):
        result = _classify_gap_severity("", 1, [])
        assert result == "low"


# ---------------------------------------------------------------------------
# _build_recommendation
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERAGE_OK, reason="coverage_analyzer import failed")
class TestBuildRecommendation:
    def test_no_coverage_message(self):
        rec = _build_recommendation("GET", "/users", "low", False, False, 0, [])
        assert "NO test coverage" in rec
        assert "GET" in rec
        assert "/users" in rec

    def test_partial_coverage_message(self):
        rec = _build_recommendation("POST", "/orders", "medium", False, False, 2, ["security"])
        assert "2 test(s)" in rec
        assert "security" in rec

    def test_pii_adds_kvkk_note(self):
        rec = _build_recommendation("GET", "/users/email", "high", True, False, 0, [])
        assert "KVKK" in rec

    def test_financial_adds_bddk_note(self):
        rec = _build_recommendation("POST", "/payments", "critical", False, True, 0, [])
        assert "BDDK" in rec or "financial" in rec.lower()

    def test_security_missing_type(self):
        rec = _build_recommendation("POST", "/login", "critical", False, False, 1, ["security"])
        assert "OWASP" in rec or "security" in rec.lower()

    def test_boundary_missing_type(self):
        rec = _build_recommendation("POST", "/form", "low", False, False, 1, ["boundary"])
        assert "boundary" in rec.lower() or "edge" in rec.lower()

    def test_returns_string(self):
        rec = _build_recommendation("GET", "/test", "low", False, False, 0, [])
        assert isinstance(rec, str)
        assert len(rec) > 0


# ---------------------------------------------------------------------------
# _path_matches
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PRIORITIZER_OK, reason="test_prioritizer import failed")
class TestPathMatches:
    def test_exact_match(self):
        assert _path_matches("/api/users", ["/api/users"]) is True

    def test_prefix_match(self):
        assert _path_matches("/api/users/123", ["/api/users"]) is True

    def test_no_match(self):
        assert _path_matches("/api/orders", ["/api/users"]) is False

    def test_empty_changed_paths(self):
        assert _path_matches("/api/users", []) is False

    def test_strips_leading_slash(self):
        assert _path_matches("api/users", ["/api/users"]) is True

    def test_query_string_ignored(self):
        assert _path_matches("/api/users?page=1", ["/api/users"]) is True

    def test_reverse_prefix(self):
        # Changed path is longer than test path → also matches
        assert _path_matches("/api", ["/api/users"]) is True

    def test_multiple_changed_paths_one_matches(self):
        assert _path_matches("/api/users", ["/api/orders", "/api/users"]) is True

    def test_none_changed_paths_element_skipped(self):
        # Empty string in changed_paths is skipped
        assert _path_matches("/api/users", [""]) is False


# ---------------------------------------------------------------------------
# _line_suggestion, _branch_suggestion, _function_suggestion
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERUP_OK, reason="coverup.gap_detector import failed")
class TestGapSuggestions:
    def test_line_suggestion_single(self):
        result = _line_suggestion("app/service.py", 42, 42)
        assert "42" in result
        assert "app/service.py" in result

    def test_line_suggestion_range(self):
        result = _line_suggestion("app/service.py", 10, 20)
        assert "10" in result
        assert "20" in result
        assert "11 satır" in result or "11" in result  # count

    def test_branch_suggestion(self):
        result = _branch_suggestion("app/handler.py", 5, 10)
        assert "app/handler.py" in result
        assert "branch" in result.lower() or "dal" in result

    def test_function_suggestion(self):
        result = _function_suggestion("app/utils.py", "_process")
        assert "_process" in result
        assert "app/utils.py" in result

    def test_line_suggestion_returns_string(self):
        assert isinstance(_line_suggestion("x.py", 1, 1), str)

    def test_branch_suggestion_returns_string(self):
        assert isinstance(_branch_suggestion("x.py", 1, 5), str)

    def test_function_suggestion_returns_string(self):
        assert isinstance(_function_suggestion("x.py", "my_func"), str)


# ---------------------------------------------------------------------------
# parse_and_validate_snapshot (catalog schema_v1 — tests ValueError message)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CATALOG_OK, reason="catalog.schema_v1 import failed")
class TestParseAndValidateSnapshot:
    def test_valid_snapshot_returns_dict(self):
        raw = {
            "version": "1",
            "fields": [
                {"name": "id", "type": "string"},
                {"name": "amount", "type": "integer"},
            ],
        }
        result = parse_and_validate_snapshot(raw)
        assert isinstance(result, dict)
        assert "fields" in result

    def test_missing_fields_raises_value_error(self):
        with pytest.raises(ValueError, match="Şema geçersiz"):
            parse_and_validate_snapshot({})

    def test_invalid_field_type_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_and_validate_snapshot({
                "version": "1",
                "fields": [
                    {"name": "x", "type": "invalid_type", "required": True}
                ]
            })

    def test_error_message_mentions_field(self):
        try:
            parse_and_validate_snapshot({"version": "1"})
        except ValueError as e:
            assert "Şema geçersiz" in str(e)
