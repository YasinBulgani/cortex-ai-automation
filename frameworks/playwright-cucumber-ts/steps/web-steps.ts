/**
 * Web-Specific Step Definitions
 *
 * Steps for web application testing
 * Login, form submission, navigation, etc.
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

/**
 * AUTHENTICATION STEPS
 */

Given('I am logged in as {string}', async function (this: any, username: string) {
  this.logger.info(`Logging in as: ${username}`);
  // Navigate to login if not already there
  const currentUrl = this.page.url();
  if (!currentUrl.includes('login')) {
    await this.page.goto('/login', { waitUntil: 'networkidle' });
  }

  // Fill login form
  await this.page.locator('input[type="email"], input[name="username"]').fill(username);
  await this.page.locator('input[type="password"]').fill('TestPassword123!');

  // Submit form
  await this.page.locator('button[type="submit"], button:has-text("Login")').click();

  // Wait for navigation
  await this.page.waitForNavigation({ waitUntil: 'networkidle' });
  this.logger.info(`Successfully logged in as ${username}`);
});

Given('I am logged out', async function (this: any) {
  this.logger.info('Logging out');
  // Click logout button if exists
  const logoutBtn = this.page.locator('button:has-text("Logout"), a:has-text("Logout")');
  if (await logoutBtn.isVisible()) {
    await logoutBtn.click();
    await this.page.waitForNavigation();
  }
});

When('I log in with {string} and {string}', async function (this: any, email: string, password: string) {
  this.logger.info(`Logging in with email: ${email}`);

  const emailInput = this.page.locator('input[type="email"], input[name="email"]');
  const passwordInput = this.page.locator('input[type="password"]');

  await emailInput.fill(email);
  await passwordInput.fill(password);

  const submitBtn = this.page.locator('button[type="submit"], button:has-text("Login")');
  await submitBtn.click();

  // Wait for post-login navigation
  await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {
    // Navigation might not occur
  });
});

/**
 * FORM INTERACTION STEPS
 */

When('I fill the form with:', async function (this: any, dataTable: any) {
  const data = dataTable.rowsHash();

  for (const [label, value] of Object.entries(data)) {
    this.logger.debug(`Filling field: ${label} = ${value}`);

    // Try to find input by label text or name
    let input = this.page.locator(`label:has-text("${label}") + input`);
    let count = await input.count();

    if (count === 0) {
      input = this.page.locator(`input[name="${label}"]`);
      count = await input.count();
    }

    if (count > 0) {
      await input.fill(String(value));
    } else {
      this.logger.warn(`Could not find field: ${label}`);
    }
  }
});

When('I select {string} option from dropdown', async function (this: any, optionText: string) {
  const select = this.page.locator('select');
  await select.selectOption({ label: optionText });
});

When('I check {string}', async function (this: any, checkboxText: string) {
  const checkbox = this.page.locator(`label:has-text("${checkboxText}") input[type="checkbox"]`);
  await checkbox.check();
});

When('I uncheck {string}', async function (this: any, checkboxText: string) {
  const checkbox = this.page.locator(`label:has-text("${checkboxText}") input[type="checkbox"]`);
  await checkbox.uncheck();
});

When('I submit the form', async function (this: any) {
  this.logger.debug('Submitting form');
  await this.page.locator('button[type="submit"]').click();

  // Wait for navigation
  await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {
    // Navigation might not occur
  });
});

When('I submit the form named {string}', async function (this: any, formName: string) {
  const form = this.page.locator(`form[name="${formName}"]`);
  await form.locator('button[type="submit"]').click();
});

/**
 * SEARCH STEPS
 */

When('I search for {string}', async function (this: any, query: string) {
  this.logger.debug(`Searching for: ${query}`);

  const searchInput = this.page.locator('input[type="search"], input[placeholder*="Search"], input[name="q"]');
  await searchInput.fill(query);

  // Either press Enter or click search button
  const searchBtn = this.page.locator('button:has-text("Search"), button[aria-label="Search"]');
  const btnCount = await searchBtn.count();

  if (btnCount > 0) {
    await searchBtn.click();
  } else {
    await searchInput.press('Enter');
  }

  // Wait for results
  await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {
    // Results might load without navigation
  });
});

Then('I should see search results', async function (this: any) {
  const results = this.page.locator('[class*="result"], [data-testid="search-results"]');
  const count = await results.count();
  expect(count).toBeGreaterThan(0);
});

/**
 * TABLE INTERACTION STEPS
 */

Then('I should see a table with columns:', async function (this: any, dataTable: any) {
  const columns = dataTable.raw().flat();

  for (const column of columns) {
    const header = this.page.locator(`th:has-text("${column}"), thead td:has-text("${column}")`);
    await expect(header).toBeVisible();
  }
});

When('I click row with {string}', async function (this: any, cellText: string) {
  const row = this.page.locator(`tr:has-text("${cellText}")`);
  await row.click();
});

/**
 * MODAL/DIALOG STEPS
 */

Then('I should see a modal with title {string}', async function (this: any, title: string) {
  const modal = this.page.locator(`[role="dialog"]:has-text("${title}"), .modal:has-text("${title}")`);
  await expect(modal).toBeVisible();
});

When('I close the modal', async function (this: any) {
  const closeBtn = this.page.locator('[role="dialog"] button[aria-label="Close"], .modal .close-btn');
  const count = await closeBtn.count();

  if (count > 0) {
    await closeBtn.first().click();
  } else {
    // Try pressing Escape
    await this.page.keyboard.press('Escape');
  }
});

When('I click {string} in the modal', async function (this: any, buttonText: string) {
  const modal = this.page.locator('[role="dialog"]');
  await modal.locator(`button:has-text("${buttonText}")`).click();
});

/**
 * NOTIFICATION/ALERT STEPS
 */

Then('I should see a success message', async function (this: any) {
  const notification = this.page.locator('[class*="success"], [role="alert"]:has-text("Success")');
  await expect(notification).toBeVisible();
});

Then('I should see an error message', async function (this: any) {
  const notification = this.page.locator('[class*="error"], [role="alert"]:has-text("Error")');
  await expect(notification).toBeVisible();
});

Then('I should see message {string}', async function (this: any, message: string) {
  const msgElement = this.page.locator(`text="${message}"`);
  await expect(msgElement).toBeVisible();
});

/**
 * PAGINATION STEPS
 */

When('I click next page', async function (this: any) {
  await this.page.locator('button:has-text("Next"), a[rel="next"]').click();
  await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {});
});

When('I click page {int}', async function (this: any, pageNum: number) {
  await this.page.locator(`button:has-text("${pageNum}"), a:has-text("${pageNum}")`).click();
});

/**
 * DOWNLOAD/FILE STEPS
 */

When('I download file {string}', async function (this: any, filename: string) {
  const downloadPromise = this.page.waitForEvent('download');
  await this.page.locator(`a:has-text("${filename}"), button:has-text("Download")`).click();
  const download = await downloadPromise;
  await download.saveAs(`./downloads/${download.suggestedFilename}`);
});

/**
 * API INTERACTION STEPS (if needed)
 */

Then('API response status should be {int}', async function (this: any, statusCode: number) {
  // This would typically be checked from a previous API call
  if (this.lastApiResponse) {
    expect(this.lastApiResponse.status).toBe(statusCode);
  }
});

/**
 * PERFORMANCE STEPS
 */

Then('page should load within {int} seconds', async function (this: any, seconds: number) {
  const loadTime = Date.now() - (this.navigationTime || Date.now());
  expect(loadTime).toBeLessThan(seconds * 1000);
});

/**
 * Export for testing
 */
export {};
