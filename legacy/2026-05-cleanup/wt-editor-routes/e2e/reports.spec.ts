import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, loginAsAdmin } from "./helpers/auth";

test.describe("Raporlar sayfası", () => {
  let projectId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    const token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Raporlar ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("raporlar hub yüklenir ve başlık görünür", async ({ page, reportsPage }) => {
    await page.goto(`/p/${projectId}/reports`);
    await reportsPage.assertPageLoaded();
    await expect(page.getByText(/rapor kaynakları/i)).toBeVisible();
  });

  test("koşular sayfasına giden bağlantı var", async ({ page, reportsPage }) => {
    await page.goto(`/p/${projectId}/reports`);
    await reportsPage.gotoExecutions();
    await expect(page).toHaveURL(new RegExp(`/p/${projectId}/executions`));
  });
});
