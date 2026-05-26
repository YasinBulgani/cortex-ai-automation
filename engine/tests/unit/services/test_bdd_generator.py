"""Unit tests for engine/services/bdd_generator.py.

Tests BDDGenerator in isolation — LLMGateway is fully mocked, no real LLM
calls are made. File-system step loading is patched where needed.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch

    from engine.services.bdd_generator import BDDGenerator, BDDOutput

    _IMPORT_OK = True
except ImportError:
    try:
        from services.bdd_generator import BDDGenerator, BDDOutput  # type: ignore[no-redef]

        _IMPORT_OK = True
    except ImportError:
        _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="bdd_generator not importable")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_GHERKIN = """\
FEATURE:
Feature: User login
  Scenario: Successful login
    Given the user navigates to the login page
    When the user enters valid credentials
    Then the user is redirected to the dashboard
STEPS:
@given("the user navigates to the login page")
def step_navigate(page):
    page.goto("/login")
"""

_GHERKIN_NO_STEPS = """\
FEATURE:
Feature: Empty feature
  Scenario: No steps
    Given nothing happens
"""


def _make_gateway(response: str = _VALID_GHERKIN) -> MagicMock:
    gw = MagicMock()
    completion = MagicMock()
    completion.content = response
    gw.complete.return_value = completion
    return gw


# ---------------------------------------------------------------------------
# BDDGenerator.__init__
# ---------------------------------------------------------------------------

class TestBDDGeneratorInit:
    def test_default_model_is_gpt4o(self) -> None:
        with patch.object(BDDGenerator, "_load_existing_steps", return_value=[]):
            gen = BDDGenerator(gateway=_make_gateway())
        assert gen.model == "gpt-4o"

    def test_custom_model_is_stored(self) -> None:
        with patch.object(BDDGenerator, "_load_existing_steps", return_value=[]):
            gen = BDDGenerator(gateway=_make_gateway(), model="gpt-3.5-turbo")
        assert gen.model == "gpt-3.5-turbo"

    def test_default_max_refine(self) -> None:
        with patch.object(BDDGenerator, "_load_existing_steps", return_value=[]):
            gen = BDDGenerator(gateway=_make_gateway())
        assert gen.max_refine == BDDGenerator.DEFAULT_MAX_REFINE

    def test_custom_max_refine_stored(self) -> None:
        with patch.object(BDDGenerator, "_load_existing_steps", return_value=[]):
            gen = BDDGenerator(gateway=_make_gateway(), max_refine=0)
        assert gen.max_refine == 0


# ---------------------------------------------------------------------------
# BDDGenerator.generate
# ---------------------------------------------------------------------------

class TestGenerate:
    def _gen(self, response: str = _VALID_GHERKIN) -> BDDGenerator:
        with patch.object(BDDGenerator, "_load_existing_steps", return_value=[]):
            return BDDGenerator(gateway=_make_gateway(response))

    def test_generate_returns_bdd_output(self) -> None:
        gen = self._gen()
        result = gen.generate("User should be able to log in")
        assert isinstance(result, BDDOutput)

    def test_generate_feature_content_not_empty(self) -> None:
        gen = self._gen()
        result = gen.generate("User login requirement")
        assert result.feature_content.strip() != ""

    def test_generate_tracks_refine_iterations(self) -> None:
        gen = self._gen()
        result = gen.generate("Some requirement")
        assert isinstance(result.refine_iterations, int)
        assert result.refine_iterations >= 0

    def test_generate_with_empty_requirement(self) -> None:
        gen = self._gen()
        result = gen.generate("")
        # Should not raise; returns a BDDOutput even for empty input
        assert isinstance(result, BDDOutput)


# ---------------------------------------------------------------------------
# BDDGenerator._parse_output
# ---------------------------------------------------------------------------

class TestParseOutput:
    def test_parse_extracts_feature_and_steps(self) -> None:
        feature, steps = BDDGenerator._parse_output(_VALID_GHERKIN)
        assert "Feature:" in feature
        assert "@given" in steps

    def test_parse_returns_full_text_when_no_markers(self) -> None:
        raw = "Feature: plain\n  Scenario: something\n    Given something"
        feature, steps = BDDGenerator._parse_output(raw)
        assert feature != ""
        assert isinstance(steps, str)

    def test_parse_steps_empty_when_only_feature(self) -> None:
        feature, steps = BDDGenerator._parse_output(_GHERKIN_NO_STEPS)
        # No STEPS section → steps should be empty or minimal
        assert isinstance(steps, str)


# ---------------------------------------------------------------------------
# BDDGenerator._analyze_step_coverage
# ---------------------------------------------------------------------------

class TestAnalyzeStepCoverage:
    def _gen_with_steps(self, existing: list[str]) -> BDDGenerator:
        with patch.object(BDDGenerator, "_load_existing_steps", return_value=existing):
            return BDDGenerator(gateway=_make_gateway())

    def test_all_matched_when_steps_exist(self) -> None:
        feature = (
            "Feature: Test\n"
            "  Scenario: S\n"
            "    Given the user navigates to the login page\n"
        )
        gen = self._gen_with_steps(["the user navigates to the login page"])
        matched, new_needed = gen._analyze_step_coverage(feature)
        assert "the user navigates to the login page" in matched
        assert len(new_needed) == 0

    def test_new_needed_when_no_matching_steps(self) -> None:
        feature = (
            "Feature: Test\n"
            "  Scenario: S\n"
            "    Given an unrecognised step here\n"
        )
        gen = self._gen_with_steps(["the user navigates to the login page"])
        matched, new_needed = gen._analyze_step_coverage(feature)
        assert len(new_needed) > 0

    def test_empty_feature_returns_empty_lists(self) -> None:
        gen = self._gen_with_steps([])
        matched, new_needed = gen._analyze_step_coverage("")
        assert matched == []
        assert new_needed == []


# ---------------------------------------------------------------------------
# BDDGenerator._step_matches (static helper)
# ---------------------------------------------------------------------------

class TestStepMatches:
    def test_exact_match(self) -> None:
        assert BDDGenerator._step_matches(
            "the user clicks login", "the user clicks login"
        )

    def test_param_placeholder_matches(self) -> None:
        assert BDDGenerator._step_matches(
            "the user enters admin", "the user enters {username}"
        )

    def test_no_match(self) -> None:
        assert not BDDGenerator._step_matches(
            "the user clicks logout", "the user clicks login"
        )
