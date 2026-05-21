/**
 * Accessibility Testing Utility
 * WCAG 2.1 compliance checker using axe-core
 */

import { Page, expect } from '@playwright/test';
import { Logger } from './Logger';

interface A11yViolation {
  id: string;
  impact: 'critical' | 'serious' | 'moderate' | 'minor';
  message: string;
  nodes: Array<{
    html: string;
    failureSummary: string;
  }>;
}

interface A11yReport {
  violations: A11yViolation[];
  passes: Array<{
    id: string;
    message: string;
  }>;
  incomplete: Array<{
    id: string;
    message: string;
  }>;
}

/**
 * Accessibility Tester Class
 */
export class A11yTester {
  private page: Page;
  private logger: Logger;

  constructor(page: Page, logger: Logger) {
    this.page = page;
    this.logger = logger;
  }

  /**
   * Inject axe-core library
   */
  private async injectAxe(): Promise<void> {
    await this.page.addScriptTag({
      url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.2/axe.min.js',
    });
  }

  /**
   * Run accessibility scan
   */
  async scan(options?: { runOnly?: string[] }): Promise<A11yReport> {
    this.logger.info('Running accessibility scan');

    try {
      // Inject axe
      await this.injectAxe();

      // Run axe scan
      const report = await this.page.evaluate(() => {
        return new Promise((resolve) => {
          (window as any).axe.run((results: any) => {
            resolve(results);
          });
        });
      });

      this.logger.info('Accessibility scan completed', {
        violations: (report as any).violations.length,
        passes: (report as any).passes.length,
        incomplete: (report as any).incomplete.length,
      });

      return report as A11yReport;
    } catch (error) {
      this.logger.error('Accessibility scan failed', { error });
      throw error;
    }
  }

  /**
   * Assert no violations
   */
  async assertNoViolations(impact?: 'critical' | 'serious'): Promise<void> {
    const report = await this.scan();

    const violations = impact
      ? report.violations.filter((v) => v.impact === impact)
      : report.violations;

    if (violations.length > 0) {
      const message = violations
        .map((v) => `${v.id} (${v.impact}): ${v.message}`)
        .join('\n');
      throw new Error(`Accessibility violations found:\n${message}`);
    }

    this.logger.info('✓ No accessibility violations found');
  }

  /**
   * Check specific rule
   */
  async checkRule(ruleId: string): Promise<boolean> {
    const report = await this.scan({ runOnly: [ruleId] });
    return report.violations.length === 0;
  }

  /**
   * Get violation details
   */
  async getViolationDetails(): Promise<Map<string, A11yViolation>> {
    const report = await this.scan();
    const map = new Map<string, A11yViolation>();

    for (const violation of report.violations) {
      map.set(violation.id, violation);
    }

    return map;
  }

  /**
   * Check contrast ratios
   */
  async checkContrast(): Promise<boolean> {
    return this.checkRule('color-contrast');
  }

  /**
   * Check ARIA attributes
   */
  async checkAria(): Promise<boolean> {
    return this.checkRule('aria-valid-attr');
  }

  /**
   * Check form labels
   */
  async checkFormLabels(): Promise<boolean> {
    return this.checkRule('label');
  }

  /**
   * Check image alt text
   */
  async checkImageAltText(): Promise<boolean> {
    return this.checkRule('image-alt');
  }

  /**
   * Generate report
   */
  async generateReport(): Promise<string> {
    const report = await this.scan();

    let output = '# Accessibility Report\n\n';
    output += `## Summary\n`;
    output += `- Violations: ${report.violations.length}\n`;
    output += `- Passes: ${report.passes.length}\n`;
    output += `- Incomplete: ${report.incomplete.length}\n\n`;

    if (report.violations.length > 0) {
      output += '## Violations\n\n';
      for (const violation of report.violations) {
        output += `### ${violation.id} (${violation.impact})\n`;
        output += `${violation.message}\n\n`;
      }
    }

    return output;
  }
}

/**
 * Helper function
 */
export async function checkPageAccessibility(page: Page, logger: Logger): Promise<void> {
  const tester = new A11yTester(page, logger);
  await tester.assertNoViolations('critical');
}
