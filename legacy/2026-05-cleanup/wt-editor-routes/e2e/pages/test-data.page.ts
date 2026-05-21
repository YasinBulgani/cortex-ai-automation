import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class TestDataPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/test-data$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("test-data-page");
  }
  get heading() {
    return this.testId("test-data-heading");
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 10_000 });
    await expect(this.heading).toBeVisible();
  }
}
