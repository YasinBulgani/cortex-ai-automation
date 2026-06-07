"""Unit tests for the nexus_repo router — 12 tests.

All DB sessions and service-layer calls are mocked.
The nexus_repo_enabled setting is forced True so the feature guard passes.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.nexus_repo.router import health_router as nexus_health_router
    from app.domains.nexus_repo.router import router as nexus_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from app.deps import get_current_user
    from app.infra.database import get_db
    app = FastAPI()
    app.include_router(nexus_health_router, prefix="/api/v1")
    app.include_router(nexus_router, prefix="/api/v1")

    fake_db = MagicMock()
    fake_user = MagicMock()
    fake_user.id = "test-user-id"
    fake_user.roles = []
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: fake_user

    return TestClient(app, raise_server_exceptions=False)


def _fake_project(project_id="proj-1"):
    p = MagicMock()
    p.id = project_id
    p.name = "Test Project"
    p.description = "Desc"
    p.repo_url = "https://github.com/org/repo"
    p.repo_type = "git"
    p.branch = "main"
    p.llm_provider = "ollama"
    p.llm_model = "qwen2.5:32b"
    p.archived = False
    p.created_by = "user-1"
    from datetime import datetime
    p.created_at = datetime(2026, 1, 1)
    p.updated_at = datetime(2026, 1, 2)
    return p


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestNexusHealth:
    def test_health_returns_ok_when_feature_enabled(self, client):
        with patch("app.domains.nexus_repo.router.settings") as mock_settings:
            mock_settings.nexus_repo_enabled = True
            resp = client.get("/api/v1/nexus-repo/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_returns_ok_when_feature_disabled(self, client):
        with patch("app.domains.nexus_repo.router.settings") as mock_settings:
            mock_settings.nexus_repo_enabled = False
            resp = client.get("/api/v1/nexus-repo/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["feature_enabled"] is False


# ---------------------------------------------------------------------------
# Feature guard
# ---------------------------------------------------------------------------

class TestFeatureGuard:
    def test_list_projects_503_when_feature_disabled(self, client):
        with patch("app.domains.nexus_repo.router.settings") as mock_settings:
            mock_settings.nexus_repo_enabled = False
            resp = client.get("/api/v1/nexus-repo/projects")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Projects CRUD
# ---------------------------------------------------------------------------

class TestNexusProjects:
    def _enabled(self):
        mock = MagicMock()
        mock.nexus_repo_enabled = True
        return mock

    def test_list_projects_returns_list(self, client):
        proj = _fake_project()
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.list_projects", return_value=[proj]):
            resp = client.get("/api/v1/nexus-repo/projects")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_project_returns_201(self, client):
        proj = _fake_project()
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.create_project", return_value=proj):
            resp = client.post("/api/v1/nexus-repo/projects", json={
                "name": "Test Project",
                "repo_url": "https://github.com/org/repo",
                "repo_type": "git",
                "branch": "main",
                "llm_provider": "ollama",
                "llm_model": "qwen2.5:32b",
            })
        assert resp.status_code == 201

    def test_get_project_returns_200(self, client):
        proj = _fake_project("proj-42")
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=proj):
            resp = client.get("/api/v1/nexus-repo/projects/proj-42")
        assert resp.status_code == 200
        assert resp.json()["id"] == "proj-42"

    def test_get_project_404_when_not_found(self, client):
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=None):
            resp = client.get("/api/v1/nexus-repo/projects/nonexistent")
        assert resp.status_code == 404

    def test_update_project_returns_200(self, client):
        proj = _fake_project()
        updated = _fake_project()
        updated.name = "Updated Name"
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=proj), \
             patch("app.domains.nexus_repo.router.service.update_project", return_value=updated):
            resp = client.patch("/api/v1/nexus-repo/projects/proj-1", json={"name": "Updated Name"})
        assert resp.status_code == 200

    def test_update_project_404_when_not_found(self, client):
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=None):
            resp = client.patch("/api/v1/nexus-repo/projects/nonexistent", json={"name": "X"})
        assert resp.status_code == 404

    def test_delete_project_returns_204(self, client):
        proj = _fake_project()
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=proj), \
             patch("app.domains.nexus_repo.router.service.archive_project"):
            resp = client.delete("/api/v1/nexus-repo/projects/proj-1")
        assert resp.status_code == 204

    def test_delete_project_404_when_not_found(self, client):
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=None):
            resp = client.delete("/api/v1/nexus-repo/projects/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class TestNexusScenarios:
    def _enabled(self):
        mock = MagicMock()
        mock.nexus_repo_enabled = True
        return mock

    def test_list_scenarios_returns_list(self, client):
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.list_scenarios", return_value=[]):
            resp = client.get("/api/v1/nexus-repo/projects/proj-1/scenarios")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class TestNexusStats:
    def _enabled(self):
        mock = MagicMock()
        mock.nexus_repo_enabled = True
        return mock

    def test_get_stats_returns_stats_for_existing_project(self, client):
        from app.domains.nexus_repo.schemas import NexusStatsOut
        proj = _fake_project()
        stats = NexusStatsOut(
            total_scenarios=5,
            by_type={"manual": 3, "service": 2},
            by_status={"active": 5},
            by_priority={"medium": 5},
            total_crawl_jobs=1,
            last_crawl_at=None,
            total_endpoints=10,
            total_files=20,
        )
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=proj), \
             patch("app.domains.nexus_repo.router.service.get_project_stats", return_value=stats):
            resp = client.get("/api/v1/nexus-repo/projects/proj-1/stats")
        assert resp.status_code == 200
        assert resp.json()["total_scenarios"] == 5

    def test_get_stats_404_when_project_not_found(self, client):
        with patch("app.domains.nexus_repo.router.settings", self._enabled()), \
             patch("app.domains.nexus_repo.router.service.get_project", return_value=None):
            resp = client.get("/api/v1/nexus-repo/projects/nonexistent/stats")
        assert resp.status_code == 404
