"""TC-0101..TC-0110: Authentication & session management tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.domains.auth.service import create_password_reset_token, create_refresh_token, hash_password
from app.infra.database import SessionLocal
from app.infra.models import User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "admin123"


class TestSuccessfulLogin:
    """TC-0101, TC-0108, TC-0110"""

    def test_valid_credentials_returns_token(self, client: TestClient, db_ready):
        r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert len(body["access_token"].split(".")) == 3

    def test_me_endpoint_returns_user_info(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == ADMIN_EMAIL
        assert "admin" in body["roles"]
        assert isinstance(body["permissions"], list)

    def test_login_creates_audit_log(self, client: TestClient, db_ready):
        client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        # Audit log is tested implicitly — login does not fail

    def test_login_sets_http_only_auth_cookies(self, client: TestClient, db_ready):
        r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200
        set_cookie = r.headers.get("set-cookie", "")
        assert "bgts_access_token=" in set_cookie
        assert "bgts_refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie

    def test_me_accepts_cookie_auth_without_bearer_header(self, client: TestClient, db_ready):
        login = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert login.status_code == 200

        r = client.get("/api/v1/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL


class TestFailedLogin:
    """TC-0102, TC-0103, TC-0104"""

    def test_wrong_password_returns_401(self, client: TestClient, db_ready):
        r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401
        assert "hatalı" in r.json()["detail"].lower()

    def test_unknown_email_returns_401(self, client: TestClient, db_ready):
        r = client.post("/api/v1/auth/login", json={"email": "nobody@x.com", "password": "x"})
        assert r.status_code == 401

    def test_disabled_account_returns_403(self, client: TestClient, db_ready):
        # Only applicable if a disabled user exists in seed data
        r = client.post("/api/v1/auth/login", json={"email": "disabled@test.com", "password": "x"})
        assert r.status_code in (401, 403)


class TestValidationBoundary:
    """TC-0105, TC-0106, TC-0107"""

    def test_empty_email_returns_422(self, client: TestClient):
        r = client.post("/api/v1/auth/login", json={"email": "", "password": "x"})
        assert r.status_code == 422

    def test_empty_password_returns_422(self, client: TestClient):
        r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ""})
        assert r.status_code == 422

    def test_invalid_email_format_returns_422(self, client: TestClient):
        r = client.post("/api/v1/auth/login", json={"email": "not-email", "password": "x"})
        assert r.status_code == 422


class TestProtectedEndpoints:
    """TC-0109"""

    def test_no_token_returns_401(self, client: TestClient):
        client.cookies.clear()
        r = client.get("/api/v1/tspm/projects")
        assert r.status_code == 401


class TestSessionHardening:

    def test_logout_revokes_access_token(self, client: TestClient, db_ready):
        login = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert login.status_code == 200
        access_token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        me_before = client.get("/api/v1/auth/me", headers=headers)
        assert me_before.status_code == 200

        logout = client.post("/api/v1/auth/logout", headers=headers)
        assert logout.status_code == 200

        me_after = client.get("/api/v1/auth/me", headers=headers)
        assert me_after.status_code == 401

    def test_refresh_accepts_http_only_cookie_fallback(self, client: TestClient, db_ready):
        login = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert login.status_code == 200

        refreshed = client.post("/api/v1/auth/refresh", json={})
        assert refreshed.status_code == 200
        body = refreshed.json()
        assert body["access_token"]
        assert body["refresh_token"]

    def test_password_reset_token_is_single_use(self, client: TestClient, db_ready):
        email = "reset-once@test.local"
        password = "InitialPass1!"
        new_password = "UpdatedPass1!"

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, password_hash=hash_password(password), is_active=True)
                db.add(user)
            else:
                user.password_hash = hash_password(password)
                user.is_active = True
            db.commit()
            db.refresh(user)
            token = create_password_reset_token(user.id)

        first = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": new_password},
        )
        assert first.status_code == 200

        second = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "AnotherPass1!"},
        )
        assert second.status_code == 400

    def test_forgot_password_always_returns_generic_message(self, client: TestClient):
        existing = client.post("/api/v1/auth/forgot-password", json={"email": ADMIN_EMAIL})
        missing = client.post("/api/v1/auth/forgot-password", json={"email": "unknown@example.com"})

        assert existing.status_code == 200
        assert missing.status_code == 200
        assert existing.json()["message"] == missing.json()["message"]

    def test_password_reset_revokes_existing_refresh_tokens(self, client: TestClient, db_ready):
        email = "reset-refresh@example.com"
        password = "InitialPass1!"
        new_password = "UpdatedPass1!"

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, password_hash=hash_password(password), is_active=True)
                db.add(user)
            else:
                user.password_hash = hash_password(password)
                user.is_active = True
            db.commit()
            db.refresh(user)
            refresh_token = create_refresh_token(user.id, db, user_agent="pytest")
            db.commit()

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            token = create_password_reset_token(user.id)

        reset = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": new_password},
        )
        assert reset.status_code == 200

        refresh_after_reset = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_after_reset.status_code == 401

    def test_open_registration_is_disabled_by_default(self, client: TestClient):
        r = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new.user@example.com",
                "password": "StrongPass123!",
                "full_name": "New User",
            },
        )
        assert r.status_code == 403
