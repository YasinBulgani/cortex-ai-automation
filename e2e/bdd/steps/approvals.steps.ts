import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici onaylar sayfasindadir",
  async function (this: PlaywrightWorld) {
    const link = this.page.getByTestId("sidebar-link-approvals");
    if (await link.isVisible()) await link.click();
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Then("onay listesi goruntulenir", async function (this: PlaywrightWorld) {
  const page = this.page.getByTestId("approvals-page");
  await expect(page).toBeVisible({ timeout: 10_000 });
});

Given(
  "bekleyen bir onay secilmistir",
  async function (this: PlaywrightWorld) {
    const items = this.page.getByTestId("approvals-page").locator(".space-y-2 > div, [data-testid='approvals-list'] > div");
    if ((await items.count()) > 0) {
      await items.first().click();
    }
  },
);

Then("onayla butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("approvals-btn-approve", {
    role: "button",
    text: "Onayla",
  });
  await btn.click();
});

Then(
  "onay basariyla kabul edilir",
  async function (this: PlaywrightWorld) {
    const success = this.page.getByText(/onaylandı|approved/i);
    await expect(success).toBeVisible({ timeout: 10_000 });
  },
);

Then("reddet butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("approvals-btn-reject", {
    role: "button",
    text: "Reddet",
  });
  await btn.click();
});

Then(
  "onay basariyla reddedilir",
  async function (this: PlaywrightWorld) {
    const success = this.page.getByText(/reddedildi|rejected/i);
    await expect(success).toBeVisible({ timeout: 10_000 });
  },
);
