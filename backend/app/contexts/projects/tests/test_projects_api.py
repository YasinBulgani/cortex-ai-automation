"""HTTP integration tests for projects context router.

Uses FastAPI TestClient + minimal app (no DB, no auth middleware).
The router's in-memory singleton is reset before each test.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.contexts.projects.api.router import router, _projects_repo


@pytest.fixture(autouse=True)
def reset_repo():
    _projects_repo.clear()
    yield
    _projects_repo.clear()


@pytest.fixture()
def client():
    app = FastAPI()

    # Bypass auth: override get_current_user dependency
    from app.deps import get_current_user

    class _FakeUser:
        id = "test-user"

    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


# ─── CREATE ─────────────────────────────────────────────────────────────────

def test_create_project_returns_201(client):
    r = client.post("/api/v1/contexts/projects", json={"name": "Alpha"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Alpha"
    assert body["status"] == "active"


def test_create_project_duplicate_returns_409(client):
    client.post("/api/v1/contexts/projects", json={"name": "Dupe"})
    r = client.post("/api/v1/contexts/projects", json={"name": "Dupe"})
    assert r.status_code == 409


def test_create_project_empty_name_rejected(client):
    r = client.post("/api/v1/contexts/projects", json={"name": ""})
    assert r.status_code == 422


# ─── LIST / GET ──────────────────────────────────────────────────────────────

def test_list_projects_empty(client):
    r = client.get("/api/v1/contexts/projects")
    assert r.status_code == 200
    assert r.json() == []


def test_list_projects_returns_active_only(client):
    r1 = client.post("/api/v1/contexts/projects", json={"name": "Keep"})
    r2 = client.post("/api/v1/contexts/projects", json={"name": "Archive"})
    pid = r2.json()["id"]
    client.delete(f"/api/v1/contexts/projects/{pid}")

    listed = client.get("/api/v1/contexts/projects").json()
    names = [p["name"] for p in listed]
    assert "Keep" in names
    assert "Archive" not in names


def test_get_project_returns_200(client):
    pid = client.post("/api/v1/contexts/projects", json={"name": "Bravo"}).json()["id"]
    r = client.get(f"/api/v1/contexts/projects/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid


def test_get_missing_project_returns_404(client):
    r = client.get("/api/v1/contexts/projects/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ─── RENAME ──────────────────────────────────────────────────────────────────

def test_rename_project_succeeds(client):
    pid = client.post("/api/v1/contexts/projects", json={"name": "Old"}).json()["id"]
    r = client.patch(f"/api/v1/contexts/projects/{pid}/name", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_rename_to_existing_name_returns_409(client):
    client.post("/api/v1/contexts/projects", json={"name": "Taken"})
    pid = client.post("/api/v1/contexts/projects", json={"name": "Other"}).json()["id"]
    r = client.patch(f"/api/v1/contexts/projects/{pid}/name", json={"name": "Taken"})
    assert r.status_code == 409


# ─── ARCHIVE ─────────────────────────────────────────────────────────────────

def test_archive_project_returns_204(client):
    pid = client.post("/api/v1/contexts/projects", json={"name": "ToArchive"}).json()["id"]
    r = client.delete(f"/api/v1/contexts/projects/{pid}")
    assert r.status_code == 204


def test_archive_sets_status_archived(client):
    pid = client.post("/api/v1/contexts/projects", json={"name": "Gone"}).json()["id"]
    client.delete(f"/api/v1/contexts/projects/{pid}")
    r = client.get(f"/api/v1/contexts/projects/{pid}")
    assert r.json()["status"] == "archived"


def test_archive_missing_returns_404(client):
    r = client.delete("/api/v1/contexts/projects/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
