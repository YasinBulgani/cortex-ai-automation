import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ReportsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/reports$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("reports-page");
  }
  get heading() {
    return this.page.getByRole("heading", { name: "Raporlar", exact: true });
  }
  get executionsLink() {
    return this.testId("reports-link-executions");
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 15_000 });
    await expect(this.heading).toBeVisible();
  }

  async gotoExecutions() {
    await this.page.goto(this.page.url().replace(/\/reports$/, "/executions"));
  }
}
