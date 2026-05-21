import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici senaryolar sayfasindadir",
  async function (this: PlaywrightWorld) {
    await expect(
      this.page.getByTestId("scenarios-page"),
    ).toBeVisible({ timeout: 10_000 }).catch(async () => {
      const link = this.page.getByTestId("sidebar-link-scenarios");
      if (await link.isVisible()) await link.click();
      await this.page.waitForLoadState("domcontentloaded");
    });
  },
);

When(
  "yeni senaryo butonuna tiklar",
  async function (this: PlaywrightWorld) {
    const btn = await this.selfHealing.findElement("scenarios-btn-new", {
      role: "button",
      text: "Yeni Senaryo",
    });
    await btn.click();
  },
);

When(
  "senaryo basligini {string} olarak girer",
  async function (this: PlaywrightWorld, title: string) {
    const input = await this.selfHealing.findElement(
      "scenario-form-input-title",
      {
        label: "Başlık",
        placeholder: "Senaryo başlığı",
      },
    );
    await input.fill(title);
  },
);

Then("kaydet butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement("scenario-form-btn-save", {
    role: "button",
    text: "Kaydet",
  });
  await btn.click();
});

Then(
  "senaryo basariyla olusturulur",
  async function (this: PlaywrightWorld) {
    await expect(this.page).toHaveURL(/\/scenarios\//, { timeout: 10_000 });
  },
);

When(
  "arama kutusuna {string} yazar",
  async function (this: PlaywrightWorld, query: string) {
    const input = await this.selfHealing.findElement(
      "scenarios-input-search",
      { placeholder: "Ara" },
    );
    await input.fill(query);
  },
);

Then(
  "filtrelenmis senaryo listesi goruntulenir",
  async function (this: PlaywrightWorld) {
    await this.page.waitForTimeout(500);
    const table = this.page.getByTestId("scenarios-table");
    await expect(table).toBeVisible({ timeout: 10_000 });
  },
);

Given(
  "mevcut bir senaryo secilmistir",
  async function (this: PlaywrightWorld) {
    const rows = this.page.getByTestId("scenarios-table").locator("tbody tr");
    const count = await rows.count();
    if (count > 0) {
      await rows.first().click();
      await this.page.waitForLoadState("domcontentloaded");
    }
  },
);

Then("sil butonuna tiklar", async function (this: PlaywrightWorld) {
  const btn = await this.selfHealing.findElement(
    "scenario-detail-btn-delete",
    {
      role: "button",
      text: "Sil",
    },
  );
  await btn.click();
});

Then(
  "silme onay dialogu goruntulenir",
  async function (this: PlaywrightWorld) {
    const dialog = this.page.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 5_000 });
  },
);
