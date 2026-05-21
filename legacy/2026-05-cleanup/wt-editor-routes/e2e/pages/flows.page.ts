import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class FlowsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/flows$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get newFlowButton() {
    return this.role("button", { name: /yeni akış|oluştur/i });
  }
  get nameInput() {
    return this.label("Ad");
  }
  get saveButton() {
    return this.role("button", { name: "Kaydet" });
  }
  get flowEditorCanvas() {
    return this.page.locator(
      "canvas, [data-testid='flow-editor'], .react-flow"
    );
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async createFlow(name: string) {
    await this.newFlowButton.click();
    await this.nameInput.fill(name);
    await this.saveButton.click();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertFlowVisible(name: string) {
    await expect(this.text(name)).toBeVisible({ timeout: 10_000 });
  }

  async assertEditorLoaded() {
    await expect(this.flowEditorCanvas.first()).toBeVisible({ timeout: 10_000 });
  }
}
