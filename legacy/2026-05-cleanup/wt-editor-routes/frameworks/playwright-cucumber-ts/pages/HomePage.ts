/**
 * Home Page Object Model
 * Represents Paribu home page
 */

import { Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { Logger } from '../utils/Logger';

export class HomePage extends BasePage {
  // Locators
  readonly searchInput = this.page.locator('input[type="search"], input[placeholder*="Search"]');
  readonly searchButton = this.page.locator('button:has-text("Search"), button[aria-label="Search"]');
  readonly marketsLink = this.page.locator('a:has-text("Markets")');
  readonly tradingLink = this.page.locator('a:has-text("Trading")');
  readonly walletLink = this.page.locator('a:has-text("Wallet")');
  readonly loginButton = this.page.locator('button:has-text("Login"), a:has-text("Login")');
  readonly signupButton = this.page.locator('button:has-text("Sign Up"), a:has-text("Sign Up")');
  readonly featuredMarkets = this.page.locator('[data-testid="featured-markets"], .featured-section');
  readonly cryptoCard = this.page.locator('[data-testid="crypto-card"], .crypto-item');
  readonly priceDisplay = this.page.locator('[data-testid="price"]');
  readonly changePercentage = this.page.locator('[data-testid="change-percent"]');

  constructor(page: Page, logger: Logger) {
    super(page, logger);
    this.pageTitle = 'Paribu - Cryptocurrency Trading Platform';
    this.pageUrl = /paribu\.com/;
  }

  /**
   * Wait for home page to load
   */
  async waitForPageLoad(): Promise<void> {
    this.logger.debug('Waiting for home page to load');
    await this.page.waitForSelector('[data-testid="featured-markets"], .featured-section', {
      timeout: this.timeout,
    });
    this.logger.info('Home page loaded');
  }

  /**
   * Search for cryptocurrency
   */
  async searchCrypto(query: string): Promise<void> {
    this.logger.info(`Searching for: ${query}`);
    await this.fill(this.searchInput, query);
    await this.click(this.searchButton);
    await this.page.waitForNavigation({ waitUntil: 'networkidle' }).catch(() => {
      // Search might load without navigation
    });
  }

  /**
   * Navigate to Markets page
   */
  async goToMarkets(): Promise<void> {
    this.logger.info('Navigating to Markets');
    await this.click(this.marketsLink);
    await this.page.waitForNavigation({ waitUntil: 'networkidle' });
  }

  /**
   * Navigate to Trading page
   */
  async goToTrading(): Promise<void> {
    this.logger.info('Navigating to Trading');
    await this.click(this.tradingLink);
    await this.page.waitForNavigation({ waitUntil: 'networkidle' });
  }

  /**
   * Navigate to Wallet page
   */
  async goToWallet(): Promise<void> {
    this.logger.info('Navigating to Wallet');
    await this.click(this.walletLink);
    await this.page.waitForNavigation({ waitUntil: 'networkidle' });
  }

  /**
   * Click login button
   */
  async clickLogin(): Promise<void> {
    this.logger.info('Clicking login button');
    await this.click(this.loginButton);
  }

  /**
   * Click signup button
   */
  async clickSignup(): Promise<void> {
    this.logger.info('Clicking signup button');
    await this.click(this.signupButton);
  }

  /**
   * Get featured markets count
   */
  async getFeaturedMarketsCount(): Promise<number> {
    return await this.getElementCount(this.cryptoCard);
  }

  /**
   * Get cryptocurrency price
   */
  async getCryptoPriceBySymbol(symbol: string): Promise<string | null> {
    const cryptoElement = this.page.locator(`[data-testid="crypto-${symbol.toLowerCase()}"]`);
    return await this.getAttribute(cryptoElement, 'data-price');
  }

  /**
   * Check if featured markets are visible
   */
  async areFeaturedMarketsVisible(): Promise<boolean> {
    return await this.isVisible(this.featuredMarkets);
  }

  /**
   * Get all cryptocurrency symbols from featured section
   */
  async getFeaturedCryptoSymbols(): Promise<string[]> {
    const symbols: string[] = [];
    const count = await this.cryptoCard.count();

    for (let i = 0; i < count; i++) {
      const symbol = await this.cryptoCard.nth(i).getAttribute('data-symbol');
      if (symbol) {
        symbols.push(symbol);
      }
    }

    return symbols;
  }
}
