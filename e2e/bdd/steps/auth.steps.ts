import { Given, When, Then } from "@cucumber/cucumber";
import { expect } from "@playwright/test";
import { PlaywrightWorld } from "../support/world";

Given(
  "kullanici giris sayfasindadir",
  async function (this: PlaywrightWorld) {
    await this.loginPage.goto();
    await this.loginPage.waitForReady();
  },
);

Given(
  "kullanici sisteme giris yapmistir",
  async function (this: PlaywrightWorld) {
    await this.loginPage.login(
      process.env.E2E_ADMIN_EMAIL || "admin@example.com",
      process.env.E2E_ADMIN_PASSWORD || "admin123",
    );
    await this.loginPage.assertRedirectToProjects();
  },
);

When(
  "{string} emailini girer",
  async function (this: PlaywrightWorld, email: string) {
    await this.loginPage.fillEmail(email);
  },
);

When(
  "{string} sifresini girer",
  async function (this: PlaywrightWorld, password: string) {
    await this.loginPage.fillPassword(password);
  },
);

Then("giris butonuna tiklar", async function (this: PlaywrightWorld) {
  await this.loginPage.submit();
});

Then(
  "kullanici projeler sayfasina yonlendirilir",
  async function (this: PlaywrightWorld) {
    await this.loginPage.assertRedirectToProjects();
  },
);

Then("hata mesaji goruntulenir", async function (this: PlaywrightWorld) {
  await this.loginPage.assertErrorVisible();
});
