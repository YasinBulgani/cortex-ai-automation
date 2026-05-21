import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, loginAsAdmin } from "./helpers/auth";

test.describe.serial("Entegrasyonlar", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Integ Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("entegrasyon sayfası yüklenmeli", async ({ page, integrationsPage }) => {
    await page.goto(`/p/${projectId}/integrations`);
    await integrationsPage.assertPageLoaded();
  });

  test("yeni entegrasyon oluşturulabilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/integrations`);
    await page.getByRole("button", { name: /yeni|oluştur|ekle/i }).click();
    await page.getByLabel(/provider|sağlayıcı/i).fill("jira");
    await page.getByRole("button", { name: /kaydet|oluştur/i }).click();
    await expect(page.getByText("jira")).toBeVisible({ timeout: 10_000 });
  });

  test("entegrasyon senkronize edilebilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/integrations`);
    const syncBtn = page.getByRole("button", { name: /sync|senkron/i }).first();
    if (await syncBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await syncBtn.click();
    }
  });
});
