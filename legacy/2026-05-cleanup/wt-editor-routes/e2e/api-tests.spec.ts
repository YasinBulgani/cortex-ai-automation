import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, loginAsAdmin } from "./helpers/auth";

const API = "http://127.0.0.1:8765";

test.describe.serial("API Testleri", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `APITest Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("API test sayfası yüklenmeli", async ({ page, apiTestsPage }) => {
    await page.goto(`/p/${projectId}/api-tests`);
    await apiTestsPage.assertPageLoaded();
  });

  test("yeni koleksiyon oluşturulabilmeli", async ({ page, apiTestsPage }) => {
    await page.goto(`/p/${projectId}/api-tests`);
    await apiTestsPage.createCollection("E2E Koleksiyon");
    await apiTestsPage.assertCollectionVisible("E2E Koleksiyon");
  });

  test("koleksiyona request eklenebilmeli", async ({ page, apiTestsPage, request }) => {
    await request.post(
      `${API}/api/v1/tspm/projects/${projectId}/api-tests/collections`,
      { headers: { Authorization: `Bearer ${token}` }, data: { name: "Req Col" } }
    );
    await page.goto(`/p/${projectId}/api-tests`);
    await apiTestsPage.assertCollectionVisible("Req Col");
  });
});
