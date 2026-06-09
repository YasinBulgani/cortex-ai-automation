import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * SettingsPage - Page Object for user settings
 * Handles: profile, password, notifications, API keys, team management
 *
 * Critical paths:
 * - Any user updates profile
 * - User changes password
 * - Manager invites new team member
 * - Admin configures integrations
 */

export class SettingsPage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  // Page-level
  readonly settingsPageContainer = '[data-testid="settings-page"]';
  readonly settingsTabs = '[data-testid="settings-tabs"]';
  readonly profileTab = '[data-testid="settings-tab-profile"]';
  readonly notificationsTab = '[data-testid="settings-tab-notifications"]';
  readonly apiKeysTab = '[data-testid="settings-tab-api-keys"]';
  readonly teamTab = '[data-testid="settings-tab-team"]';
  readonly integrationsTab = '[data-testid="settings-tab-integrations"]';

  // Profile section
  readonly profileSection = '[data-testid="settings-profile-section"]';
  readonly userNameInput = '[data-testid="profile-name-input"]';
  readonly userEmailInput = '[data-testid="profile-email-input"]';
  readonly userAvatarInput = '[data-testid="profile-avatar-input"]';
  readonly timezoneSelect = '[data-testid="profile-timezone"]';
  readonly languageSelect = '[data-testid="profile-language"]';
  readonly saveProfileBtn = '[data-testid="profile-save-btn"]';
  readonly profileError = '[data-testid="profile-error"]';
  readonly profileSuccess = '[data-testid="profile-success"]';

  // Password section
  readonly passwordSection = '[data-testid="settings-password-section"]';
  readonly changePasswordBtn = '[data-testid="change-password-btn"]';
  readonly passwordModal = '[data-testid="password-modal"]';
  readonly currentPasswordInput = '[data-testid="current-password-input"]';
  readonly newPasswordInput = '[data-testid="new-password-input"]';
  readonly confirmPasswordInput = '[data-testid="confirm-password-input"]';
  readonly savePasswordBtn = '[data-testid="password-save-btn"]';
  readonly passwordError = '[data-testid="password-error"]';
  readonly passwordSuccess = '[data-testid="password-success"]';

  // Notifications section
  readonly notificationsSection = '[data-testid="settings-notifications-section"]';
  readonly emailNotificationsToggle = '[data-testid="email-notifications-toggle"]';
  readonly slackIntegrationBtn = '[data-testid="slack-integration-btn"]';
  readonly slackConnected = '[data-testid="slack-connected"]';
  readonly slackDisconnectBtn = '[data-testid="slack-disconnect-btn"]';
  readonly dailyDigestToggle = '[data-testid="daily-digest-toggle"]';
  readonly notificationFrequencySelect = '[data-testid="notification-frequency"]';
  readonly saveNotificationsBtn = '[data-testid="notifications-save-btn"]';
  readonly notificationsSuccess = '[data-testid="notifications-success"]';

  // API Keys section
  readonly apiKeysSection = '[data-testid="settings-api-keys-section"]';
  readonly generateKeyBtn = '[data-testid="generate-key-btn"]';
  readonly apiKeyModal = '[data-testid="api-key-modal"]';
  readonly apiKeyNameInput = '[data-testid="api-key-name-input"]';
  readonly apiKeyValue = '[data-testid="api-key-value"]';
  readonly copyKeyBtn = '[data-testid="copy-key-btn"]';
  readonly confirmKeyBtn = '[data-testid="confirm-key-btn"]';
  readonly apiKeyList = '[data-testid="api-key-list"]';
  readonly apiKeyItem = '[data-testid="api-key-item"]';
  readonly revokeKeyBtn = '[data-testid="revoke-key-btn"]';
  readonly keyCopiedToast = '[data-testid="key-copied-toast"]';

  // Team section
  readonly teamSection = '[data-testid="settings-team-section"]';
  readonly inviteButton = '[data-testid="invite-button"]';
  readonly inviteModal = '[data-testid="invite-modal"]';
  readonly inviteEmailInput = '[data-testid="invite-email-input"]';
  readonly inviteRoleSelect = '[data-testid="invite-role-select"]';
  readonly inviteProjectsSelect = '[data-testid="invite-projects-select"]';
  readonly sendInviteBtn = '[data-testid="send-invite-btn"]';
  readonly teamMemberList = '[data-testid="team-member-list"]';
  readonly teamMemberItem = '[data-testid="team-member-item"]';
  readonly removeMemberBtn = '[data-testid="remove-member-btn"]';
  readonly pendingInvitesList = '[data-testid="pending-invites-list"]';
  readonly revokeInviteBtn = '[data-testid="revoke-invite-btn"]';
  readonly inviteSuccess = '[data-testid="invite-success"]';

  // Integrations section
  readonly integrationsSection = '[data-testid="settings-integrations-section"]';
  readonly jiraIntegration = '[data-testid="jira-integration"]';
  readonly jiraConnectBtn = '[data-testid="jira-connect-btn"]';
  readonly jiraConnected = '[data-testid="jira-connected"]';
  readonly jiraDisconnectBtn = '[data-testid="jira-disconnect-btn"]';
  readonly slackIntegration = '[data-testid="slack-integration"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to settings page
   */
  async goto() {
    await super.goto("/settings");
    await this.waitForPageReady();
  }

  /**
   * Check if settings page is loaded
   */
  async isLoaded(): Promise<boolean> {
    return this.isVisible(this.settingsPageContainer);
  }

  // ── Profile Tab ──────────────────────────────────────────────────────

  /**
   * Switch to profile tab
   */
  async switchToProfile(): Promise<void> {
    await this.click(this.profileTab);
    await this.waitFor(this.profileSection, 5000);
  }

  /**
   * Update user profile
   */
  async updateProfile(data: {
    name?: string;
    timezone?: string;
    language?: string;
  }): Promise<void> {
    await this.switchToProfile();

    if (data.name) {
      await this.page.fill(this.userNameInput, data.name);
    }
    if (data.timezone) {
      await this.page.selectOption(this.timezoneSelect, data.timezone);
    }
    if (data.language) {
      await this.page.selectOption(this.languageSelect, data.language);
    }

    await this.click(this.saveProfileBtn);

    // Wait for success message
    await this.waitFor(this.profileSuccess, 10000);
  }

  /**
   * Upload profile avatar
   */
  async uploadAvatar(filePath: string): Promise<void> {
    await this.switchToProfile();
    await this.page.locator(this.userAvatarInput).setInputFiles(filePath);
    await this.click(this.saveProfileBtn);
    await this.waitFor(this.profileSuccess, 10000);
  }

  /**
   * Get profile error message
   */
  async getProfileError(): Promise<string> {
    const errorEl = this.page.locator(this.profileError);
    if (await errorEl.isVisible()) {
      return this.getText(this.profileError);
    }
    return "";
  }

  // ── Password Tab ──────────────────────────────────────────────────────

  /**
   * Change password
   */
  async changePassword(
    currentPassword: string,
    newPassword: string,
    confirmPassword: string
  ): Promise<void> {
    await this.switchToProfile();
    await this.click(this.changePasswordBtn);

    // Wait for modal
    await this.waitFor(this.passwordModal, 5000);

    // Fill form
    await this.fillInput(this.currentPasswordInput, currentPassword);
    await this.fillInput(this.newPasswordInput, newPassword);
    await this.fillInput(this.confirmPasswordInput, confirmPassword);

    // Save
    await this.click(this.savePasswordBtn);

    // Wait for success
    await this.waitFor(this.passwordSuccess, 10000);

    // Modal should close
    await this.page
      .waitForSelector(this.passwordModal, { state: "hidden", timeout: 5000 })
      .catch(() => {});
  }

  /**
   * Get password error
   */
  async getPasswordError(): Promise<string> {
    const errorEl = this.page.locator(this.passwordError);
    if (await errorEl.isVisible()) {
      return this.getText(this.passwordError);
    }
    return "";
  }

  // ── Notifications Tab ──────────────────────────────────────────────────

  /**
   * Switch to notifications tab
   */
  async switchToNotifications(): Promise<void> {
    await this.click(this.notificationsTab);
    await this.waitFor(this.notificationsSection, 5000);
  }

  /**
   * Toggle email notifications
   */
  async toggleEmailNotifications(): Promise<void> {
    await this.switchToNotifications();
    await this.click(this.emailNotificationsToggle);
    await this.waitForPageReady();
  }

  /**
   * Toggle daily digest
   */
  async toggleDailyDigest(): Promise<void> {
    await this.switchToNotifications();
    await this.click(this.dailyDigestToggle);
    await this.waitForPageReady();
  }

  /**
   * Set notification frequency
   */
  async setNotificationFrequency(frequency: "immediate" | "daily" | "weekly"): Promise<void> {
    await this.switchToNotifications();
    await this.page.selectOption(this.notificationFrequencySelect, frequency);
    await this.click(this.saveNotificationsBtn);
    await this.waitFor(this.notificationsSuccess, 10000);
  }

  /**
   * Connect Slack integration
   */
  async connectSlack(): Promise<void> {
    await this.switchToNotifications();
    await this.click(this.slackIntegrationBtn);
    // Might redirect to Slack OAuth or show auth modal
    await this.page.waitForTimeout(2000);
  }

  /**
   * Disconnect Slack
   */
  async disconnectSlack(): Promise<void> {
    await this.switchToNotifications();
    const isConnected = await this.page.locator(this.slackConnected).isVisible();
    if (isConnected) {
      await this.click(this.slackDisconnectBtn);
      await this.waitForPageReady();
    }
  }

  // ── API Keys Tab ──────────────────────────────────────────────────────

  /**
   * Switch to API keys tab
   */
  async switchToApiKeys(): Promise<void> {
    await this.click(this.apiKeysTab);
    await this.waitFor(this.apiKeysSection, 5000);
  }

  /**
   * Generate new API key
   */
  async generateApiKey(name: string): Promise<string> {
    await this.switchToApiKeys();
    await this.click(this.generateKeyBtn);

    // Wait for modal
    await this.waitFor(this.apiKeyModal, 5000);

    // Fill name
    await this.fillInput(this.apiKeyNameInput, name);

    // Confirm
    await this.click(this.confirmKeyBtn);

    // Wait for key to be generated
    await this.waitFor(this.apiKeyValue, 5000);

    // Get the key value
    const keyEl = this.page.locator(this.apiKeyValue);
    const keyValue = await keyEl.inputValue();

    // Copy to clipboard
    await this.click(this.copyKeyBtn);
    await this.waitFor(this.keyCopiedToast, 5000);

    return keyValue;
  }

  /**
   * Get list of API keys
   */
  async getApiKeyList(): Promise<string[]> {
    await this.switchToApiKeys();
    const items = this.page.locator(this.apiKeyItem);
    const count = await items.count();
    const keys: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        keys.push(text.trim());
      }
    }

    return keys;
  }

  /**
   * Revoke API key
   */
  async revokeApiKey(name: string): Promise<void> {
    await this.switchToApiKeys();
    const items = this.page.locator(this.apiKeyItem);
    const count = await items.count();

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text?.includes(name)) {
        const revokeBtn = items.nth(i).locator(this.revokeKeyBtn);
        await revokeBtn.click();
        await this.page.waitForTimeout(500);
        return;
      }
    }

    throw new Error(`API key not found: ${name}`);
  }

  // ── Team Tab ──────────────────────────────────────────────────────────

  /**
   * Switch to team tab
   */
  async switchToTeam(): Promise<void> {
    await this.click(this.teamTab);
    await this.waitFor(this.teamSection, 5000);
  }

  /**
   * Invite team member
   */
  async inviteTeamMember(
    email: string,
    role: "admin" | "manager" | "tester" | "developer",
    projects?: string[]
  ): Promise<void> {
    await this.switchToTeam();
    await this.click(this.inviteButton);

    // Wait for modal
    await this.waitFor(this.inviteModal, 5000);

    // Fill form
    await this.fillInput(this.inviteEmailInput, email);
    await this.page.selectOption(this.inviteRoleSelect, role);

    if (projects && projects.length > 0) {
      for (const project of projects) {
        await this.page.selectOption(this.inviteProjectsSelect, project, { force: true });
      }
    }

    // Send
    await this.click(this.sendInviteBtn);

    // Wait for success
    await this.waitFor(this.inviteSuccess, 10000);
  }

  /**
   * Get list of team members
   */
  async getTeamMembers(): Promise<string[]> {
    await this.switchToTeam();
    const items = this.page.locator(this.teamMemberItem);
    const count = await items.count();
    const members: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        members.push(text.trim());
      }
    }

    return members;
  }

  /**
   * Get list of pending invites
   */
  async getPendingInvites(): Promise<string[]> {
    await this.switchToTeam();
    const items = this.page.locator(this.pendingInvitesList);
    if (await items.count() === 0) {
      return [];
    }

    const count = await items.count();
    const invites: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        invites.push(text.trim());
      }
    }

    return invites;
  }

  /**
   * Remove team member
   */
  async removeTeamMember(email: string): Promise<void> {
    await this.switchToTeam();
    const items = this.page.locator(this.teamMemberItem);
    const count = await items.count();

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text?.includes(email)) {
        const removeBtn = items.nth(i).locator(this.removeMemberBtn);
        await removeBtn.click();
        await this.page.waitForTimeout(500);
        return;
      }
    }

    throw new Error(`Team member not found: ${email}`);
  }

  /**
   * Revoke pending invite
   */
  async revokePendingInvite(email: string): Promise<void> {
    await this.switchToTeam();
    const items = this.page.locator(this.pendingInvitesList);
    const count = await items.count();

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text?.includes(email)) {
        const revokeBtn = items.nth(i).locator(this.revokeInviteBtn);
        await revokeBtn.click();
        await this.page.waitForTimeout(500);
        return;
      }
    }

    throw new Error(`Pending invite not found: ${email}`);
  }

  // ── Integrations Tab ──────────────────────────────────────────────────

  /**
   * Switch to integrations tab
   */
  async switchToIntegrations(): Promise<void> {
    await this.click(this.integrationsTab);
    await this.waitFor(this.integrationsSection, 5000);
  }

  /**
   * Connect Jira integration
   */
  async connectJira(): Promise<void> {
    await this.switchToIntegrations();
    await this.click(this.jiraConnectBtn);
    // Might show auth modal or redirect
    await this.page.waitForTimeout(2000);
  }

  /**
   * Disconnect Jira
   */
  async disconnectJira(): Promise<void> {
    await this.switchToIntegrations();
    const isConnected = await this.page.locator(this.jiraConnected).isVisible();
    if (isConnected) {
      await this.click(this.jiraDisconnectBtn);
      await this.waitForPageReady();
    }
  }
}
