import { Page, Locator } from 'playwright';
import { BasePage } from './BasePage';

export class LoginPage extends BasePage {
  
  private readonly countryCodeInput: Locator;
  private readonly mobileNumberInput: Locator;
  private readonly passwordInput: Locator;
  private readonly loginButton: Locator;
  private readonly errorMessage: Locator;

  constructor(page: Page, environment: string = 'paribu') {
    super(page, environment);
    
    // Form alanı selector'ları - Login sayfasında telefon numarası ve parola alanları var
    // Country code genellikle telefon input'unun içinde veya ayrı bir select olabilir
    // Eğer country code ayrı bir alan değilse, telefon input'una direkt girilebilir
    this.countryCodeInput = page.locator('input[name="countryCode"], select[name="countryCode"], [data-testid="country-code"], input[placeholder*="ülke"], select.country-code, input[type="tel"][placeholder*="+"], [aria-label*="ülke"]').first();
    // Telefon numarası: "Cep telefonu numaranız" label'ı ile textbox
    // Playwright'te getByRole kullanarak daha güvenilir selector
    this.mobileNumberInput = page.getByRole('textbox', { name: 'Cep telefonu numaranız' }).or(
      page.locator('input[name="mobile"], input[name="phone"], input[type="tel"], [data-testid="mobile-number"], input[placeholder*="telefon"], input[placeholder*="numara"]')
    ).first();
    // Parola: "Parola" label'ı ile textbox
    this.passwordInput = page.getByRole('textbox', { name: 'Parola' }).or(
      page.locator('input[type="password"], input[name="password"], [data-testid="password"], input[placeholder*="şifre"], input[placeholder*="Şifre"]')
    ).first();
    
    // Buton ve hata mesajı selector'ları
    this.loginButton = page.locator('button[type="submit"], button:has-text("Giriş"), button:has-text("Giriş yap"), [data-testid="login-button"], button[class*="login"]').first();
    this.errorMessage = page.locator('[data-testid="error-message"], .error-message, .alert-danger, [class*="error"], [role="alert"]').first();
  }

  /**
   * Ülke kodu gir
   * Not: Paribu login sayfasında country code ayrı bir alan olmayabilir
   * Bu durumda telefon numarasına direkt girilebilir
   * Playwright'un otomatik bekleme mekanizmasını kullanır - statik bekleme gerekmez
   */
  async enterCountryCode(countryCode: string): Promise<void> {
    try {
      // Önce country code input'unu bulmaya çalış
      const isVisible = await this.countryCodeInput.isVisible({ timeout: 2000 }).catch(() => false);
      if (isVisible) {
        await this.fillInput(this.countryCodeInput, countryCode);
      } else {
        // Country code alanı yoksa, telefon numarasına direkt ekle
        // Telefon numarası alanına country code + telefon numarası formatında girilebilir
        Logger.debug('Country code input not found, will be included in phone number');
      }
    } catch (error) {
      // Country code alanı bulunamazsa, telefon numarasına dahil edilecek
      Logger.debug('Country code input not available, will be included in phone number');
    }
  }

  /**
   * Cep telefonu numarası gir
   */
  async enterMobileNumber(mobileNumber: string): Promise<void> {
    await this.fillInput(this.mobileNumberInput, mobileNumber);
  }

  /**
   * Şifre gir
   */
  async enterPassword(password: string): Promise<void> {
    await this.fillInput(this.passwordInput, password);
  }

  /**
   * Giriş butonuna tıkla
   */
  async clickLoginButton(): Promise<void> {
    await this.clickElement(this.loginButton);
    // Form gönderimini ve yanıtı bekle (hata mesajı veya yönlendirme)
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Hata mesajının görünür olup olmadığını kontrol et
   */
  async isErrorMessageVisible(): Promise<boolean> {
    return await this.isVisible(this.errorMessage, 5000);
  }

  /**
   * Hata mesajı metnini al
   */
  async getErrorMessageText(): Promise<string> {
    await this.waitForElement(this.errorMessage);
    return await this.getText(this.errorMessage);
  }

  /**
   * Hata mesajının beklenen metni içerdiğini doğrula
   */
  async verifyErrorMessageContains(expectedText: string): Promise<boolean> {
    const errorText = await this.getErrorMessageText();
    return errorText.toLowerCase().includes(expectedText.toLowerCase());
  }
}

