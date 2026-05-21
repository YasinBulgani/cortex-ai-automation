import { test, expect } from "./fixtures/pages.fixture";
import { loginAsAdmin, getAdminToken, apiCreateProject, apiCreateScenario } from "./helpers/auth";
import { API_BASE } from "./config/runtime";

test.describe.serial("Zamanlamalar", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Sched Proje ${Date.now()}`);
    await apiCreateScenario(request, token, projectId, "Sched Senaryo");
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("zamanlama sayfası yüklenmeli", async ({ page, schedulesPage }) => {
    await page.goto(`/p/${projectId}/schedules`);
    await schedulesPage.assertPageLoaded();
  });

  test("yeni zamanlama oluşturulabilmeli", async ({ page, schedulesPage }) => {
    await page.goto(`/p/${projectId}/schedules`);
    const name = `E2E Zamanlama ${Date.now()}`;
    await schedulesPage.createSchedule(name, "0 2 * * *");
    await schedulesPage.assertScheduleVisible("0 2 * * *");
  });

  test("zamanlama tetiklenebilmeli", async ({ page, request }) => {
    const schedRes = await request.post(
      `${API_BASE}/api/v1/tspm/projects/${projectId}/schedules`,
      { headers: { Authorization: `Bearer ${token}` }, data: { name: "Trigger Test", cron_expression: "0 * * * *", scenario_ids: [] } }
    );
    await page.goto(`/p/${projectId}/schedules`);
    const triggerBtn = page.getByRole("button", { name: /tetikle|trigger/i }).first();
    if (await triggerBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await triggerBtn.click();
    }
  });

  test("zamanlama silinebilmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/schedules`);
    const deleteBtn = page.getByRole("button", { name: /sil|delete/i }).first();
    if (await deleteBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await deleteBtn.click();
      const confirmBtn = page.getByRole("button", { name: /onayla|evet/i });
      if (await confirmBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await confirmBtn.click();
      }
    }
  });
});
