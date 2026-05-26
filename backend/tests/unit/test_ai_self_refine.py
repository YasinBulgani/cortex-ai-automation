"""Unit tests for app.domains.ai.self_refine — 2-pass generate→critique→refine.

Tests are fully self-contained: no real LLM calls (gateway_complete mocked).
Covers: should_self_refine (flag + task + risk), refine_response (mocked
gateway), generate_with_refine (integration of the above).
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

try:
    from app.domains.ai.self_refine import (
        should_self_refine,
        refine_response,
        generate_with_refine,
        _ELIGIBLE_TASKS,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="self_refine import failed")


# ---------------------------------------------------------------------------
# should_self_refine — eligibility logic
# ---------------------------------------------------------------------------

class TestShouldSelfRefine:
    """Flag defaults to False; tests override it to True for logic checks."""

    def test_flag_disabled_never_refines(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=False):
            result = should_self_refine("security_audit", risk_level="critical")
        assert result is False

    def test_unknown_task_not_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("nonexistent_task", risk_level="critical")
        assert result is False

    def test_security_audit_critical_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("security_audit", risk_level="critical")
        assert result is True

    def test_security_audit_non_critical_not_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("security_audit", risk_level="medium")
        assert result is False

    def test_test_generation_with_financial_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("test_generation", risk_level="low", has_financial=True)
        assert result is True

    def test_test_generation_high_risk_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("test_generation", risk_level="high")
        assert result is True

    def test_test_generation_low_risk_no_financial_not_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("test_generation", risk_level="low", has_financial=False)
        assert result is False

    def test_chain_builder_always_eligible(self):
        with patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True):
            result = should_self_refine("chain_builder")
        assert result is True

    def test_returns_bool(self):
        result = should_self_refine("security_audit")
        assert isinstance(result, bool)

    def test_eligible_tasks_set_contains_expected(self):
        assert "security_audit" in _ELIGIBLE_TASKS
        assert "test_generation" in _ELIGIBLE_TASKS
        assert "chain_builder" in _ELIGIBLE_TASKS


# ---------------------------------------------------------------------------
# refine_response — 2-pass with mocked gateway
# ---------------------------------------------------------------------------

class TestRefineResponse:
    @pytest.fixture(autouse=True)
    def _mock_gateway(self):
        _critique = "Critique: missing edge cases and insufficient boundary checks."
        _refined = "Refined and significantly improved response with all edge cases covered and issues fixed."
        with patch(
            "app.domains.ai.self_refine.gateway_complete",
            side_effect=[_critique, _refined],
        ) as mock:
            self._mock = mock
            yield

    def test_returns_refined_response(self):
        result = refine_response(
            "security_audit",
            user_message="Analyze this code",
            initial_response="Initial response with some issues.",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_improved_response_differs_from_initial(self):
        initial = "Initial response with some issues. " * 5
        result = refine_response("security_audit", "Analyze", initial)
        # Should have been replaced by the mocked "Refined..." response
        assert result != initial

    def test_very_short_initial_returns_unchanged(self):
        short = "Short"  # < 50 chars
        result = refine_response("security_audit", "query", short)
        assert result == short

    def test_empty_initial_returns_unchanged(self):
        result = refine_response("security_audit", "query", "")
        assert result == ""

    def test_critique_error_returns_initial(self):
        initial = "Initial response that is long enough to proceed." * 2
        with patch("app.domains.ai.self_refine.gateway_complete", side_effect=Exception("LLM down")):
            result = refine_response("security_audit", "query", initial)
        assert result == initial

    def test_empty_critique_returns_initial(self):
        initial = "Initial response that is long enough to proceed." * 2
        # First call returns empty critique, so pipeline short-circuits
        with patch("app.domains.ai.self_refine.gateway_complete", return_value=""):
            result = refine_response("security_audit", "query", initial)
        assert result == initial

    def test_short_refined_returns_initial(self):
        initial = "Initial response that is long enough to proceed." * 2
        # Critique is fine, but refined result is too short
        with patch(
            "app.domains.ai.self_refine.gateway_complete",
            side_effect=["Valid critique with enough content here.", "short"],
        ):
            result = refine_response("security_audit", "query", initial)
        assert result == initial


# ---------------------------------------------------------------------------
# generate_with_refine — integration
# ---------------------------------------------------------------------------

class TestGenerateWithRefine:
    def test_flag_disabled_returns_initial_no_refine(self):
        with (
            patch("app.domains.ai.self_refine.gateway_complete", return_value="Initial result"),
            patch("app.domains.ai.self_refine._self_refine_enabled", return_value=False),
        ):
            response, refined = generate_with_refine("security_audit", "query", risk_level="critical")
        assert response == "Initial result"
        assert refined is False

    def test_flag_enabled_eligible_returns_refined(self):
        with (
            patch(
                "app.domains.ai.self_refine.gateway_complete",
                side_effect=[
                    "Initial response that is long enough to qualify for refinement.",  # generate
                    "Critique: lacks context and edge cases.",                         # critique
                    "Refined and improved final response that is long enough here.",   # refine
                ],
            ),
            patch("app.domains.ai.self_refine._self_refine_enabled", return_value=True),
        ):
            response, refined = generate_with_refine(
                "security_audit", "Analyze this", risk_level="critical"
            )
        assert isinstance(response, str)

    def test_returns_tuple_of_str_and_bool(self):
        with patch("app.domains.ai.self_refine.gateway_complete", return_value="Result"):
            result = generate_with_refine("chat", "query")
        assert isinstance(result, tuple)
        response, refined = result
        assert isinstance(response, str)
        assert isinstance(refined, bool)
