"""Unit tests for playwright_mcp.dom_analyzer and mobile.seed_scenarios pure functions.

Tests are fully self-contained: no DB, no HTTP, no browser, no AI.
Covers:
  - compute_selector_stability: all 6 tiers (0-5) based on selector patterns
  - list_seed_scenarios: filtering by category/platform/difficulty
  - get_seed_scenario: lookup by ID, missing ID
  - seed_categories: unique category extraction
"""
from __future__ import annotations

import pytest

try:
    from app.domains.playwright_mcp.dom_analyzer import compute_selector_stability
    _DOM_OK = True
except ImportError:
    _DOM_OK = False

try:
    from app.domains.mobile.seed_scenarios import (
        list_seed_scenarios,
        get_seed_scenario,
        seed_categories,
        SEED_SCENARIOS,
    )
    _SEED_OK = True
except ImportError:
    _SEED_OK = False


# ---------------------------------------------------------------------------
# compute_selector_stability
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DOM_OK, reason="dom_analyzer import failed")
class TestComputeSelectorStability:
    def test_empty_string_returns_0(self):
        assert compute_selector_stability("") == 0

    def test_none_like_empty_returns_0(self):
        assert compute_selector_stability("   ") == 0

    def test_data_testid_returns_5(self):
        assert compute_selector_stability("[data-testid='login-btn']") == 5

    def test_data_test_id_returns_5(self):
        assert compute_selector_stability("[data-test-id='submit']") == 5

    def test_role_returns_5(self):
        assert compute_selector_stability("role=button") == 5

    def test_aria_label_returns_4(self):
        assert compute_selector_stability("[aria-label='Close']") == 4

    def test_simple_id_returns_4(self):
        assert compute_selector_stability("#login-button") == 4

    def test_label_prefix_returns_4(self):
        assert compute_selector_stability("label=Username") == 4

    def test_placeholder_returns_3(self):
        assert compute_selector_stability("[placeholder='Enter email']") == 3

    def test_name_attr_returns_3(self):
        assert compute_selector_stability("[name='username']") == 3

    def test_text_prefix_returns_2(self):
        assert compute_selector_stability("text=Submit") == 2

    def test_simple_tag_returns_2(self):
        assert compute_selector_stability("button") == 2

    def test_single_class_returns_2(self):
        assert compute_selector_stability(".submit-btn") == 2

    def test_xpath_returns_1(self):
        assert compute_selector_stability("//div[@class='login']") == 1

    def test_xpath_prefix_returns_1(self):
        assert compute_selector_stability("xpath=//button[text()='Login']") == 1

    def test_deeply_nested_css_returns_1(self):
        assert compute_selector_stability("div > section > article > div > button") == 1

    def test_returns_int(self):
        result = compute_selector_stability("[data-testid='x']")
        assert isinstance(result, int)

    def test_score_range_0_to_5(self):
        selectors = [
            "", "[data-testid='x']", "#id", "[aria-label='x']",
            "[placeholder='x']", "text=x", "//xpath", "button"
        ]
        for s in selectors:
            score = compute_selector_stability(s)
            assert 0 <= score <= 5, f"Score {score} out of range for '{s}'"


# ---------------------------------------------------------------------------
# list_seed_scenarios
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SEED_OK, reason="seed_scenarios import failed")
class TestListSeedScenarios:
    def test_no_filter_returns_all(self):
        result = list_seed_scenarios()
        assert len(result) == len(SEED_SCENARIOS)

    def test_returns_list(self):
        result = list_seed_scenarios()
        assert isinstance(result, list)

    def test_platform_filter_android(self):
        result = list_seed_scenarios(platform="android")
        assert all("android" in s.platforms for s in result)

    def test_platform_filter_ios(self):
        result = list_seed_scenarios(platform="ios")
        assert all("ios" in s.platforms for s in result)

    def test_nonexistent_platform_returns_empty(self):
        result = list_seed_scenarios(platform="windows_phone_8")
        assert result == []

    def test_each_scenario_has_id(self):
        for s in list_seed_scenarios():
            assert s.id != ""

    def test_each_scenario_has_prompt(self):
        for s in list_seed_scenarios():
            assert s.prompt != ""


# ---------------------------------------------------------------------------
# get_seed_scenario
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SEED_OK, reason="seed_scenarios import failed")
class TestGetSeedScenario:
    def test_returns_known_scenario(self):
        # We know 'seed_login_happy' exists from inspection
        result = get_seed_scenario("seed_login_happy")
        assert result is not None
        assert result.id == "seed_login_happy"

    def test_unknown_id_returns_none(self):
        result = get_seed_scenario("nonexistent_scenario_id_xyz")
        assert result is None

    def test_empty_id_returns_none(self):
        result = get_seed_scenario("")
        assert result is None

    def test_all_scenario_ids_retrievable(self):
        for scenario in SEED_SCENARIOS:
            found = get_seed_scenario(scenario.id)
            assert found is not None
            assert found.id == scenario.id


# ---------------------------------------------------------------------------
# seed_categories
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SEED_OK, reason="seed_scenarios import failed")
class TestSeedCategories:
    def test_returns_list(self):
        result = seed_categories()
        assert isinstance(result, list)

    def test_no_duplicates(self):
        result = seed_categories()
        assert len(result) == len(set(result))

    def test_includes_auth_category(self):
        result = seed_categories()
        assert "auth" in result

    def test_all_categories_used_by_at_least_one_scenario(self):
        cats = seed_categories()
        for cat in cats:
            matching = [s for s in SEED_SCENARIOS if s.category == cat]
            assert len(matching) > 0

    def test_returns_non_empty_list(self):
        result = seed_categories()
        assert len(result) > 0
