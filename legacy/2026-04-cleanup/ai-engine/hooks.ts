/**
 * Cucumber Hooks for Test Lifecycle Management
 *
 * Handles:
 * - Browser initialization and cleanup
 * - Screenshot on failure
 * - Test context setup/teardown
 * - Retry logic
 */

import { Before, After, AfterStep, BeforeStep, ITestCaseHookParameter, Status } from '@cucumber/cucumber';
import { Browser, BrowserContext, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { chromium, firefox, webkit } from '@playwright/test';
import { Logger, getLogger } from './core/typescript/utils/Logger';
import { config } from './core/typescript/config';

// Global browser and context
let browser: Browser | null = null;
let context: BrowserContext | null = null;
let logger: Logger;

// Test context object attached to world
interface TestContext {
  browser: Browser;
  context: BrowserContext;
  page: Page | null;
  logger: Logger;
  startTime: number;
  testName: string;
  stepName: string;
}

/**
 * Before hook - Initialize browser before each test
 */
Before(async function (this: any, scenario: ITestCaseHookParameter) {
  logger = getLogger();
  logger.info(`Starting scenario: ${scenario.pickle.name}`);

  try {
    // Launch browser
    const browserType = config.get<string>('browser.type');
    const headless = config.get<boolean>('browser.headless');
    const slowMo = config.get<number>('browser.slowMo');

    logger.debug(`Launching browser: ${browserType} (headless: ${headless})`);

    switch (browserType) {
      case 'firefox':
        browser = await firefox.launch({ headless, slowMo });
        break;
      case 'webkit':
        browser = await webkit.launch({ headless, slowMo });
        break;
      default:
        browser = await chromium.launch({ headless, slowMo });
    }

    // Create context
    const viewport = {
      width: config.get<number>('browser.viewport.width'),
      height: config.get<number>('browser.viewport.height'),
    };

    context = await browser.newContext({
      viewport,
      locale: 'en-US',
      timezoneId: 'UTC',
    });

    // Create page
    const page = await context.newPage();

    // Set timeout
    const timeout = config.get<number>('timeout');
    page.setDefaultTimeout(timeout);
    page.setDefaultNavigationTimeout(timeout);

    // Attach to world for steps
    this.browser = browser;
    this.context = context;
    this.page = page;
    this.logger = logger;
    this.startTime = Date.now();
    this.testName = scenario.pickle.name;

    logger.info(`Browser initialized for scenario: ${scenario.pickle.name}`);
  } catch (error) {
    logger.error('Failed to initialize browser', { error });
    throw error;
  }
});

/**
 * Before each step - Log step start
 */
BeforeStep(async function (this: any, step: ITestCaseHookParameter) {
  if (this.logger) {
    this.stepName = step.pickle.steps[0]?.text || 'Unknown';
    this.logger.debug(`Starting step: ${this.stepName}`);
  }
});

/**
 * After each step - Take screenshot on failure
 */
AfterStep(async function (this: any, step: ITestCaseHookParameter) {
  try {
    if (this.page && step.result?.status === Status.FAILED) {
      const screenshotDir = config.get<string>('paths.screenshots');

      // Ensure directory exists
      if (!fs.existsSync(screenshotDir)) {
        fs.mkdirSync(screenshotDir, { recursive: true });
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `failure-${this.testName}-${timestamp}.png`;
      const filepath = path.join(screenshotDir, filename);

      await this.page.screenshot({ path: filepath, fullPage: true });
      this.logger?.info(`Screenshot saved on failure: ${filepath}`);

      // Attach screenshot path to scenario for reporting
      if (!this.failedSteps) {
        this.failedSteps = [];
      }
      this.failedSteps.push({
        step: this.stepName,
        screenshot: filepath,
      });
    }
  } catch (error) {
    if (this.logger) {
      this.logger.warn('Failed to take screenshot', { error });
    }
  }
});

/**
 * After hook - Cleanup after each test
 */
After(async function (this: any, scenario: ITestCaseHookParameter) {
  try {
    // Get duration
    const duration = Date.now() - this.startTime;
    const durationSec = (duration / 1000).toFixed(2);

    if (scenario.result?.status === Status.PASSED) {
      logger.info(`Scenario passed: ${scenario.pickle.name} (${durationSec}s)`);
    } else if (scenario.result?.status === Status.FAILED) {
      logger.error(`Scenario failed: ${scenario.pickle.name} (${durationSec}s)`);

      // Take full page screenshot on failure
      if (this.page) {
        const screenshotDir = config.get<string>('paths.screenshots');
        if (!fs.existsSync(screenshotDir)) {
          fs.mkdirSync(screenshotDir, { recursive: true });
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `final-failure-${this.testName}-${timestamp}.png`;
        const filepath = path.join(screenshotDir, filename);

        try {
          await this.page.screenshot({ path: filepath, fullPage: true });
          logger.info(`Final screenshot saved: ${filepath}`);
        } catch (error) {
          logger.warn('Failed to take final screenshot', { error });
        }
      }
    }

    // Close page
    if (this.page) {
      await this.page.close();
    }

    // Close context
    if (context) {
      await context.close();
    }

    // Close browser
    if (browser) {
      await browser.close();
    }

    logger.info(`Scenario cleanup completed: ${scenario.pickle.name}`);
  } catch (error) {
    logger.error('Error during scenario cleanup', { error });
  }
});

/**
 * Export test context interface for typing
 */
export { TestContext };
