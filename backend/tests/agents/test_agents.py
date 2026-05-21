"""Tests for individual banking-team agents.

Each agent is tested for:
  - Class attributes (name, temperature, max_tokens, model_fallback)
  - model property resolution (ollama vs openai)
  - run() with mocked LLM — call_json returns a valid response
  - run() with empty/missing context — no crash
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Shared fake settings
_FAKE = SimpleNamespace(
    ai_provider="ollama",
    ollama_base_url="http://localhost:11434/v1",
    ollama_api_key="ollama",
    ollama_model_analyst="qwen2.5:32b",
    ollama_model_fast="mistral:latest",
    ollama_model_coder="qwen2.5-coder:7b",
    openai_api_key="sk-test",
    openai_base_url="https://api.openai.com/v1",
    openai_model="gpt-4o",
    anthropic_api_key="",
)

_FAKE_OPENAI = SimpleNamespace(**{**vars(_FAKE), "ai_provider": "openai"})


# ---- helpers ----------------------------------------------------------------

def _patch_settings(settings_obj=_FAKE):
    """Return a context manager that patches settings across all agent modules."""
    targets = [
        "app.domains.agents.banking_team.base_agent.settings",
        "app.domains.agents.banking_team.data_analyst.settings",
        "app.domains.agents.banking_team.scenario_generator.settings",
        "app.domains.agents.banking_team.regulation_agent.settings",
        "app.domains.agents.banking_team.automation_decision.settings",
        "app.domains.agents.banking_team.code_generator.settings",
        "app.domains.agents.banking_team.quality_judge.settings",
        "app.domains.agents.banking_team.auto_healer.settings",
        "app.domains.agents.banking_team.self_improving.settings",
        "app.domains.agents.banking_team.debate_orchestrator.settings",
    ]

    class _MultiPatch:
        def __init__(self):
            self._patchers = [patch(t, settings_obj) for t in targets]

        def __enter__(self):
            for p in self._patchers:
                p.start()
            return self

        def __exit__(self, *args):
            for p in self._patchers:
                p.stop()

    return _MultiPatch()


def _make_agent(cls, call_json_return=None):
    """Instantiate agent, mock call_json and learn so no LLM/DB calls happen."""
    with _patch_settings():
        agent = cls()
    agent.call_json = MagicMock(
        return_value=call_json_return if call_json_return is not None else {}
    )
    agent.learn = MagicMock()
    return agent


# ═══════════════════════════════════════════════════════════════════════════════
# DataAnalystAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataAnalystAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.data_analyst import DataAnalystAgent
            self.cls = DataAnalystAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Veri Analisti"
        assert self.cls.temperature == 0.2
        assert self.cls.model_fallback == ["mistral:latest"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "qwen2.5:32b"  # ollama_model_analyst

    def test_model_property_openai(self):
        with _patch_settings(_FAKE_OPENAI):
            agent = self.cls()
            assert agent.model == "gpt-4o"

    def test_run_with_valid_context(self):
        agent = _make_agent(
            self.cls,
            call_json_return={
                "business_flows": [{"name": "Login", "description": "auth", "modules": ["auth"], "risk_level": "high"}],
                "critical_areas": ["authentication"],
                "risk_matrix": [],
                "data_gaps": [],
                "untested_areas": [],
                "summary": "Analysis done",
            },
        )
        result = agent.run({
            "description": "Test bank",
            "db_schema": "users(id,email)",
            "api_docs": "GET /api/users",
        })
        assert result.success is True
        assert "business_flows" in result.data
        agent.learn.assert_called_once()

    def test_run_with_empty_context(self):
        agent = _make_agent(self.cls, call_json_return={"summary": "ok"})
        result = agent.run({})
        assert result.success is True

    def test_run_with_parse_error(self):
        agent = _make_agent(self.cls, call_json_return={"parse_error": True, "raw": "bad"})
        result = agent.run({"description": "test"})
        assert result.success is False
        # learn() should NOT be called on parse error
        agent.learn.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# ScenarioGeneratorAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenarioGeneratorAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.scenario_generator import ScenarioGeneratorAgent
            self.cls = ScenarioGeneratorAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Senaryo Üretici"
        assert self.cls.temperature == 0.4
        assert self.cls.max_tokens == 6000
        assert self.cls.model_fallback == ["mistral:latest"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "qwen2.5:32b"

    def test_model_property_openai(self):
        with _patch_settings(_FAKE_OPENAI):
            agent = self.cls()
            assert agent.model == "gpt-4o"

    def test_run_with_analysis_context(self):
        agent = _make_agent(
            self.cls,
            call_json_return={
                "scenarios": [
                    {"id": "SCN-001", "title": "Login", "type": "positive", "module": "auth",
                     "steps": [], "priority": "P0"},
                ],
                "modules": ["auth"],
                "total_count": 1,
                "coverage_summary": "ok",
            },
        )
        result = agent.run({
            "analysis": {
                "business_flows": [{"name": "Login", "description": "auth flow", "risk_level": "high"}],
                "critical_areas": ["auth"],
                "risk_matrix": [{"area": "auth", "risk": "brute force", "regulation": "BDDK"}],
            },
            "description": "Banking",
        })
        assert result.success is True
        assert result.data["total_count"] == 1

    def test_run_with_empty_context(self):
        agent = _make_agent(self.cls, call_json_return={"scenarios": [], "total_count": 0})
        result = agent.run({})
        assert result.success is True

    def test_run_with_existing_scenarios_dedup(self):
        agent = _make_agent(self.cls, call_json_return={"scenarios": [], "total_count": 0})
        result = agent.run({
            "existing_scenarios": [{"title": "Existing scenario"}],
        })
        # call_json should have been called with user prompt mentioning existing
        call_args = agent.call_json.call_args
        user_prompt = call_args[0][1]
        assert "Existing scenario" in user_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# RegulationAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegulationAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.regulation_agent import RegulationAgent
            self.cls = RegulationAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Regülasyon Ajanı"
        assert self.cls.temperature == 0.1
        assert self.cls.max_tokens == 5000
        assert self.cls.model_fallback == ["qwen2.5:32b"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "mistral:latest"  # ollama_model_fast

    def test_model_property_openai(self):
        with _patch_settings(_FAKE_OPENAI):
            agent = self.cls()
            assert agent.model == "gpt-4o"

    def test_run_with_scenarios(self):
        agent = _make_agent(
            self.cls,
            call_json_return={
                "rules": [{"rule_id": "BDDK-001", "regulation": "BDDK", "title": "Test"}],
                "manual_keys": [],
                "compliance_summary": {"total_rules": 1, "mandatory": 1},
            },
        )
        result = agent.run({
            "scenarios": [{"id": "SCN-001", "title": "Login test", "type": "positive"}],
            "description": "Bank",
        })
        assert result.success is True
        assert len(result.data["rules"]) == 1

    def test_run_with_empty_scenarios(self):
        agent = _make_agent(self.cls, call_json_return={"rules": [], "manual_keys": [], "compliance_summary": {}})
        result = agent.run({})
        assert result.success is True

    def test_custom_regulations(self):
        agent = _make_agent(self.cls, call_json_return={"rules": [], "manual_keys": [], "compliance_summary": {}})
        agent.run({"regulations": ["KVKK", "PCI-DSS"]})
        call_args = agent.call_json.call_args
        user_prompt = call_args[0][1]
        assert "KVKK" in user_prompt
        assert "PCI-DSS" in user_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# AutomationDecisionAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutomationDecisionAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.automation_decision import AutomationDecisionAgent
            self.cls = AutomationDecisionAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Otomasyon Karar Ajanı"
        assert self.cls.temperature == 0.2
        assert self.cls.max_tokens == 4096
        assert self.cls.model_fallback == ["qwen2.5:32b"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "mistral:latest"

    def test_run_with_scenarios_and_manual_keys(self):
        agent = _make_agent(
            self.cls,
            call_json_return={
                "automation_matrix": [
                    {"scenario_id": "SCN-001", "decision": "UI", "tool": "Playwright"},
                ],
                "summary": {"total": 1, "ui": 1, "api": 0, "db": 0, "manual": 0, "hybrid": 0},
            },
        )
        result = agent.run({
            "scenarios": [{"id": "SCN-001", "title": "Login", "type": "positive", "priority": "P0"}],
            "manual_keys": [{"scenario_id": "SCN-002", "reason": "regulation"}],
            "description": "Bank",
        })
        assert result.success is True
        assert result.data["summary"]["ui"] == 1

    def test_run_with_empty_context(self):
        agent = _make_agent(self.cls, call_json_return={"automation_matrix": [], "summary": {}})
        result = agent.run({})
        assert result.success is True

    def test_manual_key_marked_in_prompt(self):
        agent = _make_agent(self.cls, call_json_return={"automation_matrix": [], "summary": {}})
        agent.run({
            "scenarios": [{"id": "SCN-001", "title": "Test", "type": "positive", "priority": "P0"}],
            "manual_keys": [{"scenario_id": "SCN-001"}],
        })
        call_args = agent.call_json.call_args
        user_prompt = call_args[0][1]
        assert "MANUEL" in user_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# CodeGeneratorAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestCodeGeneratorAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.code_generator import CodeGeneratorAgent
            self.cls = CodeGeneratorAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Kod Üretici"
        assert self.cls.temperature == 0.2
        assert self.cls.max_tokens == 6000
        assert self.cls.model_fallback == ["mistral:latest", "qwen2.5:32b"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "qwen2.5-coder:7b"

    def test_model_property_openai(self):
        with _patch_settings(_FAKE_OPENAI):
            agent = self.cls()
            assert agent.model == "gpt-4o"

    def test_run_generates_bdd_and_playwright(self):
        bdd_resp = {"bdd_features": [{"scenario_id": "SCN-001", "feature_file": "login.feature", "content": "Feature: Login"}]}
        pw_resp = {"playwright_tests": [{"scenario_id": "SCN-001", "file_path": "e2e/login.spec.ts", "content": "test(...)"}]}

        with _patch_settings():
            agent = self.cls()
        agent.learn = MagicMock()
        # call_json is called multiple times (bdd, playwright, api)
        agent.call_json = MagicMock(side_effect=[bdd_resp, pw_resp])

        result = agent.run({
            "automation_matrix": [
                {"scenario_id": "SCN-001", "scenario_title": "Login", "decision": "UI"},
            ],
            "scenarios": [{"id": "SCN-001", "title": "Login", "type": "positive", "steps": [], "preconditions": [], "expected_result": "ok"}],
            "description": "Bank",
            "generate": ["bdd", "playwright"],
        })
        assert result.success is True
        assert len(result.data["bdd_features"]) == 1
        assert len(result.data["playwright_tests"]) == 1
        assert result.data["generated_count"] == 2

    def test_run_with_empty_matrix(self):
        with _patch_settings():
            agent = self.cls()
        agent.learn = MagicMock()
        agent.call_json = MagicMock()  # should not be called
        result = agent.run({"automation_matrix": [], "scenarios": []})
        assert result.success is True
        assert result.data["generated_count"] == 0

    def test_run_api_tests_only(self):
        api_resp = {"api_tests": [{"scenario_id": "SCN-002", "file_path": "tests/test_api.py", "content": "def test_api(): ..."}]}

        with _patch_settings():
            agent = self.cls()
        agent.learn = MagicMock()
        agent.call_json = MagicMock(return_value=api_resp)

        result = agent.run({
            "automation_matrix": [
                {"scenario_id": "SCN-002", "scenario_title": "API Test", "decision": "API"},
            ],
            "scenarios": [{"id": "SCN-002", "steps": [], "expected_result": "200"}],
            "generate": ["api"],
        })
        assert result.success is True
        assert len(result.data["api_tests"]) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# QualityJudgeAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityJudgeAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.quality_judge import QualityJudgeAgent
            self.cls = QualityJudgeAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Kalite Hakimi"
        assert self.cls.temperature == 0.1
        assert self.cls.max_tokens == 2048
        assert self.cls.model_fallback == ["qwen2.5:32b"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "mistral:latest"

    def test_run_skip_when_no_data(self):
        agent = _make_agent(self.cls)
        result = agent.run({"scenarios": [], "generated_code": {}})
        assert result.success is True
        assert result.data["verdict"] == "SKIP"

    def test_run_with_llm_evaluation(self):
        llm_result = {
            "dimensions": [
                {"name": "scenario_completeness", "score": 8, "max_score": 10, "reasoning": "good"},
                {"name": "regulation_alignment", "score": 7, "max_score": 10, "reasoning": "ok"},
                {"name": "assertion_strength", "score": 6, "max_score": 10, "reasoning": "fair"},
                {"name": "data_boundaries", "score": 5, "max_score": 10, "reasoning": "needs work"},
            ],
            "weighted_score": 7.1,
            "summary": "Good coverage",
            "improvements": [],
        }
        agent = _make_agent(self.cls, call_json_return=llm_result)
        result = agent.run({
            "scenarios": [{"id": "SCN-001", "title": "test", "type": "positive"}],
            "generated_code": {"bdd_features": [], "generated_count": 0},
            "description": "Bank",
        })
        assert result.success is True
        assert result.data["verdict"] == "PASS"
        assert result.data["quality_gate_passed"] is True

    def test_run_heuristic_fallback(self):
        """If LLM returns parse_error, heuristic evaluation kicks in."""
        agent = _make_agent(self.cls, call_json_return={"parse_error": True})
        result = agent.run({
            "scenarios": [
                {"id": "S1", "type": "positive"},
                {"id": "S2", "type": "negative"},
                {"id": "S3", "type": "edge_case"},
            ],
            "generated_code": {"bdd_features": [], "playwright_tests": [], "api_tests": [], "generated_count": 0},
            "regulation_rules": {"rules": [{"regulation": "BDDK", "description": "rule"}]},
        })
        assert result.success is True
        assert "weighted_score" in result.data
        assert result.data.get("evaluation_method") == "heuristic"

    def test_weighted_score_calculation(self):
        with _patch_settings():
            agent = self.cls()
        dims = [
            {"name": "scenario_completeness", "score": 10},
            {"name": "regulation_alignment", "score": 10},
            {"name": "assertion_strength", "score": 10},
            {"name": "data_boundaries", "score": 10},
        ]
        score = agent._calc_weighted_score(dims)
        # 10*0.40 + 10*0.30 + 10*0.20 + 10*0.10 = 10.0
        assert score == 10.0

    def test_weighted_score_with_zeroes(self):
        with _patch_settings():
            agent = self.cls()
        dims = [
            {"name": "scenario_completeness", "score": 0},
            {"name": "regulation_alignment", "score": 0},
            {"name": "assertion_strength", "score": 0},
            {"name": "data_boundaries", "score": 0},
        ]
        assert agent._calc_weighted_score(dims) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# AutoHealerAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestAutoHealerAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.auto_healer import AutoHealerAgent
            self.cls = AutoHealerAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Otomatik Tamirci"
        assert self.cls.temperature == 0.1
        assert self.cls.max_tokens == 512
        assert self.cls.model_fallback == ["qwen2.5-coder:7b"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "mistral:latest"

    def test_run_no_failed_tests(self):
        agent = _make_agent(self.cls)
        result = agent.run({"failed_tests": []})
        assert result.success is True
        assert result.data["healed"] == 0

    def test_run_zero_cost_heal_via_data_testid(self):
        with _patch_settings():
            agent = self.cls()
        agent.learn = MagicMock()
        # Mock the cache methods to avoid DB
        agent._cache_heal = MagicMock()
        agent._lookup_cache = MagicMock(return_value=None)

        result = agent.run({
            "failed_tests": [
                {
                    "file": "test.spec.ts",
                    "test_name": "login test",
                    "error": "Element not found",
                    "selector": ".old-class",
                    "dom_snippet": '<button data-testid="submit-btn">Login</button>',
                },
            ],
        })
        assert result.success is True
        assert result.data["healed"] == 1
        details = result.data["details"]
        assert details[0]["tier"] == "zero-cost"
        assert "data-testid" in details[0]["strategy"]

    def test_zero_cost_heal_role_fallback(self):
        with _patch_settings():
            agent = self.cls()
        dom = '<input role="textbox" aria-label="Email" />'
        heal = agent._zero_cost_heal(".old-selector", dom)
        assert heal is not None
        assert heal["strategy"] == "role"

    def test_zero_cost_heal_no_match(self):
        with _patch_settings():
            agent = self.cls()
        dom = "<div><span></span></div>"
        heal = agent._zero_cost_heal(".old", dom)
        assert heal is None

    def test_zero_cost_filters_react_ids(self):
        with _patch_settings():
            agent = self.cls()
        dom = '<input id=":r5:" /><button id="stable-btn">Click</button>'
        heal = agent._zero_cost_heal(".old", dom)
        assert heal is not None
        # Should pick the stable id, not the React one
        assert "stable-btn" in heal["selector"]


# ═══════════════════════════════════════════════════════════════════════════════
# SelfImprovingAgent
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfImprovingAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.self_improving import SelfImprovingAgent
            self.cls = SelfImprovingAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Self-Improving Ajanı"
        assert self.cls.temperature == 0.3
        assert self.cls.max_tokens == 5000
        assert self.cls.model_fallback == ["mistral:latest"]

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "qwen2.5:32b"  # ollama_model_analyst

    def test_model_property_openai(self):
        with _patch_settings(_FAKE_OPENAI):
            agent = self.cls()
            assert agent.model == "gpt-4o"

    def test_run_with_full_context(self):
        agent = _make_agent(
            self.cls,
            call_json_return={
                "cycle_assessment": {"cycle_number": 1, "overall_score": 7.5, "strengths": [], "weaknesses": []},
                "improvements": [{"target": "scenario", "item_id": "SCN-001", "current_issue": "x", "suggested_fix": "y", "priority": "high"}],
                "next_cycle_priorities": [],
                "new_scenarios_needed": [],
                "automation_optimizations": [],
                "learning_summary": "Cycle 1 done",
            },
        )
        result = agent.run({
            "cycle_number": 1,
            "scenarios": [{"id": "S1", "type": "positive", "module": "auth"}],
            "automation_matrix": [{"decision": "UI"}],
            "regulation_rules": {"rules": [{"r": 1}], "manual_keys": []},
            "generated_code": {"generated_count": 3},
        })
        assert result.success is True
        assert result.data["cycle_assessment"]["overall_score"] == 7.5

    def test_run_with_empty_context(self):
        agent = _make_agent(self.cls, call_json_return={"cycle_assessment": {}, "learning_summary": "nothing"})
        result = agent.run({})
        assert result.success is True

    def test_run_includes_previous_improvements_in_prompt(self):
        agent = _make_agent(self.cls, call_json_return={"cycle_assessment": {}, "learning_summary": ""})
        agent.run({
            "previous_improvements": [
                {"item_id": "SCN-005", "suggested_fix": "Add edge case"}
            ],
        })
        user_prompt = agent.call_json.call_args[0][1]
        assert "SCN-005" in user_prompt
        assert "Add edge case" in user_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# DebateOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class TestDebateOrchestrator:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.debate_orchestrator import DebateOrchestrator
            self.cls = DebateOrchestrator
            yield

    def test_class_attributes(self):
        assert self.cls.name == "Tartışma Orkestratörü"
        assert self.cls.temperature == 0.3
        assert self.cls.max_tokens == 4096
        assert self.cls.model_fallback == ["mistral:latest"]

    def test_init_params(self):
        with _patch_settings():
            agent = self.cls(max_rounds=3, min_quality=8.0)
        assert agent.max_rounds == 3
        assert agent.min_quality == 8.0

    def test_model_property_ollama(self):
        with _patch_settings(_FAKE):
            agent = self.cls()
            assert agent.model == "qwen2.5:32b"

    def test_run_no_author_output(self):
        with _patch_settings():
            agent = self.cls()
        agent.learn = MagicMock()
        result = agent.run({"debate_type": "scenario", "author_output": {}})
        assert result.success is False
        assert "author" in result.error.lower()

    def test_run_debate_passes_on_high_quality(self):
        with _patch_settings():
            agent = self.cls(max_rounds=2, min_quality=7.0)
        agent.learn = MagicMock()
        # Mock critic to return high score immediately
        agent._run_critic = MagicMock(return_value={"score": 8.0, "weaknesses": [], "missing_scenarios": []})
        agent._run_final_judge = MagicMock(return_value={"weighted_score": 8.0, "verdict": "PASS"})

        result = agent.run({
            "debate_type": "scenario",
            "author_output": {"scenarios": [{"id": "S1"}]},
            "description": "Bank",
        })
        assert result.success is True
        assert result.data["verdict"] == "PASS"
        # No revision round since critic score >= min_quality
        agent._run_critic.assert_called_once()

    def test_run_debate_with_revision(self):
        with _patch_settings():
            agent = self.cls(max_rounds=2, min_quality=8.0)
        agent.learn = MagicMock()

        critic_results = [
            {"score": 5.0, "weaknesses": [{"description": "missing"}], "missing_scenarios": [], "revision_instructions": "fix it"},
            {"score": 9.0, "weaknesses": [], "missing_scenarios": []},
        ]
        agent._run_critic = MagicMock(side_effect=critic_results)
        agent._run_revision = MagicMock(return_value={"scenarios": [{"id": "S1"}, {"id": "S2"}]})
        agent._run_final_judge = MagicMock(return_value={"weighted_score": 9.0, "verdict": "PASS"})

        result = agent.run({
            "debate_type": "scenario",
            "author_output": {"scenarios": [{"id": "S1"}]},
            "description": "Bank",
        })
        assert result.success is True
        # Revision was called because first critic score < min_quality
        agent._run_revision.assert_called_once()

    def test_count_changes_scenario(self):
        with _patch_settings():
            agent = self.cls()
        old = {"scenarios": [{"id": "S1"}, {"id": "S2"}]}
        new = {"scenarios": [{"id": "S1"}, {"id": "S2"}, {"id": "S3"}]}
        changes = agent._count_changes(old, new, "scenario")
        assert changes["added"] == 1
        assert changes["total"] == 3

    def test_count_changes_code(self):
        with _patch_settings():
            agent = self.cls()
        old = {"bdd_features": [1], "playwright_tests": [], "api_tests": [1]}
        new = {"bdd_features": [1, 2], "playwright_tests": [1], "api_tests": [1]}
        changes = agent._count_changes(old, new, "code")
        assert changes["added"] == 2  # 1 bdd + 1 playwright
        assert changes["total"] == 4


# ═══════════════════════════════════════════════════════════════════════════════
# DiscoveryAgent (basic class attribute tests)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiscoveryAgent:
    @pytest.fixture(autouse=True)
    def _setup(self):
        with _patch_settings():
            from app.domains.agents.banking_team.discovery_agent import DiscoveryAgent
            self.cls = DiscoveryAgent
            yield

    def test_class_attributes(self):
        assert self.cls.name is not None
        assert hasattr(self.cls, "temperature")
        assert hasattr(self.cls, "model_fallback")

    def test_inherits_from_base_agent(self):
        with _patch_settings():
            from app.domains.agents.banking_team.base_agent import BaseAgent
        assert issubclass(self.cls, BaseAgent)
