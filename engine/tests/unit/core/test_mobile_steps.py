"""Engine unit tests — steps/mobile_steps.py

mobile_steps modülü pytest-bdd step fonksiyonlarını tanımlar.
Bu testler step fonksiyonlarını doğrudan çağırarak scenario_context'e
doğru veriyi yazıp yazmadığını doğrular.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# engine kök dizinini PYTHONPATH'e ekle (steps/ ve core/ modülleri)
ENGINE_ROOT = Path(__file__).resolve().parents[3]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

import steps.mobile_steps as ms  # noqa: E402


def _ctx() -> dict:
    return {}


class TestGestureSteps:
    def test_tap_appends_to_context(self):
        ctx = _ctx()
        ms.tap_element(ctx, "login-button")
        assert ("tap", "login-button") in ctx["_mobile_steps"]

    def test_swipe_up_appends(self):
        ctx = _ctx()
        ms.swipe_direction(ctx, "up")
        assert ("swipe", "up") in ctx["_mobile_steps"]

    def test_swipe_down_appends(self):
        ctx = _ctx()
        ms.swipe_direction(ctx, "down")
        assert ("swipe", "down") in ctx["_mobile_steps"]

    def test_long_press_appends(self):
        ctx = _ctx()
        ms.long_press_element(ctx, "card-item")
        assert ("long_press", "card-item") in ctx["_mobile_steps"]


class TestAppSteps:
    def test_launch_app_appends(self):
        ctx = _ctx()
        ms.launch_app(ctx, "com.example.app")
        assert ("launch_app", "com.example.app") in ctx["_mobile_steps"]

    def test_install_app_appends(self):
        ctx = _ctx()
        ms.install_app(ctx, "/tmp/app.apk")
        assert ("install_app", "/tmp/app.apk") in ctx["_mobile_steps"]


class TestNavSteps:
    def test_go_back_appends(self):
        ctx = _ctx()
        ms.go_back(ctx)
        assert ("go_back", None) in ctx["_mobile_steps"]


class TestAssertSteps:
    def test_assert_visible_appends(self):
        ctx = _ctx()
        ms.assert_element_on_screen(ctx, "success-message")
        assert ("assert_visible", "success-message") in ctx["_mobile_steps"]


class TestNetworkAndPermissionSteps:
    def test_set_network_mode(self):
        ctx = _ctx()
        ms.set_network_mode(ctx, "airplane")
        assert ("set_network_mode", "airplane") in ctx["_mobile_steps"]

    def test_grant_permission(self):
        ctx = _ctx()
        ms.grant_permission(ctx, "camera")
        assert ("grant_permission", "camera") in ctx["_mobile_steps"]

    def test_switch_to_webview(self):
        ctx = _ctx()
        ms.switch_to_webview(ctx, "WEBVIEW_chrome")
        assert ("switch_to_webview", "WEBVIEW_chrome") in ctx["_mobile_steps"]


class TestScreenshotStep:
    def test_take_screenshot_appends(self):
        ctx = _ctx()
        ms.take_mobile_screenshot(ctx, "home_screen")
        assert ("take_mobile_screenshot", "home_screen") in ctx["_mobile_steps"]


class TestMultipleStepsAccumulate:
    def test_steps_accumulate_in_order(self):
        ctx = _ctx()
        ms.launch_app(ctx, "com.example")
        ms.tap_element(ctx, "btn-login")
        ms.swipe_direction(ctx, "up")
        ms.assert_element_on_screen(ctx, "dashboard")

        steps = ctx["_mobile_steps"]
        assert steps[0] == ("launch_app", "com.example")
        assert steps[1] == ("tap", "btn-login")
        assert steps[2] == ("swipe", "up")
        assert steps[3] == ("assert_visible", "dashboard")
