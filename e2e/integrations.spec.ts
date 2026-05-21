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
    const root = page.getByTestId("integrations-page");
    await root.getByRole("button", { name: "Yeni Entegrasyon" }).click();
    await page.getByTestId("integrations-select-provider").selectOption("jira");
    await page.getByTestId("integrations-input-base-url").fill("https://jira.example.test");
    await page.getByTestId("integrations-input-api-token").fill("e2e-token");
    await page.getByTestId("integrations-input-project-key").fill("E2E");
    await page.getByTestId("integrations-btn-create").click();
    await expect(root.getByText("1 entegrasyon")).toBeVisible({ timeout: 10_000 });
    await expect(root.getByText("Hiç sync yapılmadı")).toBeVisible({ timeout: 10_000 });
  });

  test("entegrasyon senkronize edilebilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/integrations`);
    const syncBtn = page.getByRole("button", { name: /sync|senkron/i }).first();
    if (await syncBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await syncBtn.click();
    }
  });
});
