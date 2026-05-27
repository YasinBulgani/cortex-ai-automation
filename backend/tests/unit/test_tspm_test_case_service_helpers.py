"""Unit tests for TSPM test case service pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/tspm/test_case_service.py:
    _strip_fences, _parse_test_cases_json, _normalize_analysis_text,
    _estimate_requirement_count, _validate_enum, _normalize_steps
"""

from __future__ import annotations

import pytest

from app.domains.tspm.test_case_service import (
    _estimate_requirement_count,
    _normalize_analysis_text,
    _normalize_steps,
    _parse_test_cases_json,
    _strip_fences,
    _validate_enum,
)


# ── _strip_fences ─────────────────────────────────────────────────────────────


class TestStripFences:
    def test_json_fence_stripped(self) -> None:
        raw = "```json\n[{\"a\": 1}]\n```"
        assert _strip_fences(raw) == '[{"a": 1}]'

    def test_plain_fence_stripped(self) -> None:
        raw = "```\n[{\"a\": 1}]\n```"
        assert _strip_fences(raw) == '[{"a": 1}]'

    def test_no_fence_unchanged(self) -> None:
        raw = '[{"a": 1}]'
        assert _strip_fences(raw) == '[{"a": 1}]'

    def test_whitespace_trimmed(self) -> None:
        raw = "   hello world   "
        assert _strip_fences(raw) == "hello world"

    def test_empty_string(self) -> None:
        assert _strip_fences("") == ""

    def test_returns_string(self) -> None:
        assert isinstance(_strip_fences("test"), str)


# ── _parse_test_cases_json ────────────────────────────────────────────────────


class TestParseTestCasesJson:
    def test_plain_array(self) -> None:
        raw = '[{"title": "Test 1"}, {"title": "Test 2"}]'
        result = _parse_test_cases_json(raw)
        assert len(result) == 2
        assert result[0]["title"] == "Test 1"

    def test_wrapped_in_test_cases_key(self) -> None:
        raw = '{"test_cases": [{"title": "TC"}]}'
        result = _parse_test_cases_json(raw)
        assert len(result) == 1
        assert result[0]["title"] == "TC"

    def test_wrapped_in_cases_key(self) -> None:
        raw = '{"cases": [{"title": "TC"}]}'
        result = _parse_test_cases_json(raw)
        assert len(result) == 1

    def test_wrapped_in_scenarios_key(self) -> None:
        raw = '{"scenarios": [{"title": "SC"}]}'
        result = _parse_test_cases_json(raw)
        assert len(result) == 1

    def test_wrapped_in_tests_key(self) -> None:
        raw = '{"tests": [{"title": "T"}]}'
        result = _parse_test_cases_json(raw)
        assert len(result) == 1

    def test_json_fence_stripped_before_parse(self) -> None:
        raw = '```json\n[{"title": "Fenced"}]\n```'
        result = _parse_test_cases_json(raw)
        assert len(result) == 1
        assert result[0]["title"] == "Fenced"

    def test_invalid_json_returns_empty(self) -> None:
        result = _parse_test_cases_json("not json at all")
        assert result == []

    def test_empty_string_returns_empty(self) -> None:
        assert _parse_test_cases_json("") == []

    def test_single_object_not_wrapped_returns_empty(self) -> None:
        # dict without recognized keys → returns []
        result = _parse_test_cases_json('{"other_key": "value"}')
        assert result == []

    def test_array_embedded_in_text(self) -> None:
        raw = 'Here are the tests:\n[{"title": "Extracted"}]\nEnd.'
        result = _parse_test_cases_json(raw)
        # Should attempt extraction from within the text
        assert isinstance(result, list)

    def test_returns_list(self) -> None:
        assert isinstance(_parse_test_cases_json("[]"), list)

    def test_multiple_items(self) -> None:
        items = [{"title": f"TC-{i}"} for i in range(5)]
        import json
        result = _parse_test_cases_json(json.dumps(items))
        assert len(result) == 5


# ── _normalize_analysis_text ──────────────────────────────────────────────────


class TestNormalizeAnalysisText:
    def test_multiple_spaces_collapsed(self) -> None:
        result = _normalize_analysis_text("hello   world")
        assert result == "hello world"

    def test_newlines_collapsed(self) -> None:
        result = _normalize_analysis_text("line1\n\n\nline2")
        assert result == "line1 line2"

    def test_tabs_collapsed(self) -> None:
        result = _normalize_analysis_text("a\t\tb")
        assert result == "a b"

    def test_leading_trailing_stripped(self) -> None:
        result = _normalize_analysis_text("  hello  ")
        assert result == "hello"

    def test_empty_string(self) -> None:
        assert _normalize_analysis_text("") == ""

    def test_returns_string(self) -> None:
        assert isinstance(_normalize_analysis_text("text"), str)

    def test_single_word_unchanged(self) -> None:
        assert _normalize_analysis_text("hello") == "hello"


# ── _estimate_requirement_count ───────────────────────────────────────────────


class TestEstimateRequirementCount:
    def test_empty_returns_zero(self) -> None:
        assert _estimate_requirement_count("") == 0

    def test_whitespace_only_returns_zero(self) -> None:
        assert _estimate_requirement_count("   \n  ") == 0

    def test_meaningful_lines_counted(self) -> None:
        text = "\n".join([
            "- The system shall allow users to log in with email and password",
            "- The system shall validate email format before submission",
            "- The system shall display error messages for invalid credentials",
        ])
        result = _estimate_requirement_count(text)
        assert result >= 1

    def test_short_lines_min_is_1_for_nonempty_text(self) -> None:
        # Even if no lines >= 24 chars, non-empty text returns min 1
        text = "- Hi\n- Short\n- Also short"
        result = _estimate_requirement_count(text)
        assert result == 1  # max(0, 1) = 1 — floor is always 1 for non-empty text

    def test_max_capped_at_50(self) -> None:
        # 60 long lines should be capped at 50
        long_line = "- " + "A" * 30
        text = "\n".join([long_line] * 60)
        result = _estimate_requirement_count(text)
        assert result <= 50

    def test_min_is_1_for_non_empty(self) -> None:
        # One meaningful line
        result = _estimate_requirement_count("- The system must authenticate users securely")
        assert result >= 1

    def test_returns_int(self) -> None:
        assert isinstance(_estimate_requirement_count("text"), int)


# ── _validate_enum ────────────────────────────────────────────────────────────


class TestValidateEnum:
    def test_valid_value_returned(self) -> None:
        assert _validate_enum("high", ["low", "medium", "high"], "medium") == "high"

    def test_invalid_value_returns_default(self) -> None:
        assert _validate_enum("invalid", ["a", "b", "c"], "a") == "a"

    def test_empty_string_invalid_returns_default(self) -> None:
        assert _validate_enum("", ["x", "y"], "x") == "x"

    def test_case_sensitive(self) -> None:
        # "HIGH" is not in ["high", "medium", "low"]
        result = _validate_enum("HIGH", ["high", "medium", "low"], "medium")
        assert result == "medium"

    def test_all_values_in_allowed_list(self) -> None:
        allowed = ["p0", "p1", "p2", "p3"]
        for val in allowed:
            assert _validate_enum(val, allowed, "p3") == val

    def test_returns_string(self) -> None:
        assert isinstance(_validate_enum("x", ["x"], "x"), str)


# ── _normalize_steps ─────────────────────────────────────────────────────────


class TestNormalizeSteps:
    def test_empty_list(self) -> None:
        assert _normalize_steps([]) == []

    def test_not_a_list_returns_empty(self) -> None:
        assert _normalize_steps("not a list") == []
        assert _normalize_steps(None) == []
        assert _normalize_steps({}) == []

    def test_string_steps_converted(self) -> None:
        result = _normalize_steps(["Click button", "Verify modal"])
        assert len(result) == 2
        assert result[0]["action"] == "Click button"
        assert result[0]["expected"] == ""
        assert result[0]["order"] == 1

    def test_dict_steps_preserved(self) -> None:
        steps = [{"order": 1, "action": "Navigate", "expected": "Page loads"}]
        result = _normalize_steps(steps)
        assert result[0]["action"] == "Navigate"
        assert result[0]["expected"] == "Page loads"

    def test_dict_step_alt_keys(self) -> None:
        # "step" key instead of "action"
        steps = [{"step": "Do something", "expected_result": "It works"}]
        result = _normalize_steps(steps)
        assert result[0]["action"] == "Do something"
        assert result[0]["expected"] == "It works"

    def test_order_assigned_if_missing(self) -> None:
        steps = [{"action": "Step A"}, {"action": "Step B"}]
        result = _normalize_steps(steps)
        assert result[0]["order"] == 1
        assert result[1]["order"] == 2

    def test_mixed_string_and_dict(self) -> None:
        steps = ["String step", {"action": "Dict step", "expected": "Result"}]
        result = _normalize_steps(steps)
        assert len(result) == 2
        assert result[0]["action"] == "String step"
        assert result[1]["action"] == "Dict step"

    def test_returns_list_of_dicts(self) -> None:
        result = _normalize_steps([{"action": "x"}])
        assert isinstance(result, list)
        assert all(isinstance(s, dict) for s in result)
