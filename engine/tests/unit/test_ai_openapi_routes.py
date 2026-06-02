"""
tests/unit/test_ai_openapi_routes.py
====================================
ai_openapi_bp (GET /api/ai/openapi.json) için birim testler.

Blueprint yalnızca Flask ve stdlib kullandığından harici stub gerekmez;
döndürülen OpenAPI 3.0 spec'in yapısı ve içeriği doğrulanır.
"""
import sys
import pytest


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def openapi_client():
    """Sadece ai_openapi_bp ile kurulmuş minimal Flask test istemcisi."""
    sys.modules.pop("routes.ai_openapi", None)
    sys.modules.pop("ai_openapi", None)

    from flask import Flask
    from routes.ai_openapi import ai_openapi_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(ai_openapi_bp)

    with app.test_client() as client:
        yield client


# ── GET /api/ai/openapi.json ──────────────────────────────────────────────────

def test_openapi_spec_returns_200(openapi_client):
    """GET /api/ai/openapi.json 200 dönmeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    assert response.status_code == 200


def test_openapi_spec_returns_json(openapi_client):
    """Yanıt geçerli JSON olmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert data is not None


def test_openapi_spec_has_openapi_version_field(openapi_client):
    """Spec openapi alanı içermeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "openapi" in data


def test_openapi_spec_version_is_3(openapi_client):
    """openapi alanı 3.x.x ile başlamalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert data["openapi"].startswith("3.")


def test_openapi_spec_has_info_field(openapi_client):
    """Spec info alanı içermeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "info" in data


def test_openapi_spec_info_has_title(openapi_client):
    """info.title alanı mevcut ve dolu olmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert data["info"].get("title")


def test_openapi_spec_info_has_version(openapi_client):
    """info.version alanı mevcut olmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert data["info"].get("version")


def test_openapi_spec_has_paths_field(openapi_client):
    """Spec paths alanı içermeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "paths" in data


def test_openapi_spec_paths_is_not_empty(openapi_client):
    """paths alanı en az bir endpoint içermeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert len(data["paths"]) > 0


def test_openapi_spec_contains_generate_test_path(openapi_client):
    """paths içinde /api/ai/generate-test endpoint'i bulunmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "/api/ai/generate-test" in data["paths"]


def test_openapi_spec_contains_self_heal_path(openapi_client):
    """paths içinde /api/ai/self-heal endpoint'i bulunmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "/api/ai/self-heal" in data["paths"]


def test_openapi_spec_has_servers_field(openapi_client):
    """Spec servers alanı içermeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "servers" in data
    assert isinstance(data["servers"], list)
    assert len(data["servers"]) > 0


def test_openapi_spec_generate_test_has_post_method(openapi_client):
    """/api/ai/generate-test endpoint'i POST metodunu içermeli."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "post" in data["paths"]["/api/ai/generate-test"]


def test_openapi_spec_generate_bdd_path_exists(openapi_client):
    """paths içinde /api/ai/generate-bdd endpoint'i bulunmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    data = response.get_json()
    assert "/api/ai/generate-bdd" in data["paths"]


def test_openapi_spec_content_type_is_json(openapi_client):
    """Yanıt Content-Type application/json olmalı."""
    response = openapi_client.get("/api/ai/openapi.json")
    assert "application/json" in response.content_type
