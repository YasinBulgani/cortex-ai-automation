"""Engine unit tests — core/device_profiles.py"""
from __future__ import annotations

import pytest

from core.device_profiles import (
    DEVICE_CATALOG,
    DEVICE_MAP,
    DEVICE_MAP_BY_NAME,
    DeviceProfile,
)


class TestDeviceCatalog:
    def test_catalog_not_empty(self):
        assert len(DEVICE_CATALOG) > 0

    def test_device_map_keys_match_slugs(self):
        for slug, profile in DEVICE_MAP.items():
            assert profile.slug == slug

    def test_device_map_by_name_keys_match_names(self):
        for name, profile in DEVICE_MAP_BY_NAME.items():
            assert profile.name == name

    def test_all_profiles_have_required_fields(self):
        for d in DEVICE_CATALOG:
            assert d.slug, f"{d.name}: slug boş"
            assert d.name, f"{d.slug}: name boş"
            assert d.platform in ("ios", "android"), f"{d.slug}: geçersiz platform"
            assert d.width > 0
            assert d.height > 0

    def test_lookup_by_known_slug(self):
        assert "pixel_7" in DEVICE_MAP
        assert DEVICE_MAP["pixel_7"].platform == "android"

    def test_lookup_ios_device(self):
        ios_devices = [d for d in DEVICE_CATALOG if d.platform == "ios"]
        assert len(ios_devices) > 0

    def test_lookup_android_device(self):
        android_devices = [d for d in DEVICE_CATALOG if d.platform == "android"]
        assert len(android_devices) > 0


class TestToDict:
    def test_ios_device_keys(self):
        ios = next(d for d in DEVICE_CATALOG if d.platform == "ios")
        result = ios.to_dict()
        assert result["platform"] == "ios"
        assert result["icon"] == "🍎"
        assert result["os"].startswith("iOS")
        assert result["slug"] == ios.slug
        assert result["name"] == ios.name
        assert result["viewport_width"] == ios.width
        assert result["viewport_height"] == ios.height
        assert isinstance(result["has_touch"], bool)
        assert isinstance(result["device_scale_factor"], float)

    def test_android_device_keys(self):
        android = next(d for d in DEVICE_CATALOG if d.platform == "android")
        result = android.to_dict()
        assert result["platform"] == "android"
        assert result["icon"] == "🤖"
        assert result["os"].startswith("Android")

    def test_os_string_includes_version_when_set(self):
        d = DeviceProfile(
            slug="test-ios",
            name="Test iOS",
            platform="ios",
            farm_os_version="17",
        )
        result = d.to_dict()
        assert result["os"] == "iOS 17"

    def test_os_string_no_version(self):
        d = DeviceProfile(
            slug="test-android",
            name="Test Android",
            platform="android",
            farm_os_version="",
        )
        result = d.to_dict()
        assert result["os"] == "Android"

    def test_playwright_key_included_when_non_empty(self):
        d = DeviceProfile(
            slug="test",
            name="Test",
            platform="ios",
            playwright_key="iPhone 14",
        )
        result = d.to_dict()
        assert result.get("playwright_key") == "iPhone 14"

    def test_playwright_key_absent_when_empty(self):
        d = DeviceProfile(slug="test", name="Test", platform="ios", playwright_key="")
        result = d.to_dict()
        assert "playwright_key" not in result


class TestToPlaywrightContextOptions:
    def test_returns_viewport(self):
        d = DeviceProfile(slug="s", name="n", platform="ios", width=390, height=844)
        opts = d.to_playwright_context_options()
        assert opts["viewport"] == {"width": 390, "height": 844}

    def test_includes_is_mobile_and_touch(self):
        d = DeviceProfile(slug="s", name="n", platform="ios", is_mobile=True, has_touch=True)
        opts = d.to_playwright_context_options()
        assert opts["is_mobile"] is True
        assert opts["has_touch"] is True

    def test_user_agent_included_when_set(self):
        d = DeviceProfile(slug="s", name="n", platform="ios", user_agent="Mozilla/5.0 TestUA")
        opts = d.to_playwright_context_options()
        assert opts.get("user_agent") == "Mozilla/5.0 TestUA"

    def test_user_agent_absent_when_empty(self):
        d = DeviceProfile(slug="s", name="n", platform="ios", user_agent="")
        opts = d.to_playwright_context_options()
        assert "user_agent" not in opts

    def test_device_scale_factor(self):
        d = DeviceProfile(slug="s", name="n", platform="ios", device_scale_factor=3.0)
        opts = d.to_playwright_context_options()
        assert opts["device_scale_factor"] == 3.0
