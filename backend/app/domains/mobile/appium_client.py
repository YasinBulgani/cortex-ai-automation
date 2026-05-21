"""Appium HTTP istemcisi — WebDriver protokolü (W3C + Appium uzantıları).

Gerçek Appium 2.x server ile konuşur. Temel metodlar:
  - create_session    POST /session          → session_id
  - find_element      POST /session/{sid}/element
  - click             POST /session/{sid}/element/{eid}/click
  - send_keys         POST /session/{sid}/element/{eid}/value
  - get_page_source   GET  /session/{sid}/source
  - screenshot        GET  /session/{sid}/screenshot  (base64 PNG)
  - quit              DELETE /session/{sid}

Not: Gerçek Appium olmadan unit test edilemez; entegrasyon testleri
`tests/mobile/test_appium_integration.py` içinde `requires_appium` marker'ı ile
atlanır (env: APPIUM_URL=http://127.0.0.1:4723 set edildiğinde çalışır).
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

_logger = logging.getLogger(__name__)


LOCATOR_STRATEGIES = {
    "accessibilityId": "accessibility id",
    "id": "id",
    "xpath": "xpath",
    "predicate": "-ios predicate string",
    "className": "class name",
    "androidUiAutomator": "-android uiautomator",
    # Ek stratejiler
    "cssSelector": "css selector",        # WebView bağlamı
    "iosClassChain": "-ios class chain",  # iOS XPath alternatifi
    "image": "image",                     # Appium image-based locator
    "name": "name",                       # Geriye dönük uyumluluk
}


class AppiumError(Exception):
    """Appium-layer error — HTTP, protocol, or session kaynaklı."""


@dataclass
class AppiumCapabilities:
    platform_name: str                    # "Android" | "iOS"
    automation_name: str                  # "UiAutomator2" | "XCUITest"
    device_name: str
    platform_version: str
    app: Optional[str] = None             # APK/IPA path veya bundleId
    udid: Optional[str] = None
    browser_name: Optional[str] = None
    no_reset: bool = False
    full_reset: bool = False
    new_command_timeout: int = 120
    auto_grant_permissions: bool = True   # Android

    def to_w3c(self) -> dict[str, Any]:
        """W3C capabilities formatı — alwaysMatch içinde."""
        caps: dict[str, Any] = {
            "platformName": self.platform_name,
            "appium:automationName": self.automation_name,
            "appium:deviceName": self.device_name,
            "appium:platformVersion": self.platform_version,
            "appium:newCommandTimeout": self.new_command_timeout,
            "appium:noReset": self.no_reset,
            "appium:fullReset": self.full_reset,
        }
        if self.app:
            caps["appium:app"] = self.app
        if self.udid:
            caps["appium:udid"] = self.udid
        if self.browser_name:
            caps["browserName"] = self.browser_name
        if self.platform_name.lower() == "android" and self.auto_grant_permissions:
            caps["appium:autoGrantPermissions"] = True
        return caps


class AppiumClient:
    """Senkron Appium WebDriver istemcisi.

    Örnek:
        caps = AppiumCapabilities(
            platform_name="Android",
            automation_name="UiAutomator2",
            device_name="emulator-5554",
            platform_version="14",
            app="/path/orangehrm.apk",
        )
        with AppiumClient("http://127.0.0.1:4723") as client:
            client.create_session(caps)
            element = client.find_element("accessibilityId", "login_button")
            client.click(element)
            client.send_keys(client.find_element("accessibilityId", "email"), "a@b.c")
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self._http = httpx.Client(timeout=timeout)

    # ── Context manager ───────────────────────────────────────
    def __enter__(self) -> "AppiumClient":
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self.session_id:
                self.quit()
        finally:
            self._http.close()

    # ── Helpers ───────────────────────────────────────────────
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _session_url(self, suffix: str = "") -> str:
        if not self.session_id:
            raise AppiumError("Aktif session yok — önce create_session() çağırın")
        return self._url(f"/session/{self.session_id}{suffix}")

    def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        try:
            r = self._http.request(method, url, **kwargs)
        except httpx.RequestError as e:
            raise AppiumError(f"Appium erişilemiyor: {e}") from e
        try:
            payload = r.json() if r.content else {}
        except ValueError:
            raise AppiumError(f"Appium JSON olmayan yanıt: HTTP {r.status_code}: {r.text[:200]}")

        if r.status_code >= 400:
            err_val = (payload.get("value") or {}) if isinstance(payload, dict) else {}
            msg = err_val.get("message", payload) if isinstance(err_val, dict) else r.text
            raise AppiumError(f"Appium HTTP {r.status_code}: {msg}")

        # WebDriver spec: gerçek veri `value` anahtarında gelir
        if isinstance(payload, dict) and "value" in payload:
            return payload
        return {"value": payload}

    # ── Session lifecycle ─────────────────────────────────────
    def create_session(self, caps: AppiumCapabilities) -> str:
        body = {
            "capabilities": {
                "alwaysMatch": caps.to_w3c(),
                "firstMatch": [{}],
            }
        }
        res = self._request("POST", self._url("/session"), json=body)
        value = res.get("value") or {}
        sid = value.get("sessionId") or value.get("session_id")
        if not sid:
            raise AppiumError(f"sessionId dönmedi: {res}")
        self.session_id = sid
        _logger.info("Appium session açıldı: %s (%s)", sid, caps.device_name)
        return sid

    def quit(self) -> None:
        if not self.session_id:
            return
        sid = self.session_id
        try:
            self._request("DELETE", self._session_url())
        finally:
            self.session_id = None
        _logger.info("Appium session kapandı: %s", sid)

    def status(self) -> dict:
        return self._request("GET", self._url("/status")).get("value", {})

    # ── Element ops ───────────────────────────────────────────
    def find_element(self, strategy: str, selector: str) -> str:
        """Element bul, Appium element ID'sini döner.

        strategy: accessibilityId | id | xpath | predicate | className | androidUiAutomator
        """
        using = LOCATOR_STRATEGIES.get(strategy)
        if not using:
            raise AppiumError(f"Bilinmeyen locator stratejisi: {strategy}")
        body = {"using": using, "value": selector}
        res = self._request("POST", self._session_url("/element"), json=body)
        elem = res.get("value") or {}
        # W3C: {"element-6066-11e4-a52e-4f735466cecf": "..."}
        for k, v in elem.items():
            if k.startswith("element-") or k == "ELEMENT":
                return v
        raise AppiumError(f"Element ID parse edilemedi: {elem}")

    def click(self, element_id: str) -> None:
        self._request("POST", self._session_url(f"/element/{element_id}/click"), json={})

    def send_keys(self, element_id: str, text: str) -> None:
        self._request(
            "POST",
            self._session_url(f"/element/{element_id}/value"),
            json={"text": text},
        )

    def clear(self, element_id: str) -> None:
        self._request("POST", self._session_url(f"/element/{element_id}/clear"), json={})

    def is_displayed(self, element_id: str) -> bool:
        res = self._request("GET", self._session_url(f"/element/{element_id}/displayed"))
        return bool(res.get("value"))

    def get_text(self, element_id: str) -> str:
        res = self._request("GET", self._session_url(f"/element/{element_id}/text"))
        return str(res.get("value") or "")

    # ── Page / screenshot ─────────────────────────────────────
    def page_source(self) -> str:
        res = self._request("GET", self._session_url("/source"))
        return str(res.get("value") or "")

    def open_url(self, url: str) -> None:
        """WebDriver URL navigation — mobil web smoke akışları için."""
        self._request("POST", self._session_url("/url"), json={"url": url})

    def screenshot_bytes(self) -> bytes:
        """PNG screenshot — base64'ten decode edilmiş ham bytes."""
        res = self._request("GET", self._session_url("/screenshot"))
        b64 = res.get("value")
        if not b64:
            return b""
        return base64.b64decode(b64)

    def screenshot_base64(self) -> str:
        res = self._request("GET", self._session_url("/screenshot"))
        return str(res.get("value") or "")

    # ── High level ────────────────────────────────────────────
    def back(self) -> None:
        self._request("POST", self._session_url("/back"), json={})

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> None:
        """Appium dokunma API'ı (W3C actions)."""
        body = {
            "actions": [{
                "type": "pointer",
                "id": "finger1",
                "parameters": {"pointerType": "touch"},
                "actions": [
                    {"type": "pointerMove", "duration": 0, "x": start_x, "y": start_y},
                    {"type": "pointerDown", "button": 0},
                    {"type": "pointerMove", "duration": duration_ms, "x": end_x, "y": end_y},
                    {"type": "pointerUp", "button": 0},
                ],
            }],
        }
        self._request("POST", self._session_url("/actions"), json=body)


def from_device_url(appium_url: str) -> AppiumClient:
    """Helper — BGTS Device objesindeki appium_url'den client yarat."""
    return AppiumClient(appium_url)
