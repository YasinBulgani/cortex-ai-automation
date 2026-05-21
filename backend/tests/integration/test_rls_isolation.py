"""RLS tenant isolation integration tests.

Requires a live PostgreSQL with RLS migration applied.
Skips automatically when DB is not available.
"""

from __future__ import annotations

import base64
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.infra.database import SessionLocal

pytestmark = pytest.mark.integration

_TENANT_A = "00000000-0000-0000-0000-000000000001"  # local (seeded)
_TENANT_B = "00000000-0000-0000-0000-000000000002"  # second tenant (created in test)


# ── helpers ──────────────────────────────────────────────────────────────────

def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verifying signature."""
    part = token.split(".")[1]
    part += "=" * (4 - len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part))


def _login(client: TestClient, email: str, password: str) -> str | None:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        return None
    return r.json()["access_token"]


def _ensure_tenant_b(db) -> None:
    """Create tenant B row if not already present."""
    db.execute(text("""
        INSERT INTO tenants (id, slug, display_name, plan)
        VALUES (:id, 'tenant-b-test', 'Tenant B (test)', 'free')
        ON CONFLICT (slug) DO NOTHING
    """), {"id": _TENANT_B})


def _ensure_tenant_b_user(db) -> tuple[str, str]:
    """Create a user on tenant B; return (email, password)."""
    from app.domains.auth.service import hash_password
    from app.infra.models import User

    email = "tenant_b_user@integration-test.local"
    existing = db.execute(
        text("SELECT id FROM sd_users WHERE email = :e"), {"e": email}
    ).fetchone()
    if existing:
        return email, "TenantBPass!99"

    user_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO sd_users (id, email, password_hash, is_active, tenant_id)
        VALUES (:id, :email, :pw, TRUE, :tenant_id)
        ON CONFLICT (email) DO NOTHING
    """), {
        "id": user_id,
        "email": email,
        "pw": hash_password("TenantBPass!99"),
        "tenant_id": _TENANT_B,
    })
    return email, "TenantBPass!99"


# ── JWT tenant claim ─────────────────────────────────────────────────────────

class TestJWTTenantClaim:
    def test_login_token_contains_tenant_claim(
        self, client: TestClient, db_ready: bool
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        token = _login(client, "admin@example.com", "admin123")
        assert token is not None, "login başarısız"

        payload = _decode_jwt_payload(token)
        assert "tenant" in payload, f"JWT'de 'tenant' claim yok: {payload.keys()}"
        assert payload["tenant"] == _TENANT_A

    def test_refresh_preserves_tenant_claim(
        self, client: TestClient, db_ready: bool
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        # Login
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        if r.status_code != 200:
            pytest.skip("login başarısız")

        refresh_token = r.json().get("refresh_token")
        if not refresh_token:
            pytest.skip("refresh_token yok")

        # Refresh
        r2 = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert r2.status_code == 200, r2.text
        new_token = r2.json()["access_token"]
        payload = _decode_jwt_payload(new_token)
        assert payload.get("tenant") == _TENANT_A, "Refresh sonrası tenant kayboldu"


# ── RLS isolation ─────────────────────────────────────────────────────────────

class TestRLSTenantIsolation:
    """Verify tenant A cannot see tenant B's projects and vice versa."""

    def _rls_enabled(self) -> bool:
        """Check if RLS is actually enabled on tspm_projects."""
        try:
            with SessionLocal() as db:
                row = db.execute(text("""
                    SELECT relrowsecurity
                    FROM pg_class
                    WHERE relname = 'tspm_projects'
                """)).fetchone()
                return bool(row and row[0])
        except Exception:
            return False

    def test_tenant_a_project_invisible_to_tenant_b(
        self, client: TestClient, db_ready: bool
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")
        if not self._rls_enabled():
            pytest.skip("RLS tspm_projects tablosunda etkin değil — migration uygulanmamış")

        # Setup: ensure tenant B exists
        with SessionLocal() as db:
            try:
                _ensure_tenant_b(db)
                b_email, b_pass = _ensure_tenant_b_user(db)
                db.commit()
            except Exception as exc:
                pytest.skip(f"Tenant B kurulumu başarısız: {exc}")

        # Login as tenant A (admin) and create a project
        token_a = _login(client, "admin@example.com", "admin123")
        if not token_a:
            pytest.skip("Tenant A login başarısız")

        project_name = f"RLS-Test-{uuid.uuid4().hex[:6]}"
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": project_name, "description": "RLS isolation test"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        if r.status_code not in (200, 201):
            pytest.skip(f"Proje oluşturulamadı: {r.status_code} {r.text}")
        project_id = r.json()["id"]

        # Login as tenant B
        token_b = _login(client, b_email, b_pass)
        if not token_b:
            pytest.skip("Tenant B login başarısız")

        # Tenant B must NOT see tenant A's project in list
        r_list = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r_list.status_code == 200, r_list.text
        project_ids = [p["id"] for p in r_list.json()]
        assert project_id not in project_ids, (
            f"RLS ihlali: Tenant B, Tenant A'nın projesini ({project_id}) görebiliyor"
        )

    def test_tenant_b_project_invisible_to_tenant_a(
        self, client: TestClient, db_ready: bool
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")
        if not self._rls_enabled():
            pytest.skip("RLS etkin değil")

        with SessionLocal() as db:
            try:
                _ensure_tenant_b(db)
                b_email, b_pass = _ensure_tenant_b_user(db)
                db.commit()
            except Exception as exc:
                pytest.skip(f"Tenant B kurulumu başarısız: {exc}")

        token_b = _login(client, b_email, b_pass)
        if not token_b:
            pytest.skip("Tenant B login başarısız")

        # Create project as tenant B
        project_name = f"TenantB-{uuid.uuid4().hex[:6]}"
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": project_name},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        if r.status_code not in (200, 201):
            pytest.skip(f"Tenant B proje oluşturamadı: {r.status_code}")
        project_id = r.json()["id"]

        # Tenant A must NOT see it
        token_a = _login(client, "admin@example.com", "admin123")
        r_list = client.get(
            "/api/v1/tspm/projects",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r_list.status_code == 200
        project_ids = [p["id"] for p in r_list.json()]
        assert project_id not in project_ids, (
            f"RLS ihlali: Tenant A, Tenant B'nin projesini ({project_id}) görebiliyor"
        )

    def test_direct_project_fetch_returns_404_across_tenants(
        self, client: TestClient, db_ready: bool
    ) -> None:
        """GET /projects/{id} must 404 when the project belongs to another tenant."""
        if not db_ready:
            pytest.skip("DB yok")
        if not self._rls_enabled():
            pytest.skip("RLS etkin değil")

        with SessionLocal() as db:
            try:
                _ensure_tenant_b(db)
                b_email, b_pass = _ensure_tenant_b_user(db)
                db.commit()
            except Exception as exc:
                pytest.skip(f"Tenant B kurulumu başarısız: {exc}")

        # Tenant A creates project
        token_a = _login(client, "admin@example.com", "admin123")
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": f"CrossTenant-{uuid.uuid4().hex[:6]}"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        if r.status_code not in (200, 201):
            pytest.skip("Proje oluşturulamadı")
        project_id = r.json()["id"]

        # Tenant B tries direct fetch
        token_b = _login(client, b_email, b_pass)
        r2 = client.get(
            f"/api/v1/tspm/projects/{project_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r2.status_code in (403, 404), (
            f"RLS ihlali: Tenant B, Tenant A'nın projesine doğrudan erişebildi "
            f"(HTTP {r2.status_code})"
        )
