"""AppiumClient birim + entegrasyon testleri.

Unit tests: httpx mock ile protokol doğrulaması (Appium çalışmadan).
Integration tests: `APPIUM_URL` env var'ı set olursa gerçek Appium'a bağlanır;
                   yoksa skip edilir.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.domains.mobile.appium_client import (
    AppiumCapabilities,
    AppiumClient,
    AppiumError,
    LOCATOR_STRATEGIES,
)


pytestmark = pytest.mark.P2


# ═══════════════════════════════════════════════════════════════
# UNIT — Capabilities
# ═══════════════════════════════════════════════════════════════
class TestCapabilities:
    def test_android_w3c_shape(self):
        caps = AppiumCapabilities(
            platform_name="Android",
            automation_name="UiAutomator2",
            device_name="emulator-5554",
            platform_version="14",
            app="/tmp/app.apk",
        )
        w3c = caps.to_w3c()
        assert w3c["platformName"] == "Android"
        assert w3c["appium:automationName"] == "UiAutomator2"
        assert w3c["appium:deviceName"] == "emulator-5554"
        assert w3c["appium:app"] == "/tmp/app.apk"
        assert w3c["appium:autoGrantPermissions"] is True

    def test_ios_w3c_no_auto_grant(self):
        caps = AppiumCapabilities(
            platform_name="iOS",
            automation_name="XCUITest",
            device_name="iPhone 15",
            platform_version="17",
        )
        w3c = caps.to_w3c()
        assert w3c["platformName"] == "iOS"
        assert "appium:autoGrantPermissions" not in w3c
        assert "appium:app" not in w3c

    def test_default_reset_flags(self):
        caps = AppiumCapabilities(
            platform_name="Android",
            automation_name="UiAutomator2",
            device_name="d",
            platform_version="14",
        )
        assert caps.to_w3c()["appium:noReset"] is False
        assert caps.to_w3c()["appium:fullReset"] is False


# ═══════════════════════════════════════════════════════════════
# UNIT — Protocol with httpx MockTransport
# ═══════════════════════════════════════════════════════════════
def _make_client_with_mock_handler(handler) -> AppiumClient:
    """handler: Callable[[httpx.Request], httpx.Response]"""
    client = AppiumClient("http://fake:4723")
    client._http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


class TestProtocol:
    def test_create_session_parses_session_id(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/session"
            assert request.method == "POST"
            body = request.content.decode()
            assert "alwaysMatch" in body
            return httpx.Response(200, json={"value": {"sessionId": "abc-123"}})

        c = _make_client_with_mock_handler(handler)
        caps = AppiumCapabilities("Android", "UiAutomator2", "emu", "14")
        sid = c.create_session(caps)
        assert sid == "abc-123"
        assert c.session_id == "abc-123"

    def test_create_session_missing_id_raises(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"value": {}})

        c = _make_client_with_mock_handler(handler)
        with pytest.raises(AppiumError, match="sessionId"):
            c.create_session(AppiumCapabilities("Android", "UiAutomator2", "d", "14"))

    def test_http_error_surfaces_appium_message(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"value": {"message": "WebDriverAgent crashed"}})

        c = _make_client_with_mock_handler(handler)
        with pytest.raises(AppiumError, match="WebDriverAgent"):
            c.create_session(AppiumCapabilities("iOS", "XCUITest", "d", "17"))

    def test_find_element_parses_w3c_element_id(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/element"):
                import json as _json
                parsed = _json.loads(request.content.decode())
                assert parsed["using"] == "accessibility id"
                assert parsed["value"] == "login_btn"
                return httpx.Response(200, json={
                    "value": {"element-6066-11e4-a52e-4f735466cecf": "elem-42"}
                })
            return httpx.Response(404)

        c = _make_client_with_mock_handler(handler)
        c.session_id = "sid"
        eid = c.find_element("accessibilityId", "login_btn")
        assert eid == "elem-42"

    def test_find_element_unknown_strategy(self):
        c = _make_client_with_mock_handler(lambda r: httpx.Response(500))
        c.session_id = "sid"
        with pytest.raises(AppiumError, match="locator stratejisi"):
            c.find_element("telepathy", "x")

    def test_click_sends_empty_body(self):
        received = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received["path"] = request.url.path
            received["method"] = request.method
            return httpx.Response(200, json={"value": None})

        c = _make_client_with_mock_handler(handler)
        c.session_id = "sid"
        c.click("elem-1")
        assert received["path"].endswith("/element/elem-1/click")
        assert received["method"] == "POST"

    def test_send_keys_sends_text(self):
        import json as _json
        received = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received["body"] = _json.loads(request.content.decode())
            return httpx.Response(200, json={"value": None})

        c = _make_client_with_mock_handler(handler)
        c.session_id = "sid"
        c.send_keys("elem-1", "hello@bgts.ai")
        assert received["body"]["text"] == "hello@bgts.ai"

    def test_screenshot_base64(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"value": "aGVsbG8="})

        c = _make_client_with_mock_handler(handler)
        c.session_id = "sid"
        assert c.screenshot_base64() == "aGVsbG8="
        assert c.screenshot_bytes() == b"hello"

    def test_quit_clears_session(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"value": None})

        c = _make_client_with_mock_handler(handler)
        c.session_id = "sid"
        c.quit()
        assert c.session_id is None

    def test_operations_without_session_raise(self):
        c = _make_client_with_mock_handler(lambda r: httpx.Response(500))
        with pytest.raises(AppiumError, match="Aktif session yok"):
            c.page_source()

    def test_context_manager_quits_session(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "DELETE":
                return httpx.Response(200, json={"value": None})
            return httpx.Response(200, json={"value": {"sessionId": "auto"}})

        c = _make_client_with_mock_handler(handler)
        with c as client:
            client.create_session(AppiumCapabilities("Android", "UiAutomator2", "d", "14"))
            assert client.session_id == "auto"
        # __exit__ sonrası quit çağrılmalı
        assert c.session_id is None

    def test_connection_error_wrapped(self):
        def handler(_: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")

        c = _make_client_with_mock_handler(handler)
        with pytest.raises(AppiumError, match="erişilemiyor"):
            c.create_session(AppiumCapabilities("Android", "UiAutomator2", "d", "14"))


# ═══════════════════════════════════════════════════════════════
# INTEGRATION — gerçek Appium (opt-in)
# ═══════════════════════════════════════════════════════════════
_APPIUM_URL = os.environ.get("APPIUM_URL")
requires_appium = pytest.mark.skipif(
    not _APPIUM_URL,
    reason="APPIUM_URL env var set edilmedi (gerçek Appium server gerekli)",
)


@requires_appium
@pytest.mark.integration
class TestRealAppium:
    def test_status_endpoint(self):
        c = AppiumClient(_APPIUM_URL)  # type: ignore[arg-type]
        status = c.status()
        # Appium 2 status: {"ready": True, "message": "..."} veya {"build": {...}}
        assert isinstance(status, dict)

    def test_locator_strategies_expose_expected_map(self):
        # Map bütünlük kontrolü — entegrasyonda da önemli
        assert "accessibility id" in LOCATOR_STRATEGIES.values()
        assert "-ios predicate string" in LOCATOR_STRATEGIES.values()
