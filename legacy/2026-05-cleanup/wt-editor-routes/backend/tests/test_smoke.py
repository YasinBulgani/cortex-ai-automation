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
