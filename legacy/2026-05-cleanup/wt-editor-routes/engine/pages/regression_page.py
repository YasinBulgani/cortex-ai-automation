"""RegressionPage — TestwrightAI Regresyon setleri Page Object."""
from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class RegressionPage(BasePage):
    """TestwrightAI Regresyon setleri sayfası."""

    HEADING = '[data-testid="regression-heading"]'
    NAME_INPUT = '[data-testid="regression-input-name"]'
    CREATE_BTN = '[data-testid="regression-btn-create"]'
    SUGGEST_BTN = '[data-testid="regression-btn-suggest"]'

    def __init__(self, page: Page, project_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/regression")
        return self

    def create_set(self, name: str):
        self.page.locator(self.NAME_INPUT).fill(name)
        self.page.locator(self.CREATE_BTN).click()
        return self

    def suggest(self):
        self.page.locator(self.SUGGEST_BTN).click()
        return self

    def assert_page_loaded(self):
        expect(self.page.locator(self.HEADING)).to_be_visible()
        return self

    def assert_set_visible(self, name: str):
        expect(self.page.get_by_text(name)).to_be_visible(timeout=10_000)
        return self
