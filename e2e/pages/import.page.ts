import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ImportPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/import$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get heading() {
    return this.text(/içe aktar|import/i).first();
  }
  get fileInput() {
    return this.page.locator('input[type="file"]');
  }
  get uploadButton() {
    return this.testId("file-drop-zone");
  }
  get successAlert() {
    return this.text(/başarı|success|tamamlandı|aktarıldı/i).first();
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async uploadCSV(content: string, filename = "test-import.csv") {
    const buffer = Buffer.from(content, "utf-8");
    await this.fileInput.setInputFiles({
      name: filename,
      mimeType: "text/csv",
      buffer,
    });
  }

  async clickUpload() {
    await expect(this.fileInput).toBeAttached();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.heading).toBeVisible({ timeout: 10_000 });
    await expect(this.uploadButton).toBeVisible();
  }

  async assertImportSuccess() {
    await expect(this.successAlert).toBeVisible({ timeout: 15_000 });
  }
}
