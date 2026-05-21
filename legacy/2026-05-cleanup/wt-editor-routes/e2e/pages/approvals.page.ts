import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ApprovalsPage extends BasePage {
  readonly url: RegExp = /\/p\/[^/]+\/approvals$/;

  // ── Locators ───────────────────────────────────────────────────────────────
  get heading() {
    return this.text("Onaylar");
  }
  get approveButton() {
    return this.role("button", { name: "Onayla" });
  }
  get rejectButton() {
    return this.role("button", { name: "Reddet" });
  }

  approvalItem(title: string) {
    return this.text(title);
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async approve() {
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
    await expect(this.text(/onaylandı|approved/i)).toBeVisible({ timeout: 10_000 });
  }

  async assertStatusRejected() {
    await expect(this.text(/reddedildi|rejected/i)).toBeVisible({ timeout: 10_000 });
  }
}
