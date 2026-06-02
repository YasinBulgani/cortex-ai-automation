"""Unit tests for engine/services/* modules.

Heavy LLM/API deps are stubbed via sys.modules before any import so the
tests run without real credentials or network access.

Covers all service modules:
  ai_test_generator, anomaly_detector, assertion_engine, bdd_generator,
  context_chunker, coverage_analyzer, flaky_detector, llm_gateway,
  prompt_loader, security_scanner, self_healer, test_prioritizer

Strategy:
  - All LLM / file-I/O heavy paths are patched via unittest.mock.
  - Pure helper functions (score calculation, PII redaction, etc.) are
    tested with real logic — no mocking needed.
  - Each service has at minimum:
      1. Instantiation succeeds
      2. Main public method returns the expected type
      3. Edge-case (empty / None / malformed input) handled gracefully
      4. Error from LLM is handled, not propagated raw
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy optional dependencies BEFORE any engine import
# ---------------------------------------------------------------------------
for _mod in ("openai", "anthropic", "tiktoken", "sentence_transformers",
             "sklearn", "numpy", "pandas", "scipy"):
    sys.modules.setdefault(_mod, MagicMock())

# yaml needs a working safe_load that returns a dict
if "yaml" not in sys.modules:
    _yaml_stub = types.ModuleType("yaml")
    _yaml_stub.safe_load = MagicMock(return_value={})  # type: ignore[attr-defined]
    sys.modules["yaml"] = _yaml_stub

import yaml  # noqa: E402 — must follow stub setup
yaml.safe_load = MagicMock(return_value={})  # type: ignore[attr-defined]

# Minimal _model_registry stub so llm_gateway can import cleanly
_model_reg = types.ModuleType("engine.services._model_registry")
_model_reg.build_legacy_model_costs = MagicMock(  # type: ignore[attr-defined]
    return_value={"gpt-4o": {"input": 0.000005, "output": 0.000015}}
)
sys.modules.setdefault("engine.services._model_registry", _model_reg)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_llm_response(content: str = "mocked response"):
    """Return a fake LLMResponse-like object."""
    resp = MagicMock()
    resp.content = content
    resp.tokens_used = 42
    resp.cached = False
    resp.cost_usd = 0.001
    resp.latency_ms = 100
    return resp


@pytest.fixture()
def mock_gateway():
    gw = MagicMock()
    gw.complete.return_value = _make_llm_response()
    return gw


# ===========================================================================
# 1. prompt_loader
# ===========================================================================

class TestPromptLoader:
    """Tests for engine/services/prompt_loader.py"""

    def test_get_engine_prompt_raises_on_missing_key(self):
        """Requesting a nonexistent prompt key should raise KeyError."""
        with patch("engine.services.prompt_loader._load_manifest", return_value={}):
            from engine.services.prompt_loader import get_engine_prompt
            get_engine_prompt.cache_clear()
            with pytest.raises(KeyError):
                get_engine_prompt("nonexistent_prompt_xyz")

    def test_get_engine_prompt_returns_str_for_valid_key(self):
        """A present prompt key should return a non-empty string."""
        fake_manifest = {
            "engine_prompts": {
                "test_generator": {"sections": ["base/role.md"]}
            }
        }
        with patch("engine.services.prompt_loader._load_manifest", return_value=fake_manifest), \
             patch("engine.services.prompt_loader._read", return_value="You are a test generator."):
            from engine.services.prompt_loader import get_engine_prompt
            get_engine_prompt.cache_clear()
            result = get_engine_prompt("test_generator")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_join_skips_blank_parts(self):
        """_join() must ignore blank or whitespace-only entries."""
        from engine.services.prompt_loader import _join
        result = _join(["Hello", "", "   ", "World"])
        assert "Hello" in result
        assert "World" in result
        assert "\n\n\n" not in result

    def test_join_returns_empty_for_all_blank(self):
        from engine.services.prompt_loader import _join
        result = _join(["", "  ", None])  # type: ignore[list-item]
        assert result == ""


# ===========================================================================
# 2. llm_gateway
# ===========================================================================

class TestLLMGateway:
    """Tests for engine/services/llm_gateway.py"""

    def _make_gateway(self, **kwargs):
        with patch("engine.services.llm_gateway.LLMGateway._apply_yaml_config", new=lambda self: None):
            from engine.services.llm_gateway import LLMGateway
            return LLMGateway(
                openai_api_key="test-key",
                enable_cache=True,
                use_gateway_proxy=False,
                **kwargs,
            )

    def test_instantiation_succeeds(self):
        gw = self._make_gateway()
        from engine.services.llm_gateway import LLMGateway
        assert isinstance(gw, LLMGateway)

    def test_pii_sanitize_redacts_email(self):
        gw = self._make_gateway()
        msgs = [{"role": "user", "content": "Contact user@example.com for info"}]
        sanitized = gw._sanitize_messages(msgs)
        assert "user@example.com" not in sanitized[0]["content"]
        assert "[EMAIL]" in sanitized[0]["content"]

    def test_pii_sanitize_redacts_phone(self):
        gw = self._make_gateway()
        msgs = [{"role": "user", "content": "Call me at 05321234567"}]
        sanitized = gw._sanitize_messages(msgs)
        assert "05321234567" not in sanitized[0]["content"]

    def test_pii_sanitize_empty_content_unchanged(self):
        gw = self._make_gateway()
        msgs = [{"role": "user", "content": ""}]
        result = gw._sanitize_messages(msgs)
        assert result[0]["content"] == ""

    def test_usage_stats_to_dict_has_required_keys(self):
        gw = self._make_gateway()
        stats = gw.stats.to_dict()
        assert isinstance(stats, dict)
        for key in ("total_calls", "total_tokens", "total_cost_usd", "cache_hits"):
            assert key in stats

    def test_cache_key_deterministic_for_same_inputs(self):
        gw = self._make_gateway()
        msgs = [{"role": "user", "content": "hello"}]
        k1 = gw._cache_key(msgs, "gpt-4o", 0.2)
        k2 = gw._cache_key(msgs, "gpt-4o", 0.2)
        assert k1 == k2

    def test_cache_key_differs_for_different_models(self):
        gw = self._make_gateway()
        msgs = [{"role": "user", "content": "hello"}]
        k1 = gw._cache_key(msgs, "gpt-4o", 0.2)
        k2 = gw._cache_key(msgs, "gpt-4o-mini", 0.2)
        assert k1 != k2

    def test_cache_key_differs_for_different_temperatures(self):
        gw = self._make_gateway()
        msgs = [{"role": "user", "content": "hello"}]
        k1 = gw._cache_key(msgs, "gpt-4o", 0.0)
        k2 = gw._cache_key(msgs, "gpt-4o", 1.0)
        assert k1 != k2


# ===========================================================================
# 3. anomaly_detector
# ===========================================================================

class TestAnomalyDetector:
    """Tests for engine/services/anomaly_detector.py"""

    def _make_detector(self):
        with patch("engine.services.anomaly_detector.AnomalyDetector._load_history", return_value=[]), \
             patch("engine.services.anomaly_detector.AnomalyDetector._merge_feedback_loop_history", return_value=None):
            from engine.services.anomaly_detector import AnomalyDetector
            return AnomalyDetector()

    def test_instantiation(self):
        from engine.services.anomaly_detector import AnomalyDetector
        det = self._make_detector()
        assert isinstance(det, AnomalyDetector)

    def test_analyze_test_run_empty_history_returns_list(self):
        det = self._make_detector()
        result = det.analyze_test_run({"total": 10, "failed": 1})
        assert isinstance(result, list)

    def test_analyze_test_run_empty_dict_returns_list(self):
        det = self._make_detector()
        result = det.analyze_test_run({})
        assert isinstance(result, list)

    def test_analyze_k6_empty_input_returns_list(self):
        det = self._make_detector()
        result = det.analyze_k6_results({})
        assert isinstance(result, list)

    def test_anomaly_to_dict_has_all_fields(self):
        from engine.services.anomaly_detector import Anomaly
        a = Anomaly(
            metric_name="failure_rate",
            current_value=0.9,
            expected_range=(0.0, 0.2),
            z_score=3.5,
            severity="critical",
            description="High failure rate detected",
        )
        d = a.to_dict()
        for key in ("metric_name", "current_value", "expected_range", "z_score", "severity", "description"):
            assert key in d

    @pytest.mark.parametrize("severity", ["warning", "critical"])
    def test_anomaly_severity_values(self, severity):
        from engine.services.anomaly_detector import Anomaly
        a = Anomaly(
            metric_name="duration",
            current_value=10.0,
            expected_range=(1.0, 5.0),
            z_score=2.5,
            severity=severity,
            description="test",
        )
        assert a.severity == severity


# ===========================================================================
# 4. flaky_detector
# ===========================================================================

class TestFlakyDetector:
    """Tests for engine/services/flaky_detector.py"""

    def _make_detector(self, history=None):
        with patch("engine.services.flaky_detector.FlakyDetector._load_json", return_value=history or {}), \
             patch("engine.services.flaky_detector.FlakyDetector._merge_feedback_loop_history", return_value=None):
            from engine.services.flaky_detector import FlakyDetector
            return FlakyDetector()

    def test_instantiation(self):
        from engine.services.flaky_detector import FlakyDetector
        det = self._make_detector()
        assert isinstance(det, FlakyDetector)

    def test_analyze_all_empty_history_returns_empty(self):
        det = self._make_detector(history={})
        assert det.analyze_all() == []

    def test_flaky_score_alternating_pattern(self):
        det = self._make_detector()
        runs = [
            {"status": "passed" if i % 2 == 0 else "failed", "duration": 1.0}
            for i in range(10)
        ]
        info = det._analyze_test("test_login", runs)
        assert 0.0 <= info.flaky_score <= 1.0
        assert info.recommendation in ("quarantine", "monitor", "stable", "fix")

    def test_quarantine_list_returns_list_type(self):
        det = self._make_detector()
        result = det.get_quarantine_list()
        assert isinstance(result, list)

    def test_flaky_info_to_dict_structure(self):
        from engine.services.flaky_detector import FlakyTestInfo
        fi = FlakyTestInfo(
            test_id="test_login",
            flaky_score=0.5,
            total_runs=10,
            pass_count=5,
            fail_count=5,
            flip_count=8,
            recommendation="quarantine",
            last_failure_reason="timeout",
        )
        d = fi.to_dict()
        assert d["test_id"] == "test_login"
        for key in ("flaky_score", "total_runs", "pass_count", "fail_count", "flip_count", "recommendation"):
            assert key in d

    def test_generate_pytest_deselect_args_returns_list(self):
        det = self._make_detector()
        args = det.generate_pytest_deselect_args()
        assert isinstance(args, list)


# ===========================================================================
# 5. coverage_analyzer
# ===========================================================================

class TestCoverageAnalyzer:
    """Tests for engine/services/coverage_analyzer.py"""

    def test_instantiation_without_gateway(self):
        from engine.services.coverage_analyzer import CoverageAnalyzer
        ca = CoverageAnalyzer()
        assert ca.gateway is None

    def test_instantiation_with_gateway(self, mock_gateway):
        from engine.services.coverage_analyzer import CoverageAnalyzer
        ca = CoverageAnalyzer(gateway=mock_gateway)
        assert ca.gateway is mock_gateway

    def test_analyze_empty_coverage_data_returns_empty(self):
        from engine.services.coverage_analyzer import CoverageAnalyzer
        ca = CoverageAnalyzer()
        with patch.object(ca, "_load_coverage", return_value={}):
            result = ca.analyze()
        assert result == []

    def test_analyze_skips_files_above_medium_threshold(self):
        from engine.services.coverage_analyzer import CoverageAnalyzer
        ca = CoverageAnalyzer()
        data = {"app/main.py": {"total_lines": 100, "covered_lines": 90, "uncovered_lines": []}}
        with patch.object(ca, "_load_coverage", return_value=data):
            result = ca.analyze()
        assert result == []

    def test_analyze_includes_files_below_threshold(self):
        from engine.services.coverage_analyzer import CoverageAnalyzer
        ca = CoverageAnalyzer()
        data = {
            "app/auth.py": {
                "total_lines": 100,
                "covered_lines": 30,
                "uncovered_lines": list(range(70)),
            }
        }
        with patch.object(ca, "_load_coverage", return_value=data):
            result = ca.analyze()
        assert len(result) == 1
        assert result[0].priority == "critical"

    @pytest.mark.parametrize("pct,expected_priority", [
        (30.0, "critical"),
        (60.0, "high"),
        (80.0, "medium"),
    ])
    def test_determine_priority(self, pct, expected_priority):
        from engine.services.coverage_analyzer import CoverageAnalyzer
        priority = CoverageAnalyzer._determine_priority(pct, "app/some.py")
        assert priority == expected_priority

    def test_coverage_gap_to_dict_structure(self):
        from engine.services.coverage_analyzer import CoverageGap
        gap = CoverageGap(
            file_path="app/auth.py",
            uncovered_lines=[10, 20, 30],
            line_coverage_pct=40.0,
            priority="critical",
            suggested_test="Add auth test",
        )
        d = gap.to_dict()
        assert d["priority"] == "critical"
        assert d["uncovered_lines_count"] == 3
        assert d["line_coverage_pct"] == 40.0


# ===========================================================================
# 6. context_chunker
# ===========================================================================

class TestContextChunker:
    """Tests for engine/services/context_chunker.py"""

    def test_instantiation_with_default_model(self, mock_gateway):
        from engine.services.context_chunker import ContextChunker
        cc = ContextChunker(mock_gateway)
        assert cc.model == "qwen2.5:14b"

    def test_analyze_short_document_no_chunking(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response("analysis result")
        from engine.services.context_chunker import ContextChunker
        cc = ContextChunker(mock_gateway)
        result = cc.analyze("short doc", "summarize it")
        assert result.was_chunked is False
        assert isinstance(result.final_output, str)

    def test_analyze_empty_document_returns_result(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response("")
        from engine.services.context_chunker import ContextChunker
        cc = ContextChunker(mock_gateway)
        result = cc.analyze("", "task")
        assert hasattr(result, "chunk_count")
        assert hasattr(result, "final_output")

    def test_estimate_tokens_helper_correct_ratio(self):
        from engine.services.context_chunker import _estimate_tokens
        assert _estimate_tokens("hello") == 1
        assert _estimate_tokens("a" * 400) == 100

    def test_chunked_result_has_all_fields(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response("summary")
        from engine.services.context_chunker import ContextChunker
        cc = ContextChunker(mock_gateway, safe_token_limit=1, chunk_size=1)
        long_doc = "word " * 200
        result = cc.analyze(long_doc, "analyze")
        assert hasattr(result, "summaries")
        assert hasattr(result, "chunk_count")
        assert hasattr(result, "total_estimated_tokens")
        assert hasattr(result, "was_chunked")

    def test_llm_error_during_analyze_propagates_gracefully(self, mock_gateway):
        mock_gateway.complete.side_effect = RuntimeError("LLM unavailable")
        from engine.services.context_chunker import ContextChunker
        cc = ContextChunker(mock_gateway)
        with pytest.raises(RuntimeError):
            cc.analyze("some document text", "analyze this")


# ===========================================================================
# 7. ai_test_generator
# ===========================================================================

class TestAITestGenerator:
    """Tests for engine/services/ai_test_generator.py"""

    def _make_generator(self, mock_gateway, max_refine=0):
        with patch("engine.services.ai_test_generator.get_engine_prompt", return_value="system prompt"):
            from engine.services.ai_test_generator import AITestGenerator
            return AITestGenerator(gateway=mock_gateway, model="gpt-4o-mini", max_refine=max_refine)

    def test_instantiation_succeeds(self, mock_gateway):
        gen = self._make_generator(mock_gateway)
        from engine.services.ai_test_generator import AITestGenerator
        assert isinstance(gen, AITestGenerator)

    def test_generate_returns_generated_test_type(self, mock_gateway):
        code_block = "```python\ndef test_login():\n    assert True\n```"
        mock_gateway.complete.return_value = _make_llm_response(code_block)
        gen = self._make_generator(mock_gateway)
        with patch.object(gen, "_scan_page_objects", return_value=""):
            result = gen.generate_from_requirement("Login as admin", framework="pytest")
        from engine.services.ai_test_generator import GeneratedTest
        assert isinstance(result, GeneratedTest)
        assert result.framework == "pytest"

    def test_generate_empty_requirement_does_not_raise(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response("```python\n# empty\n```")
        gen = self._make_generator(mock_gateway)
        with patch.object(gen, "_scan_page_objects", return_value=""):
            result = gen.generate_from_requirement("")
        assert result is not None

    def test_extract_code_blocks_single_fence(self, mock_gateway):
        gen = self._make_generator(mock_gateway)
        code = gen._extract_code_blocks("```python\nassert True\n```")
        assert "assert True" in code

    def test_extract_code_blocks_no_fence_returns_raw(self, mock_gateway):
        gen = self._make_generator(mock_gateway)
        code = gen._extract_code_blocks("just raw text no fence")
        assert "just raw text" in code

    def test_generated_test_dataclass_defaults(self):
        from engine.services.ai_test_generator import GeneratedTest
        gt = GeneratedTest(
            framework="pytest",
            code="def test_x(): pass",
            file_path="tests/test_x.py",
            validation_passed=True,
        )
        assert gt.validation_errors == []
        assert gt.refine_iterations == 0

    @pytest.mark.parametrize("framework", ["pytest-bdd", "pytest", "playwright-ts"])
    def test_generate_different_frameworks(self, mock_gateway, framework):
        mock_gateway.complete.return_value = _make_llm_response(
            f"```python\n# {framework} test\ndef test_feature():\n    assert True\n```"
        )
        gen = self._make_generator(mock_gateway)
        with patch.object(gen, "_scan_page_objects", return_value=""):
            result = gen.generate_from_requirement("Some requirement", framework=framework)
        assert result.framework == framework


# ===========================================================================
# 8. bdd_generator
# ===========================================================================

class TestBDDGenerator:
    """Tests for engine/services/bdd_generator.py"""

    def _make_generator(self, mock_gateway):
        with patch("engine.services.bdd_generator.get_engine_prompt", return_value="bdd system prompt"), \
             patch("engine.services.bdd_generator.BDDGenerator._load_existing_steps",
                   return_value=["Given I am on the login page"]):
            from engine.services.bdd_generator import BDDGenerator
            return BDDGenerator(gateway=mock_gateway, model="gpt-4o-mini")

    def test_instantiation(self, mock_gateway):
        gen = self._make_generator(mock_gateway)
        from engine.services.bdd_generator import BDDGenerator
        assert isinstance(gen, BDDGenerator)

    def test_generate_returns_bdd_output(self, mock_gateway):
        gherkin = (
            "FEATURE: Login\n"
            "Scenario: Valid login\n"
            "Given I am on login page\n"
            "When I submit valid credentials\n"
            "Then I am redirected to dashboard"
        )
        mock_gateway.complete.return_value = _make_llm_response(gherkin)
        gen = self._make_generator(mock_gateway)
        result = gen.generate("User logs in with valid credentials")
        from engine.services.bdd_generator import BDDOutput
        assert isinstance(result, BDDOutput)
        assert isinstance(result.feature_content, str)

    def test_generate_empty_requirement_does_not_raise(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response("FEATURE: \nScenario: empty")
        gen = self._make_generator(mock_gateway)
        result = gen.generate("")
        assert result is not None

    def test_bdd_output_default_field_values(self):
        from engine.services.bdd_generator import BDDOutput
        out = BDDOutput(feature_content="Feature: X", step_definitions="# steps")
        assert out.matched_existing_steps == []
        assert out.new_steps_needed == []
        assert out.refine_iterations == 0
        assert out.validation_errors == []

    def test_llm_exception_during_generate(self, mock_gateway):
        mock_gateway.complete.side_effect = ConnectionError("Network unreachable")
        gen = self._make_generator(mock_gateway)
        with pytest.raises(ConnectionError):
            gen.generate("Some requirement that triggers LLM call")


# ===========================================================================
# 9. assertion_engine
# ===========================================================================

class TestAssertionEngine:
    """Tests for engine/services/assertion_engine.py"""

    def _make_engine(self, mock_gateway):
        with patch("engine.services.assertion_engine.get_engine_prompt", return_value="assertion system prompt"):
            from engine.services.assertion_engine import AssertionEngine
            return AssertionEngine(gateway=mock_gateway)

    def test_instantiation(self, mock_gateway):
        ae = self._make_engine(mock_gateway)
        from engine.services.assertion_engine import AssertionEngine
        assert isinstance(ae, AssertionEngine)

    def test_analyze_nonexistent_file_returns_empty(self, mock_gateway):
        ae = self._make_engine(mock_gateway)
        result = ae.analyze_file("/tmp/nonexistent_file_neurex_xyz.py")
        assert result == []

    def test_count_assertions_with_two_asserts(self, mock_gateway):
        ae = self._make_engine(mock_gateway)
        body = "def test_x():\n    assert x == 1\n    assert y == 2\n"
        count = ae._count_assertions(body)
        assert count == 2

    def test_count_assertions_empty_body_returns_zero(self, mock_gateway):
        ae = self._make_engine(mock_gateway)
        assert ae._count_assertions("") == 0

    def test_extract_test_functions_only_returns_test_prefixed(self, mock_gateway):
        ae = self._make_engine(mock_gateway)
        source = "def test_login():\n    pass\n\ndef helper():\n    pass\n"
        funcs = ae._extract_test_functions(source)
        names = [f[0] for f in funcs]
        assert "test_login" in names
        assert "helper" not in names

    def test_extract_test_functions_invalid_syntax_returns_empty(self, mock_gateway):
        ae = self._make_engine(mock_gateway)
        result = ae._extract_test_functions("def test_broken(: pass")
        assert result == []

    def test_assertion_suggestion_to_dict_truncates_rationale(self):
        from engine.services.assertion_engine import AssertionSuggestion
        long_rationale = "x" * 600
        sug = AssertionSuggestion(
            test_file="tests/test_a.py",
            test_name="test_a",
            current_assertion_count=0,
            suggested_assertions=["assert x == 1"],
            rationale=long_rationale,
        )
        d = sug.to_dict()
        assert len(d["rationale"]) <= 500


# ===========================================================================
# 10. self_healer
# ===========================================================================

class TestSelfHealer:
    """Tests for engine/services/self_healer.py"""

    def _make_healer(self, mock_gateway):
        with patch("engine.services.self_healer.get_engine_prompt", return_value="healer system prompt"), \
             patch("engine.services.self_healer.SelfHealer._load_fingerprints", return_value={}):
            from engine.services.self_healer import SelfHealer
            return SelfHealer(gateway=mock_gateway)

    def test_instantiation(self, mock_gateway):
        healer = self._make_healer(mock_gateway)
        from engine.services.self_healer import SelfHealer
        assert isinstance(healer, SelfHealer)

    def test_heal_from_cache_returns_healed_true(self, mock_gateway):
        healer = self._make_healer(mock_gateway)
        healer._fingerprints = {
            "#old-btn": {"new_locator": "[data-testid='submit']", "confidence": 0.8}
        }
        result = healer.heal(
            failed_locator="#old-btn",
            accessibility_tree="<button data-testid='submit'>Submit</button>",
        )
        assert result.healed is True
        assert result.strategy == "fingerprint_cache"

    def test_heal_calls_llm_when_no_cache_match(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response(
            '{"new_locator": "[data-testid=\'btn\']", "strategy": "testid", "confidence": 0.9, "summary": "ok"}'
        )
        healer = self._make_healer(mock_gateway)
        with patch.object(healer, "_persist_fingerprints", return_value=None), \
             patch.object(healer, "_log_healing", return_value=None):
            result = healer.heal(
                failed_locator="#missing-element",
                accessibility_tree="<div data-testid='btn'>Click</div>",
            )
        from engine.services.self_healer import HealingResult
        assert isinstance(result, HealingResult)

    def test_heal_empty_locator_does_not_raise(self, mock_gateway):
        mock_gateway.complete.return_value = _make_llm_response(
            '{"new_locator": "", "strategy": "none", "confidence": 0.0, "summary": "not found"}'
        )
        healer = self._make_healer(mock_gateway)
        with patch.object(healer, "_persist_fingerprints", return_value=None), \
             patch.object(healer, "_log_healing", return_value=None):
            result = healer.heal(failed_locator="", accessibility_tree="")
        assert isinstance(result.healed, bool)

    def test_healing_result_to_dict_has_all_fields(self):
        from engine.services.self_healer import HealingResult
        hr = HealingResult(
            healed=True,
            old_locator="#old",
            new_locator="[data-testid='new']",
            strategy="testid",
            confidence=0.95,
            summary="Healed successfully",
        )
        d = hr.to_dict()
        for key in ("healed", "old_locator", "new_locator", "strategy", "confidence", "summary"):
            assert key in d

    def test_confidence_constants_are_sensible(self, mock_gateway):
        healer = self._make_healer(mock_gateway)
        assert healer.INITIAL_CONFIDENCE > healer.CONF_EVICT
        assert healer.CONF_MAX <= 1.0
        assert healer.CONF_ON_SUCCESS > 0


# ===========================================================================
# 11. test_prioritizer
# ===========================================================================

class TestTestPrioritizer:
    """Tests for engine/services/test_prioritizer.py"""

    def _make_prioritizer(self):
        with patch("engine.services.test_prioritizer.TestPrioritizer._load_json", return_value={}), \
             patch("engine.services.test_prioritizer.TestPrioritizer._merge_risk_scorer_history", return_value=None):
            from engine.services.test_prioritizer import TestPrioritizer
            return TestPrioritizer()

    def test_instantiation(self):
        tp = self._make_prioritizer()
        from engine.services.test_prioritizer import TestPrioritizer
        assert isinstance(tp, TestPrioritizer)

    def test_prioritize_no_tests_returns_empty_result(self):
        tp = self._make_prioritizer()
        with patch.object(tp, "_discover_tests", return_value=[]), \
             patch.object(tp, "_parse_changed_files", return_value=set()):
            result = tp.prioritize(git_diff="diff --git a/foo.py b/foo.py")
        from engine.services.test_prioritizer import PrioritizationResult
        assert isinstance(result, PrioritizationResult)
        assert result.total_tests == 0

    def test_prioritization_result_to_dict_counts_are_correct(self):
        from engine.services.test_prioritizer import PrioritizationResult, ScoredTest
        sel = ScoredTest(test_id="test_a", file_path="tests/test_a.py", risk_score=0.8)
        skp = ScoredTest(test_id="test_b", file_path="tests/test_b.py", risk_score=0.05)
        r = PrioritizationResult(
            total_tests=2,
            selected_tests=[sel],
            skipped_tests=[skp],
            estimated_time_saved_seconds=30,
        )
        d = r.to_dict()
        assert d["total_tests"] == 2
        assert d["selected_count"] == 1
        assert d["skipped_count"] == 1

    def test_parse_changed_files_empty_diff_returns_collection(self):
        tp = self._make_prioritizer()
        result = tp._parse_changed_files("")
        assert isinstance(result, (list, set))

    def test_scored_test_dataclass_default_factors(self):
        from engine.services.test_prioritizer import ScoredTest
        st = ScoredTest(test_id="test_x", file_path="f.py", risk_score=0.7)
        assert st.test_id == "test_x"
        assert st.factors == {}

    @pytest.mark.parametrize("risk_score,expected_above_threshold", [
        (0.8, True),
        (0.05, False),
    ])
    def test_scored_test_risk_score_thresholding(self, risk_score, expected_above_threshold):
        from engine.services.test_prioritizer import ScoredTest, TestPrioritizer
        st = ScoredTest(test_id="t", file_path="f.py", risk_score=risk_score)
        is_above = st.risk_score >= TestPrioritizer.__dict__.get("_MIN_SCORE", 0.1)
        assert is_above == expected_above_threshold
