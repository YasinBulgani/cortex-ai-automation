"""HTTP integration tests for scenarios context router.

Uses FastAPI TestClient. In-memory repos are reset before each test.
The project repo is also reset so cross-context checks work correctly.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contexts.projects.api.router import router as projects_router, _projects_repo
from app.contexts.scenarios.api.router import router as scenarios_router, _scenarios_repo
from app.contexts.scenarios.domain import ScenarioStep, StepType


@pytest.fixture(autouse=True)
def reset_repos():
    _projects_repo.clear()
    _scenarios_repo.clear()
    yield
    _projects_repo.clear()
    _scenarios_repo.clear()


@pytest.fixture()
def client():
    from app.deps import get_current_user

    class _FakeUser:
        id = "test-user"

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(scenarios_router, prefix="/api/v1")
    return TestClient(app)


def _create_project(client, name: str = "TestProject") -> str:
    r = client.post("/api/v1/contexts/projects", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


# ─── CREATE ─────────────────────────────────────────────────────────────────

def test_create_scenario_returns_201(client):
    pid = _create_project(client)
    r = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "Login testi"})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Login testi"
    assert body["status"] == "draft"
    assert body["project_id"] == pid


def test_create_scenario_inactive_project_returns_422(client):
    pid = _create_project(client)
    client.delete(f"/api/v1/contexts/projects/{pid}")
    r = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "X"})
    assert r.status_code == 422


def test_create_scenario_nonexistent_project_returns_422(client):
    r = client.post("/api/v1/contexts/scenarios", json={
        "project_id": str(uuid4()), "title": "X"
    })
    assert r.status_code == 422


def test_create_scenario_empty_title_returns_422(client):
    pid = _create_project(client)
    r = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": ""})
    assert r.status_code == 422


# ─── LIST / GET ──────────────────────────────────────────────────────────────

def test_list_scenarios_requires_project_id(client):
    r = client.get("/api/v1/contexts/scenarios")
    assert r.status_code == 422


def test_list_scenarios_returns_only_for_project(client):
    pid1 = _create_project(client, "P1")
    pid2 = _create_project(client, "P2")
    client.post("/api/v1/contexts/scenarios", json={"project_id": pid1, "title": "A"})
    client.post("/api/v1/contexts/scenarios", json={"project_id": pid1, "title": "B"})
    client.post("/api/v1/contexts/scenarios", json={"project_id": pid2, "title": "C"})

    r = client.get(f"/api/v1/contexts/scenarios?project_id={pid1}")
    assert r.status_code == 200
    titles = {s["title"] for s in r.json()}
    assert titles == {"A", "B"}


def test_get_scenario_by_id(client):
    pid = _create_project(client)
    sid = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "Logout"}).json()["id"]
    r = client.get(f"/api/v1/contexts/scenarios/{sid}")
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_get_missing_scenario_returns_404(client):
    r = client.get("/api/v1/contexts/scenarios/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ─── SUBMIT FOR REVIEW ───────────────────────────────────────────────────────

def test_submit_without_steps_returns_422(client):
    pid = _create_project(client)
    sid = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "Empty"}).json()["id"]
    r = client.post(f"/api/v1/contexts/scenarios/{sid}/submit")
    assert r.status_code == 422


def test_submit_with_steps_added_directly(client):
    """Add a step directly to the in-memory repo, then submit via API."""
    from app.contexts.scenarios.domain import ScenarioId

    pid = _create_project(client)
    sid_str = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "S"}).json()["id"]
    from uuid import UUID
    sc = _scenarios_repo._by_id[ScenarioId(UUID(sid_str))]
    sc.add_step(ScenarioStep(type=StepType.GIVEN, text="Sayfa açık", order=0))

    r = client.post(f"/api/v1/contexts/scenarios/{sid_str}/submit")
    assert r.status_code == 204

    r2 = client.get(f"/api/v1/contexts/scenarios/{sid_str}")
    assert r2.json()["status"] == "review"


def test_submit_missing_scenario_returns_404(client):
    r = client.post("/api/v1/contexts/scenarios/00000000-0000-0000-0000-000000000000/submit")
    assert r.status_code == 404


# ─── APPROVE ─────────────────────────────────────────────────────────────────

def test_approve_after_submit_succeeds(client):
    from app.contexts.scenarios.domain import ScenarioId
    from uuid import UUID

    pid = _create_project(client)
    sid_str = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "T"}).json()["id"]
    sc = _scenarios_repo._by_id[ScenarioId(UUID(sid_str))]
    sc.add_step(ScenarioStep(type=StepType.WHEN, text="Aksiyon", order=0))
    client.post(f"/api/v1/contexts/scenarios/{sid_str}/submit")

    r = client.post(f"/api/v1/contexts/scenarios/{sid_str}/approve", json={"approver": "qa-lead"})
    assert r.status_code == 204

    assert client.get(f"/api/v1/contexts/scenarios/{sid_str}").json()["status"] == "approved"


def test_approve_draft_returns_422(client):
    pid = _create_project(client)
    sid = client.post("/api/v1/contexts/scenarios", json={"project_id": pid, "title": "Draft"}).json()["id"]
    r = client.post(f"/api/v1/contexts/scenarios/{sid}/approve", json={"approver": "lead"})
    assert r.status_code == 422
