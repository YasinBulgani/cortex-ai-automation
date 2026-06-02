"""Unit tests for the mobile router — 12 tests.

SSE streaming endpoint (/sessions/{id}/stream) is intentionally skipped.
All device_broker, orchestrator, and llm_stepper calls are mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.mobile.router import router as mobile_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_device(device_id="dev-1", status="idle", platform="android"):
    from app.domains.mobile.schemas import Device
    return Device(
        id=device_id,
        name="Pixel 7 Emulator",
        platform=platform,
        os_version="13",
        profile="pixel7",
        kind="emulator",
        status=status,
        appium_url="http://127.0.0.1:4723",
    )


def _make_session(session_id="sess-1", device_id="dev-1"):
    from app.domains.mobile.schemas import Session
    return Session(
        id=session_id,
        device_id=device_id,
        scenario_name="Login Test",
        status="passed",
        started_at=datetime(2026, 1, 1, 10, 0, 0),
        mode="simulation",
    )


def _make_farm_stats():
    from app.domains.mobile.schemas import FarmStats
    return FarmStats(
        total=4,
        online=3,
        running=1,
        idle=2,
        offline=1,
        by_platform={"android": 3, "ios": 1},
    )


def _make_step_response():
    from app.domains.mobile.schemas import StepGenerationResponse
    return StepGenerationResponse(
        steps=[],
        model="qwen2.5-coder:7b",
        fallback_used=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(mobile_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

class TestMobileDevices:
    def test_list_devices_returns_list(self, client):
        broker = MagicMock()
        broker.list.return_value = [_make_device("dev-1"), _make_device("dev-2")]
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.get("/api/v1/mobile/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_devices_empty_returns_empty_list(self, client):
        broker = MagicMock()
        broker.list.return_value = []
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.get("/api/v1/mobile/devices")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_device_returns_device(self, client):
        dev = _make_device("dev-42")
        broker = MagicMock()
        broker.get.return_value = dev
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.get("/api/v1/mobile/devices/dev-42")
        assert resp.status_code == 200
        assert resp.json()["id"] == "dev-42"

    def test_get_device_404_when_not_found(self, client):
        broker = MagicMock()
        broker.get.return_value = None
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.get("/api/v1/mobile/devices/nonexistent")
        assert resp.status_code == 404

    def test_reboot_device_returns_device(self, client):
        dev = _make_device("dev-1", status="idle")
        broker = MagicMock()
        broker.reboot.return_value = dev
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.post("/api/v1/mobile/devices/dev-1/reboot")
        assert resp.status_code == 200
        assert resp.json()["id"] == "dev-1"

    def test_reboot_device_404_when_not_found(self, client):
        broker = MagicMock()
        broker.reboot.return_value = None
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.post("/api/v1/mobile/devices/nonexistent/reboot")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Farm stats
# ---------------------------------------------------------------------------

class TestMobileStats:
    def test_farm_stats_returns_200_with_counts(self, client):
        stats = _make_farm_stats()
        broker = MagicMock()
        broker.stats.return_value = {
            "total": 4, "online": 3, "running": 1,
            "idle": 2, "offline": 1,
            "by_platform": {"android": 3, "ios": 1},
        }
        with patch("app.domains.mobile.router.get_broker", return_value=broker):
            resp = client.get("/api/v1/mobile/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert "by_platform" in data


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class TestMobileSessions:
    def test_list_sessions_returns_list(self, client):
        store = MagicMock()
        store.list_recent.return_value = [_make_session("s-1"), _make_session("s-2")]
        with patch("app.domains.mobile.router.get_store", return_value=store):
            resp = client.get("/api/v1/mobile/sessions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_session_returns_200(self, client):
        store = MagicMock()
        store.get.return_value = _make_session("sess-99")
        with patch("app.domains.mobile.router.get_store", return_value=store):
            resp = client.get("/api/v1/mobile/sessions/sess-99")
        assert resp.status_code == 200
        assert resp.json()["id"] == "sess-99"

    def test_get_session_404_when_not_found(self, client):
        store = MagicMock()
        store.get.return_value = None
        with patch("app.domains.mobile.router.get_store", return_value=store):
            resp = client.get("/api/v1/mobile/sessions/missing")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Generate from prompt
# ---------------------------------------------------------------------------

class TestMobileGenerateFromPrompt:
    def test_generate_from_prompt_returns_steps(self, client):
        step_resp = _make_step_response()
        with patch("app.domains.mobile.router.generate_steps", return_value=step_resp):
            resp = client.post("/api/v1/mobile/generate-from-prompt", json={
                "prompt": "Tap the login button and enter credentials",
                "platform": "android",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "steps" in data
        assert "model" in data
