import { Page, Locator } from 'playwright';
import { BasePage } from './BasePage';
import { Logger } from '../utils/Logger';

export class ParibuHomePage extends BasePage {
  
  private readonly cookieNotice: Locator;
  private readonly cookieAcceptButton: Locator;
  private readonly marketsLink: Locator;
  private readonly loginLink: Locator;

  constructor(page: Page, environment: string = 'paribu') {
    super(page, environment);
    
    // Cookie bildirimi selector'ları
    this.cookieNotice = page.locator('[data-testid="cookie-notice"], .cookie-banner, .cookie-notice, [class*="cookie"]').first();
    this.cookieAcceptButton = page.locator('button:has-text("Kabul Et"), button:has-text("Accept"), [data-testid="accept-cookies"], .cookie-accept, button[class*="cookie"]').first();
    
    // Navigasyon selector'ları
    this.marketsLink = page.locator('a:has-text("Piyasalar"), a[href*="markets"], nav a:has-text("Piyasalar")').first();
    this.loginLink = page.locator('a:has-text("Giriş yap"), a:has-text("Giriş"), a[href*="login"], button:has-text("Giriş yap")').first();
  }

  /**
   * Paribu ana sayfasına git
   */
  async open(): Promise<void> {
    await this.navigateTo('/');
  }

  /**
   * Cookie bildirimi görünürse kapat
   * Playwright'un otomatik bekleme mekanizmasını kullanır - statik bekleme gerekmez
   */
  async closeCookieNotice(): Promise<void> {
    try {
      // Cookie bildiriminin görünür olmasını bekle (timeout ile)
      const isVisible = await this.isVisible(this.cookieNotice, 5000);
      if (isVisible) {
        await this.clickElement(this.cookieAcceptButton);
        // Cookie bildiriminin gizlenmesini bekle
        await this.waitForElementHidden(this.cookieNotice, 5000);
      }
      
      // Cookie kapatıldıktan sonra overlay'i de kapat
      await this.closeOverlayIfPresent();
    } catch (error) {
      // Cookie bildirimi görünmeyebilir veya zaten kapatılmış olabilir - bu kabul edilebilir
      const errorMessage = error instanceof Error ? error.message : String(error);
      Logger.debug('Cookie bildirimi bulunamadı veya zaten kapatılmış', { error: errorMessage });
    }
  }

  /**
   * Markets sayfasına git
   */
  async navigateToMarkets(): Promise<void> {
    await this.clickElement(this.marketsLink);
    // Navigasyonun tamamlanmasını bekle (Playwright load state için otomatik bekler)
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Giriş sayfasına git
   */
  async navigateToLogin(): Promise<void> {
    await this.clickElement(this.loginLink);
    // Navigasyonun tamamlanmasını bekle
    await this.page.waitForLoadState('networkidle');
  }
}

