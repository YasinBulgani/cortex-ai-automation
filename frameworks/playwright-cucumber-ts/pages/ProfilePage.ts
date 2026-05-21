/**
 * User Profile Page Object Model
 */

import { Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { Logger } from '../utils/Logger';

export class ProfilePage extends BasePage {
  readonly userNameDisplay = this.page.locator('[data-testid="user-name"]');
  readonly emailDisplay = this.page.locator('[data-testid="user-email"]');
  readonly editButton = this.page.locator('button:has-text("Edit")');
  readonly saveButton = this.page.locator('button:has-text("Save")');
  readonly cancelButton = this.page.locator('button:has-text("Cancel")');
  readonly deleteAccountButton = this.page.locator('button:has-text("Delete Account")');
  readonly logoutButton = this.page.locator('button:has-text("Logout"), a:has-text("Logout")');
  readonly profileImage = this.page.locator('[data-testid="profile-image"]');
  readonly settingsTab = this.page.locator('button:has-text("Settings")');
  readonly securityTab = this.page.locator('button:has-text("Security")');
  readonly changePasswordButton = this.page.locator('button:has-text("Change Password")');
  readonly twoFactorToggle = this.page.locator('[data-testid="two-factor-toggle"]');

  constructor(page: Page, logger: Logger) {
    super(page, logger);
    this.pageUrl = /profile/;
  }

  async waitForPageLoad(): Promise<void> {
    await this.waitForVisible(this.userNameDisplay);
  }

  async getUserName(): Promise<string> {
    return await this.getText(this.userNameDisplay);
  }

  async getUserEmail(): Promise<string> {
    return await this.getText(this.emailDisplay);
  }

  async clickEditProfile(): Promise<void> {
    await this.click(this.editButton);
  }

  async saveProfile(): Promise<void> {
    await this.click(this.saveButton);
    await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {});
  }

  async clickLogout(): Promise<void> {
    await this.click(this.logoutButton);
    await this.page.waitForNavigation({ waitUntil: 'networkidle' });
  }

  async openSettingsTab(): Promise<void> {
    await this.click(this.settingsTab);
  }

  async openSecurityTab(): Promise<void> {
    await this.click(this.securityTab);
  }

  async toggleTwoFactor(): Promise<void> {
    await this.click(this.twoFactorToggle);
  }
}
