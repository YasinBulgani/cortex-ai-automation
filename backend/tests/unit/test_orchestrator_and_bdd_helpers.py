"""Unit tests for orchestrator and BDD generator pure helper functions.

Covers three modules — no DB, no LLM:
  - app/domains/tspm/bdd_generator.py      : _fuzzy_step_match
  - app/domains/agents/banking_orchestrator.py : _extract_failed_tests,
                                                 _build_final_report, CycleOutput
  - app/domains/ai/qa_orchestrator.py      : QAOrchestrator._summarize_result
"""

from __future__ import annotations

import pytest

from app.domains.agents.banking_orchestrator import (
    CycleOutput,
    _build_final_report,
    _extract_failed_tests,
)
from app.domains.ai.qa_orchestrator import QAOrchestrator
from app.domains.tspm.bdd_generator import _fuzzy_step_match


# ── _fuzzy_step_match ─────────────────────────────────────────────────────────


class TestFuzzyStepMatch:
    def test_exact_match(self) -> None:
        assert _fuzzy_step_match("kullanıcı sisteme girer", "kullanıcı sisteme girer") is True

    def test_substring_match_generated_in_known(self) -> None:
        assert _fuzzy_step_match("sisteme girer", "kullanıcı sisteme girer") is True

    def test_substring_match_known_in_generated(self) -> None:
        assert _fuzzy_step_match("kullanıcı sisteme girer", "sisteme girer") is True

    def test_high_word_overlap(self) -> None:
        # 4/5 words overlap → 80% > 60%
        result = _fuzzy_step_match(
            "kullanıcı hesaba para transfer eder",
            "kullanıcı hesaba para transfer yapar",
        )
        assert result is True

    def test_low_word_overlap(self) -> None:
        # Completely unrelated steps
        result = _fuzzy_step_match("login button clicked", "transfer amount entered")
        assert result is False

    def test_empty_generated_returns_false(self) -> None:
        assert _fuzzy_step_match("", "kullanıcı sisteme girer") is False

    def test_empty_known_returns_false(self) -> None:
        assert _fuzzy_step_match("kullanıcı sisteme girer", "") is False

    def test_both_empty_returns_false(self) -> None:
        assert _fuzzy_step_match("", "") is False

    def test_single_word_match(self) -> None:
        # Same single word → exact match
        assert _fuzzy_step_match("click", "click") is True

    def test_completely_different_steps(self) -> None:
        assert _fuzzy_step_match("alpha beta gamma", "delta epsilon zeta") is False

    def test_overlap_exactly_60_percent(self) -> None:
        # 3 matching out of 5 total unique = 60% → border case
        # {a, b, c} vs {a, b, d} → overlap=2, union=4 → 50% → False
        # Let's try 3 words same, 2 total different = {a,b,c} vs {a,b,c,d,e} → 3/5=60%
        result = _fuzzy_step_match("a b c", "a b c d e")
        assert result is True  # 3/max(3,5)=3/5=60% → >=0.6


# ── _extract_failed_tests ─────────────────────────────────────────────────────


class TestExtractFailedTests:
    def test_empty_dict_returns_empty(self) -> None:
        assert _extract_failed_tests({}) == []

    def test_no_failures_returns_empty(self) -> None:
        data = {
            "playwright": {"failed": 0, "passed": 5},
            "pytest": {"failed": 0, "passed": 10},
        }
        assert _extract_failed_tests(data) == []

    def test_playwright_failure_without_output_adds_generic(self) -> None:
        data = {"playwright": {"failed": 2, "output": ""}}
        result = _extract_failed_tests(data)
        assert len(result) >= 1
        assert result[0]["file"] == "e2e/banking/"
        assert "playwright" in result[0]["test_name"]

    def test_playwright_failure_with_no_output_key(self) -> None:
        data = {"playwright": {"failed": 1}}
        result = _extract_failed_tests(data)
        assert len(result) >= 1
        assert result[0]["test_name"] == "playwright-unknown"

    def test_pytest_failure_adds_entry(self) -> None:
        data = {"pytest": {"failed": 3}}
        result = _extract_failed_tests(data)
        assert len(result) >= 1
        assert any("pytest" in r["test_name"] for r in result)
        assert result[-1]["file"] == "api-tests/banking/"

    def test_both_playwright_and_pytest_failures(self) -> None:
        data = {
            "playwright": {"failed": 1},
            "pytest": {"failed": 2},
        }
        result = _extract_failed_tests(data)
        assert len(result) == 2  # one for each

    def test_playwright_with_selector_in_output(self) -> None:
        output = "TimeoutError: locator.click: Selector: '#submit-btn'"
        data = {"playwright": {"failed": 1, "output": output}}
        result = _extract_failed_tests(data)
        assert len(result) >= 1
        # If selector extracted, test_name is "playwright-test-1"
        # else generic "playwright-unknown"
        assert result[0]["file"] == "e2e/banking/"

    def test_result_has_required_keys(self) -> None:
        data = {"playwright": {"failed": 1}}
        result = _extract_failed_tests(data)
        for entry in result:
            assert "file" in entry
            assert "test_name" in entry
            assert "error" in entry
            assert "selector" in entry
            assert "dom_snippet" in entry

    def test_missing_playwright_key(self) -> None:
        data = {"pytest": {"failed": 1}}
        result = _extract_failed_tests(data)
        assert len(result) == 1
        assert "pytest" in result[0]["test_name"]


# ── _build_final_report ───────────────────────────────────────────────────────


def _make_cycle(
    cycle_num: int = 1,
    scenarios: list | None = None,
    rules: list | None = None,
) -> CycleOutput:
    """Helper to create CycleOutput for testing."""
    return CycleOutput(
        cycle=cycle_num,
        scenarios=scenarios or [],
        regulation_rules={"rules": rules or []},
        manual_keys=[],
        automation_matrix=[],
        generated_code={
            "bdd_features": [],
            "playwright_tests": [],
            "api_tests": [],
        },
        improvements={},
    )


class TestBuildFinalReport:
    def test_empty_cycles_returns_valid_report(self) -> None:
        result = _build_final_report([], {"description": "test system"})
        assert isinstance(result, dict)
        assert result["total_cycles"] == 0
        assert result["average_quality_score"] == 0

    def test_system_description_from_input_data(self) -> None:
        result = _build_final_report([], {"description": "Banking System"})
        assert result["system"] == "Banking System"

    def test_single_cycle_counted(self) -> None:
        cycle = _make_cycle(cycle_num=1)
        result = _build_final_report([cycle], {"description": ""})
        assert result["total_cycles"] == 1

    def test_scenario_count_in_report(self) -> None:
        scenarios = [
            {"id": "s1", "type": "positive", "priority": "P0"},
            {"id": "s2", "type": "negative", "priority": "P1"},
        ]
        cycle = _make_cycle(scenarios=scenarios)
        result = _build_final_report([cycle], {})
        assert result["scenarios"]["total"] == 2

    def test_duplicate_scenarios_deduped_by_id(self) -> None:
        s1 = {"id": "dup", "type": "positive", "priority": "P0"}
        s2 = {"id": "dup", "type": "positive", "priority": "P0"}
        cycle = _make_cycle(scenarios=[s1, s2])
        result = _build_final_report([cycle], {})
        assert result["scenarios"]["total"] == 1  # deduplicated

    def test_empty_id_scenarios_all_included(self) -> None:
        # Scenarios without id: all have id="" — first one included, rest deduplicated
        scenarios = [{"type": "positive"}, {"type": "negative"}]
        cycle = _make_cycle(scenarios=scenarios)
        result = _build_final_report([cycle], {})
        # All have sid="" so only the first is included
        assert result["scenarios"]["total"] == 1

    def test_scenarios_by_type_counted(self) -> None:
        scenarios = [
            {"id": "1", "type": "positive"},
            {"id": "2", "type": "positive"},
            {"id": "3", "type": "negative"},
        ]
        cycle = _make_cycle(scenarios=scenarios)
        result = _build_final_report([cycle], {})
        assert result["scenarios"]["by_type"]["positive"] == 2
        assert result["scenarios"]["by_type"]["negative"] == 1
        assert result["scenarios"]["by_type"]["edge_case"] == 0

    def test_average_score_from_cycles(self) -> None:
        c1 = CycleOutput(
            cycle=1,
            improvements={"cycle_assessment": {"overall_score": 80}},
        )
        c2 = CycleOutput(
            cycle=2,
            improvements={"cycle_assessment": {"overall_score": 60}},
        )
        result = _build_final_report([c1, c2], {})
        assert result["average_quality_score"] == pytest.approx(70.0)

    def test_rules_collected_from_cycles(self) -> None:
        c1 = _make_cycle(rules=[{"id": "R1"}, {"id": "R2"}])
        c2 = _make_cycle(rules=[{"id": "R3"}])
        result = _build_final_report([c1, c2], {})
        assert result["regulation"]["total_rules"] == 3

    def test_report_has_required_top_level_keys(self) -> None:
        result = _build_final_report([], {})
        required = ["system", "total_cycles", "average_quality_score",
                    "scenarios", "regulation", "automation", "generated_code"]
        for k in required:
            assert k in result, f"Missing key: {k}"


# ── QAOrchestrator._summarize_result ─────────────────────────────────────────


class TestQAOrchestratorSummarizeResult:
    def test_empty_dict_returns_empty(self) -> None:
        result = QAOrchestrator._summarize_result({})
        assert result == "empty"

    def test_coverage_rate_included(self) -> None:
        result = QAOrchestrator._summarize_result({"coverage_rate": 0.85})
        assert "coverage_rate" in result
        assert "0.85" in result

    def test_tests_generated_included(self) -> None:
        result = QAOrchestrator._summarize_result({"tests_generated": 12})
        assert "tests_generated" in result
        assert "12" in result

    def test_multiple_keys_shown(self) -> None:
        data = {
            "coverage_rate": 0.7,
            "gap_count": 5,
            "tests_generated": 3,
        }
        result = QAOrchestrator._summarize_result(data)
        assert "coverage_rate" in result
        assert "gap_count" in result
        assert "tests_generated" in result

    def test_max_5_parts_shown(self) -> None:
        data = {
            "coverage_rate": 0.7,
            "gap_count": 5,
            "tests_generated": 3,
            "flaky_count": 2,
            "prioritized_count": 10,
            "total_failures": 1,  # 6th key, should be cut
        }
        result = QAOrchestrator._summarize_result(data)
        # At most 5 parts joined with ", "
        parts = result.split(", ")
        assert len(parts) <= 5

    def test_summary_fallback_nested_dict(self) -> None:
        data = {"summary": {"status": "ok", "coverage": 0.9}}
        result = QAOrchestrator._summarize_result(data)
        # No matching known keys → falls back to nested summary
        assert isinstance(result, str)
        assert len(result) > 0

    def test_none_result_returns_empty(self) -> None:
        # None/falsy → returns "empty"
        result = QAOrchestrator._summarize_result(None)  # type: ignore[arg-type]
        assert result == "empty"

    def test_unknown_keys_fallback_to_str(self) -> None:
        data = {"unknown_key_xyz": "value"}
        result = QAOrchestrator._summarize_result(data)
        assert isinstance(result, str)
        assert len(result) <= 150 + 10  # truncated to 150

    def test_healed_key_included(self) -> None:
        result = QAOrchestrator._summarize_result({"healed": 3})
        assert "healed" in result
        assert "3" in result
