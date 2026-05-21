"""
ProjectsPage — TestwrightAI Projeler listesi Page Object.
LocatorManager üzerinden merkezi seçici yönetimi kullanır.
"""
from __future__ import annotations

import logging
from typing import Optional

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from locators.locator_manager import LocatorManager

logger = logging.getLogger(__name__)

_PAGE = "projects_list"


class ProjectsPage(BasePage):
    """TestwrightAI Projeler sayfası Page Object."""

    URL = "/projects"

    def __init__(
        self,
        page: Page,
        locator_manager: Optional[LocatorManager] = None,
        base_url: str = "",
    ) -> None:
        super().__init__(page)
        self.lm = locator_manager or LocatorManager()
        self._base_url = base_url

    def _loc(self, element: str) -> str:
        return self.lm.get_locator_with_fallback(_PAGE, element)

    # ── Navigasyon ────────────────────────────────────────────────────────────

    def goto(self) -> "ProjectsPage":
        """Projeler sayfasına git."""
        url = f"{self._base_url}{self.URL}" if self._base_url else self.URL
        logger.info("Projeler sayfasına gidiliyor: %s", url)
        self.navigate(url)
        return self

    # ── Aksiyonlar ────────────────────────────────────────────────────────────

    def create_project(self, name: str, description: str = "") -> "ProjectsPage":
        """Yeni proje oluştur."""
        logger.info("Proje oluşturuluyor: %s", name)
        self.fill(self._loc("name_input"), name)
        if description:
            self.fill(self._loc("description_input"), description)
        self.click(self._loc("create_button"))
        return self

    def open_project(self, name: str) -> None:
        """Proje adına tıklayarak proje detayına git."""
        logger.info("Proje açılıyor: %s", name)
        self.page.get_by_text(name, exact=False).first.click()

    def search_projects(self, query: str) -> "ProjectsPage":
        """Projeleri anahtar kelime ile ara."""
        logger.info("Proje aranıyor: %s", query)
        search_loc = self.lm.get_locator(_PAGE, "name_input", "test_id")
        self.fill(search_loc, query)
        return self

    def filter_by_status(self, status: str) -> "ProjectsPage":
        """Projeleri duruma göre filtrele."""
        logger.info("Durum filtreleniyor: %s", status)
        try:
            filter_loc = self.lm.get_locator(_PAGE, "filter_dropdown", "test_id")
            self.select_option(filter_loc, status)
        except (KeyError, ValueError):
            self.page.get_by_text(status).click()
        return self

    def get_project_count(self) -> int:
        """Görünür proje kartlarının sayısını döner."""
        logger.info("Proje sayısı okunuyor")
        self.wait_for(self._loc("grid"), timeout=5000)
        cards = self.page.locator(f"{self._loc('grid')} > *").all()
        count = len(cards)
        logger.info("Bulunan proje sayısı: %d", count)
        return count

    def delete_project(self, name: str) -> "ProjectsPage":
        """Proje sil — proje kartındaki sil butonuna tıkla."""
        logger.info("Proje siliniyor: %s", name)
        card = self.page.get_by_text(name).locator("..")
        delete_btn = card.locator("button:has-text('Sil'), [data-testid*='delete']")
        delete_btn.click()
        return self

    def project_card(self, project_id: str):
        """Belirli bir proje kartının locator'ını döner."""
        return self.page.locator(f"[data-testid='projects-card-{project_id}']")

    # ── Assertion ─────────────────────────────────────────────────────────────

    def assert_page_loaded(self) -> "ProjectsPage":
        """Projeler sayfasının yüklendiğini doğrula."""
        expect(self.page.locator(self._loc("heading"))).to_be_visible()
        return self

    def assert_project_visible(self, name: str) -> "ProjectsPage":
        """Proje kartının görünür olduğunu doğrula."""
        expect(self.page.get_by_text(name)).to_be_visible()
        return self
