import { test } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, loginAsAdmin } from "./helpers/auth";

test.describe("Görsel regresyon (örnek veri)", () => {
  let projectId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    const token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Görsel ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test("demo veri uyarısı ve tablo görünür", async ({ page, visualPage }) => {
    await page.goto(`/p/${projectId}/visual`);
    await visualPage.assertPageLoaded();
  });
});
