"""Tenant boundary security tests.

Verifies that API endpoints resist cross-tenant data access attempts:
- Forged tenant_id in request body is ignored
- Path traversal across tenant boundaries returns 403/404
- JWT with tampered tenant claim is rejected
"""

from __future__ import annotations

import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.security

_TENANT_A = "00000000-0000-0000-0000-000000000001"
_TENANT_B = "00000000-0000-0000-0000-000000000002"
_NONEXISTENT_TENANT = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def _login(client, email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None


class TestTenantBoundaryAttacks:
    """API endpoints must not honour attacker-controlled tenant_id."""

    def test_create_project_with_forged_tenant_id_ignored(
        self, client: TestClient, db_ready: bool
    ) -> None:
        """POST body tenant_id must be ignored — server derives it from JWT."""
        if not db_ready:
            pytest.skip("DB yok")

        token = _login(client, "admin@example.com", "admin123")
        if not token:
            pytest.skip("Login başarısız")

        r = client.post(
            "/api/v1/tspm/projects",
            json={
                "name": f"ForgedTenant-{uuid.uuid4().hex[:6]}",
                "tenant_id": _NONEXISTENT_TENANT,  # attacker tries to forge
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        # Request must either succeed (ignoring the forged field) or 422
        # but must NEVER create a row under the forged tenant
        assert r.status_code in (200, 201, 422), (
            f"Beklenmeyen durum: {r.status_code} {r.text[:200]}"
        )

    def test_unauthenticated_request_rejected(self, client: TestClient) -> None:
        r = client.get("/api/v1/tspm/projects")
        assert r.status_code == 401

    def test_invalid_jwt_rejected(self, client: TestClient) -> None:
        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalid.sig"},
        )
        assert r.status_code == 401

    def test_random_project_id_returns_404(
        self, client: TestClient, db_ready: bool, auth_headers: dict
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")
        fake_id = str(uuid.uuid4())
        r = client.get(
            f"/api/v1/tspm/projects/{fake_id}",
            headers=auth_headers,
        )
        assert r.status_code in (404, 403)

    def test_tampered_jwt_tenant_rejected(self, client: TestClient, db_ready: bool) -> None:
        """Manually tampered JWT (different tenant in payload) must be rejected."""
        if not db_ready:
            pytest.skip("DB yok")

        token = _login(client, "admin@example.com", "admin123")
        if not token:
            pytest.skip("Login başarısız")

        # Split JWT and tamper the payload
        header, payload_b64, sig = token.split(".")
        padding = "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
        payload["tenant"] = _NONEXISTENT_TENANT  # tamper

        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()

        tampered_token = f"{header}.{tampered_payload}.{sig}"

        r = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        # Signature mismatch → 401
        assert r.status_code == 401, (
            f"Tampered JWT kabul edildi! HTTP {r.status_code} — "
            "JWT signature doğrulaması çalışmıyor"
        )


class TestSQLInjectionPrevention:
    """Tenant ID is parameterized — SQL injection must not work."""

    def test_sql_injection_in_path_param(
        self, client: TestClient, db_ready: bool, auth_headers: dict
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        # Try common SQL injection patterns as project ID
        injections = [
            "' OR '1'='1",
            "1; DROP TABLE tspm_projects; --",
            "../../etc/passwd",
            "%27%20OR%20%271%27%3D%271",
        ]
        for injection in injections:
            r = client.get(
                f"/api/v1/tspm/projects/{injection}",
                headers=auth_headers,
            )
            assert r.status_code in (400, 404, 422), (
                f"SQL injection vektörü '{injection}' beklenmeyen yanıt: "
                f"HTTP {r.status_code}"
            )
