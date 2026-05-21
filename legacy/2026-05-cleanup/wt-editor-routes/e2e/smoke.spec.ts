import { test, expect } from "./fixtures/pages.fixture";
import { API_BASE } from "./config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

const API = API_BASE;

test.use({ storageState: { cookies: [], origins: [] } });

test.describe.serial("TSPM smoke", () => {
  const email = ADMIN_EMAIL;
  const password = ADMIN_PASSWORD;

  test("login, proje, senaryo, onay", async ({ page, request, loginPage }) => {
    await loginPage.login(email, password);
    await loginPage.assertRedirectToProjects();

    const loginApi = await request.post(`${API}/api/v1/auth/login`, {
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({ email, password }),
    });
    expect(loginApi.ok()).toBeTruthy();
    const { access_token: token } = await loginApi.json() as { access_token: string };
    expect(token).toBeTruthy();

    if (page.url().includes("/onboarding")) {
      await page.getByPlaceholder("ör. Ödeme API, Mobil Uygulama…").fill("E2E Proje");
      await page.getByRole("button", { name: /Proje Oluştur/i }).click();
      await expect(page.getByText(/oluşturuldu/i).first()).toBeVisible({ timeout: 15_000 });
      await page.getByRole("button", { name: /Kurulumu atla, doğrudan panele git/i }).click();
      await expect(page).toHaveURL(/\/p\/[^/]+$/, { timeout: 15_000 });
    } else {
      const created = await request.post(`${API}/api/v1/tspm/projects`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        data: JSON.stringify({
          name: "E2E Proje",
          description: "Smoke",
        }),
      });
      expect(created.ok()).toBeTruthy();
      const project = (await created.json()) as { id: string };
      await page.goto(`/p/${project.id}`);
      await expect(page).toHaveURL(new RegExp(`/p/${project.id}$`));
    }

    const projectUrl = page.url();
    const projectId = projectUrl.match(/\/p\/([^/]+)/)?.[1];
    expect(projectId).toBeTruthy();

    const appr = await request.post(`${API}/api/v1/tspm/projects/${projectId}/approvals`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: JSON.stringify({
        source_text: "Gereksinim: ödeme akışı test edilmeli.",
        draft_payload: {
          title: "Ödeme E2E",
          description: "Smoke",
          steps: [{ order: 0, text: "Giriş yap" }],
        },
      }),
    });
    expect(appr.ok()).toBeTruthy();
    const approval = (await appr.json()) as { id: string };

    await page.goto(`/p/${projectId}/scenarios/new`);
    await page.getByTestId("scenario-form-input-title").fill("Manuel senaryo");
    await page.getByTestId("scenario-form-btn-save").click();
    await expect(page).toHaveURL(/\/p\/[^/]+\/scenarios\/[^/]+$/);

    await page.goto(`/p/${projectId}/approvals`);
    await expect(page.getByTestId(`approvals-card-${approval.id}`)).toBeVisible({ timeout: 15_000 });
    await page.getByTestId(`approvals-card-${approval.id}`).click();
    const decidePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/approvals/") && r.url().includes("/decide") && r.request().method() === "POST"
    );
    await page.getByTestId("approvals-btn-approve").click();
    const decideRes = await decidePromise;
    expect(decideRes.ok()).toBeTruthy();

    await page.goto(`/p/${projectId}/scenarios`);
    await expect(page.getByRole("link", { name: "Ödeme E2E" })).toBeVisible({ timeout: 15_000 });
  });
});
