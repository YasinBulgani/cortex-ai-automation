import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, apiCreateScenario, loginAsAdmin } from "./helpers/auth";

test.describe.serial("Gereksinimler ve Kapsam", () => {
  let projectId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    const token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Req Proje ${Date.now()}`);
    await apiCreateScenario(request, token, projectId, "Req Senaryo A");
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("gereksinim sayfası yüklenmeli", async ({ page, requirementsPage }) => {
    await page.goto(`/p/${projectId}/requirements`);
    await requirementsPage.assertPageLoaded();
  });

  test("yeni gereksinim oluşturulabilmeli", async ({ page, requirementsPage }) => {
    await page.goto(`/p/${projectId}/requirements`);
    await requirementsPage.createRequirement(`REQ-${Date.now()}`, "E2E Gereksinim");
    await requirementsPage.assertRequirementVisible("E2E Gereksinim");
  });

  test("kapsam matrisi sayfası yüklenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/coverage`);
    await expect(page.getByText(/kapsam|coverage/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("kapsam yüzdesi görüntülenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/coverage`);
    await expect(page.getByText(/%/).first()).toBeVisible({ timeout: 10_000 });
  });

  test("kapsam boşlukları listesi görüntülenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/coverage`);
    await expect(page.getByText(/boşluk|gap|kapsanmayan/i).first()).toBeVisible({ timeout: 15_000 });
  });
});
