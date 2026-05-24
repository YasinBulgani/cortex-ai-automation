"""Smoke testler: DB yokken health; DB + seed varsa login ve korumalı uçlar."""

import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_ready_shape(client: TestClient) -> None:
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert "ready" in body
    # DB/engine/rate_limiter alt-kontrolleri artık "checks" altında gruplanıyor.
    assert "checks" in body
    assert "database" in body["checks"]


def test_datasets_requires_auth(client: TestClient) -> None:
    r = client.get("/api/v1/datasets")
    assert r.status_code == 401


def test_jobs_requires_auth(client: TestClient) -> None:
    r = client.get("/api/v1/jobs")
    assert r.status_code == 401


def test_login_rejects_unknown_user(client: TestClient, db_ready: bool) -> None:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "x"},
    )
    assert r.status_code == 401


def test_login_admin_and_me(client: TestClient, db_ready: bool) -> None:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "admin@example.com"
    assert "admin" in body["roles"]


def test_datasets_list_with_token(client: TestClient, db_ready: bool) -> None:
    if not db_ready:
        pytest.skip("Veritabanı hazır değil")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = client.get(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Yeni kayıt edilen router'lar (2026-05-24 fix) ─────────────────────────

def test_events_requires_auth(client: TestClient) -> None:
    """events router artık kayıtlı — 401 olmalı, 404 değil."""
    r = client.get("/api/v1/events")
    assert r.status_code in (401, 403, 405), f"events endpoint 404 döndü — router kaydı kontrol et (got {r.status_code})"


def test_defects_requires_auth(client: TestClient) -> None:
    """defects router artık kayıtlı — 401 olmalı, 404 değil."""
    r = client.get("/api/v1/defects")
    assert r.status_code in (401, 403, 405), f"defects endpoint 404 döndü — router kaydı kontrol et (got {r.status_code})"


def test_kb_requires_auth(client: TestClient) -> None:
    """knowledge_base router artık kayıtlı — 401 olmalı, 404 değil."""
    r = client.get("/api/v1/kb")
    assert r.status_code in (401, 403, 405), f"kb endpoint 404 döndü — router kaydı kontrol et (got {r.status_code})"


def test_pilot_requires_auth(client: TestClient) -> None:
    """pilot router artık kayıtlı — 401 olmalı, 404 değil."""
    r = client.get("/api/v1/pilot/sessions")
    assert r.status_code in (401, 403, 405), f"pilot endpoint 404 döndü — router kaydı kontrol et (got {r.status_code})"
