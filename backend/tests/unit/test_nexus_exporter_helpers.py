"""Unit tests for Nexus Repo exporter pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/nexus_repo/exporter.py:
    _to_gherkin, _to_postman
"""

from __future__ import annotations

import types

import pytest


def _make_project(name: str = "My Project", repo_url: str = "https://github.com/org/repo") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id="proj-1",
        name=name,
        repo_url=repo_url,
    )


def _make_scenario(
    title: str = "Login scenario",
    type: str = "manual",
    feature_area: str = "Authentication",
    priority: str = "high",
    gherkin: str = None,
    notes: str = None,
) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id="sc-1",
        title=title,
        type=type,
        feature_area=feature_area,
        priority=priority,
        gherkin=gherkin,
        notes=notes,
    )


# ── _to_gherkin ───────────────────────────────────────────────────────────────


class TestToGherkin:
    def _call(self, project=None, scenarios=None):
        from app.domains.nexus_repo.exporter import _to_gherkin
        if project is None:
            project = _make_project()
        if scenarios is None:
            scenarios = []
        return _to_gherkin(project, scenarios)

    def test_returns_string(self) -> None:
        assert isinstance(self._call(), str)

    def test_contains_project_name(self) -> None:
        project = _make_project(name="E-Commerce Tests")
        result = self._call(project)
        assert "E-Commerce Tests" in result

    def test_contains_repo_url(self) -> None:
        project = _make_project(repo_url="https://github.com/org/myrepo")
        result = self._call(project)
        assert "https://github.com/org/myrepo" in result

    def test_contains_feature_keyword(self) -> None:
        sc = _make_scenario(feature_area="Authentication")
        result = self._call(scenarios=[sc])
        assert "Feature:" in result

    def test_scenario_title_included(self) -> None:
        sc = _make_scenario(title="User can login with valid credentials")
        result = self._call(scenarios=[sc])
        assert "User can login" in result

    def test_uses_existing_gherkin_if_provided(self) -> None:
        gherkin = "Feature: Login\n  Scenario: Successful login\n    Given user has account\n    When user logs in\n    Then user sees dashboard"
        sc = _make_scenario(gherkin=gherkin)
        result = self._call(scenarios=[sc])
        assert "Successful login" in result

    def test_fallback_template_when_no_gherkin(self) -> None:
        sc = _make_scenario(gherkin=None)
        result = self._call(scenarios=[sc])
        assert "Given" in result or "Scenario:" in result

    def test_multiple_scenarios_included(self) -> None:
        scenarios = [
            _make_scenario(title="Login test", feature_area="Auth"),
            _make_scenario(title="Logout test", feature_area="Auth"),
        ]
        result = self._call(scenarios=scenarios)
        assert "Login test" in result
        assert "Logout test" in result

    def test_different_feature_areas_separated(self) -> None:
        scenarios = [
            _make_scenario(title="Login test", feature_area="Auth"),
            _make_scenario(title="Search test", feature_area="Search"),
        ]
        result = self._call(scenarios=scenarios)
        assert "Auth" in result
        assert "Search" in result

    def test_empty_scenarios_list(self) -> None:
        result = self._call(scenarios=[])
        assert isinstance(result, str)


# ── _to_postman ───────────────────────────────────────────────────────────────


class TestToPostman:
    def _call(self, project=None, scenarios=None):
        from app.domains.nexus_repo.exporter import _to_postman
        if project is None:
            project = _make_project()
        if scenarios is None:
            scenarios = []
        return _to_postman(project, scenarios)

    def test_returns_dict(self) -> None:
        assert isinstance(self._call(), dict)

    def test_has_info_key(self) -> None:
        result = self._call()
        assert "info" in result

    def test_has_item_key(self) -> None:
        result = self._call()
        assert "item" in result

    def test_non_service_scenarios_excluded(self) -> None:
        sc = _make_scenario(type="manual")
        result = self._call(scenarios=[sc])
        assert result["item"] == []

    def test_service_scenarios_included(self) -> None:
        sc = _make_scenario(type="service", title="API Test")
        result = self._call(scenarios=[sc])
        assert len(result["item"]) == 1
        assert result["item"][0]["name"] == "API Test"

    def test_gherkin_method_extraction(self) -> None:
        # Regex: (METHOD)\s+path_token — matches "POST /api/users" pattern directly
        gherkin = "When I POST /api/users with valid data"
        sc = _make_scenario(type="service", gherkin=gherkin)
        result = self._call(scenarios=[sc])
        assert len(result["item"]) == 1
        request = result["item"][0]["request"]
        assert request["method"] == "POST"
        assert "api/users" in request["url"]["raw"]

    def test_collection_name_includes_project_name(self) -> None:
        project = _make_project(name="Banking API")
        result = self._call(project=project)
        info = result.get("info", {})
        assert "Banking API" in info.get("name", "")

    def test_returns_dict_with_schema(self) -> None:
        result = self._call()
        info = result.get("info", {})
        assert "schema" in info

    def test_empty_scenarios(self) -> None:
        result = self._call(scenarios=[])
        assert result["item"] == []
