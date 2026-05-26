"""Unit tests for app.domains.tspm.bdd_generator — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no LLM.
Covers: _fuzzy_step_match, _build_legacy_system_prompt (structure only),
        _snap_scenario_steps (DSL import failure graceful path),
        _FALLBACK_ACTION_HINTS constant.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.bdd_generator import (
        _fuzzy_step_match,
        _build_legacy_system_prompt,
        _snap_scenario_steps,
        _FALLBACK_ACTION_HINTS,
        _FALLBACK_DEFAULT_GIVEN,
        _FALLBACK_DEFAULT_THEN,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="bdd_generator import failed")


# ---------------------------------------------------------------------------
# _fuzzy_step_match
# ---------------------------------------------------------------------------

class TestFuzzyStepMatch:
    def test_exact_match_returns_true(self):
        assert _fuzzy_step_match("kullanıcı giriş yapar", "kullanıcı giriş yapar") is True

    def test_empty_generated_returns_false(self):
        assert _fuzzy_step_match("", "some step") is False

    def test_empty_known_returns_false(self):
        assert _fuzzy_step_match("some step", "") is False

    def test_both_empty_returns_false(self):
        assert _fuzzy_step_match("", "") is False

    def test_generated_contains_known(self):
        # "giriş yapar" is contained in "kullanıcı giriş yapar"
        assert _fuzzy_step_match("giriş yapar", "kullanıcı giriş yapar") is True

    def test_known_contains_generated(self):
        assert _fuzzy_step_match("kullanıcı giriş yapar", "giriş yapar") is True

    def test_high_word_overlap_returns_true(self):
        # 3 out of 4 words match → 75% overlap >= 60%
        result = _fuzzy_step_match("a b c d", "a b c x")
        assert result is True

    def test_low_word_overlap_returns_false(self):
        # 1 out of 4 words match → 25% < 60%
        result = _fuzzy_step_match("a b c d", "a x y z")
        assert result is False

    def test_exact_60_percent_overlap(self):
        # 3 words match out of 5 = 60% → True (>= 0.6)
        result = _fuzzy_step_match("a b c d e", "a b c x y")
        assert result is True

    def test_completely_different_steps_returns_false(self):
        assert _fuzzy_step_match("alfa beta gamma", "one two three") is False

    def test_returns_bool(self):
        assert isinstance(_fuzzy_step_match("test step", "other step"), bool)

    def test_single_word_exact_match(self):
        assert _fuzzy_step_match("login", "login") is True

    def test_single_word_different_returns_false(self):
        # 0 overlap
        assert _fuzzy_step_match("login", "logout") is False

    def test_none_generated_returns_false(self):
        assert _fuzzy_step_match(None, "step") is False  # type: ignore[arg-type]

    def test_none_known_returns_false(self):
        assert _fuzzy_step_match("step", None) is False  # type: ignore[arg-type]

    def test_word_overlap_uses_set_semantics(self):
        # Repeated words shouldn't inflate the overlap ratio
        # "a a a" → gen_words = {"a"}, "a b c" → known_words = {"a","b","c"}
        # overlap = {"a"}, max(1, 3) = 3, ratio = 1/3 < 0.6
        result = _fuzzy_step_match("a a a", "a b c")
        assert result is False


# ---------------------------------------------------------------------------
# _build_legacy_system_prompt
# ---------------------------------------------------------------------------

class TestBuildLegacySystemPrompt:
    def test_returns_string(self):
        result = _build_legacy_system_prompt("test analizi")
        assert isinstance(result, str)

    def test_contains_gherkin_keywords(self):
        result = _build_legacy_system_prompt("some analysis")
        assert "Gherkin" in result or "Given" in result or "Diyelim ki" in result

    def test_contains_json_format_instruction(self):
        result = _build_legacy_system_prompt("some text")
        assert "JSON" in result or "scenarios" in result

    def test_contains_scenarios_key(self):
        result = _build_legacy_system_prompt("test")
        assert '"scenarios"' in result

    def test_nonempty_for_empty_input(self):
        result = _build_legacy_system_prompt("")
        assert len(result) > 100

    def test_contains_turkish_keywords(self):
        result = _build_legacy_system_prompt("analiz")
        assert "Türkçe" in result or "Turkce" in result or "Diyelim" in result

    def test_contains_feature_and_scenario_placeholders(self):
        result = _build_legacy_system_prompt("spec text")
        assert "Senaryo" in result or "Feature" in result


# ---------------------------------------------------------------------------
# _snap_scenario_steps — graceful path when DSL import fails
# ---------------------------------------------------------------------------

class TestSnapScenarioSteps:
    def test_returns_list(self):
        scenarios = [{"title": "test", "steps": []}]
        result = _snap_scenario_steps(scenarios)
        assert isinstance(result, list)

    def test_non_dict_passthrough(self):
        # Non-dict items are passed through as-is
        scenarios = ["not a dict", 42]
        result = _snap_scenario_steps(scenarios)
        assert result == ["not a dict", 42]

    def test_empty_list_returns_empty(self):
        assert _snap_scenario_steps([]) == []

    def test_preserves_scenario_structure(self):
        scenario = {"title": "my test", "steps": [], "tags": []}
        result = _snap_scenario_steps([scenario])
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_dsl_coverage_added(self):
        # After snap, dsl_coverage key should be present
        scenario = {"title": "test", "steps": []}
        result = _snap_scenario_steps([scenario])
        # dsl_coverage is added regardless of DSL availability
        assert "dsl_coverage" in result[0]

    def test_zero_steps_gives_zero_coverage(self):
        scenario = {"title": "t", "steps": []}
        result = _snap_scenario_steps([scenario])
        assert result[0]["dsl_coverage"] == 0.0

    def test_needs_dsl_tag_added_when_no_coverage(self):
        # Steps exist but no DSL match (no dsl_action_id) → needs-dsl tag appended
        scenario = {
            "title": "t",
            "steps": [{"keyword": "Eğer", "text": "bir şey olur"}],
            "tags": [],
        }
        result = _snap_scenario_steps([scenario])
        tags = result[0]["tags"]
        assert "needs-dsl" in tags or "@needs-dsl" in tags

    def test_needs_dsl_not_duplicated(self):
        scenario = {
            "title": "t",
            "steps": [{"keyword": "Eğer", "text": "bir şey"}],
            "tags": ["needs-dsl"],
        }
        result = _snap_scenario_steps([scenario])
        tags = result[0]["tags"]
        assert tags.count("needs-dsl") == 1


# ---------------------------------------------------------------------------
# _FALLBACK_ACTION_HINTS constant
# ---------------------------------------------------------------------------

class TestFallbackActionHints:
    def test_is_list(self):
        assert isinstance(_FALLBACK_ACTION_HINTS, list)

    def test_each_entry_is_tuple(self):
        for entry in _FALLBACK_ACTION_HINTS:
            assert isinstance(entry, tuple)

    def test_each_tuple_has_three_elements(self):
        for entry in _FALLBACK_ACTION_HINTS:
            assert len(entry) == 3

    def test_first_element_is_list(self):
        for entry in _FALLBACK_ACTION_HINTS:
            assert isinstance(entry[0], list)

    def test_second_element_is_string(self):
        for entry in _FALLBACK_ACTION_HINTS:
            assert isinstance(entry[1], str)

    def test_third_element_is_string(self):
        for entry in _FALLBACK_ACTION_HINTS:
            assert isinstance(entry[2], str)

    def test_click_hint_present(self):
        # At least one entry should have a click-related keyword
        all_keywords = [kw for entry in _FALLBACK_ACTION_HINTS for kw in entry[0]]
        assert any("tıkla" in kw or "bas" in kw for kw in all_keywords)

    def test_type_hint_present(self):
        all_keywords = [kw for entry in _FALLBACK_ACTION_HINTS for kw in entry[0]]
        assert any("yazar" in kw or "girer" in kw or "doldur" in kw for kw in all_keywords)


# ---------------------------------------------------------------------------
# _FALLBACK_DEFAULT_GIVEN / _FALLBACK_DEFAULT_THEN constants
# ---------------------------------------------------------------------------

class TestFallbackDefaults:
    def test_given_is_string(self):
        assert isinstance(_FALLBACK_DEFAULT_GIVEN, str)

    def test_then_is_string(self):
        assert isinstance(_FALLBACK_DEFAULT_THEN, str)

    def test_given_nonempty(self):
        assert len(_FALLBACK_DEFAULT_GIVEN) > 5

    def test_then_nonempty(self):
        assert len(_FALLBACK_DEFAULT_THEN) > 5
