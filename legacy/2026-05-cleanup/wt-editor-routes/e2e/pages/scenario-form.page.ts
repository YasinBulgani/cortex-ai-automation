import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ScenarioFormPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/scenarios\/(new|[^/]+)$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get titleInput() {
    return this.label("Başlık");
  }
  get saveButton() {
    return this.role("button", { name: "Kaydet" });
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async fillTitle(title: string) {
    await this.titleInput.clear();
    await this.titleInput.fill(title);
  }

  async save() {
    await this.saveButton.click();
  }

  async createScenario(title: string) {
    await this.fillTitle(title);
    await this.save();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertRedirectToDetail() {
    await expect(this.page).toHaveURL(/\/p\/[^/]+\/scenarios\/[^/]+$/);
  }
}
