import { test as baseTest } from "@playwright/test";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";

/**
 * Custom test fixtures for authentication tests
 * Provides pre-configured page objects and setup
 */

type AuthTestFixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  authenticatedPage: void; // Sets up authenticated session
};

export const test = baseTest.extend<AuthTestFixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  dashboardPage: async ({ page }, use) => {
    const dashboardPage = new DashboardPage(page);
    await use(dashboardPage);
  },

  authenticatedPage: async ({ page }, use) => {
    // Navigate to login page
    await page.goto("http://localhost:3000/login");

    // Get page ready
    await page.waitForSelector('[data-ui-ready="true"]', { timeout: 10000 }).catch(() => {
      // Some pages might not have this attribute
    });

    // Login with test credentials
    const emailInput = page.locator('[data-testid="login-input-email"]');
    const passwordInput = page.locator('[data-testid="login-input-password"]');
    const submitButton = page.locator('[data-testid="login-btn-submit"]');

    await emailInput.fill("test@test.com");
    await passwordInput.fill("test");
    await submitButton.click();

    // Wait for navigation
    await page.waitForURL(/.*/, { timeout: 10000 });

    // Verify we're logged in (not on login page)
    if (page.url().includes("/login")) {
      throw new Error("Failed to authenticate with test credentials");
    }

    await use();
  },
});

export { expect } from "@playwright/test";
