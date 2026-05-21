/**
 * Common Step Definitions for BDD Tests
 *
 * Shared steps used across multiple feature files
 * Covers navigation, waiting, assertions, and common interactions
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { BasePage } from '../pages/BasePage';

/**
 * NAVIGATION STEPS
 */

Given('the application is started', async function (this: any) {
  this.logger.info('Application started');
  // Can be overridden by specific page objects
});

Given('I navigate to {string}', async function (this: any, url: string) {
  this.logger.info(`Navigating to: ${url}`);
  await this.page.goto(url, { waitUntil: 'networkidle' });
});

When('I navigate to {string}', async function (this: any, url: string) {
  this.logger.info(`Navigating to: ${url}`);
  await this.page.goto(url, { waitUntil: 'networkidle' });
});

When('I go to URL {string}', async function (this: any, url: string) {
  await this.page.goto(url, { waitUntil: 'networkidle' });
});

/**
 * CLICK STEPS
 */

When('I click on {string}', async function (this: any, selector: string) {
  this.logger.debug(`Clicking element: ${selector}`);
  await this.page.locator(selector).click({ timeout: this.timeout });
});

When('I click the {string} button', async function (this: any, buttonText: string) {
  await this.page.locator(`button:has-text("${buttonText}")`).click();
});

When('I click the {string} link', async function (this: any, linkText: string) {
  await this.page.locator(`a:has-text("${linkText}")`).click();
});

/**
 * FILL INPUT STEPS
 */

When('I fill {string} with {string}', async function (this: any, selector: string, text: string) {
  this.logger.debug(`Filling ${selector} with text`);
  await this.page.locator(selector).fill(text);
});

When('I enter {string} in {string}', async function (this: any, text: string, selector: string) {
  await this.page.locator(selector).fill(text);
});

When('I type {string} in {string}', async function (this: any, text: string, selector: string) {
  await this.page.locator(selector).type(text, { delay: 50 });
});

/**
 * CLEAR STEPS
 */

When('I clear {string}', async function (this: any, selector: string) {
  await this.page.locator(selector).clear();
});

When('I clear the input field {string}', async function (this: any, selector: string) {
  await this.page.locator(selector).clear();
});

/**
 * WAIT STEPS
 */

/**
 * `I wait for N seconds` — DEPRECATED, flake üretir.
 *
 * Playwright auto-wait zaten locator action'larında işliyor. Bu step tipik
 * olarak "animasyon bitsin diye bekleyeyim" ihtiyacından kaynaklanır;
 * doğru çözüm:
 *   - `I wait for "selector" to be visible`
 *   - `I wait for network to be idle`
 *   - `expect(locator).toHaveText(...)` (auto-retry)
 *
 * Geriye dönük uyumluluk için silinmedi; bunun yerine:
 *   1) Üst limit 10sn — 10+ saniye bekleyen step'ler fail olur
 *   2) Kullanıldığında WARN log — rapora yansır, sprint'te temizlenir
 */
When('I wait for {int} seconds', async function (this: any, seconds: number) {
  if (seconds < 0) {
    throw new Error(`Negative wait (${seconds}s) not allowed`);
  }
  if (seconds > 10) {
    throw new Error(
      `Hard wait of ${seconds}s reddedildi. 10s üzeri bekleme için ` +
      `'I wait for "selector" to be visible' ya da network/assertion ` +
      `bekleme step'lerini kullanın.`
    );
  }
  this.logger.warn(
    `[deprecated] 'I wait for ${seconds} seconds' — flake üretir. ` +
    `Locator/assertion bekleme step'lerine geçin.`
  );
  await this.page.waitForTimeout(seconds * 1000);
});

When('I wait for {string} to be visible', async function (this: any, selector: string) {
  this.logger.debug(`Waiting for ${selector} to be visible`);
  await this.page.locator(selector).waitFor({ state: 'visible', timeout: this.timeout });
});

When('I wait for {string} to be hidden', async function (this: any, selector: string) {
  await this.page.locator(selector).waitFor({ state: 'hidden', timeout: this.timeout });
});

When('I wait for text {string} to appear', async function (this: any, text: string) {
  await this.page.waitForFunction(
    (searchText) => document.body.innerText.includes(searchText),
    text,
    { timeout: this.timeout }
  );
});

/**
 * ASSERTION STEPS - Element Visibility
 */

Then('{string} should be visible', async function (this: any, selector: string) {
  this.logger.debug(`Asserting ${selector} is visible`);
  await expect(this.page.locator(selector)).toBeVisible({ timeout: this.timeout });
});

Then('{string} should not be visible', async function (this: any, selector: string) {
  await expect(this.page.locator(selector)).not.toBeVisible();
});

Then('{string} should be hidden', async function (this: any, selector: string) {
  await expect(this.page.locator(selector)).toBeHidden();
});

/**
 * ASSERTION STEPS - Element Enabled/Disabled
 */

Then('{string} should be enabled', async function (this: any, selector: string) {
  await expect(this.page.locator(selector)).toBeEnabled();
});

Then('{string} should be disabled', async function (this: any, selector: string) {
  await expect(this.page.locator(selector)).toBeDisabled();
});

/**
 * ASSERTION STEPS - Text Content
 */

Then('{string} should have text {string}', async function (this: any, selector: string, text: string) {
  this.logger.debug(`Asserting ${selector} contains "${text}"`);
  await expect(this.page.locator(selector)).toContainText(text, { timeout: this.timeout });
});

Then('{string} should contain {string}', async function (this: any, selector: string, text: string) {
  await expect(this.page.locator(selector)).toContainText(text);
});

Then('page should contain {string}', async function (this: any, text: string) {
  this.logger.debug(`Asserting page contains "${text}"`);
  const pageText = await this.page.textContent('body');
  expect(pageText).toContain(text);
});

Then('page should not contain {string}', async function (this: any, text: string) {
  const pageText = await this.page.textContent('body');
  expect(pageText).not.toContain(text);
});

/**
 * ASSERTION STEPS - Input Values
 */

Then('{string} should have value {string}', async function (this: any, selector: string, value: string) {
  await expect(this.page.locator(selector)).toHaveValue(value);
});

Then('{string} should have attribute {string} with value {string}',
  async function (this: any, selector: string, attr: string, value: string) {
    await expect(this.page.locator(selector)).toHaveAttribute(attr, value);
  }
);

/**
 * ASSERTION STEPS - Count
 */

Then('{string} should exist', async function (this: any, selector: string) {
  const count = await this.page.locator(selector).count();
  expect(count).toBeGreaterThan(0);
});

Then('{string} should not exist', async function (this: any, selector: string) {
  const count = await this.page.locator(selector).count();
  expect(count).toBe(0);
});

Then('{string} count should be {int}', async function (this: any, selector: string, count: number) {
  await expect(this.page.locator(selector)).toHaveCount(count);
});

/**
 * PAGE STATE STEPS
 */

Then('page title should be {string}', async function (this: any, title: string) {
  await expect(this.page).toHaveTitle(title);
});

Then('page URL should contain {string}', async function (this: any, url: string) {
  this.logger.debug(`Asserting URL contains "${url}"`);
  await expect(this.page).toHaveURL(new RegExp(url));
});

Then('page URL should be {string}', async function (this: any, url: string) {
  await expect(this.page).toHaveURL(url);
});

/**
 * HOVER STEPS
 */

When('I hover over {string}', async function (this: any, selector: string) {
  await this.page.locator(selector).hover();
});

When('I scroll to {string}', async function (this: any, selector: string) {
  await this.page.locator(selector).scrollIntoViewIfNeeded();
});

/**
 * SELECT STEPS
 */

When('I select {string} from {string}', async function (this: any, optionText: string, selector: string) {
  await this.page.locator(selector).selectOption({ label: optionText });
});

When('I select value {string} from {string}', async function (this: any, value: string, selector: string) {
  await this.page.locator(selector).selectOption(value);
});

/**
 * KEYBOARD STEPS
 */

When('I press {string}', async function (this: any, key: string) {
  this.logger.debug(`Pressing key: ${key}`);
  await this.page.keyboard.press(key);
});

When('I press {string} in {string}', async function (this: any, key: string, selector: string) {
  await this.page.locator(selector).press(key);
});

When('I press Enter', async function (this: any) {
  await this.page.keyboard.press('Enter');
});

When('I press Escape', async function (this: any) {
  await this.page.keyboard.press('Escape');
});

/**
 * REFRESH STEPS
 */

When('I refresh the page', async function (this: any) {
  this.logger.debug('Refreshing page');
  await this.page.reload({ waitUntil: 'networkidle' });
});

When('I go back', async function (this: any) {
  await this.page.goBack({ waitUntil: 'networkidle' });
});

When('I go forward', async function (this: any) {
  await this.page.goForward({ waitUntil: 'networkidle' });
});

/**
 * SCREENSHOT STEPS
 */

When('I take a screenshot named {string}', async function (this: any, name: string) {
  this.logger.debug(`Taking screenshot: ${name}`);
  await this.page.screenshot({ path: `./screenshots/${name}.png`, fullPage: true });
});

/**
 * DATA TABLE STEPS
 */

Given('I have the following data:', async function (this: any, dataTable: any) {
  const data = dataTable.rowsHash();
  this.testData = data;
  this.logger.debug('Test data loaded', { count: Object.keys(data).length });
});

/**
 * Export for testing
 */
export {};
