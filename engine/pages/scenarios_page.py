"""
ScenariosPage — TestwrightAI Senaryo listesi + form Page Object.
LocatorManager üzerinden merkezi seçici yönetimi kullanır.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from locators.locator_manager import LocatorManager

logger = logging.getLogger(__name__)

_LIST_PAGE = "scenarios_list"
_CREATE_PAGE = "scenario_create"


class ScenariosListPage(BasePage):
    """TestwrightAI Senaryolar listesi sayfası Page Object."""

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
        return self.lm.get_locator_with_fallback(_LIST_PAGE, element)

    # ── Navigasyon ────────────────────────────────────────────────────────────

    def goto(self) -> "ScenariosListPage":
        """Senaryo listesi sayfasına git."""
        url = f"{self._base_url}/p/{self._project_id}/scenarios"
        logger.info("Senaryolar sayfasına gidiliyor: %s", url)
        self.navigate(url)
        return self

    # ── CRUD Aksiyonlar ───────────────────────────────────────────────────────

    def create_scenario(self, title: str, steps: list[str] | None = None) -> "ScenariosListPage":
        """Yeni senaryo oluşturma sayfasına gidip senaryo oluştur."""
        logger.info("Senaryo oluşturuluyor: %s", title)
        self.click(self._loc("new_button"))
        self.page.wait_for_url(f"**/p/{self._project_id}/scenarios/new", timeout=10_000)
        lm_create = self.lm
        title_loc = lm_create.get_locator_with_fallback(_CREATE_PAGE, "title_input")
        self.fill(title_loc, title)
        save_loc = lm_create.get_locator_with_fallback(_CREATE_PAGE, "save_button")
        self.click(save_loc)
        return self

    def edit_scenario(self, scenario_id: str, data: dict[str, Any]) -> "ScenariosListPage":
        """Senaryo düzenle — senaryo detayına gidip düzenleme yap."""
        logger.info("Senaryo düzenleniyor: %s", scenario_id)
        self.page.locator(f"[data-testid='scenarios-link-{scenario_id}']").click()
        if "title" in data:
            title_input = self.page.locator("[data-testid='scenario-form-input-title']")
            title_input.clear()
            title_input.fill(data["title"])
        save_btn = self.page.locator("[data-testid='scenario-form-btn-save']")
        if save_btn.is_visible():
            save_btn.click()
        return self

    def delete_scenario(self, scenario_id: str) -> "ScenariosListPage":
        """Senaryoyu sil."""
        logger.info("Senaryo siliniyor: %s", scenario_id)
        self.page.locator(f"[data-testid='scenarios-check-{scenario_id}']").check()
        self.click(self._loc("bulk_delete_button"))
        return self

    # ── Arama ve Filtreleme ───────────────────────────────────────────────────

    def search(self, query: str) -> "ScenariosListPage":
        """Senaryoları anahtar kelime ile ara."""
        logger.info("Senaryo aranıyor: %s", query)
        self.fill(self._loc("search_input"), query)
        return self

    def filter_by_priority(self, priority: str) -> "ScenariosListPage":
        """Önceliğe göre filtrele (P0, P1, P2, P3)."""
        logger.info("Öncelik filtresi: %s", priority)
        try:
            self.select_option(self._loc("priority_filter"), priority)
        except Exception:
            self.page.get_by_text(priority).click()
        return self

    def filter_by_type(self, scenario_type: str) -> "ScenariosListPage":
        """Senaryo türüne göre filtrele (fonksiyonel, regresyon, smoke)."""
        logger.info("Tür filtresi: %s", scenario_type)
        try:
            self.select_option(self._loc("type_filter"), scenario_type)
        except Exception:
            self.page.get_by_text(scenario_type).click()
        return self

    # ── Toplu İşlemler ────────────────────────────────────────────────────────

    def bulk_select(self, scenario_ids: list[str]) -> "ScenariosListPage":
        """Birden fazla senaryoyu seç."""
        logger.info("Toplu seçim: %d senaryo", len(scenario_ids))
        for sid in scenario_ids:
            self.page.locator(f"[data-testid='scenarios-check-{sid}']").check()
        return self

    def bulk_action(self, action: str) -> "ScenariosListPage":
        """Seçili senaryolara toplu işlem uygula."""
        logger.info("Toplu işlem: %s", action)
        if action == "delete":
            self.click(self._loc("bulk_delete_button"))
        else:
            self.page.get_by_text(action).click()
        return self

    # ── Bilgi Alma ────────────────────────────────────────────────────────────

    def get_scenario_list(self) -> list[str]:
        """Tablo satırlarından senaryo başlıklarını döner."""
        logger.info("Senaryo listesi okunuyor")
        self.wait_for(self._loc("table"), timeout=10_000)
        rows = self.page.locator(f"{self._loc('table')} tbody tr").all()
        titles = []
        for row in rows:
            link = row.locator("a")
            if link.count() > 0:
                titles.append(link.first.inner_text())
        return titles

    def get_scenario_count(self) -> int:
        """Görünür senaryo satır sayısını döner."""
        logger.info("Senaryo sayısı okunuyor")
        self.wait_for(self._loc("table"), timeout=10_000)
        count = self.page.locator(f"{self._loc('table')} tbody tr").count()
        logger.info("Bulunan senaryo sayısı: %d", count)
        return count

    # ── Assertion ─────────────────────────────────────────────────────────────

    def assert_page_loaded(self) -> "ScenariosListPage":
        """Senaryo listesi sayfasının yüklendiğini doğrula."""
        expect(self.page.locator(self._loc("heading"))).to_be_visible()
        return self

    def click_scenario(self, scenario_id: str) -> None:
        """Belirli bir senaryoya tıkla."""
        self.page.locator(f"[data-testid='scenarios-link-{scenario_id}']").click()

    def select_scenario(self, scenario_id: str) -> "ScenariosListPage":
        """Belirli bir senaryonun onay kutusunu işaretle."""
        self.page.locator(f"[data-testid='scenarios-check-{scenario_id}']").check()
        return self

    def click_new(self) -> None:
        """Yeni senaryo butonuna tıkla."""
        self.click(self._loc("new_button"))

    def bulk_delete(self) -> None:
        """Toplu silme butonuna tıkla."""
        self.click(self._loc("bulk_delete_button"))


class ScenarioFormPage(BasePage):
    """TestwrightAI Senaryo oluştur/düzenle formu Page Object."""

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
        return self.lm.get_locator_with_fallback(_CREATE_PAGE, element)

    def goto_new(self) -> "ScenarioFormPage":
        """Yeni senaryo formuna git."""
        url = f"{self._base_url}/p/{self._project_id}/scenarios/new"
        logger.info("Yeni senaryo formuna gidiliyor: %s", url)
        self.navigate(url)
        return self

    def fill_title(self, title: str) -> "ScenarioFormPage":
        """Senaryo başlığını doldur."""
        loc = self.page.locator(self._loc("title_input"))
        loc.clear()
        loc.fill(title)
        return self

    def save(self) -> "ScenarioFormPage":
        """Kaydet butonuna tıkla."""
        self.click(self._loc("save_button"))
        return self

    def create_scenario(self, title: str) -> "ScenarioFormPage":
        """Başlık gir ve kaydet."""
        self.fill_title(title)
        self.save()
        return self

    def assert_redirect_to_detail(self) -> "ScenarioFormPage":
        """Senaryo detay sayfasına yönlendirildiğini doğrula."""
        self.page.wait_for_url(
            f"**/p/{self._project_id}/scenarios/**", timeout=10_000
        )
        return self
