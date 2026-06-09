import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * Login Page Object Model
 * Encapsulates all login page interactions
 */
export class LoginPage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  // Login form
  readonly emailInput = '[data-testid="login-input-email"]';
  readonly passwordInput = '[data-testid="login-input-password"]';
  readonly submitButton = '[data-testid="login-btn-submit"]';
  readonly errorAlert = '[data-testid="login-alert-error"]';
  readonly loginForm = '[data-testid="login-form"]';
  readonly mfaForm = '[data-testid="mfa-form"]';
  readonly loginPage = '[data-testid="login-page"]';
  readonly loginHeading = '[data-testid="login-heading"]';
  readonly forgotPanel = '[data-testid="login-forgot-panel"]';
  readonly forgotButton = '[data-testid="login-btn-forgot"]';
  readonly forgotEmail = '[data-testid="login-input-forgot-email"]';
  readonly forgotSubmit = '[data-testid="login-btn-forgot-submit"]';
  readonly forgotCancel = '[data-testid="login-btn-forgot-cancel"]';
  readonly forgotMessage = '[data-testid="login-forgot-msg"]';

  // MFA selectors
  readonly mfaCodeInput = '#mfa-code';
  readonly mfaSubmitButton = '[data-testid="mfa-form"] button[type="submit"]';
  readonly mfaError = '[data-testid="mfa-form"] p[class*="rose"]';

  // Tabs
  readonly loginTab = '[data-testid="login-btn-tab-login"]';
  readonly registerTab = '[data-testid="login-btn-tab-register"]';

  // Register form
  readonly registerForm = '[data-testid="register-form"]';
  readonly registerName = '#register-name';
  readonly registerEmail = '#register-email';
  readonly registerPassword = '#register-password';
  readonly registerConfirm = '#register-confirm';
  readonly registerSubmit = 'button[type="submit"][class*="primary"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to login page
   */
  async goto() {
    await super.goto("/login");
    await this.waitForPageReady();
  }

  /**
   * Check if login page is loaded
   */
  async isLoaded(): Promise<boolean> {
    return this.isVisible(this.loginPage);
  }

  /**
   * Check if login form is visible
   */
  async isLoginFormVisible(): Promise<boolean> {
    return this.isVisible(this.loginForm);
  }

  /**
   * Check if MFA form is visible
   */
  async isMfaFormVisible(): Promise<boolean> {
    return this.isVisible(this.mfaForm);
  }

  /**
   * Login with valid credentials
   */
  async login(email: string, password: string) {
    await this.page.waitForLoadState("load");
    await this.fillInput(this.emailInput, email);
    await this.fillInput(this.passwordInput, password);
    await this.click(this.submitButton);
  }

  /**
   * Login and wait for error
   */
  async loginAndExpectError(email: string, password: string): Promise<string> {
    await this.login(email, password);
    await this.waitFor(this.errorAlert);
    return this.getText(this.errorAlert);
  }

  /**
   * Check if error message is displayed
   */
  async hasError(): Promise<boolean> {
    return this.isVisible(this.errorAlert);
  }

  /**
   * Get error message text
   */
  async getErrorMessage(): Promise<string> {
    return this.getText(this.errorAlert);
  }

  /**
   * Clear error message by re-entering email
   */
  async clearError() {
    const emailField = this.page.locator(this.emailInput);
    await emailField.focus();
    await emailField.fill("");
  }

  /**
   * Open forgot password panel
   */
  async openForgotPanel() {
    await this.click(this.forgotButton);
    await this.waitFor(this.forgotPanel);
  }

  /**
   * Submit forgot password
   */
  async submitForgotPassword(email: string) {
    await this.fillInput(this.forgotEmail, email);
    await this.click(this.forgotSubmit);
  }

  /**
   * Get forgot password message
   */
  async getForgotMessage(): Promise<string> {
    await this.waitFor(this.forgotMessage);
    return this.getText(this.forgotMessage);
  }

  /**
   * Close forgot password panel
   */
  async closeForgotPanel() {
    await this.click(this.forgotCancel);
  }

  /**
   * Submit MFA code
   */
  async submitMfaCode(code: string) {
    await this.fillInput(this.mfaCodeInput, code);
    await this.click(this.mfaSubmitButton);
  }

  /**
   * Get MFA error message
   */
  async getMfaError(): Promise<string> {
    await this.waitFor(this.mfaError);
    return this.getText(this.mfaError);
  }

  /**
   * Go back from MFA
   */
  async goBackFromMfa() {
    const backButton = this.page.locator(this.mfaForm).locator('button:has-text("Giriş formuna dön")');
    await backButton.click();
  }

  /**
   * Switch to register tab
   */
  async switchToRegisterTab() {
    await this.click(this.registerTab);
  }

  /**
   * Switch to login tab
   */
  async switchToLoginTab() {
    await this.click(this.loginTab);
  }

  /**
   * Register new account
   */
  async register(name: string, email: string, password: string, confirmPassword: string) {
    await this.fillInput(this.registerName, name);
    await this.fillInput(this.registerEmail, email);
    await this.fillInput(this.registerPassword, password);
    await this.fillInput(this.registerConfirm, confirmPassword);
    await this.click(this.registerSubmit);
  }

  /**
   * Check if register form is visible
   */
  async isRegisterFormVisible(): Promise<boolean> {
    return this.isVisible(this.registerForm);
  }

  /**
   * Check login heading is visible
   */
  async checkHeading() {
    return expect(this.page.locator(this.loginHeading)).toBeVisible();
  }

  /**
   * Check if submit button is disabled
   */
  async isSubmitButtonDisabled(): Promise<boolean> {
    return this.page.locator(this.submitButton).isDisabled();
  }

  /**
   * Wait for redirect (used after successful login)
   */
  async waitForRedirect() {
    await this.page.waitForNavigation();
  }
}
