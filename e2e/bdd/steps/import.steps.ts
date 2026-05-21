import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici ice aktarma sayfasindadir",
  async function (this: PlaywrightWorld) {
    const link = this.page.getByTestId("sidebar-link-import");
    if (await link.isVisible()) await link.click();
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Then(
  "ice aktarma formu goruntulenir",
  async function (this: PlaywrightWorld) {
    const form = this.page.getByTestId("import-form");
    await expect(form).toBeVisible({ timeout: 10_000 });
  },
);

When("bir test dosyasi secer", async function (this: PlaywrightWorld) {
  this.testData.fileSelected = true;
});

When("gecersiz bir dosya secer", async function (this: PlaywrightWorld) {
  this.testData.fileSelected = false;
});

Then("yukle butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("import-btn-upload", {
    role: "button",
    text: "Yükle",
  });
  await btn.click();
});

Then(
  "ice aktarma basariyla tamamlanir",
  async function (this: PlaywrightWorld) {
    const result = this.page.getByTestId("import-result");
    await expect(result).toBeVisible({ timeout: 15_000 });
  },
);
