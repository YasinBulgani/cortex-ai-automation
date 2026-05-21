import { expect, type Locator } from "@playwright/test";
import { BasePage } from "./base.page";

export class IntegrationsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/integrations$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get heading() {
    return this.text(/entegrasyon|integration/i).first();
  }

  integrationCard(name: string): Locator {
    return this.text(name);
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.heading).toBeVisible({ timeout: 10_000 });
  }

  async assertIntegrationVisible(name: string) {
    await expect(this.integrationCard(name)).toBeVisible({ timeout: 10_000 });
  }
}
