import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class FlowsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/flows$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get newFlowButton() {
    return this.testId("flows-btn-create");
  }
  get nameInput() {
    return this.testId("flows-input-name");
  }
  get saveButton() {
    return this.testId("flows-btn-create");
  }
  get flowEditorCanvas() {
    return this.page.locator(
      "canvas, [data-testid='flow-editor'], .react-flow"
    );
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async createFlow(name: string) {
    await expect(this.page.getByTestId("flows-page")).toBeVisible({ timeout: 10_000 });
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
