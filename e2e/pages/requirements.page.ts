import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class RequirementsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/requirements$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("requirements-page");
  }
  get newButton() {
    return this.testId("requirements-btn-new");
  }
  get createButton() {
    return this.testId("requirements-btn-create");
  }
  get form() {
    return this.testId("requirements-form");
  }
  get externalIdInput() {
    return this.testId("requirements-input-external-id");
  }
  get titleInput() {
    return this.testId("requirements-input-title");
  }
  get prioritySelect() {
    return this.testId("requirements-select-priority");
  }
  get sourceInput() {
    return this.testId("requirements-input-source");
  }
  get descInput() {
    return this.testId("requirements-input-desc");
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async openNewForm() {
    await this.newButton.click();
  }

  async fillExternalId(id: string) {
    await this.externalIdInput.fill(id);
  }

  async fillTitle(title: string) {
    await this.titleInput.fill(title);
  }

  async save() {
    await this.createButton.click();
  }

  async createRequirement(externalId: string, title: string) {
    await this.openNewForm();
    await this.fillExternalId(externalId);
    await this.fillTitle(title);
    await this.save();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 10_000 });
  }

  async assertRequirementVisible(title: string) {
    await expect(this.text(title)).toBeVisible({ timeout: 10_000 });
  }
}
