import { test, expect } from "./fixtures/pages.fixture";
import {
  getAdminToken,
  apiCreateProject,
  apiCreateScenario,
  loginAsAdmin,
} from "./helpers/auth";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";
import { API_BASE } from "./config/runtime";

test.describe.serial("Senaryolar", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Senaryo Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  // ── Happy path ──────────────────────────────────────────────────────────

  test("yeni senaryo oluşturulabilmeli", async ({ page, scenarioFormPage }) => {
    await page.goto(`/p/${projectId}/scenarios/new`);
    const title = `Test Senaryo ${Date.now()}`;
    await scenarioFormPage.createScenario(title);
    await scenarioFormPage.assertRedirectToDetail();

    await page.goto(`/p/${projectId}/scenarios`);
    await expect(page.getByText(title)).toBeVisible({ timeout: 10_000 });
  });

  test("senaryo düzenlenebilmeli", async ({ page, request }) => {
    const scenarioId = await apiCreateScenario(
      request, token, projectId, `Düzenle ${Date.now()}`
    );
    await page.goto(`/p/${projectId}/scenarios/edit/${scenarioId}`);
    const newTitle = `Güncellendi ${Date.now()}`;

    await page.getByLabel("Başlık").clear();
    await page.getByLabel("Başlık").fill(newTitle);
    await page.getByRole("button", { name: "Kaydet" }).click();

    await page.goto(`/p/${projectId}/scenarios`);
    await expect(page.getByText(newTitle)).toBeVisible({ timeout: 10_000 });
  });

  test("senaryo aranabilmeli", async ({ page, scenariosListPage, request }) => {
    const unique = `Arama${Date.now()}`;
    await apiCreateScenario(request, token, projectId, unique);
    await apiCreateScenario(request, token, projectId, "DiğerSenaryo");

    await page.goto(`/p/${projectId}/scenarios`);
    await scenariosListPage.search(unique);

    await scenariosListPage.assertScenarioVisible(unique);
    await scenariosListPage.assertScenarioHidden("DiğerSenaryo");
  });

  test("toplu silme yapılabilmeli", async ({ page, scenariosListPage, request }) => {
    const s1 = `Sil1_${Date.now()}`;
    const s2 = `Sil2_${Date.now()}`;
    await apiCreateScenario(request, token, projectId, s1);
    await apiCreateScenario(request, token, projectId, s2);

    await page.goto(`/p/${projectId}/scenarios`);
    await expect(page.getByText(s1)).toBeVisible({ timeout: 10_000 });

    await scenariosListPage.selectScenario(new RegExp(s1));
    await scenariosListPage.selectScenario(new RegExp(s2));
    await scenariosListPage.bulkDelete();

    await scenariosListPage.assertScenarioHidden(s1);
    await scenariosListPage.assertScenarioHidden(s2);
  });

  test("senaryo klonlanabilmeli (API)", async ({ request }) => {
    const sid = await apiCreateScenario(request, token, projectId, `Klon Kaynak ${Date.now()}`);
    const res = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios/${sid}/clone`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.title).toContain("(kopya)");
    expect(body.status).toBe("draft");
    expect(body.id).not.toBe(sid);
  });

  test("senaryolar tag ile filtrelenebilmeli (API)", async ({ request }) => {
    await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios`,
      {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { title: `TagSmoke ${Date.now()}`, tags: ["smoke"] },
      }
    );
    await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios`,
      {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        data: { title: `TagReg ${Date.now()}`, tags: ["regression"] },
      }
    );
    const res = await request.get(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios?tag=smoke`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect(res.ok()).toBeTruthy();
    const scenarios = await res.json();
    for (const s of scenarios) {
      expect(s.tags).toContain("smoke");
    }
  });

  // ── Negative / edge case ─────────────────────────────────────────────────

  test("boş başlıkla senaryo oluşturulamamalı (UI validation)", async ({ page, scenarioFormPage }) => {
    await page.goto(`/p/${projectId}/scenarios/new`);
    await page.getByTestId("scenario-form-btn-save").click();
    // Form submit engellenmiş olmalı — URL değişmemeli, hata mesajı gösterilmeli
    await expect(page).not.toHaveURL(/\/scenarios\/[^/new][^/]+$/);
    const errorVisible =
      (await page.getByRole("alert").count()) > 0 ||
      (await page.locator("[aria-invalid='true']").count()) > 0;
    expect(errorVisible).toBeTruthy();
  });

  test("yetkisiz istek senaryoya erişememeli (API 401)", async ({ request }) => {
    const sid = await apiCreateScenario(request, token, projectId, `Auth Test ${Date.now()}`);
    const res = await request.get(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios/${sid}`
    );
    expect(res.status()).toBe(401);
  });

  test("var olmayan senaryo sayfasına gidince 404 gösterilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/scenarios/nonexistent-id-00000`);
    const notFound =
      (await page.getByText(/bulunamadı|not found|404/i).count()) > 0 ||
      (await page.getByRole("heading", { name: /404/i }).count()) > 0;
    expect(notFound).toBeTruthy();
  });

  test("başka projenin senaryosuna erişilememeli (API 403/404)", async ({ request }) => {
    const otherProjectId = await apiCreateProject(request, token, `Diğer Proje ${Date.now()}`);
    const otherScenarioId = await apiCreateScenario(
      request, token, otherProjectId, `Diğer Senaryo ${Date.now()}`
    );
    // Birinci projenin URL'siyle diğer projenin senaryosuna istek
    const res = await request.get(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios/${otherScenarioId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    expect([403, 404]).toContain(res.status());
  });
});
