"""
CommonNav — TestwrightAI Ortak navigasyon Page Object.
Sidebar, header ve kullanıcı menüsü etkileşimlerini yönetir.
LocatorManager üzerinden merkezi seçici yönetimi kullanır.
"""
from __future__ import annotations

import logging
from typing import Optional

from playwright.sync_api import Page, TimeoutError, expect

from pages.base_page import BasePage
from locators.locator_manager import LocatorManager

logger = logging.getLogger(__name__)

_PAGE = "common_navigation"


class CommonNav(BasePage):
    """TestwrightAI Ortak navigasyon bileşenleri Page Object."""

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

    # ── Sidebar Navigasyonu ───────────────────────────────────────────────────

    def go_to_projects(self) -> "CommonNav":
        """Projeler sayfasına git (sidebar)."""
        logger.info("Sidebar: Projeler'e gidiliyor")
        self.click(self._loc("sidebar_link_projects"))
        return self

    def go_to_scenarios(self) -> "CommonNav":
        """Senaryolar sayfasına git (sidebar)."""
        logger.info("Sidebar: Senaryolar'a gidiliyor")
        self.click(self._loc("sidebar_link_scenarios"))
        return self

    def go_to_approvals(self) -> "CommonNav":
        """Onaylar sayfasına git (sidebar)."""
        logger.info("Sidebar: Onaylar'a gidiliyor")
        self.click(self._loc("sidebar_link_approvals"))
        return self

    def go_to_import(self) -> "CommonNav":
        """İçe aktarma sayfasına git (sidebar)."""
        logger.info("Sidebar: İçe aktar'a gidiliyor")
        self.click(self._loc("sidebar_link_import"))
        return self

    def go_to_executions(self) -> "CommonNav":
        """Koşular sayfasına git (sidebar)."""
        logger.info("Sidebar: Koşular'a gidiliyor")
        self.click(self._loc("sidebar_link_executions"))
        return self

    def go_to_flows(self) -> "CommonNav":
        """Akışlar sayfasına git (sidebar)."""
        logger.info("Sidebar: Akışlar'a gidiliyor")
        self.click(self._loc("sidebar_link_flows"))
        return self

    def go_to_regression(self) -> "CommonNav":
        """Regresyon sayfasına git (sidebar)."""
        logger.info("Sidebar: Regresyon'a gidiliyor")
        self.click(self._loc("sidebar_link_regression"))
        return self

    def go_to_analytics(self) -> "CommonNav":
        """Analitik sayfasına git (sidebar)."""
        logger.info("Sidebar: Analitik'e gidiliyor")
        self.click(self._loc("sidebar_link_analytics"))
        return self

    def go_to_requirements(self) -> "CommonNav":
        """Gereksinimler sayfasına git (sidebar)."""
        logger.info("Sidebar: Gereksinimler'e gidiliyor")
        self.click(self._loc("sidebar_link_requirements"))
        return self

    def go_to_coverage(self) -> "CommonNav":
        """Kapsam matrisi sayfasına git (sidebar)."""
        logger.info("Sidebar: Kapsam Matrisi'ne gidiliyor")
        self.click(self._loc("sidebar_link_coverage"))
        return self

    def go_to_schedules(self) -> "CommonNav":
        """Zamanlayıcı sayfasına git (sidebar)."""
        logger.info("Sidebar: Zamanlayıcı'ya gidiliyor")
        self.click(self._loc("sidebar_link_schedules"))
        return self

    def go_to_integrations(self) -> "CommonNav":
        """Entegrasyonlar sayfasına git (sidebar)."""
        logger.info("Sidebar: Entegrasyonlar'a gidiliyor")
        self.click(self._loc("sidebar_link_integrations"))
        return self

    # ── Kullanıcı Menüsü ─────────────────────────────────────────────────────

    def _open_user_menu(self) -> None:
        """Kullanıcı menüsünü aç."""
        self.click(self._loc("user_menu_button"))
        self.wait_ms(300)

    def go_to_profile(self) -> "CommonNav":
        """Profil sayfasına git (kullanıcı menüsü)."""
        logger.info("Kullanıcı menüsü: Profil'e gidiliyor")
        self._open_user_menu()
        self.click(self._loc("user_menu_profile"))
        return self

    def go_to_settings(self) -> "CommonNav":
        """Bilgiler sayfasına git (kullanıcı menüsü)."""
        logger.info("Kullanıcı menüsü: Bilgiler'e gidiliyor")
        self._open_user_menu()
        self.click(self._loc("user_menu_info"))
        return self

    def logout(self) -> "CommonNav":
        """Çıkış yap (kullanıcı menüsü)."""
        logger.info("Kullanıcı menüsü: Çıkış yapılıyor")
        self._open_user_menu()
        self.click(self._loc("user_menu_logout"))
        return self

    # ── Bilgi Alma ────────────────────────────────────────────────────────────

    def get_current_user(self) -> str:
        """Kullanıcı menüsü butonundaki baş harfleri döner."""
        return self.get_text(self._loc("user_menu_button"))

    def get_breadcrumb(self) -> str:
        """Breadcrumb navigasyon metnini döner."""
        try:
            self.wait_for(self._loc("breadcrumb"), timeout=3000)
            return self.get_text(self._loc("breadcrumb"))
        except TimeoutError:
            return ""

    def is_sidebar_visible(self) -> bool:
        """Kenar çubuğunun görünür olup olmadığını kontrol eder."""
        return self.is_visible(self._loc("sidebar"))

    # ── Assertion ─────────────────────────────────────────────────────────────

    def assert_sidebar_loaded(self) -> "CommonNav":
        """Kenar çubuğunun yüklendiğini doğrula."""
        expect(self.page.locator(self._loc("sidebar"))).to_be_visible()
        expect(self.page.locator(self._loc("sidebar_nav"))).to_be_visible()
        return self

    def assert_header_loaded(self) -> "CommonNav":
        """Üst başlık çubuğunun yüklendiğini doğrula."""
        expect(self.page.locator(self._loc("header"))).to_be_visible()
        return self
