import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici kosular sayfasindadir",
  async function (this: PlaywrightWorld) {
    const link = this.page.getByTestId("sidebar-link-executions");
    if (await link.isVisible()) await link.click();
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Then("kosu listesi goruntulenir", async function (this: PlaywrightWorld) {
  const page = this.page.getByTestId("executions-page");
  await expect(page).toBeVisible({ timeout: 10_000 });
});

When("yeni kosu butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("executions-btn-new", {
    role: "button",
    text: "Yeni Koşu",
  });
  await btn.click();
});

When(
  "kosu adini {string} olarak girer",
  async function (this: PlaywrightWorld, name: string) {
    const input = this.page.getByPlaceholder(/koşu adı|run name/i);
    await input.fill(name);
  },
);

Then("kosu baslat butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = this.page.getByRole("button", { name: /başlat|start/i });
  await btn.click();
});

Then(
  "kosu basariyla olusturulur",
  async function (this: PlaywrightWorld) {
    await expect(this.page).toHaveURL(/\/executions\//, { timeout: 10_000 });
  },
);

Given(
  "mevcut bir kosu secilmistir",
  async function (this: PlaywrightWorld) {
    const table = this.page.getByTestId("executions-table");
    const rows = table.locator("tbody tr");
    if ((await rows.count()) > 0) {
      await rows.first().click();
    }
  },
);

Then(
  "kosu detay sayfasi goruntulenir",
  async function (this: PlaywrightWorld) {
    await expect(this.page).toHaveURL(/\/executions\//, { timeout: 10_000 });
  },
);
