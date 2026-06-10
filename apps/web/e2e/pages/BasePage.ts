import { Page, expect } from "@playwright/test";

/**
 * Base Page Object
 * Common functionality shared across all page objects
 */
export class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Navigate to a path
   */
  async goto(path: string = "/") {
    await this.page.goto(path);
  }

  /**
   * Wait for page to be ready (UI rendered)
   */
  async waitForPageReady() {
    await this.page.waitForSelector('[data-ui-ready="true"]', { timeout: 10000 }).catch(() => {
      // Some pages might not have this attribute, that's ok
    });
  }

  /**
   * Take a screenshot
   */
  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
  }

  /**
   * Get page title
   */
  async getTitle(): Promise<string> {
    return this.page.title();
  }

  /**
   * Check if element is visible
   */
  async isVisible(selector: string): Promise<boolean> {
    try {
      await this.page.waitForSelector(selector, { timeout: 3000, state: "visible" });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Fill input with value
   */
  async fillInput(selector: string, value: string) {
    const input = this.page.locator(selector);
    await input.fill(value);
  }

  /**
   * Click element
   */
  async click(selector: string) {
    await this.page.locator(selector).click();
  }

  /**
   * Wait for element to be visible
   */
  async waitFor(selector: string, timeout: number = 5000) {
    await this.page.waitForSelector(selector, { state: "visible", timeout });
  }

  /**
   * Get text content
   */
  async getText(selector: string): Promise<string> {
    return (await this.page.locator(selector).textContent()) || "";
  }

  /**
   * Wait for URL to change
   */
  async waitForNavigation(callback: () => Promise<void>) {
    await Promise.all([this.page.waitForNavigation(), callback()]);
  }

  /**
   * Check if we're on expected URL
   */
  async expectUrl(path: string) {
    await expect(this.page).toHaveURL(new RegExp(path));
  }

  /**
   * Clear localStorage
   */
  async clearStorage() {
    await this.page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  }

  /**
   * Get localStorage value
   */
  async getLocalStorage(key: string): Promise<string | null> {
    return this.page.evaluate((k) => localStorage.getItem(k), key);
  }

  /**
   * Reload page
   */
  async reload() {
    await this.page.reload();
  }
}
