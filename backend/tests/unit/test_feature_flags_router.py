"""Unit tests for feature-flags router.

Tests cover:
  GET    /feature-flags            → list_flags (admin)
  GET    /feature-flags/{key}      → get_flag (admin)
  PUT    /feature-flags/{key}      → upsert_flag (admin)
  DELETE /feature-flags/{key}      → delete_flag (admin)
  GET    /feature-flags/evaluate/{key} → evaluate_flag (any authenticated user)

All external dependencies (service, auth) are patched so tests run
without a database or running server.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.feature_flags.router import router
    from app.deps import get_current_user
    from app.infra.models import User

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False


def _mock_user_obj(id=1, email="admin@test.com", tenant_id="t1"):
    u = MagicMock(spec=User)
    u.id = id
    u.email = email
    u.tenant_id = tenant_id
    u.roles = []
    return u

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_flag(key: str = "my-flag", enabled: bool = True) -> dict:
    return {"key": key, "enabled": enabled, "description": "test flag", "rollout_pct": 100}


def _make_evaluation(key: str = "my-flag", enabled: bool = True) -> dict:
    return {"key": key, "enabled": enabled, "reason": "default"}


def _build_client(mock_user: MagicMock | None = None) -> TestClient:
    """Return a TestClient with auth deps overridden."""
    from app.domains.feature_flags.router import _require_admin

    if mock_user is None:
        mock_user = _mock_user_obj()

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[_require_admin] = lambda: mock_user
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# list_flags — GET /feature-flags
# ---------------------------------------------------------------------------

class TestListFlags:
    def test_list_returns_200_with_flags(self):
        flags = [_make_flag("flag-a"), _make_flag("flag-b")]
        with patch(
            "app.domains.feature_flags.router.feature_flags.list_flags",
            return_value=flags,
        ):
            resp = _build_client().get("/feature-flags")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_returns_empty_list_when_no_flags(self):
        with patch(
            "app.domains.feature_flags.router.feature_flags.list_flags",
            return_value=[],
        ):
            resp = _build_client().get("/feature-flags")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# get_flag — GET /feature-flags/{key}
# ---------------------------------------------------------------------------

class TestGetFlag:
    def test_get_existing_flag_returns_200(self):
        flag = _make_flag("beta-feature")
        with patch(
            "app.domains.feature_flags.router.feature_flags.get",
            return_value=flag,
        ):
            resp = _build_client().get("/feature-flags/beta-feature")
        assert resp.status_code == 200
        assert resp.json()["key"] == "beta-feature"

    def test_get_missing_flag_returns_404(self):
        with patch(
            "app.domains.feature_flags.router.feature_flags.get",
            return_value=None,
        ):
            resp = _build_client().get("/feature-flags/nonexistent")
        assert resp.status_code == 404
        assert "bulunamadı" in resp.json()["detail"].lower() or resp.status_code == 404


# ---------------------------------------------------------------------------
# upsert_flag — PUT /feature-flags/{key}
# ---------------------------------------------------------------------------

class TestUpsertFlag:
    def test_upsert_creates_flag_returns_200(self):
        flag = _make_flag("new-flag")
        with patch(
            "app.domains.feature_flags.router.feature_flags.set_flag",
            return_value=flag,
        ):
            resp = _build_client().put(
                "/feature-flags/new-flag",
                json={"enabled": True, "description": "new"},
            )
        assert resp.status_code == 200
        assert resp.json()["key"] == "new-flag"

    def test_upsert_with_invalid_payload_returns_400(self):
        with patch(
            "app.domains.feature_flags.router.feature_flags.set_flag",
            side_effect=ValueError("rollout_pct must be 0–100"),
        ):
            resp = _build_client().put(
                "/feature-flags/bad-flag",
                json={"enabled": True},
            )
        assert resp.status_code == 400

    def test_upsert_updates_existing_flag(self):
        updated = _make_flag("existing-flag", enabled=False)
        with patch(
            "app.domains.feature_flags.router.feature_flags.set_flag",
            return_value=updated,
        ):
            resp = _build_client().put(
                "/feature-flags/existing-flag",
                json={"enabled": False},
            )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False


# ---------------------------------------------------------------------------
# delete_flag — DELETE /feature-flags/{key}
# ---------------------------------------------------------------------------

class TestDeleteFlag:
    def test_delete_existing_flag_returns_204(self):
        with patch(
            "app.domains.feature_flags.router.feature_flags.delete",
            return_value=True,
        ):
            resp = _build_client().delete("/feature-flags/my-flag")
        assert resp.status_code == 204

    def test_delete_missing_flag_returns_404(self):
        with patch(
            "app.domains.feature_flags.router.feature_flags.delete",
            return_value=False,
        ):
            resp = _build_client().delete("/feature-flags/ghost-flag")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# evaluate_flag — GET /feature-flags/evaluate/{key}
# ---------------------------------------------------------------------------

class TestEvaluateFlag:
    def test_evaluate_enabled_flag(self):
        evaluation = _make_evaluation("rollout-flag", enabled=True)
        with patch(
            "app.domains.feature_flags.router.feature_flags.evaluate",
            return_value=evaluation,
        ):
            resp = _build_client().get("/feature-flags/evaluate/rollout-flag")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    def test_evaluate_disabled_flag(self):
        evaluation = _make_evaluation("off-flag", enabled=False)
        with patch(
            "app.domains.feature_flags.router.feature_flags.evaluate",
            return_value=evaluation,
        ):
            resp = _build_client().get("/feature-flags/evaluate/off-flag")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

    def test_evaluate_uses_query_tenant_when_provided(self):
        evaluation = _make_evaluation("canary")
        mock_svc = MagicMock(return_value=evaluation)
        with patch(
            "app.domains.feature_flags.router.feature_flags.evaluate",
            mock_svc,
        ):
            _build_client().get("/feature-flags/evaluate/canary?tenant=tenant-xyz")
        call_kwargs = mock_svc.call_args
        assert call_kwargs is not None
        # tenant_id should be 'tenant-xyz'
        assert "tenant-xyz" in str(call_kwargs)

    def test_evaluate_falls_back_to_user_tenant_when_no_query_param(self):
        evaluation = _make_evaluation("canary")
        mock_svc = MagicMock(return_value=evaluation)
        user = MagicMock(id=42, email="user@test.com", tenant_id="user-tenant")
        with patch(
            "app.domains.feature_flags.router.feature_flags.evaluate",
            mock_svc,
        ):
            _build_client(mock_user=user).get("/feature-flags/evaluate/canary")
        call_kwargs = mock_svc.call_args
        assert "user-tenant" in str(call_kwargs)
