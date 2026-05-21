import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  apiCreateScenario,
} from "./helpers/auth";
import { API_BASE } from "./config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

test.describe.serial("Koşumlar", () => {
  let projectId: string;
  let token: string;
  let scenario1Title: string;
  let scenario2Title: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Koşum Proje ${Date.now()}`);

    scenario1Title = `Koşum Senaryo A ${Date.now()}`;
    scenario2Title = `Koşum Senaryo B ${Date.now()}`;
    await apiCreateScenario(request, token, projectId, scenario1Title);
    await apiCreateScenario(request, token, projectId, scenario2Title);
    await request.dispose();
  });

  test.beforeEach(async ({ loginPage }) => {
    await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
    await loginPage.assertRedirectToProjects();
  });

  test("yeni koşum oluşturulabilmeli", async ({ page, executionsPage }) => {
    await page.goto(`/p/${projectId}/executions/new`);

    const executionName = `Koşum ${Date.now()}`;
    await executionsPage.fillName(executionName);
    await executionsPage.selectScenario(new RegExp(scenario1Title));
    await executionsPage.selectScenario(new RegExp(scenario2Title));
    await executionsPage.start();

    await executionsPage.assertRedirectToDetail();
  });

  test("koşum detayında senaryo sonuçları görünmeli", async ({ page, request }) => {
    const createRes = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/executions`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { name: `API Koşum ${Date.now()}` },
      }
    );
    const { id: execId } = await createRes.json();

    await page.goto(`/p/${projectId}/executions/${execId}`);

    await expect(page.getByText(/koşum|execution/i)).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByText(/senaryo|sonuç|result/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
