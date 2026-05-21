"""Mobile router HTTP entegrasyon testleri (FastAPI TestClient)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.P1


def test_list_devices_returns_ten(mobile_client: TestClient):
    r = mobile_client.get("/api/v1/mobile/devices")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 10
    assert {"id", "name", "platform", "os_version", "kind", "status"}.issubset(data[0].keys())


def test_get_device_by_id(mobile_client: TestClient):
    r = mobile_client.get("/api/v1/mobile/devices/and-pixel_8")
    assert r.status_code == 200
    assert r.json()["name"] == "Pixel 8"


def test_get_device_404(mobile_client: TestClient):
    r = mobile_client.get("/api/v1/mobile/devices/ghost")
    assert r.status_code == 404


def test_stats_endpoint(mobile_client: TestClient):
    r = mobile_client.get("/api/v1/mobile/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total"] == 10
    assert stats["by_platform"]["android"] == 6
    assert stats["by_platform"]["ios"] == 4


def test_reboot_changes_status_to_booting(mobile_client: TestClient):
    r = mobile_client.post("/api/v1/mobile/devices/and-pixel_8/reboot")
    assert r.status_code == 200
    assert r.json()["status"] == "booting"


def test_reboot_404(mobile_client: TestClient):
    r = mobile_client.post("/api/v1/mobile/devices/nope/reboot")
    assert r.status_code == 404


def test_enroll_physical_adds_device(mobile_client: TestClient):
    pre = mobile_client.get("/api/v1/mobile/devices").json()
    payload = {
        "name": "Lab Device 01",
        "platform": "android",
        "os_version": "14",
        "udid": "R58M3XYZ",
        "appium_url": "http://lab:4750",
    }
    r = mobile_client.post("/api/v1/mobile/enroll-physical", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "physical"
    assert body["id"].startswith("phy-")

    post = mobile_client.get("/api/v1/mobile/devices").json()
    assert len(post) == len(pre) + 1


def test_generate_from_prompt_returns_steps(mobile_client: TestClient):
    r = mobile_client.post(
        "/api/v1/mobile/generate-from-prompt",
        json={"prompt": "Giriş yap butonuna bas, ana sayfanın yüklendiğini doğrula", "platform": "android"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["steps"]) >= 2
    assert body["steps"][0]["action"] == "launch"
    assert body["model"] in ("heuristic-tr", "ai-gateway")


def test_create_session_starts_parallel_runs(mobile_client: TestClient):
    r = mobile_client.post(
        "/api/v1/mobile/sessions",
        json={
            "scenario_name": "smoke",
            "prompt": "Uygulamayı aç ve doğrula",
            "platform": "android",
            "parallel": 2,
            "pass_rate": 100,
            "heal_rate": 0,
        },
    )
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 2
    assert all(s["scenario_name"] == "smoke" for s in sessions)


def test_create_session_conflict_when_exhausted(mobile_client: TestClient):
    # Tüm cihazları meşgul et
    first = mobile_client.post(
        "/api/v1/mobile/sessions",
        json={"scenario_name": "exhaust", "prompt": "test", "platform": "both", "parallel": 10, "pass_rate": 100, "heal_rate": 0},
    )
    assert first.status_code == 200

    second = mobile_client.post(
        "/api/v1/mobile/sessions",
        json={"scenario_name": "should-409", "prompt": "test", "platform": "both", "parallel": 1, "pass_rate": 100, "heal_rate": 0},
    )
    assert second.status_code == 409


def test_list_sessions_returns_array(mobile_client: TestClient):
    r = mobile_client.get("/api/v1/mobile/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_session_404(mobile_client: TestClient):
    r = mobile_client.get("/api/v1/mobile/sessions/nope")
    assert r.status_code == 404


def test_visual_verify_empty_screenshot_fails(mobile_client: TestClient):
    r = mobile_client.post(
        "/api/v1/mobile/visual-verify",
        json={"screenshot_base64": "", "assertion": "home visible"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["passed"] is False


def test_visual_verify_placeholder_passes(mobile_client: TestClient):
    """F2'ye kadar placeholder — non-empty screenshot → passed=True."""
    r = mobile_client.post(
        "/api/v1/mobile/visual-verify",
        json={"screenshot_base64": "aGVsbG8=", "assertion": "ok"},
    )
    body = r.json()
    assert body["passed"] is True
    assert "MVP" in body["reason"]
