/**
 * Search Results Page Object Model
 */

import { Page } from '@playwright/test';
import { BasePage } from './BasePage';
import { Logger } from '../utils/Logger';

export class SearchPage extends BasePage {
  readonly searchInput = this.page.locator('input[type="search"]');
  readonly resultsList = this.page.locator('[data-testid="search-results"], .results-list');
  readonly resultItem = this.page.locator('[data-testid="result-item"], .result-item');
  readonly noResultsMessage = this.page.locator('[data-testid="no-results"]');
  readonly filterButton = this.page.locator('button:has-text("Filter")');
  readonly sortDropdown = this.page.locator('select[name="sort"], [data-testid="sort-dropdown"]');

  constructor(page: Page, logger: Logger) {
    super(page, logger);
    this.pageUrl = /search/;
  }

  async waitForPageLoad(): Promise<void> {
    await this.waitForVisible(this.searchInput);
  }

  async searchFor(query: string): Promise<void> {
    await this.fill(this.searchInput, query);
    await this.press(this.searchInput, 'Enter');
  }

  async getResultsCount(): Promise<number> {
    return await this.getElementCount(this.resultItem);
  }

  async getFirstResultTitle(): Promise<string> {
    return await this.getText(this.resultItem.first());
  }

  async clickResultByIndex(index: number): Promise<void> {
    await this.click(this.resultItem.nth(index));
  }

  async hasNoResults(): Promise<boolean> {
    return await this.isVisible(this.noResultsMessage);
  }

  async sortBy(sortOption: string): Promise<void> {
    await this.selectOption(this.sortDropdown, sortOption);
  }
}
