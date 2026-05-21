import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { PlaywrightWorld } from './playwright-world';
import { ParibuHomePage } from '../pages/ParibuHomePage';
import { MarketsPage } from '../pages/MarketsPage';
import { CryptocurrencyDetailPage } from '../pages/CryptocurrencyDetailPage';
import { LoginPage } from '../pages/LoginPage';
import { Logger } from '../utils/Logger';
import { PageNotInitializedError, InvalidDataError } from '../utils/CustomErrors';

let homePage: ParibuHomePage;
let marketsPage: MarketsPage;
let detailPage: CryptocurrencyDetailPage;
let loginPage: LoginPage;
let unitPrice: number;
let quantity: number;

// ============================================================================
// Calculation Check Scenario Steps
// ============================================================================

/**
 * Step: I navigate to Paribu homepage
 * Paribu ana sayfasına gider (Background'da kullanılır)
 */
Given('I navigate to Paribu homepage', async function (this: PlaywrightWorld) {
  // Use 'paribu' environment for Paribu website
  const originalEnv = this.environment;
  this.environment = 'paribu';
  
  homePage = new ParibuHomePage(this.page, this.environment);
  await homePage.open();
  
  // Restore original environment if needed
  this.environment = originalEnv;
});

/**
 * Step: I close the cookie notice if present
 * Cookie bildirimini kapatır (Background'da kullanılır)
 */
Given('I close the cookie notice if present', async function (this: PlaywrightWorld) {
  await homePage.closeCookieNotice();
});

When('I navigate to the Markets page', async function (this: PlaywrightWorld) {
  await homePage.navigateToMarkets();
  marketsPage = new MarketsPage(this.page, 'paribu');
});

When('I select the {string} filter', async function (this: PlaywrightWorld, filterName: string) {
  if (!marketsPage) {
    throw new PageNotInitializedError('MarketsPage', 'navigate to Markets page');
  }
  
  if (filterName === 'FAN') {
    await marketsPage.selectFanFilter();
  } else {
    throw new Error(`Filter "${filterName}" is not implemented. Please add support for this filter.`);
  }
});

When(/^I click on the (\d+)(?:st|nd|rd|th) cryptocurrency in the list$/, async function (this: PlaywrightWorld, index: string) {
  if (!marketsPage) {
    throw new PageNotInitializedError('MarketsPage', 'navigate to Markets page');
  }
  
  const indexNum = parseInt(index, 10);
  if (isNaN(indexNum) || indexNum < 1) {
    throw new Error(`Invalid index: ${index}. Index must be a positive number.`);
  }
  
  await marketsPage.clickCryptocurrencyByIndex(indexNum);
  detailPage = new CryptocurrencyDetailPage(this.page, 'paribu');
});

When('I enter unit price {string} in the Buy-Sell panel', async function (this: PlaywrightWorld, price: string) {
  unitPrice = parseFloat(price);
  await detailPage.enterUnitPrice(unitPrice);
});

When('I enter quantity {string} in the Buy-Sell panel', async function (this: PlaywrightWorld, qty: string) {
  quantity = parseFloat(qty);
  await detailPage.enterQuantity(quantity);
});

Then('the total price should display the correct calculation result', async function (this: PlaywrightWorld) {
  if (!detailPage) {
    throw new PageNotInitializedError('CryptocurrencyDetailPage', 'navigate to detail page');
  }
  
  if (unitPrice === undefined || quantity === undefined) {
    throw new Error('Unit price or quantity is not set. Please enter unit price and quantity first.');
  }
  
  // Beklenen toplam = birim fiyat * miktar
  const expectedTotalValue = unitPrice * quantity;
  
  const isCorrect = await detailPage.verifyTotalPriceCalculation(unitPrice, quantity, expectedTotalValue);
  
  // Assertion at the end of scenario
  expect(isCorrect).toBe(true);
  
  // Additional assertion: Get actual displayed value for better error messages
  const displayedTotal = await detailPage.getTotalPrice();
  expect(displayedTotal).toBeCloseTo(expectedTotalValue, 2);
});

When('I set the time filter to {string}', async function (this: PlaywrightWorld, timeFilter: string) {
  if (!marketsPage) {
    throw new PageNotInitializedError('MarketsPage', 'navigate to Markets page');
  }
  
  if (timeFilter === '12 Saat' || timeFilter === '12h' || timeFilter === '12 hours') {
    await marketsPage.setTimeFilterTo12Hours();
  } else {
    throw new Error(`Time filter "${timeFilter}" is not implemented. Please add support for this filter.`);
  }
});

When('I click the {string} button to fill unit price', async function (this: PlaywrightWorld, buttonText: string) {
  if (!detailPage) {
    throw new PageNotInitializedError('CryptocurrencyDetailPage', 'navigate to detail page');
  }
  
  if (buttonText === 'Güncel Fiyat' || buttonText === 'Current Price') {
    await detailPage.clickCurrentPriceButton();
    // Birim fiyat değerini al (public method kullanarak)
    unitPrice = await detailPage.getUnitPrice();
  } else {
    throw new Error(`Button "${buttonText}" is not implemented.`);
  }
});

// Invalid Login Scenario Steps

When('I navigate to the Login page', async function (this: PlaywrightWorld) {
  await homePage.navigateToLogin();
  loginPage = new LoginPage(this.page, 'paribu');
});

When('I enter invalid country code {string}', async function (this: PlaywrightWorld, countryCode: string) {
  // Paribu login sayfasında country code ayrı bir alan olmayabilir
  // Bu durumda bu step'i skip edebiliriz veya telefon numarasına dahil edebiliriz
  try {
    await loginPage.enterCountryCode(countryCode);
  } catch (error) {
    // Country code alanı yoksa, bu step'i skip et
    Logger.debug('Country code input not found, skipping country code entry');
  }
});

When('I enter invalid mobile number {string}', async function (this: PlaywrightWorld, mobileNumber: string) {
  await loginPage.enterMobileNumber(mobileNumber);
});

When('I enter invalid password {string}', async function (this: PlaywrightWorld, password: string) {
  await loginPage.enterPassword(password);
});

When('I click the Login button', async function (this: PlaywrightWorld) {
  await loginPage.clickLoginButton();
});

Then('an error message should appear', async function (this: PlaywrightWorld) {
  if (!loginPage) {
    throw new PageNotInitializedError('LoginPage', 'navigate to Login page');
  }
  
  // Assertion at the end of scenario
  const isVisible = await loginPage.isErrorMessageVisible();
  expect(isVisible).toBe(true);
});

Then('the error message should contain {string}', async function (this: PlaywrightWorld, expectedText: string) {
  if (!loginPage) {
    throw new PageNotInitializedError('LoginPage', 'navigate to Login page');
  }
  
  if (!expectedText || expectedText.trim().length === 0) {
    throw new Error('Expected text cannot be empty.');
  }
  
  // Assertion at the end of scenario
  const containsText = await loginPage.verifyErrorMessageContains(expectedText);
  expect(containsText).toBe(true);
  
  // Additional assertion: Get actual error message for better error messages
  const errorMessage = await loginPage.getErrorMessageText();
  expect(errorMessage.toLowerCase()).toContain(expectedText.toLowerCase());
});

// Sorting and Form Control Scenario Steps

let selectedCoinIndices: number[] = [];

When('I sort by price in descending order', async function (this: PlaywrightWorld) {
  if (!marketsPage) {
    throw new PageNotInitializedError('MarketsPage', 'navigate to Markets page');
  }
  
  await marketsPage.sortByPriceDescending();
});

When('I select {int} random coins with positive 24h change', async function (this: PlaywrightWorld, count: number) {
  if (!marketsPage) {
    throw new PageNotInitializedError('MarketsPage', 'navigate to Markets page');
  }
  
  if (count < 1) {
    throw new InvalidDataError('count', count, 'Count must be a positive number');
  }
  
  selectedCoinIndices = await marketsPage.selectRandomCoinsWithPositive24hChange(count);
  
  if (selectedCoinIndices.length === 0) {
    throw new Error('No coins with positive 24h change found.');
  }
  
  Logger.info(`Selected ${selectedCoinIndices.length} coins with positive 24h change: ${selectedCoinIndices.join(', ')}`);
});

When('I click on the first selected cryptocurrency', async function (this: PlaywrightWorld) {
  if (!marketsPage) {
    throw new PageNotInitializedError('MarketsPage', 'navigate to Markets page');
  }
  
  if (selectedCoinIndices.length === 0) {
    throw new Error('No coins selected. Please select coins with positive 24h change first.');
  }
  
  const firstIndex = selectedCoinIndices[0];
  await marketsPage.clickCryptocurrencyByIndex(firstIndex);
  detailPage = new CryptocurrencyDetailPage(this.page, 'paribu');
});

// Store expected total quantity for verification (Case Study requirement)
let expectedTotalQuantity: number | undefined;

/**
 * Step: I click on a pending buy order from the list
 * Bekleyen alış emirlerinden birine tıklar ve toplam miktarı hesaplar
 * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
 */
When('I click on a pending buy order from the list', async function (this: PlaywrightWorld) {
  if (!detailPage) {
    throw new PageNotInitializedError('CryptocurrencyDetailPage', 'navigate to detail page');
  }
  
  // Case Study gereksinimi: İlk bekleyen alış emrine tıkla ve toplam miktarı al
  // Quantity input represents the total amount from all orders up to the selected row
  expectedTotalQuantity = await detailPage.clickPendingBuyOrder(1);
  Logger.info(`Expected total quantity from buy orders: ${expectedTotalQuantity}`);
});

/**
 * Step: I click on a pending sell order from the list
 * Bekleyen satış emirlerinden birine tıklar ve toplam miktarı hesaplar
 * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
 */
When('I click on a pending sell order from the list', async function (this: PlaywrightWorld) {
  if (!detailPage) {
    throw new PageNotInitializedError('CryptocurrencyDetailPage', 'navigate to detail page');
  }
  
  // Case Study gereksinimi: İlk bekleyen satış emrine tıkla ve toplam miktarı al
  // Quantity input represents the total amount from all orders up to the selected row
  expectedTotalQuantity = await detailPage.clickPendingSellOrder(1);
  Logger.info(`Expected total quantity from sell orders: ${expectedTotalQuantity}`);
});

/**
 * Step: the data should be correctly moved to the {string} tab
 * Verilerin doğru tab'a taşındığını ve quantity input'un toplam miktarı doğru gösterdiğini doğrular
 * Case Study Not: Quantity input represents the total amount from all orders up to the selected row
 * @param tabName - Tab adı ("Alış" veya "Satış")
 */
Then('the data should be correctly moved to the {string} tab', async function (this: PlaywrightWorld, tabName: string) {
  if (!detailPage) {
    throw new PageNotInitializedError('CryptocurrencyDetailPage', 'navigate to detail page');
  }
  
  let isCorrect = false;
  
  // Case Study gereksinimi: Quantity input'un toplam miktarı doğru gösterdiğini doğrula
  if (tabName === 'Satış' || tabName === 'Sell') {
    isCorrect = await detailPage.verifyDataMovedToSellTab(expectedTotalQuantity);
  } else if (tabName === 'Alış' || tabName === 'Buy') {
    isCorrect = await detailPage.verifyDataMovedToBuyTab(expectedTotalQuantity);
  } else {
    throw new Error(`Tab "${tabName}" is not recognized. Use "Alış" or "Satış".`);
  }
  
  // Assertion at the end of scenario
  expect(isCorrect).toBe(true);
});

