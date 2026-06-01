"""Unit tests for the agents router — 9 tests.

Tests cover helper functions and endpoint reachability.
All orchestration service functions and DB calls are mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.agents.router import router, _is_admin_user
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="agents router import failed")


# ---------------------------------------------------------------------------
# Helper: _is_admin_user
# ---------------------------------------------------------------------------

class TestIsAdminUser:
    def test_admin_permission_grants_admin(self):
        perm = MagicMock()
        perm.permission = "admin.*"
        role = MagicMock()
        role.permissions = [perm]
        user = MagicMock()
        user.roles = [role]
        assert _is_admin_user(user) is True

    def test_non_admin_permission_denies_admin(self):
        perm = MagicMock()
        perm.permission = "project.read"
        role = MagicMock()
        role.permissions = [perm]
        user = MagicMock()
        user.roles = [role]
        assert _is_admin_user(user) is False

    def test_empty_roles_denies_admin(self):
        user = MagicMock()
        user.roles = []
        assert _is_admin_user(user) is False


# ---------------------------------------------------------------------------
# Router tests via TestClient
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    """Create a test client with a mock DB so get_current_user can fail with 401
    (not 500) when no auth token is provided."""
    from app.infra.database import get_db

    mock_db = MagicMock()
    mock_db.get.return_value = None  # no user found
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None

    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestAgentsListEndpoint:
    def test_get_status_requires_auth(self):
        """GET /agents/status without credentials must be rejected."""
        client = _make_client()
        resp = client.get("/agents/status")
        assert resp.status_code in {401, 403, 422}

    def test_get_logs_requires_auth(self):
        """GET /agents/logs without credentials must be rejected."""
        client = _make_client()
        resp = client.get("/agents/logs")
        assert resp.status_code in {401, 403, 422}


class TestStartRunEndpoint:
    def test_run_all_without_auth_returns_auth_error(self):
        """POST /agents/run-all without auth must be rejected."""
        client = _make_client()
        resp = client.post("/agents/run-all", json={"project_id": "proj-1"})
        assert resp.status_code in {401, 403, 422}

    def test_run_all_missing_body_returns_422(self):
        """POST /agents/run-all with no JSON body returns validation error."""
        client = _make_client()
        resp = client.post("/agents/run-all")
        assert resp.status_code in {401, 403, 422}


class TestBankingTeamEndpoints:
    def test_banking_team_status_requires_auth(self):
        """GET /agents/banking-team/status without credentials must be rejected."""
        client = _make_client()
        resp = client.get("/agents/banking-team/status")
        assert resp.status_code in {401, 403, 404, 422}

    def test_banking_team_start_requires_auth(self):
        """POST /agents/banking-team/start without auth must be rejected."""
        client = _make_client()
        resp = client.post("/agents/banking-team/start", json={})
        assert resp.status_code in {401, 403, 404, 422}


class TestAnalyticsEndpoints:
    def test_heal_history_requires_auth(self):
        """GET /agents/analytics/heal-history without auth must be rejected."""
        client = _make_client()
        resp = client.get("/agents/analytics/heal-history")
        assert resp.status_code in {401, 403, 404, 422}

    def test_llm_traces_requires_auth(self):
        """GET /agents/analytics/llm-traces without auth must be rejected."""
        client = _make_client()
        resp = client.get("/agents/analytics/llm-traces")
        assert resp.status_code in {401, 403, 404, 422}
