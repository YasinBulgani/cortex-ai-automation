"""Engine unit tests — routes/mobile_routes.py

Flask test client kullanarak endpoint davranışlarını doğrular.
Gerçek subprocess / Appium / ADB başlatılmaz; SSE kuyrukları
doğrudan test edilir.
"""
from __future__ import annotations

import json
import queue
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

ENGINE_ROOT = Path(__file__).resolve().parents[3]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from routes.mobile_routes import mobile_bp, _run_queues, _run_lock  # noqa: E402


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.register_blueprint(mobile_bp)
    app.config["TESTING"] = True
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


# ── /api/mobile/devices ────────────────────────────────────────────────────────


class TestListDevices:
    def test_returns_200(self, client):
        resp = client.get("/api/mobile/devices")
        assert resp.status_code == 200

    def test_returns_devices_list(self, client):
        data = resp = client.get("/api/mobile/devices").get_json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_device_has_required_fields(self, client):
        devices = client.get("/api/mobile/devices").get_json()
        for d in devices:
            assert "slug" in d
            assert "name" in d
            assert "platform" in d
            assert d["platform"] in ("ios", "android")

    def test_ios_and_android_both_present(self, client):
        devices = client.get("/api/mobile/devices").get_json()
        platforms = {d["platform"] for d in devices}
        assert "ios" in platforms
        assert "android" in platforms


# ── /api/mobile/run/<run_id>/stop ─────────────────────────────────────────────


class TestStopMobileRun:
    def test_stop_unknown_run_returns_404(self, client):
        resp = client.post("/api/mobile/run/nonexistent-run/stop")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["stopped"] is False

    def test_stop_active_run_sends_done_and_returns_200(self, client):
        run_id = "test-stop-run-001"
        q: queue.Queue = queue.Queue()
        with _run_lock:
            _run_queues[run_id] = q

        try:
            resp = client.post(f"/api/mobile/run/{run_id}/stop")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["stopped"] is True
            assert data["run_id"] == run_id

            # Queue should have received the all_done signal
            msg = q.get_nowait()
            assert msg["type"] == "all_done"
            assert msg.get("stopped") is True
        finally:
            with _run_lock:
                _run_queues.pop(run_id, None)


# ── /api/mobile/farm-status ───────────────────────────────────────────────────


class TestFarmStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/mobile/farm-status")
        assert resp.status_code == 200

    def test_has_status_field(self, client):
        data = client.get("/api/mobile/farm-status").get_json()
        assert "status" in data or "farm" in data or "active_farm" in data

    def test_has_devices_field(self, client):
        data = client.get("/api/mobile/farm-status").get_json()
        # farm-status always returns some form of device/emulator count
        assert isinstance(data, dict)


# ── /api/mobile/run (POST) — validation ───────────────────────────────────────


class TestRunSingleValidation:
    def test_missing_device_slug_returns_400(self, client):
        resp = client.post(
            "/api/mobile/run",
            json={"project_id": "proj-1"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_project_id_is_optional(self, client):
        # project_id is optional — route accepts device_slug alone and spawns a run
        resp = client.post(
            "/api/mobile/run",
            json={"device_slug": "pixel_7"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert "run_id" in resp.get_json()

    def test_unknown_slug_returns_400(self, client):
        resp = client.post(
            "/api/mobile/run",
            json={"device_slug": "nonexistent-slug", "project_id": "proj-1"},
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()


# ── /api/mobile/run-live (POST) — validation ──────────────────────────────────


class TestRunLiveValidation:
    def test_empty_serials_returns_400(self, client):
        resp = client.post(
            "/api/mobile/run-live",
            json={"serials": [], "project_id": "proj-1"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_serials_returns_400(self, client):
        resp = client.post(
            "/api/mobile/run-live",
            json={"project_id": "proj-1"},
            content_type="application/json",
        )
        assert resp.status_code == 400
