import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  loginAsAdmin,
} from "./helpers/auth";
import { API_BASE } from "./config/runtime";

test.describe.serial("Akışlar", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Akış Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("yeni akış oluşturulabilmeli", async ({ page, flowsPage }) => {
    await page.goto(`/p/${projectId}/flows`);
    const flowName = `Test Akış ${Date.now()}`;
    await flowsPage.createFlow(flowName);
    await flowsPage.assertFlowVisible(flowName);
  });

  test("akış editörü yüklenmeli", async ({ page, request, flowsPage }) => {
    const flowRes = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/flows`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { name: `Editör Akış ${Date.now()}`, steps: [] },
      }
    );
    const { id: flowId } = await flowRes.json();

    await page.goto(`/p/${projectId}/flows/${flowId}`);

    await expect(
      page.getByText(/akış|flow|editör|editor/i).first()
    ).toBeVisible({ timeout: 10_000 });

    await flowsPage.assertEditorLoaded();
  });
});
