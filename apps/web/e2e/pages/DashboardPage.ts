import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * Dashboard Page Object Model
 * Encapsulates dashboard page interactions (post-login)
 */
export class DashboardPage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  readonly pageContainer = 'div[class*="container"]';
  readonly appShell = '[data-testid="app-shell"]';
  readonly userMenu = '[data-testid="user-menu"]';
  readonly logoutButton = '[data-testid="logout-button"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to dashboard
   */
  async goto() {
    await super.goto("/");
  }

  /**
   * Check if dashboard is loaded
   */
  async isLoaded(): Promise<boolean> {
    try {
      await this.page.waitForURL(/.*/, { timeout: 5000 });
      // Dashboard loaded if we're not on login page
      return !this.page.url().includes("/login");
    } catch {
      return false;
    }
  }

  /**
   * Check if we're on projects page (common after login)
   */
  async isOnProjectsPage(): Promise<boolean> {
    await this.expectUrl("/projects");
    return true;
  }

  /**
   * Check current URL
   */
  async getCurrentUrl(): Promise<string> {
    return this.page.url();
  }

  /**
   * Logout user
   */
  async logout() {
    if (await this.isVisible(this.userMenu)) {
      await this.click(this.userMenu);
    }
    if (await this.isVisible(this.logoutButton)) {
      await this.click(this.logoutButton);
    }
  }

  /**
   * Wait for page load after login
   */
  async waitForLoad() {
    await this.page.waitForLoadState("networkidle");
  }
}
