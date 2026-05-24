"""Unit tests for mobile.device_farm_adapters.

All external HTTP calls are mocked.
"""

from __future__ import annotations

import json
import os
from io import BytesIO
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import asdict

import pytest


# ── LocalFarmAdapter ──────────────────────────────────────────────────────────


class TestLocalFarmAdapter:
    @pytest.fixture
    def adapter(self):
        from app.domains.mobile.device_farm_adapters import _LocalFarmAdapter
        return _LocalFarmAdapter()

    @pytest.fixture
    def mock_broker(self):
        broker = MagicMock()
        device = MagicMock()
        device.id = "android-pixel_8"
        device.name = "Pixel 8"
        device.platform = "android"
        device.os_version = "14"
        device.status.value = "idle"
        device.appium_port = 4723
        broker.list_devices.return_value = [device]
        broker.get_device.return_value = device
        return broker

    def test_list_devices(self, adapter, mock_broker) -> None:
        with patch(
            "app.domains.mobile.device_farm_adapters.get_broker",
            return_value=mock_broker,
        ):
            devices = adapter.list_devices()

        assert len(devices) == 1
        assert devices[0].name == "Pixel 8"
        assert devices[0].provider == "local"
        assert devices[0].available is True

    def test_list_devices_platform_filter(self, adapter, mock_broker) -> None:
        with patch(
            "app.domains.mobile.device_farm_adapters.get_broker",
            return_value=mock_broker,
        ):
            devices = adapter.list_devices(platform="ios")

        assert len(devices) == 0

    def test_start_session_returns_appium_endpoint(self, adapter, mock_broker) -> None:
        with patch(
            "app.domains.mobile.device_farm_adapters.get_broker",
            return_value=mock_broker,
        ):
            session = adapter.start_session("android-pixel_8", "app.apk", {})

        assert session.status == "running"
        assert "4723" in (session.appium_endpoint or "")
        assert session.provider == "local"

    def test_start_session_unknown_device(self, adapter, mock_broker) -> None:
        mock_broker.get_device.return_value = None
        with patch(
            "app.domains.mobile.device_farm_adapters.get_broker",
            return_value=mock_broker,
        ):
            session = adapter.start_session("nonexistent", "app.apk", {})

        assert session.status == "error"

    def test_health_returns_device_counts(self, adapter, mock_broker) -> None:
        with patch(
            "app.domains.mobile.device_farm_adapters.get_broker",
            return_value=mock_broker,
        ):
            health = adapter.health()

        assert health["provider"] == "local"
        assert health["total_devices"] == 1
        assert health["idle_devices"] == 1


# ── BrowserStackAdapter ───────────────────────────────────────────────────────


class TestBrowserStackAdapter:
    @pytest.fixture
    def adapter(self):
        with patch.dict(
            os.environ,
            {
                "BROWSERSTACK_USERNAME": "testuser",
                "BROWSERSTACK_ACCESS_KEY": "testkey",
                "BROWSERSTACK_APP_URL": "bs://abc123",
            },
        ):
            from app.domains.mobile.device_farm_adapters import BrowserStackAdapter

            return BrowserStackAdapter()

    def test_health_configured(self, adapter) -> None:
        health = adapter.health()
        assert health["configured"] is True
        assert health["app_url"] == "bs://abc123"

    def test_health_not_configured(self) -> None:
        with patch.dict(os.environ, {"BROWSERSTACK_USERNAME": "", "BROWSERSTACK_ACCESS_KEY": ""}):
            from app.domains.mobile.device_farm_adapters import BrowserStackAdapter

            adapter = BrowserStackAdapter()
            health = adapter.health()
            assert health["configured"] is False

    def test_start_session_returns_appium_endpoint(self, adapter) -> None:
        session = adapter.start_session("iPhone 15-17", "bs://app123", {})
        assert session.provider == "browserstack"
        assert session.status == "queued"
        assert "browserstack.com" in (session.appium_endpoint or "")

    def test_list_devices_handles_http_error(self, adapter) -> None:
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            devices = adapter.list_devices()
        assert devices == []


# ── DeviceFarmRouter ──────────────────────────────────────────────────────────


class TestDeviceFarmRouter:
    def test_local_provider_by_default(self) -> None:
        with patch.dict(os.environ, {"DEVICE_FARM_PROVIDER": "local"}):
            from app.domains.mobile import device_farm_adapters as m

            # Reset singleton
            m._farm_router = None
            router = m.get_device_farm()
            assert router._provider == "local"
            m._farm_router = None

    def test_aws_provider_selected(self) -> None:
        with patch.dict(os.environ, {"DEVICE_FARM_PROVIDER": "aws"}):
            from app.domains.mobile import device_farm_adapters as m

            m._farm_router = None
            router = m.get_device_farm()
            assert router._provider == "aws"
            m._farm_router = None

    def test_browserstack_provider_selected(self) -> None:
        with patch.dict(os.environ, {"DEVICE_FARM_PROVIDER": "browserstack"}):
            from app.domains.mobile import device_farm_adapters as m

            m._farm_router = None
            router = m.get_device_farm()
            assert router._provider == "browserstack"
            m._farm_router = None

    def test_singleton_is_reused(self) -> None:
        from app.domains.mobile import device_farm_adapters as m

        m._farm_router = None
        r1 = m.get_device_farm()
        r2 = m.get_device_farm()
        assert r1 is r2
        m._farm_router = None


# ── FarmDevice dataclass ──────────────────────────────────────────────────────


class TestFarmDeviceDataclass:
    def test_serialisable_to_dict(self) -> None:
        from app.domains.mobile.device_farm_adapters import FarmDevice

        d = FarmDevice(
            id="d1",
            name="Pixel 8",
            platform="android",
            os_version="14",
            provider="local",
        )
        data = asdict(d)
        assert data["id"] == "d1"
        assert data["available"] is True  # default

    def test_session_serialisable(self) -> None:
        from app.domains.mobile.device_farm_adapters import FarmSession

        s = FarmSession(
            session_id="s1",
            device_id="d1",
            provider="browserstack",
            status="running",
            appium_endpoint="https://hub-cloud.browserstack.com/wd/hub",
        )
        data = asdict(s)
        assert data["session_id"] == "s1"
        assert data["video_url"] is None
