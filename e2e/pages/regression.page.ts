import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class RegressionPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/regression$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get newSetButton() {
    return this.page.getByTestId("regression-page").getByRole("button", { name: "Yeni Set" });
  }
  get nameInput() {
    return this.page.locator("#regression-set-name");
  }
  get saveButton() {
    return this.page.getByTestId("regression-page").getByRole("button", { name: "Kaydet" });
  }
  get suggestButton() {
    return this.role("button", { name: /öner|suggest/i });
  }
  get checkboxes() {
    return this.role("checkbox");
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async createSet(name: string, scenarioCount = 2) {
    await expect(this.page.getByTestId("regression-page")).toBeVisible({ timeout: 10_000 });
    await this.newSetButton.click();
    await this.nameInput.fill(name);
    const count = await this.checkboxes.count();
    for (let i = 0; i < Math.min(count, scenarioCount); i++) {
      await this.checkboxes.nth(i).check();
    }
    await this.saveButton.click();
  }

  async aiSuggest() {
    await expect(this.suggestButton).toBeVisible({ timeout: 10_000 });
    await this.suggestButton.click();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertSetVisible(name: string) {
    await expect(this.text(name)).toBeVisible({ timeout: 10_000 });
  }

  async assertSuggestionVisible() {
    await expect(
      this.text(/öneri|suggestion|senaryo/i).first()
    ).toBeVisible({ timeout: 30_000 });
  }
}
