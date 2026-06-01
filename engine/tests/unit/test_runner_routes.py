"""
tests/unit/test_runner_routes.py
=================================
runner_bp (/api/run, /api/run/<id>/stream, /api/run/<id>/cancel,
           /api/nexus/run, /api/runner/run-feature, /api/run-maven,
           /api/projects/*) için birim testler.

Dış bağımlılıklar (subprocess, threading, DB, dosya sistemi) monkeypatching
ile izole edilir; SSE stream testleri Content-Type doğrulaması üzerinden geçer.
"""
from __future__ import annotations

import importlib
import json
import queue
import sys
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def runner_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — tüm harici bağımlılıklar stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-runner-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-runner-internal")
    monkeypatch.setenv("RUN_TIMEOUT_S", "1800")
    monkeypatch.setenv("PYTEST_RUN_TIMEOUT", "600")

    # DB stub
    monkeypatch.setattr("core.db.record_test_run", lambda *a, **kw: None, raising=False)
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    # settings stub
    class _FakeSettings:
        BASE_DIR = tmp_path
        ALLURE_RESULTS_DIR = tmp_path / "allure-results"
        ALLURE_REPORT_DIR = tmp_path / "allure-report"
        TESTS_DIR = tmp_path / "tests"
        FEATURES_DIR = tmp_path / "features"

    fake_settings = _FakeSettings()
    fake_settings.ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fake_settings.ALLURE_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fake_settings.TESTS_DIR.mkdir(parents=True, exist_ok=True)
    fake_settings.FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    (tmp_path / "steps").mkdir(exist_ok=True)

    monkeypatch.setattr("config.settings.settings", fake_settings, raising=False)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


@pytest.fixture
def authed_runner_client(runner_client):
    """Oturum enjekte edilmiş istemci."""
    with runner_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "runner@example.com"
    return runner_client


# ── /api/run (POST) ──────────────────────────────────────────────────────────

class TestRunTestsEndpoint:
    """POST /api/run başlatma testleri."""

    def test_run_returns_run_id(self, monkeypatch, runner_client):
        """Geçerli istek run_id döndürmeli."""
        import threading

        # Worker thread'i hemen sonlandır
        original_thread_start = threading.Thread.start

        def _noop_start(self, *a, **kw):
            pass

        monkeypatch.setattr(threading.Thread, "start", _noop_start)

        resp = runner_client.post(
            "/api/run",
            json={"markers": "smoke", "browser": "chromium"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "run_id" in data

    def test_run_returns_browser_field(self, monkeypatch, runner_client):
        """Yanıt browser alanını içermeli."""
        import threading
        monkeypatch.setattr(threading.Thread, "start", lambda self, *a, **kw: None)

        resp = runner_client.post(
            "/api/run",
            json={"browser": "firefox"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert data.get("browser") == "firefox"

    def test_run_invalid_browser_falls_back_to_chromium(self, monkeypatch, runner_client):
        """Geçersiz browser chromium'a düşmeli."""
        import threading
        monkeypatch.setattr(threading.Thread, "start", lambda self, *a, **kw: None)

        resp = runner_client.post(
            "/api/run",
            json={"browser": "ie11"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert data.get("browser") == "chromium"

    def test_run_empty_body_is_accepted(self, monkeypatch, runner_client):
        """Boş body ile istek 200 dönmeli (defaults uygulanır)."""
        import threading
        monkeypatch.setattr(threading.Thread, "start", lambda self, *a, **kw: None)

        resp = runner_client.post("/api/run", json={}, content_type="application/json")
        assert resp.status_code == 200


# ── /api/run/<id>/cancel (DELETE/POST) ───────────────────────────────────────

class TestCancelRunEndpoint:
    """DELETE /api/run/<id>/cancel testleri."""

    def test_cancel_unknown_run_returns_404(self, runner_client):
        """Var olmayan run_id için 404 dönmeli."""
        resp = runner_client.delete("/api/run/nonexistent_run_id/cancel")
        assert resp.status_code == 404

    def test_cancel_unknown_run_json_error(self, runner_client):
        """404 yanıtı JSON error alanı içermeli."""
        resp = runner_client.delete("/api/run/nonexistent_run_id/cancel")
        data = resp.get_json()
        assert "error" in data

    def test_cancel_known_run_returns_200(self, monkeypatch, runner_client):
        """Aktif queue'si olan run_id başarıyla iptal edilmeli."""
        import routes.runner_routes as rr

        test_run_id = "test_cancel_run_001"
        rr._run_queues[test_run_id] = queue.Queue()

        try:
            resp = runner_client.delete(f"/api/run/{test_run_id}/cancel")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data.get("ok") is True
            assert data.get("run_id") == test_run_id
        finally:
            rr._run_queues.pop(test_run_id, None)
            rr._cancelled_runs.discard(test_run_id)

    def test_cancel_via_post_method(self, monkeypatch, runner_client):
        """POST methodu ile de iptal mümkün olmalı."""
        import routes.runner_routes as rr

        test_run_id = "test_cancel_post_002"
        rr._run_queues[test_run_id] = queue.Queue()

        try:
            resp = runner_client.post(f"/api/run/{test_run_id}/cancel")
            assert resp.status_code == 200
        finally:
            rr._run_queues.pop(test_run_id, None)
            rr._cancelled_runs.discard(test_run_id)


# ── /api/run/<id>/stream (GET, SSE) ─────────────────────────────────────────

class TestStreamRunEndpoint:
    """GET /api/run/<id>/stream SSE stream testleri."""

    def test_stream_unknown_id_returns_error_event(self, runner_client):
        """Var olmayan ID için SSE error event dönmeli."""
        resp = runner_client.get("/api/run/nonexistent_stream_id/stream")
        # SSE bağlantısı açılır, hata event olarak iletilir
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_stream_content_type_is_event_stream(self, runner_client):
        """Content-Type text/event-stream olmalı."""
        resp = runner_client.get("/api/run/any_id_here/stream")
        assert "text/event-stream" in resp.content_type

    def test_stream_known_id_delivers_done_event(self, runner_client):
        """Queue'si olan run_id için 'done' event alınmalı."""
        import routes.runner_routes as rr

        test_run_id = "stream_test_run_003"
        q = queue.Queue()
        q.put({"type": "output", "text": "Koşum başladı"})
        q.put({"type": "done", "returncode": 0})
        rr._run_queues[test_run_id] = q

        try:
            resp = runner_client.get(f"/api/run/{test_run_id}/stream")
            assert resp.status_code == 200
            raw = b"".join(resp.response).decode("utf-8")
            assert "done" in raw
        finally:
            rr._run_queues.pop(test_run_id, None)


# ── /api/nexus/run (POST) ────────────────────────────────────────────────────

class TestNexusRunEndpoint:
    """POST /api/nexus/run TSPM execution testleri."""

    def test_nexus_run_missing_scenarios_returns_400(self, runner_client):
        """scenarios listesi olmadan 400 dönmeli."""
        resp = runner_client.post(
            "/api/nexus/run",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_nexus_run_empty_scenarios_returns_400(self, runner_client):
        """Boş scenarios listesiyle 400 dönmeli."""
        resp = runner_client.post(
            "/api/nexus/run",
            json={"scenarios": []},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_nexus_run_invalid_mode_returns_400(self, runner_client):
        """Geçersiz mode parametresiyle 400 dönmeli."""
        resp = runner_client.post(
            "/api/nexus/run",
            json={"scenarios": [{"id": "s1", "title": "Test"}], "mode": "invalid_mode"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_nexus_run_simulation_mode_returns_run_id(self, monkeypatch, runner_client):
        """simulation mode başarıyla run_id döndürmeli."""
        import threading
        monkeypatch.setattr(threading.Thread, "start", lambda self, *a, **kw: None)

        resp = runner_client.post(
            "/api/nexus/run",
            json={"scenarios": [{"id": "s1", "title": "Senaryo 1", "steps": ["Given step"]}], "mode": "simulation"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "run_id" in data
        assert data.get("mode") == "simulation"


# ── /api/runner/run-feature (POST) ───────────────────────────────────────────

class TestRunFeatureEndpoint:
    """POST /api/runner/run-feature testleri."""

    def test_run_feature_missing_path_returns_400(self, runner_client):
        """feature_path olmadan 400 dönmeli."""
        resp = runner_client.post(
            "/api/runner/run-feature",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("ok") is False

    def test_run_feature_nonexistent_file_returns_404(self, runner_client):
        """Var olmayan dosya 404 dönmeli."""
        resp = runner_client.post(
            "/api/runner/run-feature",
            json={"feature_path": "/nonexistent/path/test.feature"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_run_feature_error_field_in_404(self, runner_client):
        """404 yanıtı error alanı içermeli."""
        resp = runner_client.post(
            "/api/runner/run-feature",
            json={"feature_path": "/nonexistent/file.feature"},
            content_type="application/json",
        )
        data = resp.get_json()
        assert "error" in data


# ── /api/run-maven (POST) ────────────────────────────────────────────────────

class TestRunMavenEndpoint:
    """POST /api/run-maven testleri."""

    def test_maven_run_path_outside_allowed_roots_returns_400(self, runner_client, monkeypatch):
        """İzin verilen kök dışı path 400 dönmeli."""
        monkeypatch.setenv("MAVEN_ALLOWED_ROOTS", "/tmp/allowed_only")

        resp = runner_client.post(
            "/api/run-maven",
            json={"maven_path": "/etc/passwd"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data


# ── /api/projects/* ──────────────────────────────────────────────────────────

class TestProjectsEndpoints:
    """Proje yönetimi endpoint testleri."""

    def test_projects_list_returns_json(self, runner_client):
        """GET /api/projects/list JSON dönmeli."""
        resp = runner_client.get("/api/projects/list")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_create_project_missing_name_returns_400(self, runner_client):
        """POST /api/projects/create isimsiz istek 400 dönmeli."""
        resp = runner_client.post(
            "/api/projects/create",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_projects_files_nonexistent_project_returns_404(self, runner_client):
        """GET /api/projects/files/<name> var olmayan proje 404 dönmeli."""
        resp = runner_client.get("/api/projects/files/nonexistent_project_xyz")
        assert resp.status_code == 404

    def test_system_status_returns_json(self, runner_client):
        """GET /api/projects/status JSON dönmeli."""
        resp = runner_client.get("/api/projects/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "backend" in data

    def test_setup_everything_returns_message(self, runner_client):
        """POST /api/projects/setup başarı mesajı dönmeli."""
        resp = runner_client.post("/api/projects/setup")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data

    def test_start_services_returns_message(self, runner_client):
        """POST /api/projects/start-services başarı mesajı dönmeli."""
        resp = runner_client.post("/api/projects/start-services")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data
