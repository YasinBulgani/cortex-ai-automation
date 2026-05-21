import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, loginAsAdmin } from "./helpers/auth";
import { API_BASE } from "./config/runtime";

test.describe("Projeler", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto("/portfolio");
  });

  test("proje listesi görüntülenmeli", async ({ page, projectsPage }) => {
    await expect(page).toHaveURL(/\/portfolio/);
    await projectsPage.assertPageLoaded();
  });

  test("yeni proje oluşturulabilmeli", async ({ projectsPage }) => {
    const name = `E2E Proje ${Date.now()}`;
    await projectsPage.createProject(name);
    await projectsPage.assertProjectVisible(name);
  });

  test("projeye tıklayınca dashboard açılmalı", async ({ page, request }) => {
    const token = await getAdminToken(request);
    const name = `Dash ${Date.now()}`;
    const res = await request.post(`${API_BASE}/api/v1/tspm/projects`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { name },
    });
    const { id } = await res.json();
    await page.reload();
    await page.locator(`[data-testid='project-card-${id}']`).click();
    await expect(page).toHaveURL(new RegExp(`/p/${id}/scenarios`));
  });

  test("boş isimle proje oluşturulamamalı (UI validation)", async ({ page, projectsPage }) => {
    await projectsPage.openCreateDialog();
    await page.getByRole("button", { name: /oluştur|create/i }).last().click();
    const errorVisible =
      (await page.getByRole("alert").count()) > 0 ||
      (await page.locator("[aria-invalid='true']").count()) > 0 ||
      (await page.locator(".error, [data-error]").count()) > 0;
    expect(errorVisible).toBeTruthy();
  });

  test("var olmayan proje URL'ine gidince 404 sayfası gösterilmeli", async ({ page }) => {
    await page.goto("/p/nonexistent-project-id-00000");
    const notFound =
      (await page.getByText(/bulunamadı|not found|404/i).count()) > 0 ||
      (await page.getByRole("heading", { name: /404/i }).count()) > 0;
    expect(notFound).toBeTruthy();
  });

  test("proje API'den silinebilmeli ve listeden kalkmalı", async ({ page, request }) => {
    const token = await getAdminToken(request);
    const projectId = await apiCreateProject(request, token, `Silinecek ${Date.now()}`);

    await page.reload();
    await expect(page.locator(`[data-testid='project-card-${projectId}']`)).toBeVisible({ timeout: 10_000 });

    const del = await request.delete(`${API_BASE}/api/v1/tspm/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect([200, 204]).toContain(del.status());

    await page.reload();
    await expect(page.locator(`[data-testid='project-card-${projectId}']`)).not.toBeVisible({ timeout: 10_000 });
  });

  test("yetkisiz kullanıcı proje listesine erişememeli (API 401)", async ({ request }) => {
    const res = await request.get(`${API_BASE}/api/v1/tspm/projects`);
    expect(res.status()).toBe(401);
  });

  test("projeyi güncellemek için PUT çalışmalı (API)", async ({ request }) => {
    const token = await getAdminToken(request);
    const projectId = await apiCreateProject(request, token, `Güncelle ${Date.now()}`);
    const updated = await request.put(
      `${API_BASE}/api/v1/tspm/projects/${projectId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: { name: "Güncellenmiş İsim" },
      }
    );
    expect([200, 204]).toContain(updated.status());
    const detail = await request.get(`${API_BASE}/api/v1/tspm/projects/${projectId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect((await detail.json()).name).toBe("Güncellenmiş İsim");
  });
});
