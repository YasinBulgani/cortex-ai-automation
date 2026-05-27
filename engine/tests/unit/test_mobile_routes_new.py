"""
tests/unit/test_mobile_routes.py
=================================
mobile_bp (/api/mobile/...) blueprint için birim testler.

Dış bağımlılıklar (DEVICE_CATALOG, DEVICE_MAP, settings, subprocess)
monkeypatching ile izole edilir.
"""
from __future__ import annotations

import importlib
import io
import sys
import pytest


# ── Sahte cihaz verileri ───────────────────────────────────────────────────


class _FakeDevice:
    def __init__(self, slug, name, platform, form_factor):
        self.slug = slug
        self.name = name
        self.platform = platform
        self.form_factor = form_factor

    def to_dict(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "platform": self.platform,
            "form_factor": self.form_factor,
        }


_FAKE_CATALOG = [
    _FakeDevice("pixel_7", "Pixel 7", "android", "phone"),
    _FakeDevice("iphone_14", "iPhone 14", "ios", "phone"),
    _FakeDevice("galaxy_tab", "Galaxy Tab S8", "android", "tablet"),
]

_FAKE_MAP = {d.slug: d for d in _FAKE_CATALOG}


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture
def mobile_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — harici bağımlılıklar stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    # Cihaz katalogu stub'ları
    monkeypatch.setattr(
        "core.device_profiles.DEVICE_CATALOG", _FAKE_CATALOG, raising=False
    )
    monkeypatch.setattr(
        "core.device_profiles.DEVICE_MAP", _FAKE_MAP, raising=False
    )

    # Settings stub'ları — farm kimlik bilgileri boş (local farm)
    monkeypatch.setattr("config.settings.settings.BROWSERSTACK_USERNAME", "", raising=False)
    monkeypatch.setattr("config.settings.settings.BROWSERSTACK_ACCESS_KEY", "", raising=False)
    monkeypatch.setattr("config.settings.settings.BROWSERSTACK_BUILD", "", raising=False)
    monkeypatch.setattr("config.settings.settings.BROWSERSTACK_PROJECT", "", raising=False)
    monkeypatch.setattr("config.settings.settings.SAUCE_USERNAME", "", raising=False)
    monkeypatch.setattr("config.settings.settings.SAUCE_ACCESS_KEY", "", raising=False)
    monkeypatch.setattr("config.settings.settings.SAUCE_REGION", "us-west-1", raising=False)
    monkeypatch.setattr("config.settings.settings.MOBILE_ARTIFACTS_DIR", tmp_path, raising=False)

    # DB stub'ları (app başlatma için gerekli)
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


# ── /api/mobile/devices ───────────────────────────────────────────────────────


def test_devices_returns_200(mobile_client):
    """GET /api/mobile/devices 200 döndürmeli."""
    resp = mobile_client.get("/api/mobile/devices")
    assert resp.status_code == 200


def test_devices_returns_list(mobile_client):
    """Yanıt JSON liste olmalı."""
    resp = mobile_client.get("/api/mobile/devices")
    data = resp.get_json()
    assert isinstance(data, list)


def test_devices_catalog_count(mobile_client):
    """Dönen liste stub kataloğundaki cihaz sayısıyla eşleşmeli."""
    resp = mobile_client.get("/api/mobile/devices")
    data = resp.get_json()
    assert len(data) == len(_FAKE_CATALOG)


def test_devices_has_name_field(mobile_client):
    """Her cihaz 'name' alanı içermeli."""
    resp = mobile_client.get("/api/mobile/devices")
    for device in resp.get_json():
        assert "name" in device, f"'name' alanı eksik: {device}"


def test_devices_has_platform_field(mobile_client):
    """Her cihaz 'platform' alanı içermeli."""
    resp = mobile_client.get("/api/mobile/devices")
    for device in resp.get_json():
        assert "platform" in device, f"'platform' alanı eksik: {device}"


def test_devices_has_form_factor_field(mobile_client):
    """Her cihaz 'form_factor' alanı içermeli."""
    resp = mobile_client.get("/api/mobile/devices")
    for device in resp.get_json():
        assert "form_factor" in device, f"'form_factor' alanı eksik: {device}"


# ── /api/mobile/farm-status ───────────────────────────────────────────────────


def test_farm_status_returns_200(mobile_client):
    """GET /api/mobile/farm-status 200 döndürmeli."""
    resp = mobile_client.get("/api/mobile/farm-status")
    assert resp.status_code == 200


def test_farm_status_local_when_no_creds(mobile_client):
    """BrowserStack/Sauce kimlik bilgisi yokken active_farm='local' olmalı."""
    resp = mobile_client.get("/api/mobile/farm-status")
    data = resp.get_json()
    assert data["active_farm"] == "local"
    assert data["local_emulation"] is True


def test_farm_status_browserstack_when_creds_set(mobile_client, monkeypatch):
    """BrowserStack kimlik bilgileri ayarlandığında active_farm='browserstack' olmalı."""
    monkeypatch.setattr("config.settings.settings.BROWSERSTACK_USERNAME", "bs_user", raising=False)
    monkeypatch.setattr("config.settings.settings.BROWSERSTACK_ACCESS_KEY", "bs_key", raising=False)
    resp = mobile_client.get("/api/mobile/farm-status")
    data = resp.get_json()
    assert data["active_farm"] == "browserstack"
    assert data["browserstack"]["configured"] is True


def test_farm_status_sauce_when_creds_set(mobile_client, monkeypatch):
    """Sauce kimlik bilgileri ayarlandığında active_farm='sauce' olmalı."""
    monkeypatch.setattr("config.settings.settings.SAUCE_USERNAME", "sauce_user", raising=False)
    monkeypatch.setattr("config.settings.settings.SAUCE_ACCESS_KEY", "sauce_key", raising=False)
    resp = mobile_client.get("/api/mobile/farm-status")
    data = resp.get_json()
    assert data["active_farm"] == "sauce"
    assert data["sauce"]["configured"] is True


def test_farm_status_has_device_count(mobile_client):
    """Yanıt device_count alanı içermeli."""
    resp = mobile_client.get("/api/mobile/farm-status")
    data = resp.get_json()
    assert "device_count" in data
    assert data["device_count"] == len(_FAKE_CATALOG)


def test_farm_status_browserstack_not_configured_by_default(mobile_client):
    """Kimlik bilgisi olmadan browserstack.configured=False olmalı."""
    resp = mobile_client.get("/api/mobile/farm-status")
    data = resp.get_json()
    assert data["browserstack"]["configured"] is False


# ── /api/mobile/run ───────────────────────────────────────────────────────────


def test_run_missing_device_returns_400(mobile_client):
    """device_slug belirtilmezse POST /api/mobile/run 400 döndürmeli."""
    resp = mobile_client.post(
        "/api/mobile/run",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_run_invalid_device_returns_400(mobile_client):
    """Bilinmeyen device_slug ile POST /api/mobile/run 400 döndürmeli."""
    resp = mobile_client.post(
        "/api/mobile/run",
        json={"device_slug": "nonexistent_device"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_run_valid_device_returns_run_id(mobile_client, monkeypatch):
    """Geçerli device_slug ile POST /api/mobile/run run_id döndürmeli."""
    # subprocess başlatılmasın
    import threading as _threading

    monkeypatch.setattr(
        _threading.Thread,
        "start",
        lambda self: None,
    )

    resp = mobile_client.post(
        "/api/mobile/run",
        json={"device_slug": "pixel_7", "browser": "chromium"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "run_id" in data


def test_run_valid_device_echoes_device_slug(mobile_client, monkeypatch):
    """Yanıt device_slug alanını içermeli."""
    import threading as _threading

    monkeypatch.setattr(_threading.Thread, "start", lambda self: None)

    resp = mobile_client.post(
        "/api/mobile/run",
        json={"device_slug": "iphone_14"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("device_slug") == "iphone_14"


# ── /api/mobile/run/<run_id>/stream (SSE) ─────────────────────────────────────


def test_stream_unknown_run_id_returns_error_event(mobile_client):
    """Bilinmeyen run_id için SSE stream hata mesajı içermeli."""
    resp = mobile_client.get("/api/mobile/run/unknown-run-xyz/stream")
    # SSE başlığı: text/event-stream
    assert "event-stream" in resp.content_type or resp.status_code in (200, 404)
    content = resp.data.decode("utf-8")
    # Hata mesajı ya data: içinde ya da response içinde olmalı
    assert "error" in content.lower() or "bulunamadı" in content


# ── /api/mobile/upload-app ────────────────────────────────────────────────────


def test_upload_app_no_file_returns_400(mobile_client):
    """Dosya olmadan POST /api/mobile/upload-app 400 döndürmeli."""
    resp = mobile_client.post("/api/mobile/upload-app", data={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_upload_app_with_valid_apk(mobile_client, tmp_path):
    """Geçerli APK dosyası ile POST /api/mobile/upload-app upload_id döndürmeli."""
    apk_content = b"PK\x03\x04fake-apk-content"
    resp = mobile_client.post(
        "/api/mobile/upload-app",
        data={"file": (io.BytesIO(apk_content), "test_app.apk")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "upload_id" in data


def test_upload_app_with_invalid_extension_returns_400(mobile_client):
    """Desteklenmeyen uzantıyla /api/mobile/upload-app 400 döndürmeli."""
    resp = mobile_client.post(
        "/api/mobile/upload-app",
        data={"file": (io.BytesIO(b"fake-content"), "malware.exe")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_upload_app_apk_platform_hint_is_android(mobile_client):
    """APK yüklemesinde platform_hint 'android' olmalı."""
    resp = mobile_client.post(
        "/api/mobile/upload-app",
        data={"file": (io.BytesIO(b"fake-apk"), "myapp.apk")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("platform_hint") == "android"
