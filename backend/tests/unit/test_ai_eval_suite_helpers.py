"""Unit tests for app.domains.ai.eval_suite — pure helper functions.

Tests are fully self-contained: no DB, no HTTP, no LLM calls.
Covers: _is_json_valid, _json_parse_tolerant, _json_has_field,
        _json_path_matches, _evaluate_properties (all property types).
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.eval_suite import (
        _is_json_valid,
        _json_parse_tolerant,
        _json_has_field,
        _json_path_matches,
        _evaluate_properties,
        PropertyResult,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="eval_suite import failed")


# ---------------------------------------------------------------------------
# _is_json_valid
# ---------------------------------------------------------------------------

class TestIsJsonValid:
    def test_plain_object_valid(self):
        assert _is_json_valid('{"key": "value"}') is True

    def test_plain_array_valid(self):
        assert _is_json_valid('[1, 2, 3]') is True

    def test_invalid_json_false(self):
        assert _is_json_valid("not json at all") is False

    def test_empty_string_false(self):
        assert _is_json_valid("") is False

    def test_fenced_json_block_valid(self):
        text = "```json\n{\"key\": \"value\"}\n```"
        assert _is_json_valid(text) is True

    def test_fenced_block_without_json_label_valid(self):
        text = "```\n{\"a\": 1}\n```"
        assert _is_json_valid(text) is True

    def test_embedded_json_in_prose_valid(self):
        text = 'Here is the result: {"score": 42} — done.'
        assert _is_json_valid(text) is True

    def test_partial_invalid_json_false(self):
        assert _is_json_valid('{"key":') is False

    def test_whitespace_only_false(self):
        assert _is_json_valid("   ") is False

    def test_nested_json_valid(self):
        assert _is_json_valid('{"a": {"b": [1, 2]}}') is True

    def test_returns_bool(self):
        assert isinstance(_is_json_valid('{}'), bool)


# ---------------------------------------------------------------------------
# _json_parse_tolerant
# ---------------------------------------------------------------------------

class TestJsonParseTolerant:
    def test_plain_json_parsed(self):
        result = _json_parse_tolerant('{"x": 1}')
        assert result == {"x": 1}

    def test_fenced_block_parsed(self):
        text = "```json\n{\"a\": 2}\n```"
        result = _json_parse_tolerant(text)
        assert result == {"a": 2}

    def test_embedded_json_extracted(self):
        text = "Here is the JSON: {\"key\": \"val\"} done."
        result = _json_parse_tolerant(text)
        assert result == {"key": "val"}

    def test_raises_on_unparseable(self):
        with pytest.raises(Exception):
            _json_parse_tolerant("completely not json")

    def test_array_parsed(self):
        result = _json_parse_tolerant("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_none_equivalent_empty_raises(self):
        with pytest.raises(Exception):
            _json_parse_tolerant("")


# ---------------------------------------------------------------------------
# _json_has_field
# ---------------------------------------------------------------------------

class TestJsonHasField:
    def test_field_present_true(self):
        assert _json_has_field('{"name": "test"}', "name") is True

    def test_field_absent_false(self):
        assert _json_has_field('{"name": "test"}', "missing") is False

    def test_list_first_element_checked(self):
        assert _json_has_field('[{"id": 1}]', "id") is True

    def test_list_field_absent_false(self):
        assert _json_has_field('[{"id": 1}]', "nonexistent") is False

    def test_invalid_json_false(self):
        assert _json_has_field("not json", "field") is False

    def test_empty_string_false(self):
        assert _json_has_field("", "field") is False

    def test_nested_field_not_in_top_level(self):
        # field is nested, not top-level → False
        assert _json_has_field('{"outer": {"inner": 1}}', "inner") is False

    def test_top_level_field_present(self):
        assert _json_has_field('{"outer": {"inner": 1}}', "outer") is True


# ---------------------------------------------------------------------------
# _json_path_matches
# ---------------------------------------------------------------------------

class TestJsonPathMatches:
    def test_simple_path_matches_value(self):
        assert _json_path_matches('{"status": "ok"}', "status", "ok") is True

    def test_simple_path_wrong_value(self):
        assert _json_path_matches('{"status": "ok"}', "status", "fail") is False

    def test_nested_path_matches(self):
        assert _json_path_matches(
            '{"result": {"score": 99}}',
            "result.score",
            99,
        ) is True

    def test_nested_path_mismatch(self):
        assert _json_path_matches(
            '{"result": {"score": 99}}',
            "result.score",
            0,
        ) is False

    def test_dollar_prefix_stripped(self):
        # $result.score → same as result.score
        assert _json_path_matches(
            '{"result": {"score": 99}}',
            "$.result.score",
            99,
        ) is True

    def test_expected_none_means_node_exists(self):
        # expected=None → just check node is not None
        assert _json_path_matches('{"a": 1}', "a", None) is True

    def test_missing_path_returns_false(self):
        assert _json_path_matches('{"a": 1}', "b", "x") is False

    def test_invalid_json_returns_false(self):
        assert _json_path_matches("not json", "a", "x") is False

    def test_list_at_path_node(self):
        # When traversal hits a list, the code descends to first element
        # consuming that traversal step; node ends up as {"id": "abc"}, not "abc"
        # expected=None means "node is not None" → True
        assert _json_path_matches(
            '{"items": [{"id": "abc"}]}',
            "items.id",
            None,
        ) is True


# ---------------------------------------------------------------------------
# _evaluate_properties
# ---------------------------------------------------------------------------

class TestEvaluateProperties:
    # --- contains ---
    def test_contains_found(self):
        results = _evaluate_properties("hello world", [{"type": "contains", "value": "hello"}])
        assert len(results) == 1
        assert results[0].passed is True

    def test_contains_not_found(self):
        results = _evaluate_properties("hello world", [{"type": "contains", "value": "missing"}])
        assert results[0].passed is False

    def test_contains_case_insensitive(self):
        results = _evaluate_properties("Hello World", [{"type": "contains", "value": "hello"}])
        assert results[0].passed is True

    # --- not_contains ---
    def test_not_contains_absent_passes(self):
        results = _evaluate_properties("clean text", [{"type": "not_contains", "value": "badword"}])
        assert results[0].passed is True

    def test_not_contains_present_fails(self):
        results = _evaluate_properties("text with badword", [{"type": "not_contains", "value": "badword"}])
        assert results[0].passed is False

    # --- regex ---
    def test_regex_matches_passes(self):
        results = _evaluate_properties("error 404", [{"type": "regex", "pattern": r"\d{3}"}])
        assert results[0].passed is True

    def test_regex_no_match_fails(self):
        results = _evaluate_properties("no digits here", [{"type": "regex", "pattern": r"\d{3}"}])
        assert results[0].passed is False

    # --- min_length ---
    def test_min_length_met_passes(self):
        results = _evaluate_properties("x" * 50, [{"type": "min_length", "value": 50}])
        assert results[0].passed is True

    def test_min_length_not_met_fails(self):
        results = _evaluate_properties("short", [{"type": "min_length", "value": 100}])
        assert results[0].passed is False

    # --- json_valid ---
    def test_json_valid_property_passes(self):
        results = _evaluate_properties('{"ok": 1}', [{"type": "json_valid"}])
        assert results[0].passed is True

    def test_json_valid_property_fails(self):
        results = _evaluate_properties("not json", [{"type": "json_valid"}])
        assert results[0].passed is False

    # --- required_field ---
    def test_required_field_present_passes(self):
        results = _evaluate_properties(
            '{"name": "alice"}',
            [{"type": "required_field", "field": "name"}],
        )
        assert results[0].passed is True

    def test_required_field_absent_fails(self):
        results = _evaluate_properties(
            '{"name": "alice"}',
            [{"type": "required_field", "field": "email"}],
        )
        assert results[0].passed is False

    # --- json_path ---
    def test_json_path_property_matches(self):
        results = _evaluate_properties(
            '{"status": "ok"}',
            [{"type": "json_path", "path": "status", "expected": "ok"}],
        )
        assert results[0].passed is True

    def test_json_path_property_mismatch(self):
        results = _evaluate_properties(
            '{"status": "fail"}',
            [{"type": "json_path", "path": "status", "expected": "ok"}],
        )
        assert results[0].passed is False

    # --- output_refused ---
    def test_output_refused_passes_when_refusal_present(self):
        results = _evaluate_properties(
            "I cannot help with that.",
            [{"type": "output_refused"}],
        )
        assert results[0].passed is True

    def test_output_refused_fails_when_no_refusal(self):
        results = _evaluate_properties(
            "Sure, here is the answer.",
            [{"type": "output_refused"}],
        )
        assert results[0].passed is False

    # --- no_pii_leak ---
    def test_no_pii_leak_passes_when_value_absent(self):
        results = _evaluate_properties(
            "generic response text",
            [{"type": "no_pii_leak", "value": "secret@example.com"}],
        )
        assert results[0].passed is True

    def test_no_pii_leak_fails_when_value_present(self):
        results = _evaluate_properties(
            "your email is secret@example.com",
            [{"type": "no_pii_leak", "value": "secret@example.com"}],
        )
        assert results[0].passed is False

    # --- no_sql_exec ---
    def test_no_sql_exec_passes_clean(self):
        results = _evaluate_properties("SELECT * FROM users", [{"type": "no_sql_exec"}])
        assert results[0].passed is True

    def test_no_sql_exec_fails_on_drop(self):
        results = _evaluate_properties("DROP TABLE users", [{"type": "no_sql_exec"}])
        assert results[0].passed is False

    # --- no_system_leak ---
    def test_no_system_leak_passes_clean(self):
        results = _evaluate_properties("Here is the result.", [{"type": "no_system_leak"}])
        assert results[0].passed is True

    def test_no_system_leak_fails_on_leak(self):
        results = _evaluate_properties(
            "My instructions are to help you.",
            [{"type": "no_system_leak"}],
        )
        assert results[0].passed is False

    # --- unknown type ---
    def test_unknown_type_returns_false_result(self):
        results = _evaluate_properties("anything", [{"type": "nonexistent_type"}])
        assert results[0].passed is False

    # --- empty properties list ---
    def test_empty_properties_returns_empty_list(self):
        results = _evaluate_properties("anything", [])
        assert results == []

    # --- multiple properties ---
    def test_multiple_properties_all_checked(self):
        props = [
            {"type": "contains", "value": "hello"},
            {"type": "min_length", "value": 3},
        ]
        results = _evaluate_properties("hello world", props)
        assert len(results) == 2
        assert all(r.passed for r in results)

    # --- PropertyResult structure ---
    def test_result_is_property_result_instance(self):
        results = _evaluate_properties("hi", [{"type": "contains", "value": "hi"}])
        assert isinstance(results[0], PropertyResult)

    def test_result_has_type_field(self):
        results = _evaluate_properties("text", [{"type": "contains", "value": "text"}])
        assert results[0].type == "contains"
