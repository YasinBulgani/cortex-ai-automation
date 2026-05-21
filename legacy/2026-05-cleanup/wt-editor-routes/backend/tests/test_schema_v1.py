"""Şema v1 doğrulama + sürüm oluşturma (Postgres gerekir)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers(client: TestClient, db_ready: bool) -> dict[str, str]:
    if not db_ready:
        pytest.skip("Veritabanı gerekli")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"},
    )
    assert r.status_code == 200
    tok = r.json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _new_dataset(client: TestClient, headers: dict[str, str]) -> str:
    name = f"schema_v1_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/v1/datasets",
        headers=headers,
        json={"name": name, "description": None},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_version_rejects_empty_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    ds = _new_dataset(client, auth_headers)
    r = client.post(
        f"/api/v1/datasets/{ds}/versions",
        headers=auth_headers,
        json={"snapshot": {"version": 1, "fields": []}, "profile": None, "pii_flags": None},
    )
    assert r.status_code == 422


def test_version_rejects_unknown_field_type(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    ds = _new_dataset(client, auth_headers)
    r = client.post(
        f"/api/v1/datasets/{ds}/versions",
        headers=auth_headers,
        json={
            "snapshot": {
                "version": 1,
                "fields": [{"name": "x", "type": "blob"}],
            },
            "profile": None,
            "pii_flags": None,
        },
    )
    assert r.status_code == 422


def test_version_rejects_invalid_field_name(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    ds = _new_dataset(client, auth_headers)
    r = client.post(
        f"/api/v1/datasets/{ds}/versions",
        headers=auth_headers,
        json={
            "snapshot": {
                "version": 1,
                "fields": [{"name": "123bad", "type": "string"}],
            },
            "profile": None,
            "pii_flags": None,
        },
    )
    assert r.status_code == 422


def test_version_rejects_duplicate_field_names(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    ds = _new_dataset(client, auth_headers)
    r = client.post(
        f"/api/v1/datasets/{ds}/versions",
        headers=auth_headers,
        json={
            "snapshot": {
                "version": 1,
                "fields": [
                    {"name": "a", "type": "string"},
                    {"name": "a", "type": "integer"},
                ],
            },
            "profile": None,
            "pii_flags": None,
        },
    )
    assert r.status_code == 422


def test_version_rejects_wrong_version_number(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    ds = _new_dataset(client, auth_headers)
    r = client.post(
        f"/api/v1/datasets/{ds}/versions",
        headers=auth_headers,
        json={
            "snapshot": {
                "version": 2,
                "fields": [{"name": "x", "type": "string"}],
            },
            "profile": None,
            "pii_flags": None,
        },
    )
    assert r.status_code == 422


def test_version_accepts_valid_snapshot_defaults_version(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    ds = _new_dataset(client, auth_headers)
    r = client.post(
        f"/api/v1/datasets/{ds}/versions",
        headers=auth_headers,
        json={
            "snapshot": {
                "fields": [
                    {"name": "id", "type": "integer"},
                    {"name": "email", "type": "string", "nullable": True},
                ],
            },
            "profile": None,
            "pii_flags": None,
        },
    )
    assert r.status_code == 201, r.text
    ver_id = r.json()["id"]

    sch = client.get(
        f"/api/v1/datasets/{ds}/versions/{ver_id}/schema",
        headers=auth_headers,
    )
    assert sch.status_code == 200
    snap = sch.json()["snapshot"]
    assert snap["version"] == 1
    assert len(snap["fields"]) == 2
    assert snap["fields"][1]["nullable"] is True
