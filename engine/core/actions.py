"""
core/actions.py — Playwright Aksiyon Sarmalayicilari

NexusQA projesindeki methods/ klasorunun (ClickMethods, InputMethods,
HoverMethods, ScrollMethods, SelectMethods, DragDropMethods,
CheckboxMethods, RadioButtonMethods, ScreenshotMethods) Playwright
uyumlu birlesmis implementasyonu.

Playwright'in auto-wait mekanizmasi sayesinde WaitMethods'a gerek yoktur;
her aksiyon otomatik olarak elementin hazir olmasini bekler.

Kullanim:
    actions = Actions(page)
    actions.click("GirisYapButon")
    actions.fill("SifreInput", "admin123")
    actions.select("SehirSelect", "Istanbul")
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    import allure
except ImportError:
    allure = None

from playwright.sync_api import Page

from config.settings import settings
from core.locator_manager import LocatorManager


def _allure_step(title):
    """allure.step wrapper; allure yuklu degilse no-op context manager doner."""
    if allure:
        return allure.step(title)
    from contextlib import nullcontext
    return nullcontext()

logger = logging.getLogger(__name__)


def _resolve(key_or_selector: str) -> str:
    """LocatorManager uzerinden locator cozumler, fallback olarak raw selector doner."""
    return LocatorManager.resolve(key_or_selector)


class Actions:
    """Playwright sayfa aksiyonlari — NexusQA methods/ pattern'inin birlesmis hali."""

    def __init__(self, page: Page):
        self.page = page

    # =========================================================================
    # CLICK
    # =========================================================================

    def click(self, key: str):
        """Verilen locator key'e tiklar."""
        selector = _resolve(key)
        with _allure_step(f"Tikla: '{key}' ({selector})"):
            self.page.locator(selector).first.click()
        logger.info("Click: %s -> %s", key, selector)

    def double_click(self, key: str):
        """Cift tikla."""
        selector = _resolve(key)
        with _allure_step(f"Cift tikla: '{key}'"):
            self.page.locator(selector).first.dblclick()
        logger.info("DblClick: %s", key)

    def right_click(self, key: str):
        """Sag tikla (context menu)."""
        selector = _resolve(key)
        with _allure_step(f"Sag tikla: '{key}'"):
            self.page.locator(selector).first.click(button="right")
        logger.info("RightClick: %s", key)

    def click_text(self, text: str):
        """Metne gore tikla."""
        with _allure_step(f"Metne tikla: '{text}'"):
            self.page.get_by_text(text, exact=False).first.click()

    def click_role(self, role: str, name: str):
        """ARIA role ve name ile tikla."""
        with _allure_step(f"Role tikla: {role}[{name}]"):
            self.page.get_by_role(role, name=name).click()

    def force_click(self, key: str):
        """Gorunurluk beklemeden tikla (overlay arkasindaki elementler icin)."""
        selector = _resolve(key)
        with _allure_step(f"Force tikla: '{key}'"):
            self.page.locator(selector).first.click(force=True)

    # =========================================================================
    # INPUT
    # =========================================================================

    def fill(self, key: str, value: str):
        """Input alanini doldurur (onceki degeri siler)."""
        selector = _resolve(key)
        with _allure_step(f"Yaz: '{key}' <- '{value}'"):
            self.page.locator(selector).first.fill(value)
        logger.info("Fill: %s = %s", key, value)

    def clear(self, key: str):
        """Input alanini temizler."""
        selector = _resolve(key)
        with _allure_step(f"Temizle: '{key}'"):
            self.page.locator(selector).first.fill("")

    def type_text(self, key: str, text: str, delay: int = 50):
        """Karakter karakter yazar (animasyon/debounce gereken durumlar icin)."""
        selector = _resolve(key)
        with _allure_step(f"Yaz (karakter): '{key}' <- '{text}'"):
            self.page.locator(selector).first.press_sequentially(text, delay=delay)

    def fill_and_enter(self, key: str, value: str):
        """Yaz ve Enter'a bas."""
        selector = _resolve(key)
        with _allure_step(f"Yaz+Enter: '{key}' <- '{value}'"):
            loc = self.page.locator(selector).first
            loc.fill(value)
            loc.press("Enter")

    # =========================================================================
    # SELECT (Dropdown)
    # =========================================================================

    def select_by_value(self, key: str, value: str):
        """<select> elementinden value ile secer."""
        selector = _resolve(key)
        with _allure_step(f"Sec (value): '{key}' <- '{value}'"):
            self.page.locator(selector).select_option(value=value)

    def select_by_label(self, key: str, label: str):
        """<select> elementinden gorunen metin ile secer."""
        selector = _resolve(key)
        with _allure_step(f"Sec (label): '{key}' <- '{label}'"):
            self.page.locator(selector).select_option(label=label)

    def select_by_index(self, key: str, index: int):
        """<select> elementinden index ile secer."""
        selector = _resolve(key)
        with _allure_step(f"Sec (index): '{key}' <- {index}"):
            self.page.locator(selector).select_option(index=index)

    # =========================================================================
    # CHECKBOX & RADIO
    # =========================================================================

    def check(self, key: str):
        """Checkbox isaretler (zaten isaretliyse dokunmaz)."""
        selector = _resolve(key)
        with _allure_step(f"Isaretle: '{key}'"):
            self.page.locator(selector).first.check()

    def uncheck(self, key: str):
        """Checkbox isaretini kaldirir."""
        selector = _resolve(key)
        with _allure_step(f"Isaret kaldir: '{key}'"):
            self.page.locator(selector).first.uncheck()

    def is_checked(self, key: str) -> bool:
        """Checkbox/Radio durumunu doner."""
        selector = _resolve(key)
        return self.page.locator(selector).first.is_checked()

    def set_checked(self, key: str, checked: bool):
        """Checkbox'i belirtilen duruma getirir."""
        selector = _resolve(key)
        with _allure_step(f"Checked={checked}: '{key}'"):
            self.page.locator(selector).first.set_checked(checked)

    # =========================================================================
    # HOVER
    # =========================================================================

    def hover(self, key: str):
        """Element uzerine gelir (hover)."""
        selector = _resolve(key)
        with _allure_step(f"Hover: '{key}'"):
            self.page.locator(selector).first.hover()

    def hover_and_click(self, hover_key: str, click_key: str):
        """Once hover, sonra baska bir elemente tikla (menu acma gibi)."""
        self.hover(hover_key)
        self.click(click_key)

    # =========================================================================
    # SCROLL
    # =========================================================================

    def scroll_to(self, key: str):
        """Elemente scroll yapar (gorunur hale getirir)."""
        selector = _resolve(key)
        with _allure_step(f"Scroll: '{key}'"):
            self.page.locator(selector).first.scroll_into_view_if_needed()

    def scroll_page(self, direction: str = "down", pixels: int = 500):
        """Sayfayi yukari/asagi scroll yapar."""
        delta = pixels if direction == "down" else -pixels
        with _allure_step(f"Sayfa scroll: {direction} {pixels}px"):
            self.page.mouse.wheel(0, delta)

    def scroll_to_top(self):
        """Sayfa basina scroll yapar."""
        with _allure_step("Sayfa basina scroll"):
            self.page.evaluate("window.scrollTo(0, 0)")

    def scroll_to_bottom(self):
        """Sayfa sonuna scroll yapar."""
        with _allure_step("Sayfa sonuna scroll"):
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    # =========================================================================
    # DRAG & DROP
    # =========================================================================

    def drag_and_drop(self, source_key: str, target_key: str):
        """Bir elementi digerine suruklr-birakir."""
        src = _resolve(source_key)
        tgt = _resolve(target_key)
        with _allure_step(f"Surukle: '{source_key}' -> '{target_key}'"):
            self.page.locator(src).first.drag_to(self.page.locator(tgt).first)

    # =========================================================================
    # KEYBOARD
    # =========================================================================

    def press_key(self, key: str):
        """Klavye tusuna basar (Enter, Tab, Escape, ArrowDown, vb.)."""
        with _allure_step(f"Tus bas: {key}"):
            self.page.keyboard.press(key)

    def press_on_element(self, element_key: str, keyboard_key: str):
        """Belirli bir element uzerinde tusa basar."""
        selector = _resolve(element_key)
        with _allure_step(f"Tus bas: {keyboard_key} on '{element_key}'"):
            self.page.locator(selector).first.press(keyboard_key)

    def type_keyboard(self, text: str, delay: int = 0):
        """Odaklanan elemente metin yazar."""
        with _allure_step(f"Klavye yaz: '{text}'"):
            self.page.keyboard.type(text, delay=delay)

    # =========================================================================
    # FILE UPLOAD
    # =========================================================================

    def upload_file(self, key: str, file_path: str | Path):
        """Dosya yukleme input'una dosya atar."""
        selector = _resolve(key)
        with _allure_step(f"Dosya yukle: '{key}' <- {file_path}"):
            self.page.locator(selector).first.set_input_files(str(file_path))

    def upload_files(self, key: str, file_paths: list[str | Path]):
        """Birden fazla dosya yukler."""
        selector = _resolve(key)
        with _allure_step(f"Dosyalar yukle: '{key}' <- {len(file_paths)} dosya"):
            self.page.locator(selector).first.set_input_files([str(p) for p in file_paths])

    def clear_upload(self, key: str):
        """Yuklenmis dosyalari temizler."""
        selector = _resolve(key)
        with _allure_step(f"Dosya temizle: '{key}'"):
            self.page.locator(selector).first.set_input_files([])

    # =========================================================================
    # ASSERTIONS
    # =========================================================================

    def assert_visible(self, key: str):
        """Elementin gorunur oldugunu dogrular."""
        selector = _resolve(key)
        with _allure_step(f"Gorunur: '{key}'"):
            assert self.page.locator(selector).first.is_visible(), \
                f"Element gorunur degil: {key} ({selector})"

    def assert_hidden(self, key: str):
        """Elementin gizli oldugunu dogrular."""
        selector = _resolve(key)
        with _allure_step(f"Gizli: '{key}'"):
            assert not self.page.locator(selector).first.is_visible(), \
                f"Element hala gorunur: {key} ({selector})"

    def assert_text(self, key: str, expected: str):
        """Elementin metnini kontrol eder."""
        selector = _resolve(key)
        actual = self.page.locator(selector).first.inner_text().strip()
        with _allure_step(f"Metin kontrol: '{key}' == '{expected}'"):
            assert expected in actual, \
                f"Beklenen: '{expected}' | Bulunan: '{actual}'"

    def assert_value(self, key: str, expected: str):
        """Input degerini kontrol eder."""
        selector = _resolve(key)
        actual = self.page.locator(selector).first.input_value()
        with _allure_step(f"Deger kontrol: '{key}' == '{expected}'"):
            assert expected == actual, \
                f"Beklenen: '{expected}' | Bulunan: '{actual}'"

    def assert_enabled(self, key: str):
        """Elementin aktif (enabled) oldugunu dogrular."""
        selector = _resolve(key)
        with _allure_step(f"Aktif: '{key}'"):
            assert self.page.locator(selector).first.is_enabled(), \
                f"Element deaktif: {key}"

    def assert_disabled(self, key: str):
        """Elementin deaktif (disabled) oldugunu dogrular."""
        selector = _resolve(key)
        with _allure_step(f"Deaktif: '{key}'"):
            assert not self.page.locator(selector).first.is_enabled(), \
                f"Element aktif: {key}"

    def assert_element_count(self, key: str, expected_count: int):
        """Belirli selector'a uyan element sayisini kontrol eder."""
        selector = _resolve(key)
        actual = self.page.locator(selector).count()
        with _allure_step(f"Sayi kontrol: '{key}' == {expected_count}"):
            assert actual == expected_count, \
                f"Beklenen: {expected_count} | Bulunan: {actual}"

    # =========================================================================
    # SCREENSHOT
    # =========================================================================

    def screenshot(self, name: str = "screenshot", full_page: bool = True) -> str:
        """Ekran goruntusu alir ve dosya yolunu doner."""
        settings.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.SCREENSHOTS_DIR / f"{name}_{ts}.png"
        self.page.screenshot(path=str(path), full_page=full_page)
        if allure:
            allure.attach(
                self.page.screenshot(full_page=full_page),
                name=name,
                attachment_type=allure.attachment_type.PNG,
            )
        return str(path)

    def element_screenshot(self, key: str, name: str = "element") -> str:
        """Belirli bir elementin ekran goruntusunu alir."""
        selector = _resolve(key)
        settings.SCREENSHOTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = settings.SCREENSHOTS_DIR / f"{name}_{ts}.png"
        self.page.locator(selector).first.screenshot(path=str(path))
        return str(path)

    # =========================================================================
    # WAIT (Playwright auto-wait'i yeterli olmayan ozel durumlar icin)
    # =========================================================================

    def wait_for_visible(self, key: str, timeout: int = None):
        """Elementin gorunur olmasini bekler."""
        selector = _resolve(key)
        self.page.locator(selector).first.wait_for(
            state="visible", timeout=timeout or settings.DEFAULT_TIMEOUT
        )

    def wait_for_hidden(self, key: str, timeout: int = None):
        """Elementin gizlenmesini bekler."""
        selector = _resolve(key)
        self.page.locator(selector).first.wait_for(
            state="hidden", timeout=timeout or settings.DEFAULT_TIMEOUT
        )

    def wait_ms(self, ms: int):
        """Belirtilen milisaniye kadar bekler."""
        self.page.wait_for_timeout(ms)

    # =========================================================================
    # INFO
    # =========================================================================

    def get_text(self, key: str) -> str:
        """Elementin metin icerigini doner."""
        selector = _resolve(key)
        return self.page.locator(selector).first.inner_text().strip()

    def get_value(self, key: str) -> str:
        """Input degerini doner."""
        selector = _resolve(key)
        return self.page.locator(selector).first.input_value()

    def get_attribute(self, key: str, attr: str) -> Optional[str]:
        """Element attribute'unu doner."""
        selector = _resolve(key)
        return self.page.locator(selector).first.get_attribute(attr)

    def element_count(self, key: str) -> int:
        """Selector'a uyan element sayisini doner."""
        selector = _resolve(key)
        return self.page.locator(selector).count()
