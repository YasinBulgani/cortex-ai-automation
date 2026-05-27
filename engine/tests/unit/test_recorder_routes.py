"""
tests/unit/test_recorder_routes.py
====================================
Recorder blueprint endpoint testleri.

TestRecorder (Playwright/browser bağımlısı) tamamen mock'lanır.
Testler yalnızca HTTP katmanını doğrular:
  - Eksik / geçersiz girdi → 400 / 404
  - Oturum bulunamadı → 404
  - Geçersiz dosya yolu → 403

Cortex_Ai_Automation sürümü ek endpoint'leri de kapsar:
  - /api/recorder/<session_id>/pause
  - /api/recorder/<session_id>/resume
  - /api/recorder/<session_id>/status
"""
import importlib
import sys
import json
import pytest
from unittest.mock import MagicMock, patch


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch):
    """TestRecorder bağımlılıkları stub'lanmış test istemcisi."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    sys.modules.pop("app", None)
    fake_recorder_module = MagicMock()
    monkeypatch.setitem(sys.modules, "core.test_recorder", fake_recorder_module)

    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(engine_client):
    """Oturum enjekte edilmiş istemci."""
    with engine_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return engine_client


# ── /api/recorder/start ───────────────────────────────────────────────────────

def test_start_requires_auth(engine_client):
    """/api/recorder/start oturum açılmadan 401 dönmeli."""
    response = engine_client.post(
        "/api/recorder/start",
        json={"name": "my-session"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_start_missing_name_returns_400(authed_client):
    """name alanı eksikken /api/recorder/start 400 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.post(
            "/api/recorder/start",
            json={"domain": "default"},
            content_type="application/json",
        )
    assert response.status_code == 400
    data = response.get_json()
    assert data.get("ok") is False
    assert "error" in data


def test_start_empty_name_returns_400(authed_client):
    """Boş name ile /api/recorder/start 400 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.post(
            "/api/recorder/start",
            json={"name": "   "},
            content_type="application/json",
        )
    assert response.status_code == 400


# ── /api/recorder/<session_id>/stop ──────────────────────────────────────────

def test_stop_nonexistent_session_returns_404(authed_client):
    """Var olmayan session_id ile stop 404 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.post("/api/recorder/nonexistent-id/stop")
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("ok") is False


# ── /api/recorder/<session_id>/pause ─────────────────────────────────────────

def test_pause_nonexistent_session_returns_404(authed_client):
    """Var olmayan session_id ile pause 404 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.post("/api/recorder/nonexistent-id/pause")
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("ok") is False


def test_pause_existing_session_calls_pause(authed_client):
    """Geçerli session ile pause recorder.pause() çağrılmalı ve ok:true dönmeli."""
    fake_recorder = MagicMock()
    fake_recorder.pause.return_value = None
    with patch("routes.recorder_routes._active_sessions", {"sess1": fake_recorder}):
        response = authed_client.post("/api/recorder/sess1/pause")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("ok") is True
    assert data.get("paused") is True


# ── /api/recorder/<session_id>/resume ────────────────────────────────────────

def test_resume_nonexistent_session_returns_404(authed_client):
    """Var olmayan session_id ile resume 404 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.post("/api/recorder/nonexistent-id/resume")
    assert response.status_code == 404


def test_resume_existing_session_returns_ok(authed_client):
    """Geçerli session ile resume ok:true dönmeli."""
    fake_recorder = MagicMock()
    fake_recorder.resume.return_value = None
    with patch("routes.recorder_routes._active_sessions", {"sess1": fake_recorder}):
        response = authed_client.post("/api/recorder/sess1/resume")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("ok") is True
    assert data.get("paused") is False


# ── /api/recorder/<session_id>/status ────────────────────────────────────────

def test_status_nonexistent_session_returns_404(authed_client):
    """Var olmayan session_id ile status 404 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.get("/api/recorder/nonexistent-id/status")
    assert response.status_code == 404


def test_status_existing_session_returns_fields(authed_client):
    """Geçerli session ile status yanıtı beklenen alanları içermeli."""
    fake_session = MagicMock()
    fake_session.actions = []
    fake_session.name = "my-test"
    fake_session.domain = "default"

    fake_recorder = MagicMock()
    fake_recorder.session = fake_session
    fake_recorder.is_paused = False

    with patch("routes.recorder_routes._active_sessions", {"sess1": fake_recorder}):
        response = authed_client.get("/api/recorder/sess1/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("ok") is True
    assert "paused" in data
    assert "action_count" in data
    assert "name" in data


# ── /api/recorder/<session_id>/action ────────────────────────────────────────

def test_add_action_nonexistent_session_returns_404(authed_client):
    """Var olmayan session'a aksiyon ekleme 404 dönmeli."""
    with patch("routes.recorder_routes._active_sessions", {}):
        response = authed_client.post(
            "/api/recorder/nonexistent/action",
            json={"action_type": "click", "selector": "#btn"},
            content_type="application/json",
        )
    assert response.status_code == 404


def test_add_action_missing_action_type_returns_400(authed_client):
    """action_type eksikken aksiyon ekleme 400 dönmeli."""
    fake_recorder = MagicMock()
    with patch("routes.recorder_routes._active_sessions", {"sess1": fake_recorder}):
        response = authed_client.post(
            "/api/recorder/sess1/action",
            json={"selector": "#btn"},
            content_type="application/json",
        )
    assert response.status_code == 400
    data = response.get_json()
    assert data.get("ok") is False


# ── /api/recorder/sessions (DELETE) ──────────────────────────────────────────

def test_delete_session_path_traversal_returns_403(authed_client, monkeypatch, tmp_path):
    """Path traversal denemesi DELETE endpoint'inde 403 dönmeli."""
    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    response = authed_client.delete("/api/recorder/sessions/../../etc/passwd")
    assert response.status_code == 403


def test_delete_nonexistent_file_returns_404(authed_client, monkeypatch, tmp_path):
    """Var olmayan dosya silinmeye çalışılınca 404 dönmeli."""
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    response = authed_client.delete("/api/recorder/sessions/no_such_file.json")
    assert response.status_code == 404


# ── /api/recorder/generate ────────────────────────────────────────────────────

def test_generate_missing_session_path_returns_400(authed_client):
    """session_path eksikken /api/recorder/generate 400 dönmeli."""
    response = authed_client.post(
        "/api/recorder/generate",
        json={"format": "playwright"},
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data.get("ok") is False


def test_generate_nonexistent_file_returns_404(authed_client, tmp_path):
    """Var olmayan dosya yolu ile /api/recorder/generate 404 dönmeli."""
    response = authed_client.post(
        "/api/recorder/generate",
        json={"session_path": str(tmp_path / "no_file.json"), "format": "playwright"},
        content_type="application/json",
    )
    assert response.status_code == 404


def test_generate_unknown_format_returns_400(authed_client, tmp_path):
    """Bilinmeyen format ile /api/recorder/generate 400 dönmeli."""
    session_file = tmp_path / "session.json"
    session_file.write_text(
        json.dumps({"name": "test", "domain": "default", "actions": [], "started_at": "2026-01-01T00:00:00"}),
        encoding="utf-8",
    )
    fake_recorder = MagicMock()
    with patch("core.test_recorder.TestRecorder.load_session", return_value=fake_recorder):
        response = authed_client.post(
            "/api/recorder/generate",
            json={"session_path": str(session_file), "format": "unknown_fmt"},
            content_type="application/json",
        )
    assert response.status_code == 400
