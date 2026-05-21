"""Shared fixtures for API tests: factories for projects, scenarios, etc."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _unique(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Project factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_project(client: TestClient, auth_headers: dict[str, str]):
    """Factory: creates a project and returns its id."""
    created_ids: list[str] = []

    def _factory(name: str | None = None, description: str = "") -> str:
        name = name or _unique("Proje-")
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": name, "description": description},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        created_ids.append(pid)
        return pid

    yield _factory


@pytest.fixture()
def project_id(create_project) -> str:
    """Convenience: a single ready-to-use project id."""
    return create_project()


# ---------------------------------------------------------------------------
# Scenario factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_scenario(client: TestClient, auth_headers: dict[str, str]):
    """Factory: creates a scenario under a given project."""

    def _factory(
        project_id: str,
        title: str | None = None,
        steps: list[dict[str, Any]] | None = None,
    ) -> str:
        title = title or _unique("Senaryo-")
        payload: dict[str, Any] = {"title": title}
        if steps is not None:
            payload["steps"] = steps
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios",
            json=payload,
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory


# ---------------------------------------------------------------------------
# Requirement factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_requirement(client: TestClient, auth_headers: dict[str, str]):
    """Factory: creates a requirement under a given project."""

    def _factory(
        project_id: str,
        external_id: str | None = None,
        title: str | None = None,
        priority: str = "medium",
    ) -> str:
        external_id = external_id or _unique("REQ-")
        title = title or _unique("Gereksinim-")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/requirements",
            json={
                "external_id": external_id,
                "title": title,
                "priority": priority,
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory


# ---------------------------------------------------------------------------
# Execution factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_execution(client: TestClient, auth_headers: dict[str, str]):
    """Factory: creates an execution run under a given project."""

    def _factory(
        project_id: str,
        name: str | None = None,
        scenario_ids: list[str] | None = None,
    ) -> str:
        name = name or _unique("Koşu-")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/executions",
            json={"name": name, "scenario_ids": scenario_ids or []},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory


# ---------------------------------------------------------------------------
# Regression set factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_regression_set(client: TestClient, auth_headers: dict[str, str]):

    def _factory(project_id: str, name: str | None = None) -> str:
        name = name or _unique("RegSet-")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/regression-sets",
            json={"name": name},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory


# ---------------------------------------------------------------------------
# Flow factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_flow(client: TestClient, auth_headers: dict[str, str]):

    def _factory(project_id: str, name: str | None = None) -> str:
        name = name or _unique("Akış-")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/flows",
            json={"name": name},
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory


# ---------------------------------------------------------------------------
# Schedule factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_schedule(client: TestClient, auth_headers: dict[str, str]):

    def _factory(
        project_id: str,
        name: str | None = None,
        cron: str = "0 2 * * *",
        scenario_ids: list[str] | None = None,
    ) -> str:
        name = name or _unique("Zamanlama-")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/schedules",
            json={
                "name": name,
                "cron_expression": cron,
                "scenario_ids": scenario_ids or [],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory


# ---------------------------------------------------------------------------
# Test data set factory
# ---------------------------------------------------------------------------

@pytest.fixture()
def create_test_data(client: TestClient, auth_headers: dict[str, str]):

    def _factory(
        project_id: str,
        name: str | None = None,
        columns: list[dict] | None = None,
        rows: list[dict] | None = None,
    ) -> str:
        name = name or _unique("Veri-")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/test-data",
            json={
                "name": name,
                "columns": columns or [{"name": "col1"}],
                "rows": rows or [{"col1": "val1"}],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return _factory
