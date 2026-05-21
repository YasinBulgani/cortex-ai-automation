import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  apiCreateScenario,
  apiCreateApproval,
} from "./helpers/auth";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

test.describe.serial("Onaylar", () => {
  let projectId: string;
  let scenarioId: string;
  let token: string;
  let approvalId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Onay Proje ${Date.now()}`);
    scenarioId = await apiCreateScenario(request, token, projectId, "Onay Senaryo");
    approvalId = await apiCreateApproval(
      request, token, projectId, "Bekleyen Onay", scenarioId
    );
    await request.dispose();
  });

  test.beforeEach(async ({ loginPage }) => {
    await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
    await loginPage.assertRedirectToProjects();
  });

  test("onay sayfası bekleyen öğelerle yüklenmeli", async ({ page, approvalsPage }) => {
    await page.goto(`/p/${projectId}/approvals`);
    await expect(approvalsPage.heading).toBeVisible();
    await approvalsPage.assertApprovalVisible("Bekleyen Onay");
  });

  test("onay onaylanabilmeli", async ({ page, request, approvalsPage }) => {
    await apiCreateApproval(
      request, token, projectId, `Onayla ${Date.now()}`, scenarioId
    );

    await page.goto(`/p/${projectId}/approvals`);
    await page.getByText("Onayla").first().click();
    await approvalsPage.approve();
    await approvalsPage.assertStatusApproved();
  });

  test("onay reddedilebilmeli", async ({ page, request, approvalsPage }) => {
    await apiCreateApproval(
      request, token, projectId, `Reddet ${Date.now()}`, scenarioId
    );

    await page.goto(`/p/${projectId}/approvals`);
    await page.getByText("Reddet").first().click();
    await approvalsPage.reject();
    await approvalsPage.assertStatusRejected();
  });
});
