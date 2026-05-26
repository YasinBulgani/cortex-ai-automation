"""Unit tests for the billing router.

Uses FastAPI TestClient in isolation. All service and Stripe calls
are patched so no external system is needed.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.billing.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="billing router deps not available")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fake_sub(
    tenant_id: str = "t-001",
    plan_code: str = "free",
    status: str = "active",
    external_customer_id: str | None = None,
) -> MagicMock:
    sub = MagicMock()
    sub.tenant_id = tenant_id
    sub.plan_code = plan_code
    sub.status = status
    sub.current_period_start = None
    sub.current_period_end = None
    sub.cancel_at_period_end = False
    sub.external_subscription_id = None
    sub.external_customer_id = external_customer_id
    return sub


def _make_client(*, perms: set[str] | None = None) -> "TestClient":
    from app.deps import get_current_user, get_db, require_permission
    from app.infra.models import User

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    fake_user = MagicMock(spec=User)
    fake_user.id = "user-001"
    fake_user.email = "admin@test.com"
    fake_user.tenant_id = "t-001"
    fake_user.roles = []

    fake_db = MagicMock()
    fake_db.commit.return_value = None
    fake_db.rollback.return_value = None
    fake_db.add.return_value = None
    fake_db.flush.return_value = None

    effective_perms = perms or {"admin.*"}

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[require_permission("admin.*")] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: fake_db

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client() -> "TestClient":
    return _make_client()


# ---------------------------------------------------------------------------
# GET /admin/billing/plans
# ---------------------------------------------------------------------------

class TestGetPlans:
    """GET /api/v1/admin/billing/plans — public, no auth needed."""

    def test_returns_200_with_plans_list(self, client: "TestClient") -> None:
        with patch(
            "app.domains.billing.router.list_plans",
            return_value=[{"code": "free"}, {"code": "starter"}],
        ):
            r = client.get("/api/v1/admin/billing/plans")
        assert r.status_code == 200
        assert "plans" in r.json()

    def test_plans_list_is_a_list(self, client: "TestClient") -> None:
        with patch("app.domains.billing.router.list_plans", return_value=[]):
            r = client.get("/api/v1/admin/billing/plans")
        assert isinstance(r.json()["plans"], list)


# ---------------------------------------------------------------------------
# GET /admin/billing/usage
# ---------------------------------------------------------------------------

class TestGetUsage:
    """GET /api/v1/admin/billing/usage"""

    def test_returns_usage_dict(self, client: "TestClient") -> None:
        mock_snapshot = MagicMock()
        mock_snapshot.to_dict.return_value = {"tests_run": 10, "team_size": 3}
        with patch(
            "app.domains.billing.router.compute_usage_snapshot",
            return_value=mock_snapshot,
        ):
            r = client.get("/api/v1/admin/billing/usage")
        assert r.status_code == 200
        assert r.json()["tests_run"] == 10


# ---------------------------------------------------------------------------
# GET /admin/billing/subscription
# ---------------------------------------------------------------------------

class TestGetSubscription:
    """GET /api/v1/admin/billing/subscription"""

    def test_returns_subscription_info(self, client: "TestClient") -> None:
        with patch(
            "app.domains.billing.router.get_or_create_subscription",
            return_value=_fake_sub(),
        ):
            r = client.get("/api/v1/admin/billing/subscription")
        assert r.status_code == 200
        data = r.json()
        assert data["plan_code"] == "free"
        assert data["status"] == "active"


# ---------------------------------------------------------------------------
# POST /admin/billing/plan
# ---------------------------------------------------------------------------

class TestChangePlan:
    """POST /api/v1/admin/billing/plan"""

    def test_invalid_plan_code_returns_400(self, client: "TestClient") -> None:
        with patch(
            "app.domains.billing.router.PLAN_CATALOG",
            {"free": {}, "starter": {}, "pro": {}},
        ):
            r = client.post(
                "/api/v1/admin/billing/plan",
                json={"plan_code": "nonexistent_plan"},
            )
        assert r.status_code == 400

    def test_enterprise_plan_returns_409(self, client: "TestClient") -> None:
        with patch(
            "app.domains.billing.router.PLAN_CATALOG",
            {"free": {}, "starter": {}, "pro": {}, "enterprise": {}},
        ):
            r = client.post(
                "/api/v1/admin/billing/plan",
                json={"plan_code": "enterprise"},
            )
        assert r.status_code == 409

    def test_valid_plan_change_returns_200(self, client: "TestClient") -> None:
        mock_sub = _fake_sub(plan_code="starter", status="active")
        with (
            patch(
                "app.domains.billing.router.PLAN_CATALOG",
                {"free": {}, "starter": {}, "pro": {}},
            ),
            patch(
                "app.domains.billing.router.set_plan",
                return_value=mock_sub,
            ),
        ):
            r = client.post(
                "/api/v1/admin/billing/plan",
                json={"plan_code": "starter"},
            )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_service_value_error_returns_400(self, client: "TestClient") -> None:
        with (
            patch(
                "app.domains.billing.router.PLAN_CATALOG",
                {"free": {}, "starter": {}, "pro": {}},
            ),
            patch(
                "app.domains.billing.router.set_plan",
                side_effect=ValueError("downgrade not allowed"),
            ),
        ):
            r = client.post(
                "/api/v1/admin/billing/plan",
                json={"plan_code": "starter"},
            )
        assert r.status_code == 400

    def test_missing_plan_code_returns_422(self, client: "TestClient") -> None:
        r = client.post("/api/v1/admin/billing/plan", json={})
        assert r.status_code == 422

    def test_plan_code_too_short_returns_422(self, client: "TestClient") -> None:
        r = client.post("/api/v1/admin/billing/plan", json={"plan_code": "x"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /admin/billing/checkout
# ---------------------------------------------------------------------------

class TestCreateCheckout:
    """POST /api/v1/admin/billing/checkout"""

    def test_unknown_plan_returns_400(self, client: "TestClient") -> None:
        r = client.post(
            "/api/v1/admin/billing/checkout",
            json={"plan_code": "enterprise"},
        )
        assert r.status_code == 400

    def test_missing_plan_code_returns_422(self, client: "TestClient") -> None:
        r = client.post("/api/v1/admin/billing/checkout", json={})
        assert r.status_code == 422
