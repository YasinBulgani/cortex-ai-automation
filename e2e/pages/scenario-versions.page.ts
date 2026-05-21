import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ScenarioVersionsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/scenarios\/[^/]+\/versions$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("versions-page");
  }
  get heading() {
    return this.testId("versions-heading");
  }
  get backButton() {
    return this.testId("versions-btn-back");
  }
  get compareButton() {
    return this.testId("versions-btn-compare");
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async goBack() {
    await this.backButton.click();
  }

  async compare() {
    await this.compareButton.click();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 10_000 });
    await expect(this.heading).toBeVisible();
  }
}
