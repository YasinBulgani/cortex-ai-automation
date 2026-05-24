/**
 * Playwright World
 * Custom Cucumber World implementation for Playwright integration
 */

import { World, IWorldOptions } from '@cucumber/cucumber';
// setWorldConstructor is intentionally called ONLY in hooks.ts to avoid double registration.
import { Browser, BrowserContext, Page, APIRequestContext } from 'playwright';
import { launchBrowser, BrowserType, getBrowserConfig, getEnvironmentConfig } from '../config/config';
import * as dotenv from 'dotenv';

dotenv.config();

export interface WorldParameters {
  browser?: BrowserType;
  environment?: string;
  headless?: boolean;
}

export class PlaywrightWorld extends World {
  public browser!: Browser;
  public context!: BrowserContext;
  public page!: Page;
  public apiContext!: APIRequestContext;
  public browserType: BrowserType;
  public environment: string;
  public accessToken: string | null = null;
  public lastResponse: unknown = null;
  public lastStatusCode: number | null = null;

  constructor(options: IWorldOptions) {
    super(options);
    
    const params: WorldParameters = options.parameters || {};
    this.browserType = (params.browser as BrowserType) || 'chromium';
    this.environment = params.environment || process.env.ENVIRONMENT || 'qa';
  }

  async init(): Promise<void> {
    this.browser = await launchBrowser(this.browserType);
    
    const browserConfig = getBrowserConfig(this.browserType);
    this.context = await this.browser.newContext(browserConfig.contextOptions);
    
    this.page = await this.context.newPage();
    
    this.page.setDefaultTimeout(getEnvironmentConfig(this.environment).timeout);
    
    this.apiContext = this.context.request;
  }

  async cleanup(): Promise<void> {
    // Close in reverse order; ignore "already closed" errors so a mid-test
    // browser crash does not swallow the original failure.
    if (this.page && !this.page.isClosed()) {
      await this.page.close().catch(() => {});
    }
    if (this.context) {
      await this.context.close().catch(() => {});
    }
    if (this.browser && this.browser.isConnected()) {
      await this.browser.close().catch(() => {});
    }
  }
}