"""
Regression route'unun unit testleri — Flask → FastAPI port doğrulaması.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.engine.routes.regression import RegressionStore, get_store, router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)

    # Her test için yeni store
    fresh_store = RegressionStore()
    app.dependency_overrides[get_store] = lambda: fresh_store
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_list_empty_returns_empty_array(client):
    r = client.get("/api/regression-sets")
    assert r.status_code == 200
    assert r.json() == []


def test_create_set_returns_set(client):
    r = client.post("/api/regression-sets", json={"name": "Smoke"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Smoke"
    assert body["id"] == 1


def test_create_duplicate_name_rejected(client):
    client.post("/api/regression-sets", json={"name": "Smoke"})
    r = client.post("/api/regression-sets", json={"name": "Smoke"})
    assert r.status_code == 400
    assert "zaten var" in r.json()["detail"]


def test_create_empty_name_rejected(client):
    r = client.post("/api/regression-sets", json={"name": ""})
    assert r.status_code == 422  # Pydantic validation


def test_delete_set(client):
    client.post("/api/regression-sets", json={"name": "Smoke"})
    r = client.delete("/api/regression-sets/1")
    assert r.status_code == 204
    r = client.get("/api/regression-sets")
    assert r.json() == []


def test_add_feature_to_set(client):
    client.post("/api/regression-sets", json={"name": "Smoke"})
    r = client.post("/api/regression-sets/1/features", json={"feature_name": "login.feature"})
    assert r.status_code == 201
    assert r.json() == {"ok": True}


def test_remove_feature_from_set(client):
    client.post("/api/regression-sets", json={"name": "Smoke"})
    client.post("/api/regression-sets/1/features", json={"feature_name": "login.feature"})
    r = client.delete("/api/regression-sets/1/features/login.feature")
    assert r.status_code == 204
