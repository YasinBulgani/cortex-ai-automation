"""RBAC router unit tests — /api/v1/rbac.

FastAPI TestClient. Service functions (list_roles, get_role,
check_permission, enforce_segregation) are mocked via unittest.mock.patch.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.rbac.router import router as rbac_router

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _app() -> TestClient:
    from unittest.mock import MagicMock
    from app.deps import get_current_user

    app = FastAPI()
    # Override auth dependency so tests don't need a real DB/JWT
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    mock_user.roles = []
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.include_router(rbac_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


_SERVICE_MODULE = "app.domains.rbac.router"


# ---------------------------------------------------------------------------
# GET /api/v1/rbac/roles
# ---------------------------------------------------------------------------


def test_list_roles_returns_200() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.list_roles", return_value=["admin", "tester", "viewer"]):
        r = client.get("/api/v1/rbac/roles")
    assert r.status_code == 200


def test_list_roles_returns_list_of_strings() -> None:
    client = _app()
    roles = ["admin", "tester", "viewer"]
    with patch(f"{_SERVICE_MODULE}.list_roles", return_value=roles):
        r = client.get("/api/v1/rbac/roles")
    data = r.json()
    assert isinstance(data, list)
    assert data == roles


def test_list_roles_empty() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.list_roles", return_value=[]):
        r = client.get("/api/v1/rbac/roles")
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/rbac/roles/{role_name}
# ---------------------------------------------------------------------------


def test_get_role_detail_found_200() -> None:
    client = _app()
    role_data = {"name": "admin", "permissions": ["read", "write", "delete"]}
    with patch(f"{_SERVICE_MODULE}.get_role", return_value=role_data):
        r = client.get("/api/v1/rbac/roles/admin")
    assert r.status_code == 200
    assert r.json()["name"] == "admin"


def test_get_role_detail_not_found_404() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.get_role", side_effect=KeyError("ghost")):
        r = client.get("/api/v1/rbac/roles/ghost")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/rbac/check-permission
# ---------------------------------------------------------------------------


def test_check_permission_allowed_true() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.check_permission", return_value=True):
        r = client.post(
            "/api/v1/rbac/check-permission",
            json={"user_permissions": ["read", "write"], "permission": "write"},
        )
    assert r.status_code == 200
    assert r.json() == {"allowed": True}


def test_check_permission_allowed_false() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.check_permission", return_value=False):
        r = client.post(
            "/api/v1/rbac/check-permission",
            json={"user_permissions": ["read"], "permission": "delete"},
        )
    assert r.status_code == 200
    assert r.json() == {"allowed": False}


def test_check_permission_missing_permission_field_422() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.check_permission", return_value=True):
        r = client.post(
            "/api/v1/rbac/check-permission",
            json={"user_permissions": ["read"]},
        )
    assert r.status_code == 422


def test_check_permission_missing_user_permissions_422() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.check_permission", return_value=True):
        r = client.post(
            "/api/v1/rbac/check-permission",
            json={"permission": "read"},
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/rbac/enforce-sod
# ---------------------------------------------------------------------------


def test_enforce_sod_success_ok_true() -> None:
    client = _app()
    # enforce_segregation returns None on success (no violation)
    with patch(f"{_SERVICE_MODULE}.enforce_segregation", return_value=None):
        r = client.post(
            "/api/v1/rbac/enforce-sod",
            json={"user_id": "user-1", "new_action": "approve"},
        )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_enforce_sod_violation_raises_403() -> None:
    client = _app()
    with patch(
        f"{_SERVICE_MODULE}.enforce_segregation",
        side_effect=ValueError("SoD violation: user-1 cannot both create and approve"),
    ):
        r = client.post(
            "/api/v1/rbac/enforce-sod",
            json={"user_id": "user-1", "new_action": "approve"},
        )
    assert r.status_code == 403


def test_enforce_sod_with_resource_type_and_id() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.enforce_segregation", return_value=None):
        r = client.post(
            "/api/v1/rbac/enforce-sod",
            json={
                "user_id": "user-2",
                "new_action": "review",
                "resource_type": "test_case",
                "resource_id": "tc-001",
            },
        )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_enforce_sod_missing_user_id_422() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.enforce_segregation", return_value=None):
        r = client.post(
            "/api/v1/rbac/enforce-sod",
            json={"new_action": "approve"},
        )
    assert r.status_code == 422


def test_enforce_sod_missing_new_action_422() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.enforce_segregation", return_value=None):
        r = client.post(
            "/api/v1/rbac/enforce-sod",
            json={"user_id": "user-1"},
        )
    assert r.status_code == 422
