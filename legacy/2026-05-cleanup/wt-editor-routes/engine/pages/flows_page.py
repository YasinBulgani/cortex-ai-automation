"""FlowsPage — TestwrightAI Akışlar ekranı Page Object."""
from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class FlowsPage(BasePage):
    """TestwrightAI Akışlar listesi sayfası."""

    NAME_INPUT = '[data-testid="flows-input-name"]'
    CREATE_BTN = '[data-testid="flows-btn-create"]'
    GRID = '[data-testid="flows-grid"]'

    def __init__(self, page: Page, project_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/flows")
        return self

    def create_flow(self, name: str):
        self.page.locator(self.NAME_INPUT).fill(name)
        self.page.locator(self.CREATE_BTN).click()
        return self

    def flow_card(self, flow_id: str):
        return self.page.locator(f'[data-testid="flows-card-{flow_id}"]')

    def assert_flow_visible(self, name: str):
        expect(self.page.get_by_text(name)).to_be_visible(timeout=10_000)
        return self


class FlowEditorPage(BasePage):
    """TestwrightAI Akış editör sayfası."""

    EDITOR = '[data-testid="flow-editor"]'
    TOOLBAR = '[data-testid="flow-editor-toolbar"]'
    SAVE_BTN = '[data-testid="flow-editor-btn-save"]'

    def __init__(self, page: Page, project_id: str, flow_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._flow_id = flow_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/flows/{self._flow_id}")
        return self

    def save(self):
        self.page.locator(self.SAVE_BTN).click()
        return self

    def assert_editor_loaded(self):
        expect(self.page.locator(self.EDITOR)).to_be_visible(timeout=10_000)
        return self
