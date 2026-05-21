"""
BrowserEngine - Playwright tarayıcı yönetimi
Playwright browser/context/page yaşam döngüsünü yönetir.
Mobil cihaz emülasyonu ve gerçek cihaz farm (BrowserStack / Sauce Labs) desteği içerir.

Öncelik sırası:
  1. BROWSERSTACK_USERNAME + BROWSERSTACK_ACCESS_KEY → BrowserStack Automate (CDP)
  2. SAUCE_USERNAME + SAUCE_ACCESS_KEY              → Sauce Labs Playwright (CDP)
  3. Yerel Playwright emülasyonu (varsayılan)
"""
import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from config.settings import settings

if TYPE_CHECKING:
    from core.device_profiles import DeviceProfile

logger = logging.getLogger(__name__)


class BrowserEngine:
    """Playwright tarayıcı motoru. Context manager olarak kullanılabilir."""

    def __init__(
        self,
        browser_type: str = None,
        headless: bool = None,
        timeout: int = None,
        device_profile: "DeviceProfile | None" = None,
        # Farm override: None → settings üzerinden otomatik seçim
        farm: str | None = None,
    ):
        self.browser_type = browser_type or settings.BROWSER
        self.headless = headless if headless is not None else settings.HEADLESS
        self.timeout = timeout or settings.DEFAULT_TIMEOUT
        self.device_profile = device_profile

        # farm: "browserstack" | "sauce" | "local" | None (otomatik)
        self._farm_override = farm

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    # ── Context Manager ────────────────────────────────────────────────────────
    def __enter__(self) -> "BrowserEngine":
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    # ── Farm Yardımcıları ──────────────────────────────────────────────────────
    @property
    def active_farm(self) -> str:
        """Kullanılacak farm'ı belirler: 'browserstack' | 'sauce' | 'local'."""
        if self._farm_override:
            return self._farm_override
        if settings.BROWSERSTACK_USERNAME and settings.BROWSERSTACK_ACCESS_KEY:
            return "browserstack"
        if settings.SAUCE_USERNAME and settings.SAUCE_ACCESS_KEY:
            return "sauce"
        return "local"

    def _build_bs_ws_url(self, test_name: str = "") -> str:
        """BrowserStack Playwright CDP WebSocket URL'sini oluşturur."""
        caps: dict = {
            "browser": "chrome",
            "browser_version": "latest",
            "os": "Windows",
            "os_version": "11",
            "build": settings.BROWSERSTACK_BUILD,
            "project": settings.BROWSERSTACK_PROJECT,
            "name": test_name or (self.device_profile.name if self.device_profile else "Nexus QA Test"),
            "browserstack.username": settings.BROWSERSTACK_USERNAME,
            "browserstack.accessKey": settings.BROWSERSTACK_ACCESS_KEY,
            "browserstack.networkLogs": True,
            "browserstack.consoleLogs": "info",
            "browserstack.idleTimeout": 120,
        }
        encoded = base64.b64encode(json.dumps(caps).encode()).decode()
        return f"wss://cdp.browserstack.com/playwright?caps={encoded}"

    def _build_sauce_ws_url(self, test_name: str = "") -> str:
        """Sauce Labs Playwright CDP WebSocket URL'sini oluşturur."""
        region = settings.SAUCE_REGION  # "eu-central" | "us-west"
        caps: dict = {
            "browserName": "chrome",
            "browserVersion": "latest",
            "platformName": "Windows 11",
            "sauce:options": {
                "username": settings.SAUCE_USERNAME,
                "accessKey": settings.SAUCE_ACCESS_KEY,
                "name": test_name or (self.device_profile.name if self.device_profile else "Nexus QA Test"),
                "build": settings.BROWSERSTACK_BUILD,
                "idleTimeout": 120,
            },
        }
        encoded = base64.b64encode(json.dumps(caps).encode()).decode()
        return f"wss://ondemand.{region}.saucelabs.com/playwright?caps={encoded}"

    # ── Başlat / Durdur ────────────────────────────────────────────────────────
    def start(self):
        """Tarayıcıyı başlatır. Farm durumuna göre CDP ya da yerel başlatma yapar."""
        self._playwright = sync_playwright().start()
        farm = self.active_farm

        if farm == "browserstack":
            ws_url = self._build_bs_ws_url()
            logger.info("BrowserStack Automate bağlantısı kuruluyor: build=%s", settings.BROWSERSTACK_BUILD)
            self._browser = self._playwright.chromium.connect(ws_url)

        elif farm == "sauce":
            ws_url = self._build_sauce_ws_url()
            logger.info("Sauce Labs bağlantısı kuruluyor: region=%s", settings.SAUCE_REGION)
            self._browser = self._playwright.chromium.connect(ws_url)

        else:
            # Yerel Playwright başlatma
            launcher = getattr(self._playwright, self.browser_type)
            self._browser = launcher.launch(headless=self.headless)

        # ── Context (farm farkı yok: CDP remote browser da context alır) ──────
        if self.device_profile is not None:
            # Mobil cihaz emülasyonu: playwright.devices key varsa kullan (sadece yerel modda)
            if (
                farm == "local"
                and self.device_profile.playwright_key
                and self.device_profile.playwright_key in self._playwright.devices
            ):
                device_opts = dict(self._playwright.devices[self.device_profile.playwright_key])
            else:
                device_opts = self.device_profile.to_playwright_context_options()
            device_opts["locale"] = "tr-TR"
            self._context = self._browser.new_context(**device_opts)
        else:
            # Masaüstü varsayılan
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="tr-TR",
            )

        self._context.set_default_timeout(self.timeout)
        self._page = self._context.new_page()
        return self

    def stop(self):
        """Tüm kaynakları temizler."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass

    # ── Sayfa Erişimi ──────────────────────────────────────────────────────────
    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("BrowserEngine henüz başlatılmadı. start() çağrısı yapın.")
        return self._page

    # ── Yardımcı Metodlar ──────────────────────────────────────────────────────
    def new_page(self) -> Page:
        """Yeni bir sekme açar ve aktif sayfa yapar."""
        self._page = self._context.new_page()
        return self._page

    def screenshot(self, name: str = None, full_page: bool = True) -> str:
        """Ekran görüntüsü alır ve kaydeder. Dosya yolunu döndürür."""
        settings.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_slug = f"_{self.device_profile.slug}" if self.device_profile else ""
        farm_slug = f"_{self.active_farm}" if self.active_farm != "local" else ""
        filename = f"{name or 'screenshot'}{device_slug}{farm_slug}_{ts}.png"
        path = settings.SCREENSHOTS_DIR / filename
        self._page.screenshot(path=str(path), full_page=full_page)
        return str(path)

    def navigate(self, url: str):
        """URL'ye gider."""
        self._page.goto(url, wait_until="domcontentloaded", timeout=settings.NAVIGATION_TIMEOUT)

    def wait_for_selector(self, selector: str, timeout: int = None):
        """Belirtilen selector görünene kadar bekler."""
        self._page.wait_for_selector(selector, timeout=timeout or self.timeout)
