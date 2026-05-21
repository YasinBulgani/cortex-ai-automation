import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ApiTestsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/api-tests$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("api-tests-page");
  }
  get newButton() {
    return this.role("button", { name: /yeni|oluştur/i });
  }
  get nameInput() {
    return this.page.getByLabel(/ad|name/i);
  }
  get saveButton() {
    return this.role("button", { name: /kaydet|oluştur/i });
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async openNewCollectionForm() {
    await this.newButton.click();
  }

  async fillName(name: string) {
    await this.nameInput.fill(name);
  }

  async save() {
    await this.saveButton.click();
  }

  async createCollection(name: string) {
    await this.openNewCollectionForm();
    await this.fillName(name);
    await this.save();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 10_000 });
  }

  async assertCollectionVisible(name: string) {
    await expect(this.text(name)).toBeVisible({ timeout: 10_000 });
  }
}
