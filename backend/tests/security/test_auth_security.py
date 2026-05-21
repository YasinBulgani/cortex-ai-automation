"""Security: JWT manipulation, expired tokens, brute force tests."""

import pytest
from fastapi.testclient import TestClient


class TestJWTSecurity:

    def test_invalid_jwt_signature(self, client: TestClient):
        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIn0.invalid_sig"},
        )
        assert r.status_code in (401, 403)

    def test_no_bearer_prefix(self, client: TestClient):
        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": "just-a-token-no-bearer"},
        )
        assert r.status_code in (401, 403)

    def test_empty_authorization_header(self, client: TestClient):
        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": ""},
        )
        assert r.status_code in (401, 403)

    def test_bearer_with_empty_token(self, client: TestClient):
        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": "Bearer "},
        )
        assert r.status_code in (401, 403)

    def test_jwt_with_sql_injection_payload(self, client: TestClient):
        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": "Bearer '; DROP TABLE sd_users; --"},
        )
        assert r.status_code in (401, 403)


class TestBruteForce:

    def test_multiple_failed_login_attempts(self, client: TestClient, db_ready):
        for _ in range(20):
            r = client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.com", "password": "wrong"},
            )
            assert r.status_code in (401, 429)


class TestPasswordLeak:

    def test_me_does_not_expose_password(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        body = r.json()
        assert "password" not in body
        assert "password_hash" not in body
        raw = r.text.lower()
        assert "password_hash" not in raw
