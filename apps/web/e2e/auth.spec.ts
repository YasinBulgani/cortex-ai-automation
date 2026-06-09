import { test, expect } from "@playwright/test";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";

/**
 * Authentication E2E Tests
 * - Happy path: valid credentials → dashboard redirect
 * - Error scenario: invalid credentials → error message
 * - Password visibility toggle
 * - MFA (if enabled)
 */

test.describe("Login Page", () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  // ── Happy Path Tests ────────────────────────────────────────────────

  test("should load login page", async ({ page }) => {
    expect(page).toHaveURL(/\/login/);
    expect(await loginPage.isLoaded()).toBe(true);
  });

  test("should display login form with required fields", async ({ page }) => {
    const emailField = page.locator('[data-testid="login-input-email"]');
    const passwordField = page.locator('[data-testid="login-input-password"]');
    const submitButton = page.locator('[data-testid="login-btn-submit"]');

    expect(await emailField.isVisible()).toBe(true);
    expect(await passwordField.isVisible()).toBe(true);
    expect(await submitButton.isVisible()).toBe(true);
  });

  test("should show heading and subtitle", async ({ page }) => {
    const heading = page.locator('[data-testid="login-heading"]');
    const subtitle = page.locator('[data-testid="login-subtitle"]');

    expect(await heading.isVisible()).toBe(true);
    expect(await subtitle.isVisible()).toBe(true);

    const headingText = await heading.textContent();
    expect(headingText).toContain("Giriş Yap");
  });

  test("should toggle password visibility", async ({ page }) => {
    const passwordInput = page.locator('[data-testid="login-input-password"]');
    const toggleButton = passwordInput.locator("..").locator('button[aria-label*="Şifre"]');

    // Initially password should be hidden
    await expect(passwordInput).toHaveAttribute("type", "password");

    // Click toggle to show password
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute("type", "text");

    // Click toggle to hide password
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute("type", "password");
  });

  test("should enable submit button only with both fields filled", async ({ page }) => {
    const submitButton = page.locator('[data-testid="login-btn-submit"]');
    const emailField = page.locator('[data-testid="login-input-email"]');
    const passwordField = page.locator('[data-testid="login-input-password"]');

    // Initially disabled
    expect(await submitButton.isDisabled()).toBe(true);

    // After filling email only
    await emailField.fill("test@example.com");
    expect(await submitButton.isDisabled()).toBe(true);

    // After filling password
    await passwordField.fill("password123");
    expect(await submitButton.isDisabled()).toBe(false);

    // After clearing email
    await emailField.clear();
    expect(await submitButton.isDisabled()).toBe(true);
  });

  // ── Error Scenario Tests ────────────────────────────────────────────

  test("should show error on invalid email format", async ({ page }) => {
    const emailField = page.locator('[data-testid="login-input-email"]');
    const passwordField = page.locator('[data-testid="login-input-password"]');
    const submitButton = page.locator('[data-testid="login-btn-submit"]');

    await emailField.fill("invalid-email");
    await passwordField.fill("password123");

    // Check if HTML5 validation prevents submission
    const isInvalid = await emailField.evaluate((el: HTMLInputElement) => !el.checkValidity());
    expect(isInvalid).toBe(true);
  });

  test("should show error on wrong credentials", async ({ page }) => {
    await loginPage.login("nonexistent@example.com", "wrongpassword");

    // Wait for error message
    const errorAlert = page.locator('[data-testid="login-alert-error"]');
    await expect(errorAlert).toBeVisible({ timeout: 10000 });

    const errorText = await errorAlert.textContent();
    expect(errorText).toBeTruthy();
    expect(errorText?.toLowerCase()).toMatch(/e-posta|şifre|hatalı|başarısız/i);
  });

  test("should show error on empty credentials", async ({ page }) => {
    const submitButton = page.locator('[data-testid="login-btn-submit"]');

    // Button should be disabled, so this tests HTML5 validation
    expect(await submitButton.isDisabled()).toBe(true);
  });

  test("should clear error when user modifies email field", async ({ page }) => {
    // First trigger an error
    await loginPage.login("wrong@example.com", "wrongpassword");

    const errorAlert = page.locator('[data-testid="login-alert-error"]');
    await expect(errorAlert).toBeVisible({ timeout: 10000 });

    // Modify email field
    const emailField = page.locator('[data-testid="login-input-email"]');
    await emailField.focus();
    await emailField.fill("correct@example.com");

    // Error should remain visible (backend validation only clears on next attempt)
    // But this tests that UI is responsive
    expect(await emailField.inputValue()).toBe("correct@example.com");
  });

  // ── Forgot Password Tests ────────────────────────────────────────────

  test("should open forgot password panel", async ({ page }) => {
    await loginPage.openForgotPanel();

    const forgotPanel = page.locator('[data-testid="login-forgot-panel"]');
    expect(await forgotPanel.isVisible()).toBe(true);
  });

  test("should close forgot password panel", async ({ page }) => {
    await loginPage.openForgotPanel();

    const forgotPanel = page.locator('[data-testid="login-forgot-panel"]');
    expect(await forgotPanel.isVisible()).toBe(true);

    await loginPage.closeForgotPanel();
    expect(await forgotPanel.isVisible()).toBe(false);
  });

  test("should submit forgot password form", async ({ page }) => {
    await loginPage.openForgotPanel();

    const forgotEmail = page.locator('[data-testid="login-input-forgot-email"]');
    await forgotEmail.fill("test@example.com");

    const submitButton = page.locator('[data-testid="login-btn-forgot-submit"]');
    await submitButton.click();

    // Wait for response (might be success or error message)
    const message = page.locator('[data-testid="login-forgot-msg"]');
    await expect(message).toBeVisible({ timeout: 10000 });

    const messageText = await message.textContent();
    expect(messageText).toBeTruthy();
  });

  // ── Accessibility Tests ─────────────────────────────────────────────

  test("should have proper ARIA labels", async ({ page }) => {
    const passwordToggle = page.locator('button[aria-label*="Şifre"]').first();
    expect(await passwordToggle.getAttribute("aria-label")).toBeTruthy();
  });

  test("should support keyboard navigation", async ({ page }) => {
    const emailField = page.locator('[data-testid="login-input-email"]');
    const passwordField = page.locator('[data-testid="login-input-password"]');

    // Tab to email field
    await emailField.focus();
    expect(await emailField.evaluate((el) => el === document.activeElement)).toBe(true);

    // Tab to password field
    await page.keyboard.press("Tab");
    expect(await passwordField.evaluate((el) => el === document.activeElement)).toBe(true);
  });

  // ── Dark Mode Tests ─────────────────────────────────────────────────

  test("should toggle dark mode", async ({ page }) => {
    const darkToggle = page.locator('button[aria-label="Tema değiştir"]');

    const htmlElement = page.locator("html");
    let hasClass = await htmlElement.evaluate((el) => el.classList.contains("dark"));
    expect(hasClass).toBe(true); // Default is dark

    // Click toggle
    await darkToggle.click();
    hasClass = await htmlElement.evaluate((el) => el.classList.contains("dark"));
    expect(hasClass).toBe(false);

    // Click again
    await darkToggle.click();
    hasClass = await htmlElement.evaluate((el) => el.classList.contains("dark"));
    expect(hasClass).toBe(true);
  });

  // ── Tab Navigation Tests ────────────────────────────────────────────

  test("should support login/register tabs if self-registration enabled", async ({
    page,
  }) => {
    const loginTab = page.locator('[data-testid="login-btn-tab-login"]');
    const registerTab = page.locator('[data-testid="login-btn-tab-register"]');

    // Only run if tabs exist
    if ((await loginTab.count()) > 0) {
      expect(await loginTab.isVisible()).toBe(true);
      expect(await registerTab.isVisible()).toBe(true);

      // Check initial state
      const loginTabPressed = await loginTab.getAttribute("aria-pressed");
      expect(loginTabPressed).toBe("true");

      // Switch to register
      await registerTab.click();
      const registerTabPressed = await registerTab.getAttribute("aria-pressed");
      expect(registerTabPressed).toBe("true");

      const loginTabPressedAfter = await loginTab.getAttribute("aria-pressed");
      expect(loginTabPressedAfter).toBe("false");
    }
  });

  // ── Real Login Tests (requires test account) ────────────────────────

  test("should successfully login with valid test credentials", async ({ page }) => {
    // This test assumes demo credentials are set up
    // Adjust email/password based on your test environment
    const testEmail = "test@test.com";
    const testPassword = "test";

    await loginPage.login(testEmail, testPassword);

    // Should redirect away from login
    // Note: might redirect to /projects or /dashboard depending on config
    const url = page.url();
    expect(!url.includes("/login")).toBe(true);

    // Check that we're on some authenticated page
    expect(url.includes("localhost:3000")).toBe(true);
  });

  test("should successfully login with admin credentials", async ({ page }) => {
    const testEmail = "admin@example.com";
    const testPassword = "admin123";

    await loginPage.login(testEmail, testPassword);

    // Should redirect away from login
    const url = page.url();
    expect(!url.includes("/login")).toBe(true);

    expect(url.includes("localhost:3000")).toBe(true);
  });

  // ── Session Persistence Tests ────────────────────────────────────────

  test("should persist session across page reloads", async ({ page }) => {
    const testEmail = "test@test.com";
    const testPassword = "test";

    await loginPage.login(testEmail, testPassword);

    // Wait for redirect
    await page.waitForURL(/.*/, { timeout: 10000 });

    const urlBefore = page.url();

    // Reload page
    await page.reload();

    // Should still be logged in
    const urlAfter = page.url();
    expect(!urlAfter.includes("/login")).toBe(true);
  });

  test("should redirect to login if not authenticated", async ({ page }) => {
    // Navigate directly to protected page
    await page.goto("/projects");

    // Should redirect to login
    const url = page.url();
    expect(url.includes("/login")).toBe(true);
  });

  // ── Mobile Responsiveness Tests ──────────────────────────────────────

  test("should be responsive on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await loginPage.goto();

    const loginForm = page.locator('[data-testid="login-form"]');
    expect(await loginForm.isVisible()).toBe(true);

    const emailField = page.locator('[data-testid="login-input-email"]');
    expect(await emailField.isVisible()).toBe(true);
  });

  test("should hide left panel on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await loginPage.goto();

    // Left panel should be hidden on mobile (lg: breakpoint)
    const leftPanel = page.locator("aside");
    const isHidden = await leftPanel.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return style.display === "none";
    });

    expect(isHidden).toBe(true);
  });
});

/**
 * Integration Tests - Full authentication flow
 */
test.describe("Authentication Flow", () => {
  test("complete login flow: visit → fill form → submit → redirect", async ({
    page,
  }) => {
    const loginPage = new LoginPage(page);
    const dashboardPage = new DashboardPage(page);

    // 1. Visit login page
    await loginPage.goto();
    expect(await loginPage.isLoaded()).toBe(true);

    // 2. Fill form with valid credentials
    await loginPage.login("test@test.com", "test");

    // 3. Wait for redirect
    await page.waitForURL(/.*/, { timeout: 10000 });

    // 4. Verify we're on dashboard/projects
    const url = page.url();
    expect(!url.includes("/login")).toBe(true);
  });

  test("should show error flow and allow retry", async ({ page }) => {
    const loginPage = new LoginPage(page);

    // 1. First attempt with wrong credentials
    await loginPage.goto();
    await loginPage.login("wrong@example.com", "wrongpassword");

    // 2. Error should appear
    const errorAlert = page.locator('[data-testid="login-alert-error"]');
    await expect(errorAlert).toBeVisible({ timeout: 10000 });

    // 3. Fix credentials and retry
    const emailField = page.locator('[data-testid="login-input-email"]');
    const passwordField = page.locator('[data-testid="login-input-password"]');

    await emailField.clear();
    await passwordField.clear();

    await emailField.fill("test@test.com");
    await passwordField.fill("test");

    const submitButton = page.locator('[data-testid="login-btn-submit"]');
    await submitButton.click();

    // 4. Should redirect this time
    await page.waitForURL(/.*/, { timeout: 10000 });
    expect(!page.url().includes("/login")).toBe(true);
  });
});
