import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ApprovalsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/approvals$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get heading() {
    return this.text("Onaylar");
  }
  get approveButton() {
    return this.testId("approvals-btn-approve");
  }
  get rejectButton() {
    return this.testId("approvals-btn-reject");
  }

  approvalItem(title: string) {
    return this.text(title);
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async approve() {
    if (!(await this.approveButton.isVisible({ timeout: 1_000 }).catch(() => false))) {
      await this.page.locator("[data-testid^='approvals-card-']").first().click();
      await expect(this.approveButton).toBeVisible({ timeout: 10_000 });
    }
    const decidePromise = this.page.waitForResponse(
      (r) =>
        r.url().includes("/approvals/") &&
        r.url().includes("/decide") &&
        r.request().method() === "POST"
    );
    await this.approveButton.click();
    const res = await decidePromise;
    expect(res.ok()).toBeTruthy();
  }

  async reject() {
    if (!(await this.rejectButton.isVisible({ timeout: 1_000 }).catch(() => false))) {
      await this.page.locator("[data-testid^='approvals-card-']").first().click();
      await expect(this.rejectButton).toBeVisible({ timeout: 10_000 });
    }
    const decidePromise = this.page.waitForResponse(
      (r) =>
        r.url().includes("/approvals/") &&
        r.url().includes("/decide") &&
        r.request().method() === "POST"
    );
    await this.rejectButton.click();
    const res = await decidePromise;
    expect(res.ok()).toBeTruthy();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertApprovalVisible(title: string) {
    await expect(this.approvalItem(title)).toBeVisible({ timeout: 10_000 });
  }

  async assertStatusApproved() {
    await expect(
      this.page.getByTestId("kanban-column-approved").locator("[data-testid^='approvals-card-']")
    ).toHaveCount(1, { timeout: 10_000 });
  }

  async assertStatusRejected() {
    await expect(
      this.page.getByTestId("kanban-column-rejected").locator("[data-testid^='approvals-card-']")
    ).toHaveCount(1, { timeout: 10_000 });
  }
}
