/**
 * Visual Regression Testing Step Definitions
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { VisualRegressionTester } from '../utils/VisualRegressionTester';

/**
 * VISUAL COMPARISON STEPS
 */

When('I take a full page screenshot named {string}', async function (this: any, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const result = await visualTester.compareFullPage(name, { updateBaseline: false });
  this.lastVisualResult = result;
  this.logger.info(`Screenshot comparison: ${name}`, result);
});

When('I take a screenshot of {string} named {string}', async function (this: any, selector: string, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const result = await visualTester.compareElement(selector, name, { updateBaseline: false });
  this.lastVisualResult = result;
  this.logger.info(`Element screenshot comparison: ${name}`, result);
});

Then('the visual comparison should pass', async function (this: any) {
  if (!this.lastVisualResult) {
    throw new Error('No visual comparison result found');
  }

  const { passed, message } = this.lastVisualResult;
  if (!passed) {
    throw new Error(`Visual comparison failed: ${message}`);
  }
});

Then('the visual match should be above {float} percent', async function (this: any, percentage: number) {
  if (!this.lastVisualResult) {
    throw new Error('No visual comparison result found');
  }

  const { similarity } = this.lastVisualResult;
  const threshold = percentage / 100;

  if (similarity < threshold) {
    throw new Error(
      `Visual similarity ${(similarity * 100).toFixed(2)}% is below threshold ${percentage}%`
    );
  }
});

When('I update the visual baseline {string}', async function (this: any, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const result = await visualTester.compareFullPage(name, { updateBaseline: true });
  this.logger.info(`✓ Baseline updated: ${name}`);
});

When('I update the visual baseline for {string} as {string}', async function (this: any, selector: string, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const result = await visualTester.compareElement(selector, name, { updateBaseline: true });
  this.logger.info(`✓ Element baseline updated: ${name}`);
});

/**
 * VISUAL BASELINE MANAGEMENT STEPS
 */

Given('the visual baseline {string} exists', async function (this: any, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const baselines = visualTester.getBaselineList();

  if (!baselines.includes(name)) {
    throw new Error(`Baseline "${name}" does not exist`);
  }
});

When('I delete the visual baseline {string}', async function (this: any, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  visualTester.deleteBaseline(name);
  this.logger.info(`✓ Baseline deleted: ${name}`);
});

When('I clear all visual baselines', async function (this: any) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  visualTester.clearAllBaselines();
  this.logger.info('✓ All baselines cleared');
});

Then('visual baseline {string} should not exist', async function (this: any, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const baselines = visualTester.getBaselineList();

  if (baselines.includes(name)) {
    throw new Error(`Baseline "${name}" still exists`);
  }
});

/**
 * VISUAL THRESHOLD STEPS
 */

When('I set visual threshold to {float}', async function (this: any, threshold: number) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  visualTester.setDefaultThreshold(threshold / 100);
  this.logger.info(`Visual threshold set to ${threshold}%`);
});

/**
 * VISUAL ASSERTION STEPS
 */

Then('the page should match visual baseline {string}', async function (this: any, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  await visualTester.assertVisualMatch(name);
  this.logger.info(`✓ Page matches visual baseline: ${name}`);
});

Then('the element {string} should match visual baseline {string}', async function (this: any, selector: string, name: string) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  await visualTester.assertElementVisualMatch(selector, name);
  this.logger.info(`✓ Element matches visual baseline: ${name}`);
});

/**
 * Export
 */
export {};
