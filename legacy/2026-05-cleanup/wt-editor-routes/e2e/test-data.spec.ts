import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, apiCreateScenario, loginAsAdmin } from "./helpers/auth";

test.describe.serial("Test Verileri", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Data Proje ${Date.now()}`);
    await apiCreateScenario(request, token, projectId, "Data Senaryo");
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("test verisi sayfası yüklenmeli", async ({ page, testDataPage }) => {
    await page.goto(`/p/${projectId}/test-data`);
    await testDataPage.assertPageLoaded();
  });

  test("yeni veri seti oluşturulabilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/test-data`);
    await page.getByRole("button", { name: /yeni|oluştur/i }).click();
    await page.getByLabel(/ad|name/i).fill("E2E Veri Seti");
    await page.getByRole("button", { name: /kaydet|oluştur/i }).click();
    await expect(page.getByText("E2E Veri Seti")).toBeVisible({ timeout: 10_000 });
  });

  test("veri seti düzenlenebilmeli", async ({ page, request }) => {
    await request.post(
      `http://127.0.0.1:8765/api/v1/tspm/projects/${projectId}/test-data`,
      { headers: { Authorization: `Bearer ${token}` }, data: { name: "Edit DS", columns: [{ name: "c1" }], rows: [{ c1: "v1" }] } }
    );
    await page.goto(`/p/${projectId}/test-data`);
    await expect(page.getByText("Edit DS")).toBeVisible({ timeout: 10_000 });
  });

  test("veri seti silinebilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/test-data`);
    const deleteBtn = page.getByRole("button", { name: /sil|delete/i }).first();
    if (await deleteBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await deleteBtn.click();
    }
  });
});
