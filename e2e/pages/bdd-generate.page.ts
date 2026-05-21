import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class BddGeneratePage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/scenarios\/generate$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get textarea() {
    return this.page.locator("textarea").first();
  }
  get generateButton() {
    return this.role("button", { name: /üret|generate/i });
  }
  get minLengthError() {
    return this.text(/en az 10 karakter/i);
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async fillAnalysis(text: string) {
    await this.textarea.fill(text);
  }

  async generate() {
    await this.generateButton.click();
  }

  async generateFromText(text: string) {
    await this.fillAnalysis(text);
    await this.generate();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.text(/analiz dokümanı|BDD/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(this.generateButton).toBeVisible();
  }

  async assertMinLengthErrorVisible() {
    await expect(this.minLengthError).toBeVisible({ timeout: 5_000 });
  }

  async assertGenerationStarted() {
    await expect(
      this.text(/üretiliyor|üretilen|senaryo/i).first()
    ).toBeVisible({ timeout: 60_000 });
  }
}
