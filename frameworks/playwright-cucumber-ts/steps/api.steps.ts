import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { PlaywrightWorld } from './playwright-world';
import { DummyJsonApi, LoginResponse, ProductsResponse } from '../utils/DummyJsonApi';
import { TestDataLoader } from '../utils/TestDataLoader';
import { Logger } from '../utils/Logger';
import { InvalidDataError } from '../utils/CustomErrors';
import { LIMITS } from '../config/constants';

let apiClient: DummyJsonApi;
let loginCredentials: { username: string; password: string };
let productsResponse: ProductsResponse;
let firstProductId: number;
let updateResponse: unknown;
let deleteResponse: unknown;

// ============================================================================
// Login & Token Management Steps
// ============================================================================

/**
 * Step: I have valid login credentials
 * Test data'dan rastgele geçerli kullanıcı seçer
 */
Given('I have valid login credentials', async function (this: PlaywrightWorld) {
  // Test data'dan rastgele geçerli kullanıcı seç
  const user = TestDataLoader.getRandomValidUser();
  loginCredentials = {
    username: user.username,
    password: user.password
  };
});

/**
 * Step: I have invalid login credentials
 * Test data'dan rastgele geçersiz kullanıcı seçer
 */
Given('I have invalid login credentials', async function (this: PlaywrightWorld) {
  // Test data'dan rastgele geçersiz kullanıcı seç
  const user = TestDataLoader.getRandomInvalidUser();
  loginCredentials = {
    username: user.username,
    password: user.password
  };
});

/**
 * Step: I perform a login request
 * DummyJSON API'ye login isteği gönderir ve response'u saklar
 */
When('I perform a login request', async function (this: PlaywrightWorld) {
  if (!loginCredentials || !loginCredentials.username || !loginCredentials.password) {
    throw new Error('Login credentials are not set. Please set valid or invalid credentials first.');
  }
  
  Logger.info('Performing login request', { username: loginCredentials.username });
  apiClient = new DummyJsonApi(this.apiContext);
  const response = await apiClient.login(loginCredentials);
  this.lastStatusCode = response.status();
  this.lastResponse = await response.json();
  
  // Debug: Log response for troubleshooting
  if (this.lastStatusCode !== 200) {
    Logger.error('Login failed', { 
      status: this.lastStatusCode, 
      response: this.lastResponse,
      credentials: { username: loginCredentials.username }
    });
  }
});

Then('the login response status code should be {int}', async function (this: PlaywrightWorld, expectedStatusCode: number) {
  expect(this.lastStatusCode).toBe(expectedStatusCode);
});

// Handle scenario outline pattern <statusCode>
Then('the login response status code should be <statusCode>', async function (this: PlaywrightWorld, expectedStatusCode: number) {
  expect(this.lastStatusCode).toBe(expectedStatusCode);
});

// Unified step definition for both positive and negative cases (including scenario outline)
// Handles: "the response should contain an access token" and "the response should not contain an access token"
// Also handles scenario outline with spaces: "the response should  contain an access token"
Then(/^the response should\s+(not\s+)?contain an access token$/, async function (this: PlaywrightWorld, notKeyword: string | undefined) {
  const response = this.lastResponse as LoginResponse | Record<string, unknown>;
  if (notKeyword && notKeyword.trim() === 'not') {
    expect(response).not.toHaveProperty('accessToken');
    expect(response).not.toHaveProperty('token');
  } else {
    const loginResponse = response as LoginResponse;
    // DummyJSON API returns 'token' field, not 'accessToken'
    const token = loginResponse.token || loginResponse.accessToken;
    expect(token).toBeTruthy();
    expect(typeof token).toBe('string');
  }
});

Then('I store the access token for subsequent requests', async function (this: PlaywrightWorld) {
  const response = this.lastResponse as LoginResponse;
  // DummyJSON API returns 'token' field, not 'accessToken'
  this.accessToken = response.token || response.accessToken || null;
  if (!this.accessToken) {
    Logger.error('Token not found in response', { response });
    throw new Error('Access token not found in response');
  }
  expect(this.accessToken).toBeTruthy();
  Logger.debug('Access token stored successfully');
});

// Products List Steps

Given('I have a valid access token', async function (this: PlaywrightWorld) {
  // If token doesn't exist, perform login first
  if (!this.accessToken) {
    apiClient = new DummyJsonApi(this.apiContext);
    // Test data'dan geçerli kullanıcı seç
    const user = TestDataLoader.getRandomValidUser();
    const response = await apiClient.login({
      username: user.username,
      password: user.password
    });
    this.lastStatusCode = response.status();
    
    if (response.status() !== 200) {
      throw new Error(`Login failed with status ${response.status()}`);
    }
    
    const loginResponse = await response.json() as LoginResponse;
    // DummyJSON API returns 'token' field, not 'accessToken'
    this.accessToken = loginResponse.token || loginResponse.accessToken || null;
    
    if (!this.accessToken) {
      Logger.error('Token not found in login response', { response: loginResponse });
      throw new Error('Access token not found in login response');
    }
    
    Logger.debug('Access token obtained successfully');
  }
  expect(this.accessToken).toBeTruthy();
});

When('I request the products list with limit {int}', async function (this: PlaywrightWorld, limit: number) {
  if (!this.accessToken) {
    throw new Error('Access token is not available. Please login first.');
  }
  
  if (limit < LIMITS.PRODUCT_LIMIT_MIN || limit > LIMITS.PRODUCT_LIMIT_MAX) {
    throw new InvalidDataError('limit', limit, `Limit must be between ${LIMITS.PRODUCT_LIMIT_MIN} and ${LIMITS.PRODUCT_LIMIT_MAX}`);
  }
  
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  const response = await apiClient.getProducts(this.accessToken, limit);
  this.lastStatusCode = response.status();
  productsResponse = await response.json() as ProductsResponse;
  this.lastResponse = productsResponse;
});

Then('the response status code should be {int}', async function (this: PlaywrightWorld, expectedStatusCode: number) {
  expect(this.lastStatusCode).toBe(expectedStatusCode);
});

Then('the products array length should match the limit {int}', async function (this: PlaywrightWorld, expectedLimit: number) {
  expect(productsResponse).toHaveProperty('products');
  expect(Array.isArray(productsResponse.products)).toBe(true);
  expect(productsResponse.products.length).toBe(expectedLimit);
  expect(productsResponse.limit).toBe(expectedLimit);
});

// Update & Delete Flow Steps

Then('I store the first product ID', async function (this: PlaywrightWorld) {
  expect(productsResponse).toHaveProperty('products');
  expect(productsResponse.products.length).toBeGreaterThan(0);
  firstProductId = productsResponse.products[0].id;
  expect(firstProductId).toBeTruthy();
});

When('I update the title of the first product to {string}', async function (this: PlaywrightWorld, newTitle: string) {
  if (!this.accessToken) {
    throw new Error('Access token is not available. Please login first.');
  }
  
  if (!firstProductId) {
    throw new Error('Product ID is not stored. Please request products list and store first product ID first.');
  }
  
  if (!newTitle || newTitle.trim().length === 0) {
    throw new Error('New title cannot be empty.');
  }
  
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  const response = await apiClient.updateProduct(firstProductId, this.accessToken, {
    title: newTitle
  });
  this.lastStatusCode = response.status();
  updateResponse = await response.json();
  this.lastResponse = updateResponse;
});

Then('the update response status code should be {int}', async function (this: PlaywrightWorld, expectedStatusCode: number) {
  expect(this.lastStatusCode).toBe(expectedStatusCode);
});

When('I delete the first product', async function (this: PlaywrightWorld) {
  if (!this.accessToken) {
    throw new Error('Access token is not available. Please login first.');
  }
  
  if (!firstProductId) {
    throw new Error('Product ID is not stored. Please request products list and store first product ID first.');
  }
  
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  const response = await apiClient.deleteProduct(firstProductId, this.accessToken);
  this.lastStatusCode = response.status();
  deleteResponse = await response.json();
  this.lastResponse = deleteResponse;
});

Then('the delete response status code should be {int}', async function (this: PlaywrightWorld, expectedStatusCode: number) {
  expect(this.lastStatusCode).toBe(expectedStatusCode);
});

// Scenario Outline Steps
Given('I have login credentials with username {string} and password {string}', async function (this: PlaywrightWorld, username: string, password: string) {
  loginCredentials = { username, password };
});

// isDeleted Update Steps
When('I update the isDeleted field of the first product to {string}', async function (this: PlaywrightWorld, isDeletedValue: string) {
  if (!this.accessToken) {
    throw new Error('Access token is not available. Please login first.');
  }
  
  if (!firstProductId) {
    throw new Error('Product ID is not stored. Please request products list and store first product ID first.');
  }
  
  const isDeleted = isDeletedValue.toLowerCase() === 'true';
  
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  const response = await apiClient.updateProductIsDeleted(firstProductId, this.accessToken, isDeleted);
  this.lastStatusCode = response.status();
  updateResponse = await response.json();
  this.lastResponse = updateResponse;
});

When('I update the isDeleted field of the first product to true', async function (this: PlaywrightWorld) {
  if (!this.accessToken) {
    throw new Error('Access token is not available. Please login first.');
  }
  
  if (!firstProductId) {
    throw new Error('Product ID is not stored. Please request products list and store first product ID first.');
  }
  
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  const response = await apiClient.updateProductIsDeleted(firstProductId, this.accessToken, true);
  this.lastStatusCode = response.status();
  updateResponse = await response.json();
  this.lastResponse = updateResponse;
});

Then('the response should contain isDeleted field as {string}', async function (this: PlaywrightWorld, expectedValue: string) {
  const response = updateResponse as Record<string, unknown>;
  expect(response).toHaveProperty('isDeleted');
  const isDeleted = response.isDeleted as boolean;
  const expected = expectedValue.toLowerCase() === 'true';
  expect(isDeleted).toBe(expected);
});

Then('the response should contain isDeleted field as true', async function (this: PlaywrightWorld) {
  const response = updateResponse as Record<string, unknown>;
  expect(response).toHaveProperty('isDeleted');
  const isDeleted = response.isDeleted as boolean;
  expect(isDeleted).toBe(true);
});

// Categories Steps
let categoriesList: string[] = [];

When('I request the products categories list', async function (this: PlaywrightWorld) {
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  const response = await apiClient.getCategories();
  this.lastStatusCode = response.status();
  const categories = await response.json() as string[];
  categoriesList = categories;
  this.lastResponse = categories;
});

Then('I verify each category endpoint returns {int} OK', async function (this: PlaywrightWorld, expectedStatusCode: number) {
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  
  if (categoriesList.length === 0) {
    throw new Error('Categories list is empty. Please request categories list first.');
  }
  
  // Her kategori için ürün listesini kontrol et
  for (const category of categoriesList) {
    try {
      const response = await apiClient.getProductsByCategory(category, 1);
      const statusCode = response.status();
      expect(statusCode).toBe(expectedStatusCode);
      Logger.info(`Category "${category}" returned ${statusCode}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Category "${category}" failed: ${errorMessage}`);
    }
  }
});

// Performance/Timeout Steps
let responseStartTime: number = 0;
let responseEndTime: number = 0;

When('I perform a login request with delay parameter {int}', async function (this: PlaywrightWorld, delay: number) {
  if (!loginCredentials || !loginCredentials.username || !loginCredentials.password) {
    throw new Error('Login credentials are not set. Please set valid credentials first.');
  }
  
  if (!apiClient) {
    apiClient = new DummyJsonApi(this.apiContext);
  }
  
  responseStartTime = Date.now();
  const response = await apiClient.loginWithDelay(loginCredentials, delay);
  responseEndTime = Date.now();
  
  this.lastResponse = await response.json();
  this.lastStatusCode = response.status();
});

Then('the login response time should be less than {int} milliseconds', async function (this: PlaywrightWorld, maxTime: number) {
  const responseTime = responseEndTime - responseStartTime;
  expect(responseTime).toBeLessThan(maxTime);
  Logger.info(`Response time: ${responseTime}ms (max: ${maxTime}ms)`);
});

