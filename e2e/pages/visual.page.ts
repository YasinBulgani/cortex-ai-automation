import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class VisualPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/visual$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("visual-regression-page");
  }
  get table() {
    return this.page.getByText(/baseline/i).first();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 15_000 });
    await expect(this.table).toBeVisible();
  }
}
