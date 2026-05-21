import { test, expect } from "./fixtures/pages.fixture";
import { getAdminToken } from "./helpers/auth";
import { API_BASE } from "./config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

test.describe("Projeler", () => {
  test.beforeEach(async ({ loginPage }) => {
    await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
    await loginPage.assertRedirectToProjects();
  });

  test("proje listesi görüntülenmeli", async ({ page, projectsPage }) => {
    await expect(page).toHaveURL(/\/projects/);
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
    // 2026-04 itibariyle proje kartı bir <div> (tıklanabilir değil) ve aşağıda
    // iki link var: "… ile aç" ve "Proje Özeti". Proje Özeti linki /p/{id}
    // altına götürüyor; kart içindeki bu linki tıklıyoruz.
    await page
      .locator(`[data-testid='projects-card-${id}']`)
      .getByRole("link", { name: /Proje Özeti/i })
      .click();
    await expect(page).toHaveURL(new RegExp(`/p/${id}`));
  });
});
