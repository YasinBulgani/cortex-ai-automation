import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici regresyon sayfasindadir",
  async function (this: PlaywrightWorld) {
    const link = this.page.getByTestId("sidebar-link-regression");
    if (await link.isVisible()) await link.click();
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Then(
  "regresyon seti listesi goruntulenir",
  async function (this: PlaywrightWorld) {
    const page = this.page.getByTestId("regression-page");
    await expect(page).toBeVisible({ timeout: 10_000 });
  },
);

When(
  "set adini {string} olarak girer",
  async function (this: PlaywrightWorld, name: string) {
    const input = await this.selfHealing.findElement("regression-input-name", {
      label: "Set Adı",
      placeholder: "Set adı",
    });
    await input.fill(name);
  },
);

Then("set olustur butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("regression-btn-create", {
    role: "button",
    text: "Oluştur",
  });
  await btn.click();
});

Then(
  "regresyon seti basariyla olusturulur",
  async function (this: PlaywrightWorld) {
    await expect(this.page).toHaveURL(/\/regression/, { timeout: 10_000 });
  },
);

Then("AI oner butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("regression-btn-suggest", {
    role: "button",
    text: "AI Önerisi",
  });
  await btn.click();
});

Then("AI onerisi goruntulenir", async function (this: PlaywrightWorld) {
  await this.page.waitForTimeout(2000);
  const suggestion = this.page.getByText(/önerilen|suggested|öneri/i);
  await expect(suggestion).toBeVisible({ timeout: 15_000 });
});
