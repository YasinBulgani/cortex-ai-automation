"""ApprovalsPage — TestwrightAI Onaylar ekranı Page Object."""
from playwright.sync_api import Page, expect
from pages.base_page import BasePage


class ApprovalsPage(BasePage):
    """TestwrightAI Onaylar sayfası."""

    HEADING = '[data-testid="approvals-heading"]'
    APPROVE_BTN = '[data-testid="approvals-btn-approve"]'
    REJECT_BTN = '[data-testid="approvals-btn-reject"]'

    def __init__(self, page: Page, project_id: str, base_url: str = ""):
        super().__init__(page)
        self._project_id = project_id
        self._base_url = base_url

    def goto(self):
        self.navigate(f"{self._base_url}/p/{self._project_id}/approvals")
        return self

    def approval_item(self, approval_id: str):
        return self.page.locator(f'[data-testid="approvals-item-{approval_id}"]')

    def click_approval(self, approval_id: str):
        self.approval_item(approval_id).click()
        return self

    def approve(self):
        self.page.locator(self.APPROVE_BTN).click()
        return self

    def reject(self):
        self.page.locator(self.REJECT_BTN).click()
        return self

    def assert_page_loaded(self):
        expect(self.page.locator(self.HEADING)).to_be_visible()
        return self
