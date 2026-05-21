import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class SchedulesPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/schedules$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get page_() {
    return this.testId("schedules-page");
  }
  get newButton() {
    return this.testId("schedules-btn-new");
  }
  get nameInput() {
    return this.testId("schedules-input-name");
  }
  get cronInput() {
    return this.testId("schedules-input-cron");
  }
  get form() {
    return this.testId("schedules-form");
  }
  get createButton() {
    return this.testId("schedules-btn-create");
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async openNewForm() {
    await this.newButton.click();
  }

  async fillName(name: string) {
    await this.nameInput.fill(name);
  }

  async fillCron(cron: string) {
    await this.cronInput.fill(cron);
  }

  async save() {
    await this.createButton.click();
  }

  async createSchedule(name: string, cron: string) {
    await this.openNewForm();
    await this.fillName(name);
    await this.fillCron(cron);
    await this.save();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.page_).toBeVisible({ timeout: 10_000 });
  }

  async assertScheduleVisible(name: string) {
    await expect(this.text(name)).toBeVisible({ timeout: 10_000 });
  }
}
