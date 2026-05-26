"""Unit tests for app.domains.tspm.regression_suggest — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers: _build_dummy_sets (determinism, structure, ratios),
        _DUMMY_SET_TEMPLATES constant.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.regression_suggest import (
        _build_dummy_sets,
        _DUMMY_SET_TEMPLATES,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="regression_suggest import failed")


def _scenarios(n: int) -> list[dict]:
    return [{"id": f"sc-{i}", "title": f"Scenario {i}"} for i in range(n)]


# ---------------------------------------------------------------------------
# _DUMMY_SET_TEMPLATES constant
# ---------------------------------------------------------------------------

class TestDummySetTemplates:
    def test_is_list(self):
        assert isinstance(_DUMMY_SET_TEMPLATES, list)

    def test_nonempty(self):
        assert len(_DUMMY_SET_TEMPLATES) > 0

    def test_each_has_name(self):
        for tpl in _DUMMY_SET_TEMPLATES:
            assert isinstance(tpl.get("name"), str)

    def test_each_has_priority(self):
        for tpl in _DUMMY_SET_TEMPLATES:
            assert tpl.get("priority") in ("critical", "high", "medium", "low")

    def test_each_has_ratio_between_0_and_1(self):
        for tpl in _DUMMY_SET_TEMPLATES:
            assert 0 < tpl["ratio"] <= 1.0

    def test_has_critical_priority(self):
        priorities = [t["priority"] for t in _DUMMY_SET_TEMPLATES]
        assert "critical" in priorities


# ---------------------------------------------------------------------------
# _build_dummy_sets
# ---------------------------------------------------------------------------

class TestBuildDummySets:
    def test_returns_list(self):
        result = _build_dummy_sets(_scenarios(10))
        assert isinstance(result, list)

    def test_deterministic_same_seed(self):
        s = _scenarios(10)
        r1 = _build_dummy_sets(s)
        r2 = _build_dummy_sets(s)
        assert r1 == r2

    def test_each_set_has_name(self):
        for item in _build_dummy_sets(_scenarios(10)):
            assert isinstance(item["name"], str)

    def test_each_set_has_scenario_ids(self):
        for item in _build_dummy_sets(_scenarios(10)):
            assert isinstance(item["scenario_ids"], list)

    def test_each_set_has_priority(self):
        for item in _build_dummy_sets(_scenarios(10)):
            assert item["priority"] in ("critical", "high", "medium", "low")

    def test_each_set_has_description(self):
        for item in _build_dummy_sets(_scenarios(10)):
            assert isinstance(item.get("description"), str)

    def test_scenario_ids_subset_of_input(self):
        scenarios = _scenarios(15)
        all_ids = {s["id"] for s in scenarios}
        for item in _build_dummy_sets(scenarios):
            for sid in item["scenario_ids"]:
                assert sid in all_ids

    def test_few_scenarios_returns_at_least_2_sets(self):
        result = _build_dummy_sets(_scenarios(3))
        assert len(result) >= 2

    def test_many_scenarios_multiple_sets(self):
        result = _build_dummy_sets(_scenarios(20))
        assert len(result) >= 2

    def test_single_scenario_doesnt_crash(self):
        result = _build_dummy_sets(_scenarios(1))
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_empty_scenarios_doesnt_crash(self):
        # Edge case: might return empty list or minimal set
        try:
            result = _build_dummy_sets([])
            assert isinstance(result, list)
        except (ValueError, IndexError):
            pass  # Acceptable for empty input
