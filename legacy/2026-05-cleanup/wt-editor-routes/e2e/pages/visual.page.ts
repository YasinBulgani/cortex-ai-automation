import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class VisualPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/visual$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get demoBanner() {
    return this.testId("demo-data-banner");
  }
  get table() {
    return this.testId("visual-table");
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.demoBanner).toBeVisible({ timeout: 15_000 });
    await expect(this.table).toBeVisible();
  }
}
