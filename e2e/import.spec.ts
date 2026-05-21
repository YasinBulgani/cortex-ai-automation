import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  loginAsAdmin,
} from "./helpers/auth";

test.describe.serial("İçe Aktarma", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Import Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("içe aktarma sayfası yüklenmeli", async ({ page, importPage }) => {
    await page.goto(`/p/${projectId}/import`);
    await importPage.assertPageLoaded();
  });

  test("dosya içe aktarma işlemi yapılabilmeli", async ({ page, importPage }) => {
    await page.goto(`/p/${projectId}/import`);

    const csvContent = "title,description,steps\nTest Senaryo,Açıklama,Adım 1|Adım 2";
    await importPage.uploadCSV(csvContent);
    await importPage.clickUpload();
    await importPage.assertImportSuccess();
  });
});
