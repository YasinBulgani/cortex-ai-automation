/**
 * Paribu-Specific Step Definitions
 * Cryptocurrency trading platform specific steps
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { HomePage } from '../pages/HomePage';
import { LoginPage } from '../pages/LoginPage';
import { MarketPage } from '../pages/MarketPage';
import { ProfilePage } from '../pages/ProfilePage';

/**
 * PAGE NAVIGATION STEPS
 */

Given('I am on the Paribu home page', async function (this: any) {
  const homePage = new HomePage(this.page, this.logger);
  await this.page.goto('https://paribu.com');
  await homePage.waitForPageLoad();
  this.currentPage = homePage;
});

Given('I navigate to Paribu login page', async function (this: any) {
  await this.page.goto('https://paribu.com/login');
  const loginPage = new LoginPage(this.page, this.logger);
  await loginPage.waitForPageLoad();
  this.currentPage = loginPage;
});

When('I go to markets page', async function (this: any) {
  const homePage = new HomePage(this.page, this.logger);
  await homePage.goToMarkets();
  const marketPage = new MarketPage(this.page, this.logger);
  await marketPage.waitForPageLoad();
  this.currentPage = marketPage;
});

When('I go to trading page', async function (this: any) {
  const homePage = new HomePage(this.page, this.logger);
  await homePage.goToTrading();
});

When('I go to wallet page', async function (this: any) {
  const homePage = new HomePage(this.page, this.logger);
  await homePage.goToWallet();
});

/**
 * LOGIN STEPS
 */

When('I enter credentials and login', async function (this: any) {
  const loginPage = new LoginPage(this.page, this.logger);
  const testData = this.testData || {};
  const email = testData.email || 'test@example.com';
  const password = testData.password || 'TestPassword123!';

  await loginPage.login(email, password);
});

When('I login with {string} and {string}', async function (this: any, email: string, password: string) {
  const loginPage = new LoginPage(this.page, this.logger);
  await loginPage.login(email, password);
});

Then('login should be successful', async function (this: any) {
  await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {});
  const url = this.page.url();
  if (url.includes('login')) {
    throw new Error('Login failed - still on login page');
  }
});

Then('login error message should appear', async function (this: any) {
  const loginPage = new LoginPage(this.page, this.logger);
  const isError = await loginPage.isErrorMessageVisible();
  if (!isError) {
    throw new Error('Expected error message but none appeared');
  }
});

/**
 * CRYPTO/MARKET STEPS
 */

When('I search for {string}', async function (this: any, cryptoName: string) {
  const homePage = new HomePage(this.page, this.logger);
  await homePage.searchCrypto(cryptoName);
});

Then('search results should show {string}', async function (this: any, cryptoName: string) {
  const pageText = await this.page.textContent('body');
  if (!pageText?.includes(cryptoName)) {
    throw new Error(`Expected "${cryptoName}" in search results`);
  }
});

When('I view the markets', async function (this: any) {
  const homePage = new HomePage(this.page, this.logger);
  await homePage.goToMarkets();
  const marketPage = new MarketPage(this.page, this.logger);
  await marketPage.waitForPageLoad();
  this.currentPage = marketPage;
});

Then('market table should be visible', async function (this: any) {
  const marketPage = new MarketPage(this.page, this.logger);
  const isVisible = await marketPage.isTableVisible();
  if (!isVisible) {
    throw new Error('Market table not visible');
  }
});

Then('market should have {int} or more cryptocurrencies', async function (this: any, minCount: number) {
  const marketPage = new MarketPage(this.page, this.logger);
  const count = await marketPage.getMarketTableRowCount();
  if (count < minCount) {
    throw new Error(`Expected at least ${minCount} cryptocurrencies, got ${count}`);
  }
});

When('I get the price for {string}', async function (this: any, cryptoName: string) {
  const marketPage = new MarketPage(this.page, this.logger);
  const price = await marketPage.getPriceForCrypto(cryptoName);
  this.lastPrice = price;
});

Then('the price should be available', async function (this: any) {
  if (!this.lastPrice) {
    throw new Error('Price not available');
  }
});

/**
 * PROFILE/ACCOUNT STEPS
 */

// NOT: 'I am logged in as {string}' adımı web-steps.ts içinde tanımlı (genel login).
// Paribu'ya özel login için 'I login with {string} and {string}' adımını kullanın.

When('I go to my profile', async function (this: any) {
  await this.page.goto('https://paribu.com/profile');
  const profilePage = new ProfilePage(this.page, this.logger);
  await profilePage.waitForPageLoad();
  this.currentPage = profilePage;
});

Then('profile information should be displayed', async function (this: any) {
  const profilePage = new ProfilePage(this.page, this.logger);
  const userName = await profilePage.getUserName();
  if (!userName) {
    throw new Error('User name not displayed');
  }
});

When('I logout', async function (this: any) {
  const profilePage = new ProfilePage(this.page, this.logger);
  await profilePage.clickLogout();
});

Then('I should be logged out', async function (this: any) {
  const url = this.page.url();
  if (!url.includes('login') && !url.includes('home')) {
    throw new Error('Not logged out');
  }
});

/**
 * FEATURED CRYPTOS STEPS
 */

Then('featured markets should be visible', async function (this: any) {
  const homePage = new HomePage(this.page, this.logger);
  const isVisible = await homePage.areFeaturedMarketsVisible();
  if (!isVisible) {
    throw new Error('Featured markets not visible');
  }
});

Then('featured markets should contain at least {int} cryptocurrencies', async function (this: any, minCount: number) {
  const homePage = new HomePage(this.page, this.logger);
  const count = await homePage.getFeaturedMarketsCount();
  if (count < minCount) {
    throw new Error(`Expected at least ${minCount} featured cryptos, got ${count}`);
  }
});

Then('I should see {string} in featured markets', async function (this: any, cryptoSymbol: string) {
  const homePage = new HomePage(this.page, this.logger);
  const symbols = await homePage.getFeaturedCryptoSymbols();
  if (!symbols.includes(cryptoSymbol)) {
    throw new Error(`${cryptoSymbol} not found in featured markets`);
  }
});

/**
 * Export
 */
export {};
