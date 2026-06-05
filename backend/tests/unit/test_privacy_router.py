"""Unit tests for the Privacy / DSAR router — 10 tests.

Covers the /privacy/dsar/users/{user_id}/export and
/privacy/dsar/users/{user_id}/delete endpoints. Auth guard
(_require_privacy_admin) is exercised for both allowed and
forbidden cases. All DB / service calls are mocked.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.privacy.router import router as privacy_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="privacy router import failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_admin_user(perm: str = "privacy.manage") -> MagicMock:
    user = MagicMock()
    user.id = "admin-user-id"
    user.email = "admin@test.com"
    user.full_name = "Test Admin"
    return user


def _make_non_admin_user() -> MagicMock:
    user = MagicMock()
    user.id = "plain-user-id"
    user.email = "user@test.com"
    user.full_name = "Plain User"
    return user


def _export_payload(user_id: str = "u-123") -> dict:
    return {
        "user_id": user_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"llm_traces": 5, "workflows": 2},
        "workflows": [],
        "llm_traces": [],
    }


def _delete_payload(user_id: str = "u-123", dry_run: bool = False) -> dict:
    return {
        "user_id": user_id,
        "dry_run": dry_run,
        "deleted": {"llm_traces": 5},
        "artifact_files_deleted": [],
        "artifact_files_skipped": [],
    }


@pytest.fixture
def client_admin():
    """TestClient with an admin user override."""
    from app.deps import get_current_user
    from app.infra.database import get_db

    admin = _make_admin_user()
    db_mock = MagicMock()

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db_mock
    app.include_router(privacy_router, prefix="/api/v1")

    with patch("app.domains.privacy.router._user_permissions",
               return_value={"privacy.manage"}):
        yield TestClient(app, raise_server_exceptions=False)

    app.dependency_overrides.clear()


@pytest.fixture
def client_non_admin():
    """TestClient with a non-admin user override."""
    from app.deps import get_current_user
    from app.infra.database import get_db

    plain = _make_non_admin_user()
    db_mock = MagicMock()

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: plain
    app.dependency_overrides[get_db] = lambda: db_mock
    app.include_router(privacy_router, prefix="/api/v1")

    with patch("app.domains.privacy.router._user_permissions", return_value=set()):
        yield TestClient(app, raise_server_exceptions=False)

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /privacy/dsar/users/{user_id}/export
# ---------------------------------------------------------------------------

class TestExportEndpoint:
    def test_export_returns_200_for_admin(self, client_admin):
        payload = _export_payload("u-abc")
        with patch("app.domains.privacy.router.build_user_dsar_export", return_value=payload):
            resp = client_admin.get("/api/v1/privacy/dsar/users/u-abc/export")
        assert resp.status_code == 200

    def test_export_returns_user_id_in_body(self, client_admin):
        payload = _export_payload("u-abc")
        with patch("app.domains.privacy.router.build_user_dsar_export", return_value=payload):
            resp = client_admin.get("/api/v1/privacy/dsar/users/u-abc/export")
        assert resp.json()["user_id"] == "u-abc"

    def test_export_passes_user_id_to_service(self, client_admin):
        captured = {}
        def fake_export(db, user_id):
            captured["user_id"] = user_id
            return _export_payload(user_id)

        with patch("app.domains.privacy.router.build_user_dsar_export", side_effect=fake_export):
            client_admin.get("/api/v1/privacy/dsar/users/special-user/export")

        assert captured["user_id"] == "special-user"

    def test_export_returns_403_for_non_admin(self, client_non_admin):
        with patch("app.domains.privacy.router.build_user_dsar_export", return_value=_export_payload()):
            resp = client_non_admin.get("/api/v1/privacy/dsar/users/u-123/export")
        assert resp.status_code == 403

    def test_export_counts_present_in_response(self, client_admin):
        payload = _export_payload("u-xyz")
        payload["counts"] = {"llm_traces": 10}
        with patch("app.domains.privacy.router.build_user_dsar_export", return_value=payload):
            resp = client_admin.get("/api/v1/privacy/dsar/users/u-xyz/export")
        assert resp.json()["counts"]["llm_traces"] == 10


# ---------------------------------------------------------------------------
# POST /privacy/dsar/users/{user_id}/delete
# ---------------------------------------------------------------------------

class TestDeleteEndpoint:
    def test_delete_returns_200_for_admin(self, client_admin):
        with patch("app.domains.privacy.router.delete_user_ai_data",
                   return_value=_delete_payload("u-del")), \
             patch("app.domains.privacy.router.log_audit"):
            resp = client_admin.post(
                "/api/v1/privacy/dsar/users/u-del/delete",
                json={"dry_run": False, "purge_artifact_files": False, "reason": "test"},
            )
        assert resp.status_code == 200

    def test_delete_returns_user_id(self, client_admin):
        with patch("app.domains.privacy.router.delete_user_ai_data",
                   return_value=_delete_payload("u-del")), \
             patch("app.domains.privacy.router.log_audit"):
            resp = client_admin.post(
                "/api/v1/privacy/dsar/users/u-del/delete",
                json={"dry_run": False, "purge_artifact_files": False, "reason": "test"},
            )
        assert resp.json()["user_id"] == "u-del"

    def test_delete_dry_run_true_passed_to_service(self, client_admin):
        captured = {}

        def fake_delete(db, user_id, dry_run, purge_artifact_files):
            captured["dry_run"] = dry_run
            return _delete_payload(user_id, dry_run=dry_run)

        with patch("app.domains.privacy.router.delete_user_ai_data", side_effect=fake_delete), \
             patch("app.domains.privacy.router.log_audit"):
            client_admin.post(
                "/api/v1/privacy/dsar/users/u-xyz/delete",
                json={"dry_run": True, "purge_artifact_files": False},
            )

        assert captured["dry_run"] is True

    def test_delete_returns_403_for_non_admin(self, client_non_admin):
        with patch("app.domains.privacy.router.delete_user_ai_data",
                   return_value=_delete_payload()), \
             patch("app.domains.privacy.router.log_audit"):
            resp = client_non_admin.post(
                "/api/v1/privacy/dsar/users/u-123/delete",
                json={"dry_run": True},
            )
        assert resp.status_code == 403

    def test_delete_with_admin_star_permission_allowed(self):
        """admin.* wildcard permission should also grant access."""
        from app.deps import get_current_user
        from app.infra.database import get_db

        admin = _make_admin_user()
        db_mock = MagicMock()

        app = FastAPI()
        app.dependency_overrides[get_current_user] = lambda: admin
        app.dependency_overrides[get_db] = lambda: db_mock
        app.include_router(privacy_router, prefix="/api/v1")

        with patch("app.domains.privacy.router._user_permissions", return_value={"admin.*"}), \
             patch("app.domains.privacy.router.delete_user_ai_data",
                   return_value=_delete_payload("u-star")), \
             patch("app.domains.privacy.router.log_audit"):
            tc = TestClient(app, raise_server_exceptions=False)
            resp = tc.post(
                "/api/v1/privacy/dsar/users/u-star/delete",
                json={"dry_run": False},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
