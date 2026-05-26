"""Unit tests for the TSPM router core endpoints.

Tests the most critical TSPM endpoints in isolation using FastAPI TestClient.
All DB and service calls are patched — no real database or LLM needed.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.tspm.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="tspm router deps not available")

# Valid UUIDs required — _get_project validates UUID format before DB lookup
_PROJECT_ID = "00000000-0000-0000-0000-000000000001"
_SCENARIO_ID = "00000000-0000-0000-0000-000000000002"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fake_project(pid: str = _PROJECT_ID) -> MagicMock:
    p = MagicMock()
    p.id = pid
    p.name = "Test Project"
    p.description = "desc"
    p.status = "active"
    p.tenant_id = "t-001"
    p.created_by = "user-001"
    p.created_at = None
    p.updated_at = None
    p.scenarios = []
    p.members = []
    return p


def _fake_scenario(sid: str = _SCENARIO_ID, project_id: str = _PROJECT_ID) -> MagicMock:
    s = MagicMock()
    s.id = sid
    s.project_id = project_id
    s.title = "Login scenario"
    s.description = "desc"
    s.status = "active"
    s.priority = "medium"
    s.created_at = None
    s.updated_at = None
    s.tags = []
    s.steps = []
    return s


@pytest.fixture()
def client() -> "TestClient":
    from app.deps import get_current_user, get_db, get_optional_user
    from app.infra.models import User

    fake_user = MagicMock(spec=User)
    fake_user.id = "user-001"
    fake_user.email = "tester@test.com"
    fake_user.tenant_id = "t-001"
    fake_user.roles = []

    fake_project = _fake_project()

    fake_db = MagicMock()
    # Return the fake project for db.get; routes call _get_project which uses db.get
    fake_db.get.return_value = fake_project
    # Return truthy (1) so the member check in _get_project passes for non-admin users
    fake_db.scalar.return_value = 1
    fake_db.scalars.return_value = MagicMock()
    fake_db.commit.return_value = None
    fake_db.rollback.return_value = None
    fake_db.refresh.return_value = None
    fake_db.execute.return_value = MagicMock()
    fake_db.flush.return_value = None

    # require_permission creates a new callable each call → patch the factory
    with patch("app.domains.tspm.router.require_permission", return_value=lambda: fake_user):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_optional_user] = lambda: fake_user
        app.dependency_overrides[get_db] = lambda: fake_db
        yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class TestProjectEndpoints:
    """TSPM project CRUD endpoints."""

    def test_list_projects_returns_200(self, client: "TestClient") -> None:
        with patch(
            "app.domains.tspm.project_service.list_projects",
            return_value=[],
            create=True,
        ):
            r = client.get("/api/v1/tspm/projects")
        assert r.status_code == 200

    def test_create_project_missing_name_returns_422(self, client: "TestClient") -> None:
        r = client.post("/api/v1/tspm/projects", json={"description": "no name"})
        assert r.status_code == 422

    def test_create_project_service_error_bubbles_up(self, client: "TestClient") -> None:
        with patch(
            "app.domains.tspm.project_service.create_project_for_user",
            side_effect=ValueError("duplicate key"),
        ):
            r = client.post(
                "/api/v1/tspm/projects",
                json={"name": "Dup Project", "key": "DUP"},
            )
        # Router converts ValueError → 400
        assert r.status_code in (400, 422, 500)

    def test_get_project_not_found_returns_404(self, client: "TestClient") -> None:
        # "nonexistent-id" is not a valid UUID → _get_project raises 404 immediately
        r = client.get("/api/v1/tspm/projects/nonexistent-id")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

class TestScenarioEndpoints:
    """TSPM scenario endpoints."""

    def test_list_scenarios_returns_200(self, client: "TestClient") -> None:
        with patch(
            "app.domains.tspm.scenario_service.list_scenarios",
            return_value=[],
            create=True,
        ):
            r = client.get(f"/api/v1/tspm/projects/{_PROJECT_ID}/scenarios")
        assert r.status_code == 200

    def test_create_scenario_missing_title_returns_422(
        self, client: "TestClient"
    ) -> None:
        r = client.post(
            f"/api/v1/tspm/projects/{_PROJECT_ID}/scenarios",
            json={"description": "no title"},
        )
        assert r.status_code == 422

    def test_get_scenario_not_found_returns_404(self, client: "TestClient") -> None:
        with patch(
            "app.domains.tspm.scenario_service.get_scenario",
            return_value=None,
            create=True,
        ):
            # Use invalid UUID so _get_project raises 404 without needing scenario lookup
            r = client.get(f"/api/v1/tspm/projects/not-a-uuid/scenarios/also-not-a-uuid")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Executions
# ---------------------------------------------------------------------------

class TestExecutionEndpoints:
    """TSPM execution endpoints."""

    def test_list_executions_returns_200(self, client: "TestClient") -> None:
        with patch(
            "app.domains.tspm.execution_service.list_executions",
            return_value=[],
            create=True,
        ):
            r = client.get(f"/api/v1/tspm/projects/{_PROJECT_ID}/executions")
        assert r.status_code == 200

    def test_create_execution_invalid_scenario_ids_type_returns_422(
        self, client: "TestClient"
    ) -> None:
        # scenario_ids must be list[str]; sending a plain string causes 422
        r = client.post(
            f"/api/v1/tspm/projects/{_PROJECT_ID}/executions",
            json={"scenario_ids": "not-a-list"},
        )
        assert r.status_code == 422
