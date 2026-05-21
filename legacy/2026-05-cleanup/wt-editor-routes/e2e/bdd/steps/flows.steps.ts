import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici akislar sayfasindadir",
  async function (this: PlaywrightWorld) {
    const link = this.page.getByTestId("sidebar-link-flows");
    if (await link.isVisible()) await link.click();
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Then("akis listesi goruntulenir", async function (this: PlaywrightWorld) {
  const page = this.page.getByTestId("flows-page");
  await expect(page).toBeVisible({ timeout: 10_000 });
});

When("yeni akis butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("flows-btn-create", {
    role: "button",
    text: "Yeni Akış",
  });
  await btn.click();
});

When(
  "akis adini {string} olarak girer",
  async function (this: PlaywrightWorld, name: string) {
    const input = await this.selfHealing.findElement("flows-input-name", {
      label: "Akış Adı",
      placeholder: "Akış adı",
    });
    await input.fill(name);
  },
);

Then("akis olustur butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("flows-btn-create", {
    role: "button",
    text: "Oluştur",
  });
  await btn.click();
});

Then(
  "akis basariyla olusturulur",
  async function (this: PlaywrightWorld) {
    await expect(this.page).toHaveURL(/\/flows\//, { timeout: 10_000 });
  },
);
