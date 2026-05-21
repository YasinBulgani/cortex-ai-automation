"""ImportPage — TestwrightAI İçe Aktarma ekranı Page Object."""
from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class ImportPage(BasePage):
    """TestwrightAI İçe aktarma sayfası."""

    HEADING = '[data-testid="import-heading"]'
    FILENAME_INPUT = '[data-testid="import-input-filename"]'
    UPLOAD_BTN = '[data-testid="import-btn-upload"]'
    RESULT = '[data-testid="import-result"]'

    def __init__(self, page: Page, project_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/import")
        return self

    def fill_filename(self, filename: str):
        self.page.locator(self.FILENAME_INPUT).fill(filename)
        return self

    def upload(self):
        self.page.locator(self.UPLOAD_BTN).click()
        return self

    def assert_page_loaded(self):
        expect(self.page.locator(self.HEADING)).to_be_visible(timeout=10_000)
        return self

    def assert_result_visible(self):
        expect(self.page.locator(self.RESULT)).to_be_visible(timeout=15_000)
        return self
