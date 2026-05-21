import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ExecutionsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/executions/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get nameInput() {
    return this.label("Koşum Adı");
  }
  get startButton() {
    return this.role("button", { name: "Başlat" });
  }

  scenarioCheckbox(title: string | RegExp) {
    return this.role("checkbox", { name: title });
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async fillName(name: string) {
    await this.nameInput.fill(name);
  }

  async selectScenario(title: string | RegExp) {
    const cb = this.scenarioCheckbox(title);
    if (await cb.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await cb.check();
    }
  }

  async start() {
    await this.startButton.click();
  }

  async createExecution(name: string, scenarios: (string | RegExp)[] = []) {
    await this.fillName(name);
    for (const s of scenarios) {
      await this.selectScenario(s);
    }
    await this.start();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertRedirectToDetail() {
    await expect(this.page).toHaveURL(/\/p\/[^/]+\/executions\/[^/]+$/, {
      timeout: 15_000,
    });
  }
}
