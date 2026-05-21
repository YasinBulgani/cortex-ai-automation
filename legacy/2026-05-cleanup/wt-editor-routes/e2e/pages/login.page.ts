import { expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class LoginPage extends BasePage {
  readonly url = "/login";

  // ── Locators ───────────────────────────────────────────────────────────────
  get logo() {
    return this.page.locator("svg[aria-label='Visium Operations']");
  }
  get pageRoot() {
    return this.testId("login-page");
  }
  get emailInput() {
    return this.testId("login-input-email");
  }
  get passwordInput() {
    return this.testId("login-input-password");
  }
  get submitButton() {
    return this.testId("login-btn-submit");
  }
  get loadingButton() {
    return this.testId("login-btn-submit");
  }
  get errorAlert() {
    return this.text(/hatalı|geçersiz|başarısız/i);
  }
  get rememberMe() {
    return this.text("Beni hatırla");
  }
  get forgotPassword() {
    return this.text("Şifremi unuttum");
  }
  get registerPrompt() {
    return this.text("Hesabınız yok mu?");
  }
  get footer() {
    // "Visium Product Family Access" üst kısımda da var — bu yüzden
    // regex eşleşmesi strict mode'da çakışıyor. Spesifik test ID kullan.
    return this.testId("login-footer");
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async fillEmail(email: string) {
    await this.emailInput.fill(email);
  }

  async fillPassword(password: string) {
    await this.passwordInput.fill(password);
  }

  async submit() {
    await this.submitButton.click();
  }

  async login(email: string, password: string) {
    await this.goto();
    await this.assertPageLoaded();
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.submit();
  }

  // ── Assertions ─────────────────────────────────────────────────────────────
  async assertPageLoaded() {
    await expect(this.pageRoot).toBeVisible({ timeout: 30_000 });
    try {
      await expect(this.pageRoot).toHaveAttribute("data-ui-ready", "true", { timeout: 10_000 });
    } catch {
      // Next dev server bazen ilk istekte chunk'lari gec hazirliyor; tek reload ile hydration tamamlanir.
      await this.page.reload({ waitUntil: "domcontentloaded" });
      await expect(this.pageRoot).toHaveAttribute("data-ui-ready", "true", { timeout: 30_000 });
    }
    await expect(this.emailInput).toBeVisible({ timeout: 30_000 });
    await expect(this.passwordInput).toBeVisible({ timeout: 30_000 });
    await expect(this.emailInput).toBeEnabled({ timeout: 30_000 });
    await expect(this.passwordInput).toBeEnabled({ timeout: 30_000 });
    await expect(this.submitButton).toBeVisible({ timeout: 30_000 });
    await expect(this.submitButton).toBeEnabled({ timeout: 30_000 });
  }

  async assertErrorVisible() {
    await expect(this.errorAlert).toBeVisible({ timeout: 10_000 });
  }

  async assertRedirectToProjects() {
    await expect(this.page).toHaveURL(/\/(projects|onboarding)$/, { timeout: 10_000 });
  }

  async assertLoadingState() {
    const submitVisible = await this.loadingButton.isVisible({ timeout: 1_000 }).catch(() => false);
    if (submitVisible) {
      await expect(this.loadingButton).toBeVisible({ timeout: 2_000 });
      await expect(this.loadingButton).toBeDisabled();
      return;
    }

    await expect(this.text(/giriş yapılıyor…/i)).toBeVisible({ timeout: 2_000 });
    await expect(this.page.getByRole("button", { name: /manuel giriş yap/i })).toBeVisible({
      timeout: 2_000,
    });
  }
}
