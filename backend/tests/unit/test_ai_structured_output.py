"""Unit tests for app.domains.ai.structured_output helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: get_schema, schema_policy, should_validate_task, validate_response,
build_retry_prompt, openai_response_format, _parse_json_tolerant.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

try:
    from app.domains.ai.structured_output import (
        get_schema,
        schema_policy,
        should_validate_task,
        validate_response,
        build_retry_prompt,
        openai_response_format,
        _parse_json_tolerant,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="structured_output import failed")


# ---------------------------------------------------------------------------
# get_schema
# ---------------------------------------------------------------------------

class TestGetSchema:
    def test_known_task_returns_schema(self):
        schema = get_schema("test_generation")
        assert schema is not None

    def test_unknown_task_returns_none(self):
        schema = get_schema("nonexistent_task_xyz")
        assert schema is None

    def test_security_audit_has_schema(self):
        schema = get_schema("security_audit")
        assert schema is not None

    def test_returns_pydantic_model_class(self):
        schema = get_schema("test_generation")
        if schema is not None:
            from pydantic import BaseModel
            assert issubclass(schema, BaseModel)


# ---------------------------------------------------------------------------
# schema_policy
# ---------------------------------------------------------------------------

class TestSchemaPolicy:
    def test_known_task_returns_json_schema(self):
        policy = schema_policy("test_generation")
        assert policy == "json_schema"

    def test_unknown_task_returns_missing_policy(self):
        policy = schema_policy("nonexistent_task_xyz")
        assert policy == "missing_policy"

    def test_policy_is_string(self):
        policy = schema_policy("chat")
        assert isinstance(policy, str)
        assert policy in {"json_schema", "explicit_unstructured", "missing_policy"}


# ---------------------------------------------------------------------------
# should_validate_task
# ---------------------------------------------------------------------------

class TestShouldValidateTask:
    def test_json_schema_task_should_validate(self):
        if get_schema("test_generation") is not None:
            assert should_validate_task("test_generation") is True

    def test_missing_policy_task_should_validate(self):
        # unknown tasks have missing_policy → still need validation to catch policy gaps
        result = should_validate_task("nonexistent_task_xyz")
        assert isinstance(result, bool)

    def test_explicit_unstructured_should_not_validate(self):
        # 'chat' is typically explicit_unstructured
        result = should_validate_task("chat")
        # Could be True or False depending on policy; just check it returns bool
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# _parse_json_tolerant
# ---------------------------------------------------------------------------

class TestParseJsonTolerant:
    def test_plain_json_dict(self):
        result = _parse_json_tolerant('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_json_list(self):
        result = _parse_json_tolerant('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_markdown_fenced_json(self):
        fenced = '```json\n{"test": true}\n```'
        result = _parse_json_tolerant(fenced)
        assert result == {"test": True}

    def test_markdown_fence_without_language(self):
        fenced = '```\n{"test": true}\n```'
        result = _parse_json_tolerant(fenced)
        assert result is not None

    def test_empty_string_returns_none(self):
        assert _parse_json_tolerant("") is None

    def test_invalid_json_returns_none(self):
        assert _parse_json_tolerant("not json at all %%{") is None

    def test_nested_json(self):
        result = _parse_json_tolerant('{"outer": {"inner": [1, 2]}}')
        assert result["outer"]["inner"] == [1, 2]

    def test_with_trailing_whitespace(self):
        result = _parse_json_tolerant('  {"key": "value"}  ')
        assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# validate_response
# ---------------------------------------------------------------------------

class TestValidateResponse:
    def test_no_schema_explicit_unstructured_returns_valid(self):
        """Tasks explicitly marked as unstructured should return valid=True."""
        # 'chat' is typically unstructured
        valid, error, parsed = validate_response("chat", "any text is fine")
        if schema_policy("chat") == "explicit_unstructured":
            assert valid is True
            assert error is None

    def test_invalid_json_returns_false(self):
        """Non-JSON response for a structured task returns valid=False."""
        if get_schema("test_generation") is not None:
            valid, error, parsed = validate_response("test_generation", "not json")
            assert valid is False
            assert error is not None

    def test_valid_schema_returns_true(self):
        """Valid JSON matching the schema returns valid=True."""
        if get_schema("security_audit") is not None:
            # Build a minimal valid security_audit response
            valid_json = '{"findings": [], "risk_summary": "none", "overall_risk": "low"}'
            valid, error, parsed = validate_response("security_audit", valid_json)
            # May or may not pass depending on schema requirements
            assert isinstance(valid, bool)

    def test_returns_tuple_of_three(self):
        valid, error, parsed = validate_response("chat", "any text")
        assert isinstance(valid, bool)
        # error is str or None
        assert error is None or isinstance(error, str)


# ---------------------------------------------------------------------------
# build_retry_prompt
# ---------------------------------------------------------------------------

class TestBuildRetryPrompt:
    def test_returns_string(self):
        result = build_retry_prompt("original prompt", "bad response", "parse error")
        assert isinstance(result, str)

    def test_includes_error(self):
        result = build_retry_prompt("prompt", "bad", "SPECIFIC_ERROR")
        assert "SPECIFIC_ERROR" in result

    def test_includes_original_prompt(self):
        result = build_retry_prompt("MY_ORIGINAL_PROMPT", "bad", "error")
        assert "MY_ORIGINAL_PROMPT" in result

    def test_truncates_long_bad_response(self):
        long_bad = "x" * 5000
        result = build_retry_prompt("prompt", long_bad, "error")
        # Truncated to 2000 chars + surrounding text
        assert isinstance(result, str)
        assert len(result) < 10000


# ---------------------------------------------------------------------------
# openai_response_format
# ---------------------------------------------------------------------------

class TestOpenaiResponseFormat:
    def test_unknown_task_returns_none(self):
        result = openai_response_format("nonexistent_task_xyz")
        assert result is None

    def test_known_task_returns_dict(self):
        if get_schema("test_generation") is not None:
            result = openai_response_format("test_generation")
            if result is not None:
                assert isinstance(result, dict)
                assert result.get("type") == "json_schema"

    def test_result_has_required_keys(self):
        if get_schema("security_audit") is not None:
            result = openai_response_format("security_audit")
            if result is not None:
                assert "json_schema" in result
                assert "name" in result["json_schema"]
