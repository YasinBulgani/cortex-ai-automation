import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  apiCreateScenario,
} from "./helpers/auth";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

test.describe.serial("Regresyon", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Regresyon Proje ${Date.now()}`);
    await apiCreateScenario(request, token, projectId, "Regresyon Senaryo A");
    await apiCreateScenario(request, token, projectId, "Regresyon Senaryo B");
    await apiCreateScenario(request, token, projectId, "Regresyon Senaryo C");
    await request.dispose();
  });

  test.beforeEach(async ({ loginPage }) => {
    await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
    await loginPage.assertRedirectToProjects();
  });

  test("regresyon seti oluşturulabilmeli", async ({ page, regressionPage }) => {
    await page.goto(`/p/${projectId}/regression`);
    const setName = `Reg Set ${Date.now()}`;
    await regressionPage.createSet(setName, 2);
    await regressionPage.assertSetVisible(setName);
  });

  test("AI önerisi çalışmalı", async ({ page, regressionPage }) => {
    await page.goto(`/p/${projectId}/regression`);
    await regressionPage.aiSuggest();
    await regressionPage.assertSuggestionVisible();
  });
});
