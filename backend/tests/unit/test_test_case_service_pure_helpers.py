"""Unit tests for tspm.test_case_service pure helper functions.

All tests are self-contained: no DB, no HTTP, no AI calls.
Covers:
  - _strip_fences: markdown code-fence removal
  - _parse_test_cases_json: JSON array extraction with multiple fallbacks
  - _normalize_analysis_text: whitespace collapse
  - _estimate_requirement_count: meaningful line counter
  - _validate_enum: enum guard with default
  - _normalize_steps: step list normalisation (str / dict inputs)
  - _build_trace_links: structured traceability dict
  - _build_prompt_for_modules: prompt string builder
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.test_case_service import (
        _strip_fences,
        _parse_test_cases_json,
        _normalize_analysis_text,
        _estimate_requirement_count,
        _validate_enum,
        _normalize_steps,
        _build_trace_links,
        _build_prompt_for_modules,
    )
    _TC_OK = True
except ImportError:
    _TC_OK = False


# ---------------------------------------------------------------------------
# _strip_fences
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestStripFences:
    def test_removes_json_fence(self):
        result = _strip_fences("```json\n{\"a\": 1}\n```")
        assert "```" not in result
        assert "{\"a\": 1}" in result

    def test_removes_generic_fence(self):
        result = _strip_fences("```\n[1, 2, 3]\n```")
        assert "```" not in result

    def test_no_fence_unchanged(self):
        text = '{"a": 1}'
        result = _strip_fences(text)
        assert result == text

    def test_strips_surrounding_whitespace(self):
        result = _strip_fences("   hello   ")
        assert result == "hello"

    def test_empty_string(self):
        result = _strip_fences("")
        assert result == ""

    def test_only_fences_returns_empty(self):
        result = _strip_fences("```json\n```")
        assert result == ""

    def test_returns_string(self):
        assert isinstance(_strip_fences("abc"), str)

    def test_content_preserved(self):
        content = '[{"id": 1, "title": "Test"}]'
        result = _strip_fences(f"```json\n{content}\n```")
        assert result == content


# ---------------------------------------------------------------------------
# _parse_test_cases_json
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestParseTestCasesJson:
    def test_plain_json_array(self):
        raw = '[{"title": "TC1"}, {"title": "TC2"}]'
        result = _parse_test_cases_json(raw)
        assert len(result) == 2
        assert result[0]["title"] == "TC1"

    def test_json_fence_array(self):
        raw = '```json\n[{"title": "TC1"}]\n```'
        result = _parse_test_cases_json(raw)
        assert len(result) == 1

    def test_dict_with_test_cases_key(self):
        raw = '{"test_cases": [{"title": "X"}]}'
        result = _parse_test_cases_json(raw)
        assert result == [{"title": "X"}]

    def test_dict_with_testCases_key(self):
        raw = '{"testCases": [{"title": "Y"}]}'
        result = _parse_test_cases_json(raw)
        assert result == [{"title": "Y"}]

    def test_dict_with_cases_key(self):
        raw = '{"cases": [{"id": 1}]}'
        result = _parse_test_cases_json(raw)
        assert result == [{"id": 1}]

    def test_dict_with_scenarios_key(self):
        raw = '{"scenarios": [{"name": "S1"}]}'
        result = _parse_test_cases_json(raw)
        assert result == [{"name": "S1"}]

    def test_dict_with_tests_key(self):
        raw = '{"tests": [{"id": "t1"}]}'
        result = _parse_test_cases_json(raw)
        assert result == [{"id": "t1"}]

    def test_embedded_array_in_prose(self):
        raw = 'Here are the test cases: [{"title": "TC"}] done.'
        result = _parse_test_cases_json(raw)
        assert result == [{"title": "TC"}]

    def test_invalid_json_returns_empty_list(self):
        result = _parse_test_cases_json("not valid json at all")
        assert result == []

    def test_empty_string_returns_empty_list(self):
        result = _parse_test_cases_json("")
        assert result == []

    def test_returns_list(self):
        assert isinstance(_parse_test_cases_json('[{"x": 1}]'), list)

    def test_plain_dict_without_known_key_returns_empty(self):
        raw = '{"unknown": [{"title": "X"}]}'
        result = _parse_test_cases_json(raw)
        assert result == []

    def test_empty_array(self):
        result = _parse_test_cases_json("[]")
        assert result == []


# ---------------------------------------------------------------------------
# _normalize_analysis_text
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestNormalizeAnalysisText:
    def test_collapses_multiple_spaces(self):
        result = _normalize_analysis_text("hello   world")
        assert result == "hello world"

    def test_strips_leading_trailing_whitespace(self):
        result = _normalize_analysis_text("  hello  ")
        assert result == "hello"

    def test_newlines_collapsed(self):
        result = _normalize_analysis_text("line1\nline2")
        assert "\n" not in result

    def test_tabs_collapsed(self):
        result = _normalize_analysis_text("a\t\tb")
        assert "\t" not in result

    def test_empty_string(self):
        assert _normalize_analysis_text("") == ""

    def test_single_word_unchanged(self):
        assert _normalize_analysis_text("word") == "word"

    def test_returns_string(self):
        assert isinstance(_normalize_analysis_text("test"), str)

    def test_mixed_whitespace(self):
        result = _normalize_analysis_text("a  \t\n  b")
        assert result == "a b"


# ---------------------------------------------------------------------------
# _estimate_requirement_count
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestEstimateRequirementCount:
    def test_empty_string_returns_zero(self):
        assert _estimate_requirement_count("") == 0

    def test_whitespace_only_returns_zero(self):
        assert _estimate_requirement_count("   ") == 0

    def test_meaningful_lines_counted(self):
        text = "This is a meaningful requirement line with content\nAnother line here"
        result = _estimate_requirement_count(text)
        assert result >= 1

    def test_short_lines_minimum_one_for_non_empty(self):
        # Lines < 24 chars after stripping → meaningful=[]; but max(0, 1) = 1 for non-empty text
        text = "Hi\nYo\nOk"
        result = _estimate_requirement_count(text)
        assert result == 1

    def test_bullet_stripped_before_counting(self):
        # Lines starting with "-" should be stripped; the content still counted if ≥24 chars
        text = "- This is a long requirement that has lots of content\n- Another one here also"
        result = _estimate_requirement_count(text)
        assert result >= 1

    def test_max_capped_at_50(self):
        # 100 lines of 30+ chars
        text = "\n".join(["This is a requirement line here!" for _ in range(100)])
        result = _estimate_requirement_count(text)
        assert result == 50

    def test_min_is_1_for_non_empty(self):
        # At least 1 line with ≥24 chars
        text = "This is exactly 24 chars!"
        result = _estimate_requirement_count(text)
        assert result >= 1

    def test_returns_int(self):
        assert isinstance(_estimate_requirement_count("test"), int)


# ---------------------------------------------------------------------------
# _validate_enum
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestValidateEnum:
    def test_valid_value_returned(self):
        result = _validate_enum("high", ["low", "medium", "high"], "medium")
        assert result == "high"

    def test_invalid_value_returns_default(self):
        result = _validate_enum("extreme", ["low", "medium", "high"], "medium")
        assert result == "medium"

    def test_empty_string_invalid_returns_default(self):
        result = _validate_enum("", ["a", "b"], "a")
        assert result == "a"

    def test_case_sensitive(self):
        # "High" is not in ["low", "high"] (case-sensitive)
        result = _validate_enum("High", ["low", "high"], "low")
        assert result == "low"

    def test_first_allowed_value_works(self):
        result = _validate_enum("functional", ["functional", "regression", "smoke"], "functional")
        assert result == "functional"

    def test_returns_string(self):
        assert isinstance(_validate_enum("a", ["a", "b"], "b"), str)

    def test_single_allowed_value(self):
        result = _validate_enum("only", ["only"], "only")
        assert result == "only"

    def test_default_must_be_in_allowed(self):
        # If passed a value not in list, default is returned as-is
        result = _validate_enum("x", ["a", "b"], "a")
        assert result == "a"


# ---------------------------------------------------------------------------
# _normalize_steps
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestNormalizeSteps:
    def test_string_steps_wrapped(self):
        result = _normalize_steps(["Click login", "Enter password"])
        assert result[0]["action"] == "Click login"
        assert result[0]["expected"] == ""

    def test_string_steps_order_assigned(self):
        result = _normalize_steps(["step1", "step2"])
        assert result[0]["order"] == 1
        assert result[1]["order"] == 2

    def test_dict_steps_with_action_key(self):
        steps = [{"order": 1, "action": "Click", "expected": "Button pressed"}]
        result = _normalize_steps(steps)
        assert result[0]["action"] == "Click"
        assert result[0]["expected"] == "Button pressed"

    def test_dict_steps_with_step_key_fallback(self):
        steps = [{"step": "Do something", "expected": "Result"}]
        result = _normalize_steps(steps)
        assert result[0]["action"] == "Do something"

    def test_dict_steps_with_description_key_fallback(self):
        steps = [{"description": "Navigate to home"}]
        result = _normalize_steps(steps)
        assert result[0]["action"] == "Navigate to home"

    def test_not_list_returns_empty(self):
        assert _normalize_steps(None) == []
        assert _normalize_steps("not a list") == []
        assert _normalize_steps(42) == []

    def test_empty_list_returns_empty(self):
        assert _normalize_steps([]) == []

    def test_mixed_string_and_dict_steps(self):
        steps = ["Click", {"action": "Type", "expected": "Typed"}]
        result = _normalize_steps(steps)
        assert len(result) == 2
        assert result[0]["action"] == "Click"
        assert result[1]["action"] == "Type"

    def test_returns_list(self):
        assert isinstance(_normalize_steps(["step1"]), list)

    def test_expected_result_key_fallback(self):
        steps = [{"action": "Do it", "expected_result": "Done"}]
        result = _normalize_steps(steps)
        assert result[0]["expected"] == "Done"

    def test_dict_has_order_action_expected_keys(self):
        result = _normalize_steps(["step1"])
        assert "order" in result[0]
        assert "action" in result[0]
        assert "expected" in result[0]


# ---------------------------------------------------------------------------
# _build_trace_links
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestBuildTraceLinks:
    def _make(self, **kwargs):
        defaults = dict(
            source_type="document",
            source_name="spec.pdf",
            source_checksum="abc123",
        )
        defaults.update(kwargs)
        return _build_trace_links(**defaults)

    def test_returns_dict(self):
        assert isinstance(self._make(), dict)

    def test_source_type(self):
        r = self._make(source_type="user_story")
        assert r["source"]["type"] == "user_story"

    def test_source_name(self):
        r = self._make(source_name="requirements.docx")
        assert r["source"]["name"] == "requirements.docx"

    def test_source_checksum(self):
        r = self._make(source_checksum="deadbeef")
        assert r["source"]["checksum"] == "deadbeef"

    def test_requirements_status_derived(self):
        r = self._make()
        assert r["requirements"]["status"] == "derived"

    def test_test_cases_status_generated(self):
        r = self._make()
        assert r["test_cases"]["status"] == "generated"

    def test_test_cases_total(self):
        r = self._make(total_generated=15)
        assert r["test_cases"]["total"] == 15

    def test_approvals_status_pending_when_zero(self):
        r = self._make(approved_count=0, rejected_count=0)
        assert r["approvals"]["status"] == "pending_review"

    def test_approvals_status_in_review_when_nonzero(self):
        r = self._make(approved_count=3, rejected_count=1)
        assert r["approvals"]["status"] == "in_review"

    def test_approvals_approved_count(self):
        r = self._make(approved_count=5)
        assert r["approvals"]["approved"] == 5

    def test_approvals_rejected_count(self):
        r = self._make(rejected_count=2)
        assert r["approvals"]["rejected"] == 2

    def test_scenarios_status_pending_when_zero_approved(self):
        r = self._make(approved_count=0)
        assert r["scenarios"]["status"] == "pending_creation"

    def test_scenarios_status_partially_created_when_approved(self):
        r = self._make(approved_count=3)
        assert r["scenarios"]["status"] == "partially_created"

    def test_scenarios_created_equals_approved(self):
        r = self._make(approved_count=7)
        assert r["scenarios"]["created"] == 7

    def test_source_name_none_allowed(self):
        r = self._make(source_name=None)
        assert r["source"]["name"] is None


# ---------------------------------------------------------------------------
# _build_prompt_for_modules
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TC_OK, reason="test_case_service import failed")
class TestBuildPromptForModules:
    def test_returns_string(self):
        result = _build_prompt_for_modules("analysis text", [])
        assert isinstance(result, str)

    def test_analysis_text_included(self):
        result = _build_prompt_for_modules("some analysis content", [])
        assert "some analysis content" in result

    def test_module_name_included(self):
        modules = [{"module_name": "LoginModule", "risk_level": "high", "estimated_tests": 5}]
        result = _build_prompt_for_modules("analysis", modules)
        assert "LoginModule" in result

    def test_module_risk_level_included(self):
        modules = [{"module_name": "Mod", "risk_level": "critical", "estimated_tests": 3}]
        result = _build_prompt_for_modules("text", modules)
        assert "critical" in result

    def test_no_modules_no_module_section(self):
        result = _build_prompt_for_modules("analysis text only", [])
        assert "Modüller" not in result

    def test_extra_instructions_included(self):
        result = _build_prompt_for_modules("text", [], extra_instructions="Focus on edge cases")
        assert "Focus on edge cases" in result

    def test_empty_extra_instructions_excluded(self):
        result = _build_prompt_for_modules("text", [], extra_instructions="")
        assert "Ek Talimat" not in result

    def test_json_format_hint_present(self):
        result = _build_prompt_for_modules("text", [])
        assert "JSON" in result

    def test_max_10_modules_used(self):
        # Provide 15 modules, only 10 should appear in the prompt
        modules = [
            {"module_name": f"Module{i}", "risk_level": "low", "estimated_tests": 1}
            for i in range(15)
        ]
        result = _build_prompt_for_modules("text", modules)
        assert "Module9" in result
        # Module10..14 should be cut off
        assert "Module14" not in result
