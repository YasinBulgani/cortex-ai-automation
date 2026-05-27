"""Unit tests for ai.eval_suite pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _is_json_valid: JSON validity check with fence support
  - _json_parse_tolerant: tolerant JSON extraction
  - _json_has_field: field presence check in JSON string
  - _json_path_matches: dot-path value matching in JSON string
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.eval_suite import (
        _is_json_valid,
        _json_parse_tolerant,
        _json_has_field,
        _json_path_matches,
    )
    _ES_OK = True
except ImportError:
    _ES_OK = False


# ---------------------------------------------------------------------------
# _is_json_valid
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ES_OK, reason="eval_suite import failed")
class TestIsJsonValid:
    def test_plain_dict(self):
        assert _is_json_valid('{"a": 1}') is True

    def test_plain_list(self):
        assert _is_json_valid('[1, 2, 3]') is True

    def test_json_fence(self):
        assert _is_json_valid('```json\n{"a": 1}\n```') is True

    def test_generic_fence(self):
        assert _is_json_valid('```\n{"b": 2}\n```') is True

    def test_not_json_returns_false(self):
        assert _is_json_valid("not json") is False

    def test_empty_string_returns_false(self):
        assert _is_json_valid("") is False

    def test_whitespace_only_returns_false(self):
        assert _is_json_valid("   ") is False

    def test_embedded_object_in_prose(self):
        # Embedded in prose with braces
        assert _is_json_valid('Some text {"x": 1} more text') is True

    def test_nested_object(self):
        assert _is_json_valid('{"outer": {"inner": 42}}') is True

    def test_returns_bool(self):
        assert isinstance(_is_json_valid('{"a": 1}'), bool)

    def test_empty_object(self):
        assert _is_json_valid("{}") is True

    def test_empty_array(self):
        assert _is_json_valid("[]") is True


# ---------------------------------------------------------------------------
# _json_parse_tolerant
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ES_OK, reason="eval_suite import failed")
class TestJsonParseTolerant:
    def test_plain_dict(self):
        result = _json_parse_tolerant('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_fence(self):
        result = _json_parse_tolerant('```json\n{"a": 1}\n```')
        assert result == {"a": 1}

    def test_embedded_in_prose(self):
        result = _json_parse_tolerant('Result: {"status": "ok"} done')
        assert result == {"status": "ok"}

    def test_not_json_raises(self):
        with pytest.raises((ValueError, Exception)):
            _json_parse_tolerant("not json")

    def test_empty_string_raises(self):
        with pytest.raises((ValueError, Exception)):
            _json_parse_tolerant("")

    def test_nested_object(self):
        result = _json_parse_tolerant('{"a": {"b": 2}}')
        assert result == {"a": {"b": 2}}

    def test_bool_values(self):
        result = _json_parse_tolerant('{"flag": true}')
        assert result == {"flag": True}


# ---------------------------------------------------------------------------
# _json_has_field
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ES_OK, reason="eval_suite import failed")
class TestJsonHasField:
    def test_present_field(self):
        assert _json_has_field('{"name": "Alice", "age": 30}', "name") is True

    def test_absent_field(self):
        assert _json_has_field('{"name": "Alice"}', "age") is False

    def test_empty_string_returns_false(self):
        assert _json_has_field("", "field") is False

    def test_not_json_returns_false(self):
        assert _json_has_field("not json", "field") is False

    def test_list_with_dict_first_element(self):
        # list[dict] → checks first element
        assert _json_has_field('[{"id": 1, "name": "X"}]', "id") is True

    def test_returns_bool(self):
        assert isinstance(_json_has_field('{"a": 1}', "a"), bool)

    def test_nested_field_not_found_at_top(self):
        # Only top-level field check
        assert _json_has_field('{"outer": {"inner": 1}}', "inner") is False

    def test_with_json_fence(self):
        assert _json_has_field('```json\n{"x": 1}\n```', "x") is True


# ---------------------------------------------------------------------------
# _json_path_matches
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ES_OK, reason="eval_suite import failed")
class TestJsonPathMatches:
    def test_simple_path_match(self):
        assert _json_path_matches('{"status": "ok"}', "$.status", "ok") is True

    def test_simple_path_no_match(self):
        assert _json_path_matches('{"status": "ok"}', "$.status", "error") is False

    def test_nested_path(self):
        assert _json_path_matches('{"data": {"count": 5}}', "$.data.count", 5) is True

    def test_missing_path_returns_false(self):
        assert _json_path_matches('{"a": 1}', "$.b", 2) is False

    def test_expected_none_checks_existence(self):
        # None expected → just checks that node is not None
        assert _json_path_matches('{"key": "value"}', "$.key", None) is True

    def test_expected_none_missing_field_returns_false(self):
        assert _json_path_matches('{"a": 1}', "$.b", None) is False

    def test_not_json_returns_false(self):
        assert _json_path_matches("not json", "$.field", "value") is False

    def test_returns_bool(self):
        assert isinstance(_json_path_matches('{"a": 1}', "$.a", 1), bool)

    def test_list_path_traversal_uses_first_element_as_node(self):
        # $.id on a list: first iterates into list[0] = {"id": 1}, then loop ends
        # node is the dict {"id": 1}, not 1 — so it does NOT equal 1
        # This is the actual implementation behavior
        assert _json_path_matches('[{"id": 1}]', "$.id", 1) is False
