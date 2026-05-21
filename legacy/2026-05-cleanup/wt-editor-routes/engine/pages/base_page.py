"""
BasePage — Page Object Model temel sinifi
Tum sayfa nesneleri bu siniftan turetilir.
LocatorManager entegrasyonu ile JSON locator destegi saglar.
"""
import logging

from playwright.sync_api import Page, TimeoutError, expect
from config.settings import settings
from core.locator_manager import LocatorManager

logger = logging.getLogger(__name__)


class BasePage:
    """Tum sayfa nesneleri icin temel sinif."""

    _PAGE: str = ""

    def __init__(self, page: Page):
        self.page = page

    def _resolve(self, key_or_selector: str) -> str:
        """LocatorManager uzerinden locator cozumler, fallback olarak raw selector doner."""
        return LocatorManager.resolve(key_or_selector)

    # ── Navigasyon ─────────────────────────────────────────────────────────────
    def navigate(self, url: str):
        """Belirtilen URL'ye git."""
        self.page.goto(url, wait_until="domcontentloaded", timeout=settings.NAVIGATION_TIMEOUT)
        return self

    def reload(self):
        self.page.reload(wait_until="domcontentloaded")
        return self

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    # ── Etkilesim ─────────────────────────────────────────────────────────────
    def click(self, selector: str):
        resolved = self._resolve(selector)
        try:
            self.page.locator(resolved).click()
        except TimeoutError:
            healed = self._try_self_heal(selector)
            if healed:
                self.page.locator(healed).click()
            else:
                raise
        return self

    def click_text(self, text: str):
        self.page.get_by_text(text, exact=False).first.click()
        return self

    def fill(self, selector: str, value: str):
        self.page.locator(self._resolve(selector)).fill(value)
        return self

    def press(self, selector: str, key: str):
        self.page.locator(self._resolve(selector)).press(key)
        return self

    def select_option(self, selector: str, value: str):
        self.page.locator(self._resolve(selector)).select_option(value)
        return self

    def hover(self, selector: str):
        self.page.locator(self._resolve(selector)).hover()
        return self

    # ── Self-heal yardimcisi ─────────────────────────────────────────────────
    def _try_self_heal(self, selector: str) -> str | None:
        """Locator basarisiz oldugunda self-heal dener. Basarisizsa None doner."""
        try:
            canonical = LocatorManager.get_canonical()
            if self._PAGE:
                return canonical.self_heal(self._PAGE, selector, self.page)
        except Exception as exc:
            logger.debug("Self-heal basarisiz: %s", exc)
        return None

    # ── Bekle ─────────────────────────────────────────────────────────────────
    def wait_for(self, selector: str, state: str | None = None, timeout: int | None = None):
        if state is None:
            try:
                canonical = LocatorManager.get_canonical()
                if self._PAGE:
                    state = canonical.get_wait_strategy(self._PAGE, selector)
            except Exception:
                pass
            if state is None:
                state = "visible"
        self.page.wait_for_selector(self._resolve(selector), state=state, timeout=timeout or settings.DEFAULT_TIMEOUT)
        return self

    def wait_ms(self, ms: int):
        self.page.wait_for_timeout(ms)
        return self

    def wait_for_url(self, url_pattern: str):
        self.page.wait_for_url(url_pattern, timeout=settings.NAVIGATION_TIMEOUT)
        return self

    # ── Bilgi Alma ────────────────────────────────────────────────────────────
    def get_text(self, selector: str) -> str:
        return self.page.locator(self._resolve(selector)).inner_text()

    def get_value(self, selector: str) -> str:
        return self.page.locator(self._resolve(selector)).input_value()

    def is_visible(self, selector: str) -> bool:
        return self.page.locator(self._resolve(selector)).is_visible()

    # ── Assertion ─────────────────────────────────────────────────────────────
    def assert_text(self, selector: str, expected: str):
        actual = self.get_text(selector)
        assert actual == expected, f"Beklenen: '{expected}' | Bulunan: '{actual}'"
        return self

    def assert_text_contains(self, selector: str, expected: str):
        """Elementin metninin beklenen değeri içerdiğini doğrular."""
        actual = self.get_text(selector)
        assert expected in actual, f"'{expected}' metni '{actual}' içinde bulunamadı"
        return self

    def assert_visible(self, selector: str):
        assert self.is_visible(selector), f"Element gorunur degil: {selector}"
        return self

    def assert_url_contains(self, text: str):
        assert text in self.page.url, f"URL '{text}' içermiyor. URL: {self.page.url}"
        return self

    def assert_title_contains(self, text: str):
        assert text in self.title, f"Başlık '{text}' içermiyor. Başlık: {self.title}"
        return self

    # ── Screenshot ────────────────────────────────────────────────────────────
    def screenshot(self, name: str = "screenshot") -> str:
        from datetime import datetime
        settings.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.SCREENSHOTS_DIR / f"{name}_{ts}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return str(path)
