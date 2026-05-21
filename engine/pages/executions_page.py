"""ExecutionsPage — TestwrightAI Koşum ekranları Page Object."""
from __future__ import annotations

from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class ExecutionsListPage(BasePage):
    """TestwrightAI Koşum listesi sayfası."""

    HEADING = '[data-testid="executions-heading"]'
    NEW_BTN = '[data-testid="executions-btn-new"]'
    TABLE = '[data-testid="executions-table"]'

    def __init__(self, page: Page, project_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/executions")
        return self

    def goto_new(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/executions/new")
        return self

    def assert_page_loaded(self):
        expect(self.page.locator(self.HEADING)).to_be_visible()
        return self


class NewExecutionPage(BasePage):
    """TestwrightAI Yeni koşum sayfası."""

    NAME_INPUT = '[data-testid="execution-input-name"]'
    START_BTN = '[data-testid="execution-btn-start"]'
    SCENARIO_LIST = '[data-testid="execution-scenario-list"]'

    def __init__(self, page: Page, project_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/executions/new")
        return self

    def fill_name(self, name: str):
        self.page.locator(self.NAME_INPUT).fill(name)
        return self

    def select_scenario(self, scenario_id: str):
        cb = self.page.locator(f'[data-testid="execution-check-scenario-{scenario_id}"]')
        if cb.is_visible():
            cb.check()
        return self

    def start(self):
        self.page.locator(self.START_BTN).click()
        return self

    def create_execution(self, name: str, scenario_ids: list[str] | None = None):
        self.fill_name(name)
        for sid in (scenario_ids or []):
            self.select_scenario(sid)
        self.start()
        return self

    def assert_redirect_to_detail(self):
        self.page.wait_for_url(f"**/p/{self._project_id}/executions/**", timeout=15_000)
        return self
