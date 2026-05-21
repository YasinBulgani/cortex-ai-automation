/**
 * Market Page Object Model
 */

import { Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { Logger } from '../utils/Logger';

export class MarketPage extends BasePage {
  readonly marketTable = this.page.locator('table, [data-testid="market-table"]');
  readonly tableRow = this.page.locator('tbody tr, [data-testid="market-row"]');
  readonly priceCell = this.page.locator('[data-testid="price"]');
  readonly changeCell = this.page.locator('[data-testid="change"]');
  readonly volumeCell = this.page.locator('[data-testid="volume"]');
  readonly cryptoNameCell = this.page.locator('[data-testid="crypto-name"]');
  readonly favoriteButton = this.page.locator('[data-testid="favorite-btn"]');
  readonly refreshButton = this.page.locator('button:has-text("Refresh")');
  readonly filterPanel = this.page.locator('[data-testid="filter-panel"]');

  constructor(page: Page, logger: Logger) {
    super(page, logger);
    this.pageUrl = /market/;
  }

  async waitForPageLoad(): Promise<void> {
    await this.waitForVisible(this.marketTable);
  }

  async getMarketTableRowCount(): Promise<number> {
    return await this.getElementCount(this.tableRow);
  }

  async getPriceForCrypto(cryptoName: string): Promise<string | null> {
    const row = this.page.locator(`tr:has-text("${cryptoName}")`);
    return await row.locator('[data-testid="price"]').textContent();
  }

  async clickCryptoRow(cryptoName: string): Promise<void> {
    const row = this.page.locator(`tr:has-text("${cryptoName}")`);
    await this.click(row);
  }

  async isTableVisible(): Promise<boolean> {
    return await this.isVisible(this.marketTable);
  }

  async refreshMarketData(): Promise<void> {
    await this.click(this.refreshButton);
    // Refresh → market tablosunun tekrar render edildiğini bekle.
    // Daha önce `waitForTimeout(1000)` hard-wait vardı; flake üretirdi.
    // Şimdi networkidle + table visibility — Playwright auto-retry kullanır.
    await this.page.waitForLoadState("networkidle", { timeout: 15_000 }).catch(() => {
      // Bazı SPA'lar networkidle'a hiç girmez (WS/analytics pings);
      // sessizce yut — fallback olarak table visibility'ye güvenilir.
    });
    // `marketTable` zaten bir Locator (readonly property'ye bak); doğrudan
    // waitFor çağırıyoruz.
    await this.marketTable.waitFor({ state: "visible", timeout: 10_000 });
  }

  async openFilterPanel(): Promise<void> {
    await this.click(this.filterPanel);
  }
}
