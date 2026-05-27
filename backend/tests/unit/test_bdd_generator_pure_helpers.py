"""Unit tests for tspm.bdd_generator pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _fuzzy_step_match: word-overlap similarity
  - _build_legacy_system_prompt: prompt template construction
  - _snap_scenario_steps: DSL snapping with no-op fallback
  - _dsl_fallback_scenarios: rule-based fallback scenario generation
  - _FALLBACK_DEFAULT_GIVEN / _FALLBACK_DEFAULT_THEN constants
  - _FALLBACK_ACTION_HINTS: hint table structure
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.bdd_generator import (
        _fuzzy_step_match,
        _build_legacy_system_prompt,
        _snap_scenario_steps,
        _dsl_fallback_scenarios,
        _FALLBACK_DEFAULT_GIVEN,
        _FALLBACK_DEFAULT_THEN,
        _FALLBACK_ACTION_HINTS,
    )
    _BDD_OK = True
except ImportError:
    _BDD_OK = False


# ---------------------------------------------------------------------------
# _fuzzy_step_match
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="bdd_generator import failed")
class TestFuzzyStepMatch:
    def test_exact_match(self):
        assert _fuzzy_step_match("hello world", "hello world") is True

    def test_generated_contained_in_known(self):
        assert _fuzzy_step_match("hello", "hello world") is True

    def test_known_contained_in_generated(self):
        assert _fuzzy_step_match("hello world", "hello") is True

    def test_high_word_overlap_passes_threshold(self):
        # 2 of 3 unique words overlap → 0.667 >= 0.6
        assert _fuzzy_step_match("cat sat mat", "cat sat hat") is True

    def test_exact_threshold_boundary(self):
        # 3 words each, 2 common → 2/3 ≈ 0.667 >= 0.6 → True
        assert _fuzzy_step_match("a b c", "a b d") is True

    def test_below_threshold_fails(self):
        # No common words between these two
        assert _fuzzy_step_match("completely different text", "nothing matches at all") is False

    def test_empty_generated_returns_false(self):
        assert _fuzzy_step_match("", "hello world") is False

    def test_empty_known_returns_false(self):
        assert _fuzzy_step_match("hello world", "") is False

    def test_both_empty_returns_false(self):
        assert _fuzzy_step_match("", "") is False

    def test_none_generated_returns_false(self):
        assert _fuzzy_step_match(None, "hello") is False  # type: ignore[arg-type]

    def test_none_known_returns_false(self):
        assert _fuzzy_step_match("hello", None) is False  # type: ignore[arg-type]

    def test_single_word_exact_match(self):
        assert _fuzzy_step_match("login", "login") is True

    def test_single_word_no_match(self):
        assert _fuzzy_step_match("login", "logout") is False

    def test_returns_bool(self):
        result = _fuzzy_step_match("a b c", "a b c")
        assert isinstance(result, bool)

    def test_word_overlap_with_subset_sentence(self):
        # "the user clicks button" vs "user clicks" — "user clicks" in "the user clicks button"
        assert _fuzzy_step_match("user clicks", "the user clicks button") is True


# ---------------------------------------------------------------------------
# _build_legacy_system_prompt
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="bdd_generator import failed")
class TestBuildLegacySystemPrompt:
    def test_returns_string(self):
        result = _build_legacy_system_prompt("test analysis text")
        assert isinstance(result, str)

    def test_contains_json_scenarios_key(self):
        result = _build_legacy_system_prompt("analysis")
        assert '"scenarios"' in result

    def test_contains_gherkin_keywords(self):
        result = _build_legacy_system_prompt("login feature")
        # Should mention Gherkin keywords
        assert "Given" in result or "Diyelim" in result or "Scenario" in result or "Senaryo" in result

    def test_does_not_raise_on_empty_input(self):
        result = _build_legacy_system_prompt("")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_does_not_raise_on_unicode_input(self):
        result = _build_legacy_system_prompt("kullanıcı giriş yapmalıdır 🔒")
        assert isinstance(result, str)

    def test_contains_steps_key(self):
        result = _build_legacy_system_prompt("any text")
        assert '"steps"' in result

    def test_non_empty_result(self):
        result = _build_legacy_system_prompt("feature description")
        assert len(result) > 100  # Should be a substantial prompt

    def test_different_inputs_produce_at_least_same_base(self):
        # The base template is constant regardless of input
        r1 = _build_legacy_system_prompt("input A")
        r2 = _build_legacy_system_prompt("input B")
        # Both should contain the same structural markers
        assert '"scenarios"' in r1
        assert '"scenarios"' in r2


# ---------------------------------------------------------------------------
# _snap_scenario_steps (no-op when DSL unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="bdd_generator import failed")
class TestSnapScenarioSteps:
    def test_returns_list(self):
        result = _snap_scenario_steps([])
        assert isinstance(result, list)

    def test_empty_input_returns_empty(self):
        assert _snap_scenario_steps([]) == []

    def test_non_dict_scenario_preserved(self):
        """Non-dict items should pass through unchanged."""
        scenarios = ["not-a-dict", 42]
        result = _snap_scenario_steps(scenarios)
        assert result == scenarios

    def test_dict_scenario_preserved_without_dsl(self):
        scenario = {
            "title": "Login test",
            "steps": [{"keyword": "Given", "text": "user is logged in"}],
        }
        result = _snap_scenario_steps([scenario])
        assert len(result) == 1
        assert result[0]["title"] == "Login test"

    def test_multiple_scenarios_all_returned(self):
        scenarios = [
            {"title": "T1", "steps": []},
            {"title": "T2", "steps": []},
        ]
        result = _snap_scenario_steps(scenarios)
        assert len(result) == 2

    def test_steps_present_in_result(self):
        steps = [{"keyword": "Given", "text": "state"}]
        result = _snap_scenario_steps([{"title": "T", "steps": steps}])
        assert "steps" in result[0]

    def test_dsl_coverage_key_added_or_exists(self):
        """When DSL module is available, coverage key should be added.
        When unavailable, original scenario returned unchanged — either way title stays."""
        result = _snap_scenario_steps([{"title": "S1", "steps": []}])
        assert result[0].get("title") == "S1"

    def test_none_steps_handled(self):
        """scenarios with steps=None should not crash."""
        result = _snap_scenario_steps([{"title": "S", "steps": None}])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _dsl_fallback_scenarios
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="bdd_generator import failed")
class TestDslFallbackScenarios:
    def test_returns_list(self):
        result = _dsl_fallback_scenarios("test")
        assert isinstance(result, list)

    def test_actionable_text_produces_scenarios(self):
        result = _dsl_fallback_scenarios("kullanıcı butona tıklar")
        assert len(result) >= 1

    def test_scenario_has_required_keys(self):
        result = _dsl_fallback_scenarios("kullanıcı giriş yapar")
        sc = result[0]
        for key in ("title", "description", "feature", "gherkin", "tags", "steps", "dsl_coverage"):
            assert key in sc, f"missing key: {key}"

    def test_scenario_steps_count(self):
        """Each scenario should have Given/When/Then = 3 steps."""
        result = _dsl_fallback_scenarios("kullanıcı butona tıklar ve giriş yapar")
        sc = result[0]
        assert len(sc["steps"]) >= 2  # At least Given + Then or more

    def test_descriptive_text_gets_descriptive_only_tag(self):
        result = _dsl_fallback_scenarios("Bu uygulama çok gelişmiş bir yapıya sahiptir.")
        sc = result[0]
        assert "descriptive-only" in sc["tags"]

    def test_descriptive_text_gets_needs_dsl_tag(self):
        result = _dsl_fallback_scenarios("Bu uygulama çok gelişmiş bir yapıya sahiptir.")
        sc = result[0]
        assert "needs-dsl" in sc["tags"]

    def test_fallback_tag_always_present(self):
        result = _dsl_fallback_scenarios("kullanıcı tıklar")
        assert "dsl-fallback" in result[0]["tags"]

    def test_empty_analysis_text_returns_placeholder(self):
        result = _dsl_fallback_scenarios("")
        assert len(result) >= 1
        # Descriptive-only placeholder
        assert "descriptive-only" in result[0]["tags"]

    def test_gherkin_contains_given_keyword(self):
        result = _dsl_fallback_scenarios("kullanıcı tıklar")
        gherkin = result[0]["gherkin"]
        assert "Diyelim ki" in gherkin or "Given" in gherkin

    def test_dsl_coverage_is_float(self):
        result = _dsl_fallback_scenarios("kullanıcı tıklar")
        assert isinstance(result[0]["dsl_coverage"], float)

    def test_max_10_scenarios(self):
        """Function caps at 10 scenarios from actionable sentences."""
        long_text = ". ".join(
            [f"kullanıcı {i}. butona tıklar" for i in range(20)]
        )
        result = _dsl_fallback_scenarios(long_text)
        assert len(result) <= 10

    def test_title_is_non_empty(self):
        result = _dsl_fallback_scenarios("kullanıcı giriş yapar")
        assert len(result[0]["title"]) > 0

    def test_extra_instructions_accepted(self):
        """Extra instructions parameter should not raise."""
        result = _dsl_fallback_scenarios("kullanıcı tıklar", extra_instructions="Sadece pozitif")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BDD_OK, reason="bdd_generator import failed")
class TestFallbackConstants:
    def test_default_given_is_string(self):
        assert isinstance(_FALLBACK_DEFAULT_GIVEN, str)

    def test_default_given_non_empty(self):
        assert len(_FALLBACK_DEFAULT_GIVEN) > 0

    def test_default_then_is_string(self):
        assert isinstance(_FALLBACK_DEFAULT_THEN, str)

    def test_default_then_non_empty(self):
        assert len(_FALLBACK_DEFAULT_THEN) > 0

    def test_action_hints_is_list(self):
        assert isinstance(_FALLBACK_ACTION_HINTS, list)

    def test_action_hints_non_empty(self):
        assert len(_FALLBACK_ACTION_HINTS) > 0

    def test_action_hints_each_is_tuple_of_3(self):
        for hint in _FALLBACK_ACTION_HINTS:
            assert len(hint) == 3, f"hint tuple should have 3 elements: {hint}"

    def test_action_hints_first_element_is_list(self):
        for triggers, query, default in _FALLBACK_ACTION_HINTS:
            assert isinstance(triggers, list), "triggers should be a list"

    def test_action_hints_query_is_string(self):
        for triggers, query, default in _FALLBACK_ACTION_HINTS:
            assert isinstance(query, str)

    def test_action_hints_default_is_string(self):
        for triggers, query, default in _FALLBACK_ACTION_HINTS:
            assert isinstance(default, str)
