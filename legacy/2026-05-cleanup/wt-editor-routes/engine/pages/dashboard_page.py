"""
DashboardPage — TestwrightAI Proje özet paneli (dashboard) Page Object.
LocatorManager üzerinden merkezi seçici yönetimi kullanır.
"""
from __future__ import annotations

import logging
from typing import Optional

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from locators.locator_manager import LocatorManager

logger = logging.getLogger(__name__)

_PAGE = "dashboard"


class DashboardPage(BasePage):
    """TestwrightAI Proje özet paneli Page Object."""

    def __init__(
        self,
        page: Page,
        project_id: str,
        locator_manager: Optional[LocatorManager] = None,
        base_url: str = "",
    ) -> None:
        super().__init__(page)
        self._project_id = project_id
        self.lm = locator_manager or LocatorManager()
        self._base_url = base_url

    def _loc(self, element: str) -> str:
        return self.lm.get_locator_with_fallback(_PAGE, element)

    # ── Navigasyon ────────────────────────────────────────────────────────────

    def goto(self) -> "DashboardPage":
        """Dashboard sayfasına git."""
        url = f"{self._base_url}/p/{self._project_id}"
        logger.info("Dashboard'a gidiliyor: %s", url)
        self.navigate(url)
        return self

    # ── Bilgi Alma ────────────────────────────────────────────────────────────

    def get_stat_cards(self) -> list[dict[str, str]]:
        """İstatistik kartlarındaki verileri döner."""
        logger.info("İstatistik kartları okunuyor")
        self.wait_for(self._loc("stats_grid"))
        cards = self.page.locator(f"{self._loc('stats_grid')} > div").all()
        result = []
        for card in cards:
            label_el = card.locator("p").first
            value_el = card.locator("p.text-2xl, p.text-3xl, .font-bold").first
            result.append({
                "label": label_el.inner_text() if label_el.is_visible() else "",
                "value": value_el.inner_text() if value_el.is_visible() else "",
            })
        return result

    def get_recent_activities(self) -> list[str]:
        """Son aktivite listesindeki metinleri döner."""
        logger.info("Son aktiviteler okunuyor")
        try:
            self.wait_for(self._loc("activity_list"), timeout=5000)
            items = self.page.locator(f"{self._loc('activity_list')} > *").all()
            return [item.inner_text() for item in items]
        except Exception:
            return []

    def navigate_to_project(self, name: str) -> None:
        """Belirtilen proje adına tıklayarak proje detayına git."""
        logger.info("Proje detayına gidiliyor: %s", name)
        self.click_text(name)

    def get_quick_actions(self) -> list[str]:
        """Hızlı işlem butonlarının metinlerini döner."""
        logger.info("Hızlı işlemler okunuyor")
        try:
            self.wait_for(self._loc("quick_actions"), timeout=5000)
            buttons = self.page.locator(f"{self._loc('quick_actions')} button").all()
            return [btn.inner_text() for btn in buttons]
        except Exception:
            return []

    def verify_dashboard_loaded(self) -> "DashboardPage":
        """Dashboard sayfasının yüklendiğini doğrula."""
        logger.info("Dashboard yükleme doğrulanıyor")
        expect(self.page.locator(self._loc("page_container"))).to_be_visible()
        expect(self.page.locator(self._loc("heading"))).to_be_visible()
        expect(self.page.locator(self._loc("stats_grid"))).to_be_visible()
        return self
