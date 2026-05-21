import { expect, type Locator } from "@playwright/test";
import { BasePage } from "./base.page";

export class ScenariosListPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/scenarios$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get heading() {
    return this.text("Senaryolar");
  }
  get searchInput() {
    return this.placeholder("Başlıkta ara…");
  }
  get newScenarioButton() {
    return this.text("Yeni senaryo");
  }
  get aiGenerateButton() {
    return this.text("AI ile Üret");
  }
  get bulkDeleteButton() {
    return this.role("button", { name: /Seçilenleri sil/ });
  }
  get emptyState() {
    return this.text("Kayıt yok.");
  }

  scenarioLink(title: string): Locator {
    return this.text(title);
  }

  scenarioCheckbox(title: string | RegExp): Locator {
    return this.role("checkbox", { name: title });
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async search(query: string) {
    await this.searchInput.fill(query);
  }

  async selectScenario(title: string | RegExp) {
    await this.scenarioCheckbox(title).check();
  }

  async bulkDelete() {
    await this.bulkDeleteButton.click();
    const confirmBtn = this.role("button", { name: "Onayla" });
    if (await confirmBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await confirmBtn.click();
    }
  }

  async gotoNew(projectId: string) {
    await this.page.goto(`/p/${projectId}/scenarios/new`);
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertScenarioVisible(title: string) {
    await expect(this.scenarioLink(title)).toBeVisible({ timeout: 10_000 });
  }

  async assertScenarioHidden(title: string) {
    await expect(this.scenarioLink(title)).not.toBeVisible({ timeout: 10_000 });
  }
}
