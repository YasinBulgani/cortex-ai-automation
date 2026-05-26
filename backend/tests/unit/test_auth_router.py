"""Unit tests for the auth router.

Uses FastAPI TestClient to exercise the router in isolation.
All DB and service calls are patched — no real database needed.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.auth.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="auth router deps not available")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_user(
    user_id: str = "user-uuid-001",
    email: str = "test@example.com",
    is_active: bool = True,
    roles: list[str] | None = None,
    perms: list[str] | None = None,
) -> MagicMock:
    from app.infra.models import User

    user = MagicMock(spec=User)
    user.id = user_id
    user.email = email
    user.is_active = is_active
    user.full_name = "Test User"
    user.phone = None
    user.department = None
    user.tenant_id = "00000000-0000-0000-0000-000000000001"
    user.password_hash = "hashed"
    user.created_at = None

    role_mocks = []
    for r in (roles or ["operator"]):
        rm = MagicMock()
        rm.name = r
        role_mocks.append(rm)
    user.roles = role_mocks
    return user


@pytest.fixture()
def client() -> "TestClient":
    from app.deps import get_current_user, get_db

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    fake_user = _make_fake_user()
    fake_db = MagicMock()
    fake_db.scalar.return_value = None
    fake_db.scalars.return_value = MagicMock(return_value=[])
    fake_db.commit.return_value = None
    fake_db.rollback.return_value = None
    fake_db.refresh.return_value = None
    fake_db.get.return_value = None
    fake_db.execute.return_value = None
    fake_db.flush.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: fake_db

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def admin_client() -> "TestClient":
    """Client where the injected user has admin.* permission."""
    from app.deps import get_current_user, get_db, _user_permissions

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    fake_user = _make_fake_user(roles=["admin"])
    fake_db = MagicMock()
    fake_db.scalar.return_value = None
    fake_db.scalars.return_value = MagicMock(return_value=[])
    fake_db.commit.return_value = None
    fake_db.rollback.return_value = None
    fake_db.refresh.return_value = None
    fake_db.get.return_value = None
    fake_db.execute.return_value = None
    fake_db.flush.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: fake_db
    # Patch _user_permissions so it returns admin.* for this user
    with patch("app.deps._user_permissions", return_value={"admin.*"}):
        tc = TestClient(app, raise_server_exceptions=False)
        yield tc


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    """POST /api/v1/auth/login"""

    def test_login_missing_email_returns_422(self, client: "TestClient") -> None:
        r = client.post("/api/v1/auth/login", json={"password": "secret"})
        assert r.status_code == 422

    def test_login_missing_password_returns_422(self, client: "TestClient") -> None:
        r = client.post("/api/v1/auth/login", json={"email": "a@b.com"})
        assert r.status_code == 422

    def test_login_wrong_credentials_returns_401(self, client: "TestClient") -> None:
        with patch("app.domains.auth.router.verify_password", return_value=False):
            with patch("app.domains.auth.router.create_access_token", return_value="tok"):
                r = client.post(
                    "/api/v1/auth/login",
                    json={"email": "a@b.com", "password": "wrong"},
                )
        assert r.status_code == 401

    def test_login_user_not_found_returns_401(self, client: "TestClient") -> None:
        # DB returns None → user not found
        with patch("app.domains.auth.router.verify_password", return_value=True):
            r = client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@x.com", "password": "pass"},
            )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

class TestLogoutEndpoint:
    """POST /api/v1/auth/logout"""

    def test_logout_returns_ok(self, client: "TestClient") -> None:
        with (
            patch("app.domains.auth.router.revoke_token"),
            patch("app.domains.auth.router.log_audit"),
        ):
            r = client.post("/api/v1/auth/logout")
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

class TestRefreshEndpoint:
    """POST /api/v1/auth/refresh"""

    def test_refresh_without_token_returns_401(self, client: "TestClient") -> None:
        r = client.post("/api/v1/auth/refresh", json={})
        assert r.status_code == 401

    def test_refresh_with_invalid_token_returns_401(self, client: "TestClient") -> None:
        with patch(
            "app.domains.auth.router.verify_refresh_token",
            side_effect=ValueError("invalid"),
        ):
            r = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "bad-token"},
            )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class TestMeEndpoint:
    """GET /api/v1/auth/me"""

    def test_me_returns_user_info(self, client: "TestClient") -> None:
        with patch("app.deps._user_permissions", return_value=set()):
            r = client.get("/api/v1/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "test@example.com"


# ---------------------------------------------------------------------------
# GET /auth/profile
# ---------------------------------------------------------------------------

class TestProfileEndpoint:
    """GET /api/v1/auth/profile"""

    def test_get_profile_returns_200(self, client: "TestClient") -> None:
        with patch("app.deps._user_permissions", return_value=set()):
            r = client.get("/api/v1/auth/profile")
        assert r.status_code == 200
        data = r.json()
        assert "email" in data


# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------

class TestForgotPasswordEndpoint:
    """POST /api/v1/auth/forgot-password"""

    def test_forgot_password_always_returns_ok_even_for_missing_email(
        self, client: "TestClient"
    ) -> None:
        """Security: response must be identical regardless of user existence."""
        with (
            patch("app.services.email_service.build_password_reset_email", return_value={}),
            patch("app.services.email_service.send_email", return_value=None),
            patch("app.domains.auth.router.create_password_reset_token", return_value="tok"),
            patch("app.domains.auth.router.log_audit"),
        ):
            r = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "ghost@nowhere.com"},
            )
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_forgot_password_missing_email_field_returns_422(
        self, client: "TestClient"
    ) -> None:
        r = client.post("/api/v1/auth/forgot-password", json={})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------

class TestResetPasswordEndpoint:
    """POST /api/v1/auth/reset-password"""

    def test_reset_password_invalid_token_returns_400(
        self, client: "TestClient"
    ) -> None:
        with patch(
            "app.domains.auth.router.verify_password_reset_token",
            return_value=None,
        ):
            r = client.post(
                "/api/v1/auth/reset-password",
                json={"token": "bad", "new_password": "NewPass1!Secure123"},
            )
        assert r.status_code == 400
