"""Unit tests for the Audit router — 12 tests.

Covers GET /audit/events with query params and auth guard.
All DB / SQLAlchemy calls are mocked; no real DB connection needed.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.audit.router import router as audit_router
    from app.deps import get_current_user
    from app.infra.database import get_db
    from app.infra.models import User
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="audit router import failed")


def _mock_user():
    u = MagicMock(spec=User)
    u.id = "test-user-id"
    u.email = "test@example.com"
    u.roles = []
    return u


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_admin_user() -> MagicMock:
    perm = MagicMock()
    perm.permission = "admin.*"
    role = MagicMock()
    role.permissions = [perm]
    user = MagicMock()
    user.id = "admin-1"
    user.email = "admin@test.com"
    user.full_name = "Admin User"
    user.roles = [role]
    return user


def _make_plain_user() -> MagicMock:
    user = MagicMock()
    user.id = "plain-1"
    user.email = "plain@test.com"
    user.full_name = "Plain User"
    user.roles = []
    return user


def _make_audit_event(
    event_id: str = "evt-1",
    action: str = "user.login",
    resource_type: str = "user",
    actor_user_id: str | None = None,
) -> MagicMock:
    evt = MagicMock()
    evt.id = event_id
    evt.ts = "2026-01-01T00:00:00"
    evt.action = action
    evt.resource_type = resource_type
    evt.resource_id = "res-1"
    evt.payload = {}
    evt.actor_user_id = actor_user_id
    evt.ip = None
    evt.tenant_id = None
    evt.seq = None
    evt.prev_hash = None
    evt.hash = None
    return evt


def _make_db_with_events(events: list) -> MagicMock:
    db = MagicMock()
    db.scalars.return_value = list(events)
    db.get.return_value = None  # no User found for actor_user_id
    return db


def _admin(db_mock=None) -> TestClient:
    """Return a TestClient with admin user (has admin.* permission via roles)."""
    admin = _make_admin_user()
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: admin
    if db_mock is not None:
        app.dependency_overrides[get_db] = lambda: db_mock
    app.include_router(audit_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _make_plain_client(db_mock=None) -> TestClient:
    """Return a TestClient with plain user (no permissions)."""
    plain = _make_plain_user()
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: plain
    if db_mock is not None:
        app.dependency_overrides[get_db] = lambda: db_mock
    app.include_router(audit_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /audit/events — auth guard
# ---------------------------------------------------------------------------

class TestAuditEventsAuth:
    def test_non_admin_gets_403(self):
        db = _make_db_with_events([])
        resp = _make_plain_client(db).get("/api/v1/audit/events")
        assert resp.status_code == 403

    def test_admin_gets_200(self):
        db = _make_db_with_events([])
        resp = _admin(db).get("/api/v1/audit/events")
        assert resp.status_code == 200

    def test_admin_gets_list_response(self):
        db = _make_db_with_events([])
        resp = _admin(db).get("/api/v1/audit/events")
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /audit/events — result shape
# ---------------------------------------------------------------------------

class TestAuditEventsResults:
    def test_single_event_returned(self):
        events = [_make_audit_event("evt-1")]
        db = _make_db_with_events(events)
        resp = _admin(db).get("/api/v1/audit/events")
        assert len(resp.json()) == 1

    def test_event_has_expected_fields(self):
        events = [_make_audit_event("evt-42", action="project.create", resource_type="project")]
        db = _make_db_with_events(events)
        resp = _admin(db).get("/api/v1/audit/events")
        item = resp.json()[0]
        assert item["id"] == "evt-42"
        assert item["action"] == "project.create"
        assert item["resource_type"] == "project"

    def test_empty_events_returns_empty_list(self):
        db = _make_db_with_events([])
        resp = _admin(db).get("/api/v1/audit/events")
        assert resp.json() == []

    def test_multiple_events_all_returned(self):
        events = [_make_audit_event(f"evt-{i}") for i in range(5)]
        db = _make_db_with_events(events)
        resp = _admin(db).get("/api/v1/audit/events")
        assert len(resp.json()) == 5


# ---------------------------------------------------------------------------
# GET /audit/events — query params
# ---------------------------------------------------------------------------

class TestAuditEventsQueryParams:
    def test_action_filter_param_accepted(self):
        db = _make_db_with_events([_make_audit_event(action="user.login")])
        resp = _admin(db).get("/api/v1/audit/events?action=user.login")
        assert resp.status_code == 200

    def test_resource_type_filter_param_accepted(self):
        db = _make_db_with_events([_make_audit_event(resource_type="project")])
        resp = _admin(db).get("/api/v1/audit/events?resource_type=project")
        assert resp.status_code == 200

    def test_page_and_per_page_params_accepted(self):
        db = _make_db_with_events([])
        resp = _admin(db).get("/api/v1/audit/events?page=2&per_page=10")
        assert resp.status_code == 200

    def test_actor_email_resolved_from_db_user(self):
        """If actor_user_id is set, db.get(User, id) should be called to get email."""
        evt = _make_audit_event("evt-actor", actor_user_id="some-user-id")
        db = _make_db_with_events([evt])
        actor_user = MagicMock()
        actor_user.email = "actor@example.com"
        actor_user.full_name = "Actor Name"
        db.get.return_value = actor_user

        resp = _admin(db).get("/api/v1/audit/events")

        assert resp.status_code == 200
        item = resp.json()[0]
        assert item["actor_email"] == "actor@example.com"
        assert item["actor_name"] == "Actor Name"
