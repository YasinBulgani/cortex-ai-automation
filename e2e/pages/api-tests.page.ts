import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ApiTestsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/api-testing$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("api-testing-page");
  }
  get endpointTable() {
    return this.testId("endpoint-table");
  }
  get testCasesTab() {
    return this.role("button", { name: /test cases/i });
  }

  async openTestCases() {
    await this.testCasesTab.click();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 10_000 });
  }

  async assertSpecVisible(name: string) {
    await expect(this.role("button", { name: new RegExp(name, "i") })).toBeVisible({ timeout: 10_000 });
  }

  async assertEndpointVisible(method: string, path: string) {
    await expect(this.endpointTable).toBeVisible({ timeout: 10_000 });
    await expect(this.endpointTable.getByText(method, { exact: true })).toBeVisible();
    await expect(this.endpointTable.getByText(path, { exact: true })).toBeVisible();
  }

  async assertTestCaseVisible(title: string) {
    await this.openTestCases();
    await expect(this.text(title)).toBeVisible({ timeout: 10_000 });
  }
}
