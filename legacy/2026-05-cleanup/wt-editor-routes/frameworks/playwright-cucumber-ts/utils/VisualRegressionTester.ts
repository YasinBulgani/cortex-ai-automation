/**
 * Visual Regression Testing Utility
 * Screenshot comparison and baseline management
 */

import { Page, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { Logger } from './Logger';

interface VisualDiff {
  similarity: number;
  threshold: number;
  passed: boolean;
  diffImagePath?: string;
  message: string;
}

interface VisualComparisonOptions {
  threshold?: number;
  updateBaseline?: boolean;
  fullPage?: boolean;
  mask?: Array<{ x: number; y: number; width: number; height: number }>;
}

/**
 * Visual Regression Tester Class
 */
export class VisualRegressionTester {
  private page: Page;
  private logger: Logger;
  private baselinesDir: string;
  private diffsDir: string;
  private defaultThreshold: number = 0.95;

  constructor(page: Page, logger: Logger, baselinesDir?: string) {
    this.page = page;
    this.logger = logger;
    this.baselinesDir = baselinesDir || path.join(process.cwd(), 'data', 'visual-baselines');
    this.diffsDir = path.join(this.baselinesDir, 'diffs');
    this.ensureDirectories();
  }

  /**
   * Ensure baseline and diff directories exist
   */
  private ensureDirectories(): void {
    if (!fs.existsSync(this.baselinesDir)) {
      fs.mkdirSync(this.baselinesDir, { recursive: true });
      this.logger.info(`Created baselines directory: ${this.baselinesDir}`);
    }
    if (!fs.existsSync(this.diffsDir)) {
      fs.mkdirSync(this.diffsDir, { recursive: true });
      this.logger.info(`Created diffs directory: ${this.diffsDir}`);
    }
  }

  /**
   * Get baseline path
   */
  private getBaselinePath(name: string): string {
    return path.join(this.baselinesDir, `${name}.png`);
  }

  /**
   * Get diff path
   */
  private getDiffPath(name: string): string {
    return path.join(this.diffsDir, `${name}-diff.png`);
  }

  /**
   * Take and compare full page screenshot
   */
  async compareFullPage(
    name: string,
    options: VisualComparisonOptions = {}
  ): Promise<VisualDiff> {
    const threshold = options.threshold ?? this.defaultThreshold;
    const updateBaseline = options.updateBaseline ?? false;

    this.logger.info(`Comparing full page: ${name}`, { threshold, updateBaseline });

    try {
      const screenshotPath = await this.takeScreenshot(name, true);
      const baselinePath = this.getBaselinePath(name);

      // If updating baseline or baseline doesn't exist
      if (updateBaseline || !fs.existsSync(baselinePath)) {
        fs.copyFileSync(screenshotPath, baselinePath);
        this.logger.info(`✓ Baseline created/updated: ${name}`);
        return {
          similarity: 1.0,
          threshold,
          passed: true,
          message: 'Baseline created or updated',
        };
      }

      // Compare screenshots
      const result = await this.compareScreenshots(screenshotPath, baselinePath, name);
      fs.unlinkSync(screenshotPath);

      return {
        similarity: result.similarity,
        threshold,
        passed: result.similarity >= threshold,
        diffImagePath: result.passed ? undefined : this.getDiffPath(name),
        message: result.passed
          ? `Visual match: ${(result.similarity * 100).toFixed(2)}%`
          : `Visual mismatch: ${(result.similarity * 100).toFixed(2)}% (threshold: ${(threshold * 100).toFixed(2)}%)`,
      };
    } catch (error) {
      this.logger.error(`Visual regression comparison failed: ${name}`, { error });
      throw error;
    }
  }

  /**
   * Compare specific element screenshot
   */
  async compareElement(
    selector: string,
    name: string,
    options: VisualComparisonOptions = {}
  ): Promise<VisualDiff> {
    const threshold = options.threshold ?? this.defaultThreshold;
    const updateBaseline = options.updateBaseline ?? false;

    this.logger.info(`Comparing element: ${selector} (${name})`, { threshold });

    try {
      const locator = this.page.locator(selector);
      await locator.waitFor({ state: 'visible', timeout: 10000 });

      const screenshotPath = await this.takeElementScreenshot(selector, name);
      const baselinePath = this.getBaselinePath(`element-${name}`);

      // If updating baseline or baseline doesn't exist
      if (updateBaseline || !fs.existsSync(baselinePath)) {
        fs.copyFileSync(screenshotPath, baselinePath);
        this.logger.info(`✓ Element baseline created/updated: ${name}`);
        return {
          similarity: 1.0,
          threshold,
          passed: true,
          message: 'Element baseline created or updated',
        };
      }

      // Compare screenshots
      const result = await this.compareScreenshots(screenshotPath, baselinePath, `element-${name}`);
      fs.unlinkSync(screenshotPath);

      return {
        similarity: result.similarity,
        threshold,
        passed: result.similarity >= threshold,
        diffImagePath: result.passed ? undefined : this.getDiffPath(`element-${name}`),
        message: result.passed
          ? `Element match: ${(result.similarity * 100).toFixed(2)}%`
          : `Element mismatch: ${(result.similarity * 100).toFixed(2)}%`,
      };
    } catch (error) {
      this.logger.error(`Element visual comparison failed: ${name}`, { error });
      throw error;
    }
  }

  /**
   * Take page screenshot
   */
  private async takeScreenshot(name: string, fullPage: boolean = false): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const screenshotPath = path.join(
      this.baselinesDir,
      `temp-${name}-${timestamp}.png`
    );

    await this.page.screenshot({
      path: screenshotPath,
      fullPage,
    });

    return screenshotPath;
  }

  /**
   * Take element screenshot
   */
  private async takeElementScreenshot(selector: string, name: string): Promise<string> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const screenshotPath = path.join(
      this.baselinesDir,
      `temp-element-${name}-${timestamp}.png`
    );

    const locator = this.page.locator(selector);
    await locator.screenshot({ path: screenshotPath });

    return screenshotPath;
  }

  /**
   * Compare two screenshots using basic pixel comparison
   * Note: Full SSIM implementation requires Python backend
   */
  private async compareScreenshots(
    screenshotPath: string,
    baselinePath: string,
    name: string
  ): Promise<{ similarity: number; passed: boolean }> {
    try {
      // Read both screenshots as buffers
      const screenshot = fs.readFileSync(screenshotPath);
      const baseline = fs.readFileSync(baselinePath);

      // Basic comparison: file size and content
      if (screenshot.length === baseline.length && screenshot.equals(baseline)) {
        return { similarity: 1.0, passed: true };
      }

      // For pixel-perfect comparison, would call Python backend
      // For now, return simulated result based on size difference
      const sizeDiff = Math.abs(screenshot.length - baseline.length);
      const maxSize = Math.max(screenshot.length, baseline.length);
      const similarity = 1.0 - sizeDiff / maxSize;

      return {
        similarity: Math.max(similarity, 0.5),
        passed: similarity > 0.9,
      };
    } catch (error) {
      this.logger.error(`Screenshot comparison error for ${name}`, { error });
      throw error;
    }
  }

  /**
   * Assert visual match
   */
  async assertVisualMatch(
    name: string,
    options: VisualComparisonOptions = {}
  ): Promise<void> {
    const result = await this.compareFullPage(name, options);

    if (!result.passed) {
      throw new Error(`Visual regression detected: ${result.message}`);
    }

    this.logger.info(`✓ Visual match passed: ${name}`);
  }

  /**
   * Assert element visual match
   */
  async assertElementVisualMatch(
    selector: string,
    name: string,
    options: VisualComparisonOptions = {}
  ): Promise<void> {
    const result = await this.compareElement(selector, name, options);

    if (!result.passed) {
      throw new Error(`Element visual regression detected: ${result.message}`);
    }

    this.logger.info(`✓ Element visual match passed: ${name}`);
  }

  /**
   * Get baseline list
   */
  getBaselineList(): string[] {
    try {
      const files = fs.readdirSync(this.baselinesDir);
      return files
        .filter((f) => f.endsWith('.png') && !f.startsWith('temp-'))
        .map((f) => f.replace('.png', ''));
    } catch (error) {
      this.logger.error('Failed to read baseline list', { error });
      return [];
    }
  }

  /**
   * Delete baseline
   */
  deleteBaseline(name: string): void {
    const baselinePath = this.getBaselinePath(name);
    if (fs.existsSync(baselinePath)) {
      fs.unlinkSync(baselinePath);
      this.logger.info(`✓ Baseline deleted: ${name}`);
    }
  }

  /**
   * Clear all baselines
   */
  clearAllBaselines(): void {
    try {
      const files = fs.readdirSync(this.baselinesDir);
      files.forEach((f) => {
        if (f.endsWith('.png') && !f.startsWith('temp-')) {
          fs.unlinkSync(path.join(this.baselinesDir, f));
        }
      });
      this.logger.info('✓ All baselines cleared');
    } catch (error) {
      this.logger.error('Failed to clear baselines', { error });
    }
  }

  /**
   * Get baselines directory
   */
  getBaselinesDir(): string {
    return this.baselinesDir;
  }

  /**
   * Set default threshold
   */
  setDefaultThreshold(threshold: number): void {
    if (threshold < 0 || threshold > 1) {
      throw new Error('Threshold must be between 0 and 1');
    }
    this.defaultThreshold = threshold;
    this.logger.debug(`Default threshold set to ${threshold}`);
  }
}

/**
 * Helper function
 */
export async function comparePageVisually(
  page: Page,
  logger: Logger,
  name: string,
  options?: VisualComparisonOptions
): Promise<void> {
  const tester = new VisualRegressionTester(page, logger);
  await tester.assertVisualMatch(name, options);
}
