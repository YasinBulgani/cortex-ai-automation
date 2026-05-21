import { test, expect } from "./fixtures/pages.fixture";
import { loginAsAdmin, getAdminToken, apiCreateProject, apiCreateScenario } from "./helpers/auth";
import { API_BASE } from "./config/runtime";

test.describe.serial("Senaryo Versiyonları", () => {
  let projectId: string;
  let scenarioId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Version Proje ${Date.now()}`);
    scenarioId = await apiCreateScenario(request, token, projectId, "V1 Senaryo");
    await request.put(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios/${scenarioId}`,
      { headers: { Authorization: `Bearer ${token}` }, data: { title: "V2 Senaryo" } }
    );
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("versiyon geçmişi sayfası yüklenmeli", async ({ page, scenarioVersionsPage }) => {
    await page.goto(`/p/${projectId}/scenarios/${scenarioId}/versions`);
    await scenarioVersionsPage.assertPageLoaded();
  });

  test("önceki versiyon bilgileri görünmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/scenarios/${scenarioId}/versions`);
    await expect(page.getByText(/V1 Senaryo|1/).first()).toBeVisible({ timeout: 10_000 });
  });

  test("senaryo düzenleme sayfası yüklenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/scenarios/edit/${scenarioId}`);
    await expect(page.getByText(/düzenle|edit|senaryo/i).first()).toBeVisible({ timeout: 10_000 });
  });
});
