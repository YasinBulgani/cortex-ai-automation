"""Unit tests for mobile.appium_client and mobile.appium_runner dataclasses.

Tests are fully self-contained: no DB, no HTTP, no Appium server.
Covers:
  - AppiumCapabilities: defaults, to_w3c() key mapping, optional fields
  - AppiumError: exception hierarchy
  - StepRunResult: dataclass defaults
  - AppiumRunResult: dataclass defaults
"""
from __future__ import annotations

import pytest

try:
    from app.domains.mobile.appium_client import (
        AppiumCapabilities,
        AppiumError,
    )
    _CLIENT_OK = True
except ImportError:
    _CLIENT_OK = False

try:
    from app.domains.mobile.appium_runner import (
        StepRunResult,
        AppiumRunResult,
    )
    _RUNNER_OK = True
except ImportError:
    _RUNNER_OK = False


# ---------------------------------------------------------------------------
# AppiumError
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CLIENT_OK, reason="appium_client import failed")
class TestAppiumError:
    def test_is_exception(self):
        exc = AppiumError("connection failed")
        assert isinstance(exc, Exception)

    def test_message_preserved(self):
        exc = AppiumError("session lost")
        assert "session lost" in str(exc)

    def test_can_raise_and_catch(self):
        with pytest.raises(AppiumError):
            raise AppiumError("test error")


# ---------------------------------------------------------------------------
# AppiumCapabilities
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _CLIENT_OK, reason="appium_client import failed")
class TestAppiumCapabilities:
    def _android_caps(self, **kwargs):
        return AppiumCapabilities(
            platform_name="Android",
            automation_name="UiAutomator2",
            device_name="emulator-5554",
            platform_version="13",
            **kwargs,
        )

    def _ios_caps(self, **kwargs):
        return AppiumCapabilities(
            platform_name="iOS",
            automation_name="XCUITest",
            device_name="iPhone 15",
            platform_version="17",
            **kwargs,
        )

    def test_defaults(self):
        caps = self._android_caps()
        assert caps.app is None
        assert caps.udid is None
        assert caps.browser_name is None
        assert caps.no_reset is False
        assert caps.full_reset is False
        assert caps.new_command_timeout == 120
        assert caps.auto_grant_permissions is True

    def test_to_w3c_required_fields(self):
        w3c = self._android_caps().to_w3c()
        assert w3c["platformName"] == "Android"
        assert w3c["appium:automationName"] == "UiAutomator2"
        assert w3c["appium:deviceName"] == "emulator-5554"
        assert w3c["appium:platformVersion"] == "13"
        assert w3c["appium:newCommandTimeout"] == 120
        assert w3c["appium:noReset"] is False
        assert w3c["appium:fullReset"] is False

    def test_to_w3c_with_app(self):
        caps = self._android_caps(app="/apps/banking.apk")
        w3c = caps.to_w3c()
        assert w3c["appium:app"] == "/apps/banking.apk"

    def test_to_w3c_without_app(self):
        caps = self._android_caps()
        w3c = caps.to_w3c()
        assert "appium:app" not in w3c

    def test_to_w3c_with_udid(self):
        caps = self._android_caps(udid="emulator-5554-serial")
        w3c = caps.to_w3c()
        assert w3c["appium:udid"] == "emulator-5554-serial"

    def test_to_w3c_without_udid(self):
        caps = self._android_caps()
        w3c = caps.to_w3c()
        assert "appium:udid" not in w3c

    def test_to_w3c_android_auto_grant_permissions(self):
        caps = self._android_caps(auto_grant_permissions=True)
        w3c = caps.to_w3c()
        assert w3c.get("appium:autoGrantPermissions") is True

    def test_to_w3c_ios_no_auto_grant(self):
        caps = self._ios_caps()
        w3c = caps.to_w3c()
        assert "appium:autoGrantPermissions" not in w3c

    def test_to_w3c_browser_name(self):
        caps = self._android_caps(browser_name="Chrome")
        w3c = caps.to_w3c()
        assert w3c["browserName"] == "Chrome"

    def test_to_w3c_returns_dict(self):
        caps = self._android_caps()
        assert isinstance(caps.to_w3c(), dict)

    def test_custom_timeout(self):
        caps = self._android_caps(new_command_timeout=60)
        w3c = caps.to_w3c()
        assert w3c["appium:newCommandTimeout"] == 60

    def test_full_reset(self):
        caps = self._android_caps(full_reset=True)
        w3c = caps.to_w3c()
        assert w3c["appium:fullReset"] is True


# ---------------------------------------------------------------------------
# StepRunResult
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RUNNER_OK, reason="appium_runner import failed")
class TestStepRunResult:
    def test_creation(self):
        result = StepRunResult(seq=1, status="passed", duration_ms=150)
        assert result.seq == 1
        assert result.status == "passed"
        assert result.duration_ms == 150

    def test_defaults(self):
        result = StepRunResult(seq=0, status="failed", duration_ms=0)
        assert result.artifact_ids == []
        assert result.error_message is None
        assert result.failure_category is None

    def test_with_error(self):
        result = StepRunResult(
            seq=3,
            status="failed",
            duration_ms=500,
            error_message="Element not found",
        )
        assert "not found" in result.error_message

    def test_mutable_artifact_ids(self):
        r1 = StepRunResult(seq=0, status="passed", duration_ms=100)
        r2 = StepRunResult(seq=1, status="passed", duration_ms=200)
        r1.artifact_ids.append("art-1")
        assert r2.artifact_ids == []


# ---------------------------------------------------------------------------
# AppiumRunResult
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RUNNER_OK, reason="appium_runner import failed")
class TestAppiumRunResult:
    def test_creation(self):
        result = AppiumRunResult(status="completed", steps=[])
        assert result.status == "completed"
        assert result.steps == []

    def test_defaults(self):
        result = AppiumRunResult(status="failed", steps=[])
        assert result.artifacts == []
        assert result.failure_category is None
        assert result.failure_message is None

    def test_with_steps(self):
        step = StepRunResult(seq=0, status="passed", duration_ms=100)
        result = AppiumRunResult(status="completed", steps=[step])
        assert len(result.steps) == 1
        assert result.steps[0].status == "passed"
