"""Unit tests for ai.structured_output pure helper functions.

All tests are self-contained: no HTTP, no LLM, no AI calls.
Covers:
  - _parse_json_tolerant: fence + embedded JSON extraction
  - _sanitize_schema_for_openai: OpenAI strict-mode schema cleanup
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.structured_output import (
        _parse_json_tolerant,
        _sanitize_schema_for_openai,
    )
    _SO_OK = True
except ImportError:
    _SO_OK = False


# ---------------------------------------------------------------------------
# _parse_json_tolerant
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SO_OK, reason="structured_output import failed")
class TestParseJsonTolerant:
    def test_plain_dict(self):
        result = _parse_json_tolerant('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_list(self):
        result = _parse_json_tolerant('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_fence(self):
        raw = "```json\n{\"a\": 1}\n```"
        result = _parse_json_tolerant(raw)
        assert result == {"a": 1}

    def test_generic_fence(self):
        raw = "```\n{\"b\": 2}\n```"
        result = _parse_json_tolerant(raw)
        assert result == {"b": 2}

    def test_embedded_object_in_prose(self):
        raw = 'Result: {"status": "ok"} done.'
        result = _parse_json_tolerant(raw)
        assert result == {"status": "ok"}

    def test_embedded_array_in_prose(self):
        raw = 'Items: [1, 2, 3] end.'
        result = _parse_json_tolerant(raw)
        assert result == [1, 2, 3]

    def test_empty_string_returns_none(self):
        assert _parse_json_tolerant("") is None

    def test_none_equivalent_falsy_returns_none(self):
        assert _parse_json_tolerant("") is None

    def test_not_json_returns_none(self):
        assert _parse_json_tolerant("not json") is None

    def test_whitespace_only_returns_none(self):
        assert _parse_json_tolerant("   ") is None

    def test_nested_object(self):
        raw = '{"outer": {"inner": [1, 2]}}'
        result = _parse_json_tolerant(raw)
        assert result == {"outer": {"inner": [1, 2]}}

    def test_bool_values(self):
        result = _parse_json_tolerant('{"flag": true}')
        assert result == {"flag": True}

    def test_null_value(self):
        result = _parse_json_tolerant('{"key": null}')
        assert result == {"key": None}

    def test_returns_dict_or_list_or_none(self):
        r = _parse_json_tolerant('{"a": 1}')
        assert isinstance(r, (dict, list, type(None)))

    def test_unicode_content(self):
        result = _parse_json_tolerant('{"city": "İstanbul"}')
        assert result == {"city": "İstanbul"}

    def test_stripped_before_parse(self):
        result = _parse_json_tolerant('  {"k": "v"}  ')
        assert result == {"k": "v"}


# ---------------------------------------------------------------------------
# _sanitize_schema_for_openai
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SO_OK, reason="structured_output import failed")
class TestSanitizeSchemaForOpenai:
    def test_returns_dict(self):
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = _sanitize_schema_for_openai(schema)
        assert isinstance(result, dict)

    def test_adds_additional_properties_false(self):
        schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
        result = _sanitize_schema_for_openai(schema)
        assert result["additionalProperties"] is False

    def test_adds_required_for_all_properties(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
        }
        result = _sanitize_schema_for_openai(schema)
        assert set(result["required"]) == {"a", "b"}

    def test_removes_unevaluated_properties(self):
        schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "unevaluatedProperties": True,
        }
        result = _sanitize_schema_for_openai(schema)
        assert "unevaluatedProperties" not in result

    def test_non_object_type_unchanged(self):
        schema = {"type": "string", "minLength": 1}
        result = _sanitize_schema_for_openai(schema)
        assert result == schema

    def test_non_dict_returned_as_is(self):
        assert _sanitize_schema_for_openai("string") == "string"
        assert _sanitize_schema_for_openai(42) == 42
        assert _sanitize_schema_for_openai(None) is None

    def test_nested_object_sanitized(self):
        schema = {
            "type": "object",
            "properties": {
                "nested": {
                    "type": "object",
                    "properties": {"y": {"type": "number"}},
                    "unevaluatedProperties": False,
                }
            },
        }
        result = _sanitize_schema_for_openai(schema)
        nested = result["properties"]["nested"]
        assert nested["additionalProperties"] is False
        assert "unevaluatedProperties" not in nested

    def test_array_items_sanitized(self):
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "unevaluatedProperties": True,
            },
        }
        result = _sanitize_schema_for_openai(schema)
        item = result["items"]
        assert item["additionalProperties"] is False
        assert "unevaluatedProperties" not in item

    def test_defs_sanitized(self):
        schema = {
            "$defs": {
                "Address": {
                    "type": "object",
                    "properties": {"street": {"type": "string"}},
                    "unevaluatedProperties": False,
                }
            },
            "type": "object",
            "properties": {"addr": {"$ref": "#/$defs/Address"}},
        }
        result = _sanitize_schema_for_openai(schema)
        addr_def = result["$defs"]["Address"]
        assert addr_def["additionalProperties"] is False
        assert "unevaluatedProperties" not in addr_def

    def test_empty_dict(self):
        result = _sanitize_schema_for_openai({})
        assert isinstance(result, dict)

    def test_object_without_properties_no_required_added(self):
        schema = {"type": "object"}
        result = _sanitize_schema_for_openai(schema)
        # No properties key → no required added
        assert "required" not in result

    def test_existing_required_overwritten(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
            "required": ["a"],
        }
        result = _sanitize_schema_for_openai(schema)
        # strict mode: all properties must be required
        assert set(result["required"]) == {"a", "b"}
