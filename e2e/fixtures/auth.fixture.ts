import { test as base, expect } from "@playwright/test";
import { LoginPage } from "../pages/login.page";
import { ADMIN_EMAIL, ADMIN_PASSWORD, API_BASE } from "../config/runtime";

type AuthFixtures = {
  authenticatedPage: ReturnType<typeof base["extend"]> extends infer T ? T : never;
  adminToken: string;
};

/**
 * Authenticated fixture — storageState ile login durumunu paylaşır.
 * Her test suite'in başında bir kez login olur, sonraki testler cookie/localStorage'dan devam eder.
 */
export const test = base.extend<AuthFixtures>({
  adminToken: async ({ playwright }, use) => {
    const request = await playwright.request.newContext();
    const res = await request.post(`${API_BASE}/api/v1/auth/login`, {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    });
    const body = await res.json();
    await request.dispose();
    await use(body.access_token);
  },

  storageState: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    const loginPage = new LoginPage(page);
    await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
    await loginPage.assertRedirectToProjects();

    const storage = await context.storageState();
    await context.close();

    await use(storage as any);
  },
});

export { expect } from "@playwright/test";

export { ADMIN_EMAIL, ADMIN_PASSWORD, API_BASE as API };
