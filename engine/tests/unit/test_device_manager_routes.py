"""
tests/unit/test_device_manager_routes.py
==========================================
Device Manager blueprint (/api/device-manager/*) icin birim testler.

ADB/xcrun dis bagimliliklar subprocess stub'lari ile izole edilir.
_DEMO_DEVICES modül-seviyesi verisi test stub'larinda kullanilir.
"""
from __future__ import annotations

import base64
import importlib
import json
import sys
import types
import pytest


# ── Stubs ─────────────────────────────────────────────────────────────────────

def _make_settings_stub(monkeypatch, tmp_path):
    """config.settings modülünü sahte nesneyle stubla."""
    settings_mod = types.ModuleType("config.settings")
    cfg = types.SimpleNamespace(BASE_DIR=str(tmp_path))
    settings_mod.settings = cfg
    monkeypatch.setitem(sys.modules, "config", types.ModuleType("config"))
    monkeypatch.setitem(sys.modules, "config.settings", settings_mod)
    return cfg


def _stub_subprocess_no_adb(monkeypatch, mod):
    """subprocess.run her zaman FileNotFoundError firlatir (ADB/xcrun yok)."""
    import subprocess as sp

    def _fake_run(cmd, *args, **kwargs):
        raise FileNotFoundError("adb not found")

    monkeypatch.setattr(mod.subprocess, "run", _fake_run)


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def device_client(monkeypatch, tmp_path):
    """Flask test istemcisi — subprocess ve settings stub'laniyor."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    _make_settings_stub(monkeypatch, tmp_path)

    # Tüm önbellekleri temizle
    for mod_name in list(sys.modules.keys()):
        if "device_manager" in mod_name or mod_name == "app":
            sys.modules.pop(mod_name, None)

    # core.db stub
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    app_module = importlib.import_module("app")
    app_module.app.config["TESTING"] = True

    # device_manager_routes modülünü al ve subprocess'i stubla
    dm_mod = sys.modules.get("routes.device_manager_routes") or sys.modules.get("engine.routes.device_manager_routes")
    if dm_mod is None:
        for key in sys.modules:
            if "device_manager_routes" in key:
                dm_mod = sys.modules[key]
                break

    if dm_mod:
        import subprocess as real_sp
        monkeypatch.setattr(dm_mod, "subprocess", real_sp)
        # ADB mevcut degil simüle et
        monkeypatch.setattr(dm_mod, "_is_adb_available", lambda: False)
        monkeypatch.setattr(dm_mod, "_is_xcrun_available", lambda: False)
        monkeypatch.setattr(dm_mod, "_discover_android_devices", lambda: [])
        monkeypatch.setattr(dm_mod, "_discover_ios_simulators", lambda: [])
        # Önbelleği temizle
        dm_mod._device_cache["devices"] = []
        dm_mod._device_cache["ts"] = 0

    with app_module.app.test_client() as client:
        yield client, dm_mod


# ── Demo cihaz verileri (modülden bağımsız kopyası) ──────────────────────────

_DEMO_DEVICES = [
    {
        "serial": "emulator-5554", "device_type": "emulator", "platform": "android",
        "name": "Pixel 7 Pro (API 34)", "brand": "Google", "model": "Pixel 7 Pro",
        "android_version": "14", "api_level": "34",
        "health_score": 95, "installed_apps_count": 12,
        "online": True, "state": "device", "demo": True,
    },
    {
        "serial": "emulator-5556", "device_type": "emulator", "platform": "android",
        "name": "Samsung Galaxy S23 (API 33)", "brand": "Samsung", "model": "Galaxy S23",
        "android_version": "13", "api_level": "33",
        "health_score": 81, "installed_apps_count": 8,
        "online": True, "state": "device", "demo": True,
    },
    {
        "serial": "emulator-5558", "device_type": "emulator", "platform": "android",
        "name": "Pixel 6 (API 31)", "brand": "Google", "model": "Pixel 6",
        "android_version": "12", "api_level": "31",
        "health_score": 62, "installed_apps_count": 5,
        "online": False, "state": "offline", "demo": True,
    },
]


# ── /api/device-manager/devices ───────────────────────────────────────────────

def test_devices_returns_200(device_client):
    """ADB mevcut olmadığında demo cihazlar dönmeli ve 200 verilmeli."""
    client, _ = device_client
    response = client.get("/api/device-manager/devices")
    assert response.status_code == 200


def test_devices_returns_json(device_client):
    """Yanıt JSON formatinda olmali."""
    client, _ = device_client
    response = client.get("/api/device-manager/devices")
    data = response.get_json()
    assert data is not None


def test_devices_contains_devices_key(device_client):
    """Yanıt 'devices' anahtarini icermeli."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    assert "devices" in data


def test_devices_contains_summary(device_client):
    """Yanit 'summary' anahtarini icermeli."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    assert "summary" in data


def test_devices_summary_has_total(device_client):
    """summary.total sayisal olmali."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    assert isinstance(data["summary"]["total"], int)


def test_devices_returns_demo_when_adb_unavailable(device_client):
    """ADB yoksa demo cihazlar dönmeli (liste bos olmamali)."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    assert len(data["devices"]) > 0


def test_devices_demo_devices_have_serial(device_client):
    """Her demo cihazin serial numarasi olmali."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    for device in data["devices"]:
        assert "serial" in device
        assert device["serial"]


def test_devices_demo_devices_have_platform(device_client):
    """Her demo cihazin platform bilgisi olmali."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    for device in data["devices"]:
        assert "platform" in device


def test_devices_contains_timestamp(device_client):
    """Yanit timestamp icermeli."""
    client, _ = device_client
    data = client.get("/api/device-manager/devices").get_json()
    assert "timestamp" in data


# ── /api/device-manager/device/<serial>/details ───────────────────────────────

def test_device_details_known_serial(device_client, monkeypatch):
    """Bilinen serial → cihaz bilgisi 200 ile dönmeli."""
    client, dm_mod = device_client
    if dm_mod:
        monkeypatch.setattr(dm_mod, "_discover_all_devices", lambda use_cache=True: list(_DEMO_DEVICES))
    response = client.get("/api/device-manager/device/emulator-5554/details")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("serial") == "emulator-5554"


def test_device_details_unknown_serial(device_client, monkeypatch):
    """Bilinmeyen serial → 404 dönmeli."""
    client, dm_mod = device_client
    if dm_mod:
        monkeypatch.setattr(dm_mod, "_discover_all_devices", lambda use_cache=True: list(_DEMO_DEVICES))
    response = client.get("/api/device-manager/device/unknown-9999/details")
    assert response.status_code == 404


def test_device_details_404_contains_error(device_client, monkeypatch):
    """404 yaniti error mesaji icermeli."""
    client, dm_mod = device_client
    if dm_mod:
        monkeypatch.setattr(dm_mod, "_discover_all_devices", lambda use_cache=True: list(_DEMO_DEVICES))
    data = client.get("/api/device-manager/device/no-such-device/details").get_json()
    assert "error" in data


# ── /api/device-manager/actions/screenshot ────────────────────────────────────

def test_screenshot_missing_serial_returns_400(device_client):
    """Serial verilmezse 400 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/screenshot",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_screenshot_missing_serial_has_error(device_client):
    """400 yaniti error icermeli."""
    client, _ = device_client
    data = client.post(
        "/api/device-manager/actions/screenshot",
        json={},
        content_type="application/json",
    ).get_json()
    assert "error" in data


def test_screenshot_success_returns_base64(device_client, monkeypatch):
    """Screenshot basarili oldugunda base64 veri dönmeli."""
    client, dm_mod = device_client
    fake_b64 = base64.b64encode(b"PNG_FAKE_DATA").decode("utf-8")
    if dm_mod:
        monkeypatch.setattr(dm_mod, "_take_screenshot_b64", lambda serial, platform: fake_b64)
    response = client.post(
        "/api/device-manager/actions/screenshot",
        json={"serial": "emulator-5554", "platform": "android"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("success") is True
    assert "screenshot_b64" in data


def test_screenshot_failure_returns_500(device_client, monkeypatch):
    """Screenshot alinamamissa 500 dönmeli."""
    client, dm_mod = device_client
    if dm_mod:
        monkeypatch.setattr(dm_mod, "_take_screenshot_b64", lambda serial, platform: None)
    response = client.post(
        "/api/device-manager/actions/screenshot",
        json={"serial": "emulator-5554"},
        content_type="application/json",
    )
    assert response.status_code == 500


# ── /api/device-manager/actions/install ──────────────────────────────────────

def test_install_missing_serial_returns_400(device_client):
    """Serial verilmezse install 400 dönmeli."""
    client, _ = device_client
    from io import BytesIO
    data = {"file": (BytesIO(b"APK_CONTENT"), "test.apk")}
    response = client.post(
        "/api/device-manager/actions/install",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_install_missing_file_returns_400(device_client):
    """Dosya verilmezse install 400 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/install",
        data={"serial": "emulator-5554"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_install_success_with_adb(device_client, monkeypatch):
    """ADB install basarili oldugunda success:True dönmeli."""
    client, dm_mod = device_client
    if dm_mod is None:
        pytest.skip("device_manager module not found")
    import subprocess as sp

    class FakeResult:
        returncode = 0
        stdout = "Success\nSuccess"
        stderr = ""

    monkeypatch.setattr(dm_mod.subprocess, "run", lambda *a, **kw: FakeResult())

    from io import BytesIO
    data = {
        "serial": "emulator-5554",
        "platform": "android",
        "file": (BytesIO(b"FAKE_APK"), "app.apk"),
    }
    response = client.post(
        "/api/device-manager/actions/install",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    result = response.get_json()
    assert result.get("success") is True


# ── /api/device-manager/actions/uninstall ────────────────────────────────────

def test_uninstall_missing_params_returns_400(device_client):
    """Serial ve package verilmezse 400 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/uninstall",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_uninstall_success(device_client, monkeypatch):
    """Basarili uninstall success:True dönmeli."""
    client, dm_mod = device_client
    if dm_mod is None:
        pytest.skip("device_manager module not found")

    class FakeResult:
        returncode = 0
        stdout = "Success"
        stderr = ""

    monkeypatch.setattr(dm_mod.subprocess, "run", lambda *a, **kw: FakeResult())

    response = client.post(
        "/api/device-manager/actions/uninstall",
        json={"serial": "emulator-5554", "package": "com.example.app"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "success" in data


# ── /api/device-manager/actions/shell ────────────────────────────────────────

def test_shell_blocklist_command_returns_403(device_client):
    """Bloklanan kabuk komutu 403 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/shell",
        json={"serial": "emulator-5554", "command": "rm -rf /"},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_shell_missing_serial_returns_400(device_client):
    """Serial verilmezse shell 400 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/shell",
        json={"command": "getprop ro.build.version.release"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_shell_missing_command_returns_400(device_client):
    """Command verilmezse shell 400 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/shell",
        json={"serial": "emulator-5554"},
        content_type="application/json",
    )
    assert response.status_code == 400


# ── /api/device-manager/actions/reboot ───────────────────────────────────────

def test_reboot_missing_serial_returns_400(device_client):
    """Serial verilmezse reboot 400 dönmeli."""
    client, _ = device_client
    response = client.post(
        "/api/device-manager/actions/reboot",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


# ── _compute_health_score pure function ───────────────────────────────────────

def test_health_score_full_battery_normal_temp():
    """Dolu batarya ve normal sicaklikta health_score yüksek olmali."""
    for key in list(sys.modules.keys()):
        if "device_manager_routes" in key:
            dm_mod = sys.modules[key]
            score = dm_mod._compute_health_score(
                {"level": 100, "temperature": 25},
                {"total_kb": 4000000, "available_kb": 2000000},
                {"total_kb": 8000000, "available_kb": 4000000},
            )
            assert score >= 80
            return
    pytest.skip("device_manager_routes not loaded")


def test_health_score_critical_battery():
    """Kritik batarya seviyesinde health_score dusuk olmali."""
    for key in list(sys.modules.keys()):
        if "device_manager_routes" in key:
            dm_mod = sys.modules[key]
            score = dm_mod._compute_health_score(
                {"level": 10, "temperature": 50},
                {"total_kb": 4000000, "available_kb": 100000},
                {"total_kb": 8000000, "available_kb": 100000},
            )
            assert score < 50
            return
    pytest.skip("device_manager_routes not loaded")


def test_health_score_max_is_100():
    """health_score hic zaman 100'ü asmamali."""
    for key in list(sys.modules.keys()):
        if "device_manager_routes" in key:
            dm_mod = sys.modules[key]
            score = dm_mod._compute_health_score(
                {"level": 100, "temperature": 20},
                {"total_kb": 8000000, "available_kb": 7000000},
                {"total_kb": 16000000, "available_kb": 15000000},
            )
            assert score <= 100
            return
    pytest.skip("device_manager_routes not loaded")


def test_health_score_min_is_zero():
    """health_score hic zaman 0'in altina dusmemeli."""
    for key in list(sys.modules.keys()):
        if "device_manager_routes" in key:
            dm_mod = sys.modules[key]
            score = dm_mod._compute_health_score(
                {"level": 1, "temperature": 60},
                {"total_kb": 4000000, "available_kb": 10},
                {"total_kb": 8000000, "available_kb": 10},
            )
            assert score >= 0
            return
    pytest.skip("device_manager_routes not loaded")
