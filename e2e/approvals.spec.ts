import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  apiCreateScenario,
  apiCreateApproval,
  loginAsAdmin,
} from "./helpers/auth";
import { API_BASE } from "./config/runtime";

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

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

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
    await approvalsPage.approve();
    await approvalsPage.assertStatusApproved();
  });

  test("onay reddedilebilmeli", async ({ page, request, approvalsPage }) => {
    await apiCreateApproval(
      request, token, projectId, `Reddet ${Date.now()}`, scenarioId
    );

    await page.goto(`/p/${projectId}/approvals`);
    await approvalsPage.reject();
    await approvalsPage.assertStatusRejected();
  });

  test("zaten onaylanmış onayı tekrar onaylama engellenebilmeli (API 409/422)", async ({ request }) => {
    const id = await apiCreateApproval(
      request, token, projectId, `Tekrar Onay ${Date.now()}`, scenarioId
    );
    await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/approvals/${id}/decide`,
      {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { decision: "approved" },
      }
    );
    const second = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/approvals/${id}/decide`,
      {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { decision: "approved" },
      }
    );
    expect([409, 422, 400]).toContain(second.status());
  });

  test("yetkisiz kullanıcı onay karar veremez (API 401)", async ({ request }) => {
    const id = await apiCreateApproval(
      request, token, projectId, `Auth Onay ${Date.now()}`, scenarioId
    );
    const res = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/approvals/${id}/decide`,
      {
        headers: { "Content-Type": "application/json" },
        data: { decision: "approved" },
      }
    );
    expect(res.status()).toBe(401);
  });

  test("geçersiz karar tipi reddedilmeli (API 422)", async ({ request }) => {
    const id = await apiCreateApproval(
      request, token, projectId, `Geçersiz Karar ${Date.now()}`, scenarioId
    );
    const res = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/approvals/${id}/decide`,
      {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { decision: "invalid_decision_xyz" },
      }
    );
    expect([400, 422]).toContain(res.status());
  });

  test("onay sayfası boşken empty state göstermeli", async ({ page, request }) => {
    const emptyProjectId = await apiCreateProject(
      request, token, `Boş Onay Proje ${Date.now()}`
    );
    await page.goto(`/p/${emptyProjectId}/approvals`);
    const emptyState =
      (await page.getByText(/onay yok|henüz|empty|no approvals/i).count()) > 0 ||
      (await page.getByTestId("approvals-empty-state").count()) > 0;
    expect(emptyState).toBeTruthy();
  });

  test("onay listesi API'den sayfalanabilmeli", async ({ request }) => {
    for (let i = 0; i < 4; i++) {
      await apiCreateApproval(
        request, token, projectId, `Sayfalama Onay ${i} ${Date.now()}`, scenarioId
      );
    }
    const res = await request.get(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/approvals?limit=2&offset=0`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    const items = Array.isArray(body) ? body : body.items ?? body.data ?? body;
    expect(Array.isArray(items)).toBeTruthy();
    expect(items.length).toBeLessThanOrEqual(2);
  });
});
