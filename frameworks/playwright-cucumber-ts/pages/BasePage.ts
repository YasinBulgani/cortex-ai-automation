/**
 * Base Page
 * Abstract base class for all page objects
 * Provides common methods and utilities for page interactions
 */

import { Page, Locator } from 'playwright';
import { getEnvironmentConfig } from '../config/config';
import { Logger } from '../utils/Logger';
import { TIMEOUTS } from '../config/constants';

export abstract class BasePage {
  protected page: Page;
  protected environment: string;

  constructor(page: Page, environment: string = 'qa') {
    this.page = page;
    this.environment = environment;
  }

  protected get baseUrl(): string {
    return getEnvironmentConfig(this.environment).baseUrl;
  }

  protected get timeout(): number {
    return getEnvironmentConfig(this.environment).timeout;
  }

  /**
   * Navigate to a URL and verify page load
   */
  async navigateTo(path: string = ''): Promise<void> {
    try {
      const url = path.startsWith('http') ? path : `${this.baseUrl}${path}`;
      await this.page.goto(url, { 
        waitUntil: 'networkidle',
        timeout: this.timeout 
      });
      
      const pageTitle = await this.page.title();
      if (!pageTitle || pageTitle.trim().length === 0) {
        throw new Error('Page title not loaded - page may not have loaded correctly');
      }
      
      const currentUrl = this.page.url();
      if (!currentUrl || currentUrl.trim().length === 0) {
        throw new Error('Page URL not loaded - page may not have loaded correctly');
      }
      
      Logger.debug('Page loaded successfully', { url: currentUrl, title: pageTitle });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Navigation failed: ${errorMessage}`);
    }
  }

  /**
   * Wait for element to be visible
   */
  async waitForElement(locator: Locator, timeout?: number): Promise<void> {
    try {
      await locator.waitFor({ state: 'visible', timeout: timeout || this.timeout });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Element not visible: ${errorMessage}`);
    }
  }

  /**
   * Wait for element to be hidden
   */
  async waitForElementHidden(locator: Locator, timeout?: number): Promise<void> {
    await locator.waitFor({ state: 'hidden', timeout: timeout || this.timeout });
  }

  /**
   * Click an element
   */
  async clickElement(locator: Locator, timeout?: number, force: boolean = false): Promise<void> {
    try {
      await this.closeOverlayIfPresent();
      
      if (!force) {
        await this.waitForElement(locator, timeout);
      }
      
      await locator.click({ timeout: timeout || this.timeout, force });
    } catch (error) {
      if (!force && error instanceof Error && error.message.includes('intercepts pointer events')) {
        Logger.debug('Overlay intercepting click, closing overlay and retrying with force');
        await this.closeOverlayIfPresent();
        await locator.waitFor({ state: 'visible', timeout: 1000 }).catch(() => {});
        await locator.click({ timeout: timeout || this.timeout, force: true });
      } else {
        const errorMessage = error instanceof Error ? error.message : String(error);
        throw new Error(`Element click failed: ${errorMessage}`);
      }
    }
  }

  /**
   * Fill input field
   */
  async fillInput(locator: Locator, text: string, timeout?: number): Promise<void> {
    try {
      await this.waitForElement(locator, timeout);
      await locator.clear({ timeout: timeout || this.timeout });
      await locator.fill(text, { timeout: timeout || this.timeout });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Input fill failed: ${errorMessage}`);
    }
  }

  /**
   * Get text content from element
   */
  async getText(locator: Locator, timeout?: number): Promise<string> {
    await this.waitForElement(locator, timeout);
    return await locator.textContent() || '';
  }

  /**
   * Check if element is visible
   */
  async isVisible(locator: Locator, timeout?: number): Promise<boolean> {
    try {
      await this.waitForElement(locator, timeout);
      return await locator.isVisible();
    } catch {
      return false;
    }
  }

  /**
   * Take screenshot
   */
  async takeScreenshot(fileName: string): Promise<void> {
    try {
      const sanitizedFileName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
      await this.page.screenshot({ 
        path: `reports/screenshots/${sanitizedFileName}`, 
        fullPage: true,
        timeout: this.timeout
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Screenshot failed: ${errorMessage}`);
    }
  }

  /**
   * Get page title
   */
  async getTitle(): Promise<string> {
    return await this.page.title();
  }

  /**
   * Get current URL
   */
  getCurrentUrl(): string {
    return this.page.url();
  }

  /**
   * Close overlay if present
   */
  protected async closeOverlayIfPresent(): Promise<void> {
    try {
      const overlaySelectors = ['.p-overlay', '[class*="overlay"]', '[class*="modal"]', '[role="dialog"]'];
      
      for (const selector of overlaySelectors) {
        try {
          const overlay = this.page.locator(selector).first();
          const isVisible = await this.isVisible(overlay, TIMEOUTS.ELEMENT_VISIBILITY);
          if (isVisible) {
            await this.page.keyboard.press('Escape');
            await this.waitForElementHidden(overlay, TIMEOUTS.OVERLAY_CLOSE).catch(() => {});
            
            const closeButtonSelectors = [
              'button[aria-label="Close"]',
              'button.close',
              '.close-button',
              '[class*="close"]'
            ];
            
            const stillVisible = await this.isVisible(overlay, TIMEOUTS.ELEMENT_VISIBILITY);
            if (stillVisible) {
              for (const closeSelector of closeButtonSelectors) {
                try {
                  const closeButton = overlay.locator(closeSelector).first();
                  if (await this.isVisible(closeButton, TIMEOUTS.ELEMENT_VISIBILITY)) {
                    await closeButton.click({ force: true });
                    break;
                  }
                } catch {
                  continue;
                }
              }
            }
            
            await this.waitForElementHidden(overlay, TIMEOUTS.OVERLAY_CLOSE);
            return;
          }
        } catch {
          continue;
        }
      }
    } catch (error) {
      Logger.debug('Overlay close failed or not found', { error });
    }
  }
}
