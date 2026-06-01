"""
tests/unit/test_utility_routes.py
===================================
Utility blueprint (/api/health, /api/stats, /api/settings, /api/request, …)
için birim testler.

Dış bağımlılıklar (DB, dosya sistemi, harici HTTP) monkeypatching ile izole edilir.
"""
import importlib
import sys
import json
import pytest


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — harici bağımlılıklar stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    # DB stub'ları
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(engine_client):
    """Oturum enjekte edilmiş istemci — auth gerektiren endpoint'ler için."""
    with engine_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return engine_client


# ── /api/health ───────────────────────────────────────────────────────────────

def test_health_returns_200(engine_client):
    """Health endpoint kimlik doğrulama gerektirmemeli ve 200 dönmeli."""
    response = engine_client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_json(engine_client):
    """Health yanıtı JSON formatında olmalı."""
    response = engine_client.get("/api/health")
    data = response.get_json()
    assert data is not None


def test_health_contains_status_ok(engine_client):
    """Health yanıtı status=ok içermeli."""
    response = engine_client.get("/api/health")
    data = response.get_json()
    assert data.get("status") == "ok"


def test_health_contains_timestamp(engine_client):
    """Health yanıtı timestamp alanı içermeli."""
    response = engine_client.get("/api/health")
    data = response.get_json()
    assert "timestamp" in data
    assert isinstance(data["timestamp"], (int, float))


# ── /api/stats ────────────────────────────────────────────────────────────────

def test_stats_requires_auth(engine_client):
    """/api/stats endpoint'i oturum açılmadan 401 dönmeli."""
    response = engine_client.get("/api/stats")
    assert response.status_code == 401


def test_stats_returns_data_when_authed(authed_client):
    """/api/stats oturum açıkken geçerli yanıt dönmeli."""
    response = authed_client.get("/api/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert "totals" in data
    assert "history" in data


# ── /api/settings ─────────────────────────────────────────────────────────────

def test_get_settings_requires_auth(engine_client):
    """/api/settings GET oturum açılmadan 401 dönmeli."""
    response = engine_client.get("/api/settings")
    assert response.status_code == 401


def test_get_settings_returns_json_when_authed(authed_client, monkeypatch, tmp_path):
    """Oturum açıkken /api/settings GET JSON dönmeli."""
    # .env dosyasını geçici dizinde simüle et
    monkeypatch.setattr("config.settings.BASE_DIR", tmp_path, raising=False)
    response = authed_client.get("/api/settings")
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
    assert "has_api_key" in data


def test_save_settings_requires_auth(engine_client):
    """/api/settings POST oturum açılmadan 401 dönmeli."""
    response = engine_client.post(
        "/api/settings",
        json={"BROWSER": "chromium"},
        content_type="application/json",
    )
    assert response.status_code == 401


# ── /api/request (proxy) ──────────────────────────────────────────────────────

def test_proxy_request_requires_auth(engine_client):
    """/api/request proxy endpoint'i oturum açılmadan 401 dönmeli."""
    response = engine_client.post(
        "/api/request",
        json={"url": "http://example.com"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_proxy_request_missing_url_returns_400(authed_client):
    """URL belirtilmezse /api/request 400 dönmeli."""
    response = authed_client.post(
        "/api/request",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
