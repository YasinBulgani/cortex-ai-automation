import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici projeler sayfasindadir",
  async function (this: PlaywrightWorld) {
    await this.page.goto("/projects");
    await this.page.waitForLoadState("domcontentloaded");
  },
);

Given(
  "aktif bir proje secilmistir",
  async function (this: PlaywrightWorld) {
    const projectCards = this.page.getByTestId("projects-grid").locator("a");
    const count = await projectCards.count();
    if (count > 0) {
      await projectCards.first().click();
      await this.page.waitForLoadState("domcontentloaded");
    }
    this.testData.projectSelected = count > 0;
  },
);

When("yeni proje formunu acar", async function (this: PlaywrightWorld) {
  // form is inline on projects page
});

When(
  "proje adini {string} olarak girer",
  async function (this: PlaywrightWorld, name: string) {
    const input = await this.selfHealing.findElement("projects-input-name", {
      label: "Proje Adı",
      placeholder: "Proje adı",
    });
    await input.fill(name);
  },
);

When(
  "proje aciklamasini {string} olarak girer",
  async function (this: PlaywrightWorld, description: string) {
    const input = await this.selfHealing.findElement("projects-input-desc", {
      label: "Açıklama",
      placeholder: "Proje açıklaması",
    });
    await input.fill(description);
  },
);

Then(
  "proje olustur butonuna tiklar",
  async function (this: PlaywrightWorld) {
    const btn = await this.selfHealing.findElement("projects-btn-create", {
      role: "button",
      text: "Oluştur",
    });
    await btn.click();
  },
);

Then(
  "proje basariyla olusturulur",
  async function (this: PlaywrightWorld) {
    await expect(this.page).toHaveURL(/\/p\//, { timeout: 10_000 });
  },
);

Then("proje listesi goruntulenir", async function (this: PlaywrightWorld) {
  const grid = this.page.getByTestId("projects-grid");
  await expect(grid).toBeVisible({ timeout: 10_000 });
});
