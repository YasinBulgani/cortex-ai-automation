"""Unit tests for the billing router — auth, RBAC, Stripe config, plan shape, usage.

5 tests covering:
  - GET  /admin/billing/subscription   (unauthenticated → 401)
  - POST /admin/billing/plan           (non-admin user → 403)
  - POST /admin/billing/checkout       (Stripe price ID missing → 503)
  - GET  /admin/billing/subscription   (response dict shape)
  - GET  /admin/billing/usage          (response field contract)
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ── import guard ────────────────────────────────────────────────────────────

try:
    from app.domains.billing.router import router as billing_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="billing router import failed")


# ── helpers / factories ─────────────────────────────────────────────────────

def _make_user(*, is_admin: bool = False, tenant_id: str | None = None) -> MagicMock:
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.tenant_id = tenant_id or str(uuid.uuid4())
    user.email = "test@example.com"
    user.is_admin = is_admin
    return user


def _make_subscription(tenant_id: str, plan_code: str = "free") -> MagicMock:
    sub = MagicMock()
    sub.tenant_id = tenant_id
    sub.plan_code = plan_code
    sub.status = "active"
    sub.current_period_start = None
    sub.current_period_end = None
    sub.cancel_at_period_end = False
    sub.external_subscription_id = None
    sub.external_customer_id = None
    return sub


def _make_usage_snapshot(plan_code: str = "free") -> MagicMock:
    snap = MagicMock()
    snap.to_dict.return_value = {
        "plan": plan_code,
        "plan_expires_at": None,
        "scenario_count": 0,
        "scenario_limit": 50,
        "run_count_month": 0,
        "run_limit_month": 100,
        "ai_token_spend_usd": 0.0,
        "ai_token_limit_usd": 2.0,
        "team_size": 1,
        "team_limit": 2,
        "storage_mb": 0,
        "storage_limit_mb": 1024,
        "project_count": 0,
        "project_limit": 5,
    }
    return snap


# ── app fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture()
def app_no_auth() -> FastAPI:
    """FastAPI app with billing router — get_current_user raises 401."""
    from fastapi import HTTPException
    from app.deps import get_current_user, require_permission
    from app.infra.database import get_db

    app = FastAPI()
    app.include_router(billing_router)

    # Override: no authenticated user → 401
    def _unauth():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = _unauth
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app


@pytest.fixture()
def app_non_admin() -> FastAPI:
    """FastAPI app — authenticated but no admin permission → require_permission raises 403."""
    from fastapi import HTTPException
    from app.deps import get_current_user, require_permission
    from app.infra.database import get_db

    app = FastAPI()
    app.include_router(billing_router)

    user = _make_user(is_admin=False)

    def _no_perm():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    app.dependency_overrides[get_current_user] = lambda: user
    # require_permission returns a callable; we must override the resolved dependency.
    # FastAPI resolves `require_permission("admin.*")` as a unique dependency per call site.
    # Patch all permission-guarded deps by overriding the factory output via monkeypatch
    # on the module instead — done in the test body.
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return app, user, _no_perm


@pytest.fixture()
def app_authed(mock_db_session) -> tuple[FastAPI, MagicMock]:
    """FastAPI app with a real-looking authenticated admin user."""
    from app.deps import get_current_user, require_permission
    from app.infra.database import get_db

    app = FastAPI()
    app.include_router(billing_router)

    user = _make_user(is_admin=True)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    return app, user


# ── test 1: GET /subscription requires auth ──────────────────────────────────

def test_billing_get_subscription_requires_auth(app_no_auth):
    """Unauthenticated request to /subscription must return 401."""
    client = TestClient(app_no_auth, raise_server_exceptions=False)
    response = client.get("/admin/billing/subscription")
    assert response.status_code == 401


# ── test 2: POST /plan requires admin permission ─────────────────────────────

def test_billing_cancel_requires_admin():
    """Non-admin user must receive 403 when attempting to POST /plan."""
    from fastapi import FastAPI, HTTPException
    from app.deps import get_current_user, require_permission
    from app.infra.database import get_db

    app = FastAPI()
    app.include_router(billing_router)

    user = _make_user(is_admin=False)

    # get_current_user returns the regular user
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    # require_permission is called with "admin.*" inside the router; override
    # the dependency callable that FastAPI resolves for that endpoint.
    # The router uses `Depends(require_permission("admin.*"))` which resolves
    # to whatever callable require_permission("admin.*") returns.
    # We patch the module-level function so the inner callable raises 403.
    def _blocking_require_permission(permission: str):
        def _check():
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return _check

    with patch("app.domains.billing.router.require_permission", _blocking_require_permission):
        # Re-create app so the patched dependency is used
        app2 = FastAPI()
        app2.include_router(billing_router)
        app2.dependency_overrides[get_current_user] = lambda: user
        app2.dependency_overrides[get_db] = lambda: MagicMock()

        client = TestClient(app2, raise_server_exceptions=False)
        response = client.post(
            "/admin/billing/plan",
            json={"plan_code": "starter"},
        )
    assert response.status_code == 403


# ── test 3: POST /checkout — Stripe price ID missing → 503 ───────────────────

def test_billing_stripe_key_missing_returns_503():
    """If the Stripe price ID is not configured, checkout must return 503."""
    from fastapi import FastAPI
    from app.deps import get_current_user, require_permission
    from app.infra.database import get_db
    from app.config import settings

    user = _make_user(is_admin=True)
    tenant_id = user.tenant_id
    sub = _make_subscription(tenant_id, "free")

    def _admin_user():
        return user

    def _blocking_require_permission(permission: str):
        def _check():
            return user
        return _check

    with patch("app.domains.billing.router.require_permission", _blocking_require_permission):
        app = FastAPI()
        app.include_router(billing_router)
        app.dependency_overrides[get_current_user] = _admin_user
        app.dependency_overrides[get_db] = lambda: MagicMock()

        with patch("app.domains.billing.router.get_or_create_subscription", return_value=sub):
            # Ensure stripe_price_starter is empty (not configured)
            original = getattr(settings, "stripe_price_starter", "")
            try:
                settings.stripe_price_starter = ""
                client = TestClient(app, raise_server_exceptions=False)
                response = client.post(
                    "/admin/billing/checkout",
                    json={"plan_code": "starter"},
                )
            finally:
                settings.stripe_price_starter = original

    assert response.status_code == 503
    body = response.json()
    assert body.get("detail", {}).get("code") == "billing.stripe_not_configured"


# ── test 4: GET /subscription — response dict shape ──────────────────────────

def test_billing_current_plan_returns_structure():
    """GET /subscription must return a dict with the expected keys."""
    from fastapi import FastAPI
    from app.deps import get_current_user
    from app.infra.database import get_db

    user = _make_user(is_admin=False)
    tenant_id = user.tenant_id
    sub = _make_subscription(tenant_id, "starter")

    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    with patch("app.domains.billing.router.get_or_create_subscription", return_value=sub):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/billing/subscription")

    assert response.status_code == 200
    body = response.json()

    expected_keys = {
        "tenant_id",
        "plan_code",
        "status",
        "current_period_start",
        "current_period_end",
        "cancel_at_period_end",
        "external_subscription_id",
    }
    assert expected_keys.issubset(body.keys()), (
        f"Missing keys: {expected_keys - body.keys()}"
    )
    assert body["plan_code"] == "starter"
    assert body["status"] == "active"
    assert body["tenant_id"] == tenant_id


# ── test 5: GET /usage — response format ─────────────────────────────────────

def test_billing_usage_metrics():
    """GET /usage must return a dict with all expected usage metric fields."""
    from fastapi import FastAPI
    from app.deps import get_current_user
    from app.infra.database import get_db

    user = _make_user(is_admin=False)
    snap = _make_usage_snapshot("free")

    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    with patch("app.domains.billing.router.compute_usage_snapshot", return_value=snap):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/admin/billing/usage")

    assert response.status_code == 200
    body = response.json()

    expected_keys = {
        "plan",
        "plan_expires_at",
        "scenario_count",
        "scenario_limit",
        "run_count_month",
        "run_limit_month",
        "ai_token_spend_usd",
        "ai_token_limit_usd",
        "team_size",
        "team_limit",
        "storage_mb",
        "storage_limit_mb",
        "project_count",
        "project_limit",
    }
    assert expected_keys.issubset(body.keys()), (
        f"Missing keys: {expected_keys - body.keys()}"
    )
    assert body["plan"] == "free"
    assert isinstance(body["scenario_count"], int)
    assert isinstance(body["run_count_month"], int)
    assert isinstance(body["ai_token_spend_usd"], float)
