/**
 * Performance Testing Utility
 * Metrics collection, analysis, and reporting
 */

import { Page } from '@playwright/test';
import { Logger } from './Logger';

interface PerformanceMetrics {
  navigationStart: number;
  pageLoadTime: number;
  domContentLoadedTime: number;
  resourceLoadTime: number;
  timeToFirstContentfulPaint: number;
  timeToLargestContentfulPaint: number;
  cumulativeLayoutShift: number;
  firstInputDelay: number;
  totalBlockingTime: number;
  interactiveTime: number;
  customMetrics?: Record<string, number>;
}

interface PerformanceThresholds {
  pageLoadTime?: number;
  domContentLoadedTime?: number;
  resourceLoadTime?: number;
  fcp?: number;
  lcp?: number;
  cls?: number;
  fid?: number;
  tbt?: number;
  tti?: number;
}

interface PerformanceReport {
  url: string;
  timestamp: string;
  metrics: PerformanceMetrics;
  thresholds: PerformanceThresholds;
  violations: string[];
  passed: boolean;
}

/**
 * Performance Tester Class
 */
export class PerformanceTester {
  private page: Page;
  private logger: Logger;
  private defaultThresholds: PerformanceThresholds = {
    pageLoadTime: 3000,
    domContentLoadedTime: 2000,
    fcp: 1800,
    lcp: 2500,
    cls: 0.1,
    fid: 100,
    tbt: 300,
    tti: 3000,
  };

  constructor(page: Page, logger: Logger) {
    this.page = page;
    this.logger = logger;
  }

  /**
   * Measure page load performance
   */
  async measurePageLoad(): Promise<PerformanceMetrics> {
    this.logger.info('Measuring page load performance');

    try {
      const metrics = await this.page.evaluate(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        const paintEntries = performance.getEntriesByType('paint');
        const largestContentfulPaint = performance.getEntriesByType('largest-contentful-paint');
        const layoutShift = performance.getEntriesByType('layout-shift');

        // Extract metrics
        const navigationStart = navigation?.fetchStart || 0;
        const pageLoadTime = navigation?.loadEventEnd - navigationStart;
        const domContentLoadedTime = navigation?.domContentLoadedEventEnd - navigationStart;
        const resourceLoadTime = navigation?.loadEventStart - navigationStart;

        // Get FCP
        const fcp = paintEntries.find((entry) => entry.name === 'first-contentful-paint');
        const timeToFirstContentfulPaint = fcp
          ? (fcp as PerformanceEntry).startTime - navigationStart
          : 0;

        // Get LCP
        const lcp = largestContentfulPaint[largestContentfulPaint.length - 1];
        const timeToLargestContentfulPaint = lcp
          ? (lcp as PerformanceEntry).startTime - navigationStart
          : 0;

        // Get CLS
        let cumulativeLayoutShift = 0;
        for (const entry of layoutShift as any[]) {
          if (!entry.hadRecentInput) {
            cumulativeLayoutShift += entry.value;
          }
        }

        return {
          navigationStart,
          pageLoadTime: Math.round(pageLoadTime),
          domContentLoadedTime: Math.round(domContentLoadedTime),
          resourceLoadTime: Math.round(resourceLoadTime),
          timeToFirstContentfulPaint: Math.round(timeToFirstContentfulPaint),
          timeToLargestContentfulPaint: Math.round(timeToLargestContentfulPaint),
          cumulativeLayoutShift: Number(cumulativeLayoutShift.toFixed(3)),
        };
      });

      this.logger.info('Page load metrics collected', metrics);
      return metrics as any;
    } catch (error) {
      this.logger.error('Failed to measure page load performance', { error });
      throw error;
    }
  }

  /**
   * Measure operation performance
   */
  async measureOperation<T>(
    operation: () => Promise<T>,
    operationName: string
  ): Promise<{ result: T; duration: number }> {
    this.logger.info(`Measuring operation: ${operationName}`);

    const startTime = performance.now();
    try {
      const result = await operation();
      const duration = performance.now() - startTime;
      this.logger.info(`Operation completed: ${operationName} (${duration.toFixed(2)}ms)`);
      return { result, duration };
    } catch (error) {
      const duration = performance.now() - startTime;
      this.logger.error(`Operation failed: ${operationName} (${duration.toFixed(2)}ms)`, { error });
      throw error;
    }
  }

  /**
   * Assert performance metrics against thresholds
   */
  async assertPerformance(thresholds?: PerformanceThresholds): Promise<PerformanceReport> {
    const metrics = await this.measurePageLoad();
    const appliedThresholds = { ...this.defaultThresholds, ...thresholds };
    const violations: string[] = [];

    this.logger.info('Checking performance thresholds', appliedThresholds);

    // Check each metric
    if (metrics.pageLoadTime > appliedThresholds.pageLoadTime!) {
      violations.push(
        `Page load time ${metrics.pageLoadTime}ms exceeds threshold ${appliedThresholds.pageLoadTime}ms`
      );
    }

    if (metrics.domContentLoadedTime > appliedThresholds.domContentLoadedTime!) {
      violations.push(
        `DOM content loaded time ${metrics.domContentLoadedTime}ms exceeds threshold ${appliedThresholds.domContentLoadedTime}ms`
      );
    }

    if (metrics.timeToFirstContentfulPaint > appliedThresholds.fcp!) {
      violations.push(
        `FCP ${metrics.timeToFirstContentfulPaint}ms exceeds threshold ${appliedThresholds.fcp}ms`
      );
    }

    if (metrics.timeToLargestContentfulPaint > appliedThresholds.lcp!) {
      violations.push(
        `LCP ${metrics.timeToLargestContentfulPaint}ms exceeds threshold ${appliedThresholds.lcp}ms`
      );
    }

    if (metrics.cumulativeLayoutShift > appliedThresholds.cls!) {
      violations.push(
        `CLS ${metrics.cumulativeLayoutShift} exceeds threshold ${appliedThresholds.cls}`
      );
    }

    const passed = violations.length === 0;

    const report: PerformanceReport = {
      url: this.page.url(),
      timestamp: new Date().toISOString(),
      metrics,
      thresholds: appliedThresholds,
      violations,
      passed,
    };

    if (passed) {
      this.logger.info('✓ All performance thresholds met');
    } else {
      this.logger.error('✗ Performance threshold violations', { violations });
    }

    return report;
  }

  /**
   * Get Core Web Vitals
   */
  async getCoreWebVitals(): Promise<Record<string, number>> {
    try {
      const vitals = await this.page.evaluate(() => {
        const metrics = {
          fcp: 0,
          lcp: 0,
          cls: 0,
          fid: 0,
          ttfb: 0,
        };

        // FCP
        const fcp = performance
          .getEntriesByType('paint')
          .find((entry) => entry.name === 'first-contentful-paint');
        if (fcp) metrics.fcp = Math.round(fcp.startTime);

        // LCP
        const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
        if (lcpEntries.length > 0) {
          metrics.lcp = Math.round(lcpEntries[lcpEntries.length - 1].startTime);
        }

        // CLS
        const layoutShifts = performance.getEntriesByType('layout-shift');
        let cls = 0;
        for (const shift of layoutShifts as any[]) {
          if (!shift.hadRecentInput) {
            cls += shift.value;
          }
        }
        metrics.cls = Number(cls.toFixed(3));

        // TTFB
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        if (navigation) {
          metrics.ttfb = Math.round(navigation.responseStart - navigation.fetchStart);
        }

        return metrics;
      });

      this.logger.info('Core Web Vitals', vitals);
      return vitals;
    } catch (error) {
      this.logger.error('Failed to get Core Web Vitals', { error });
      throw error;
    }
  }

  /**
   * Measure network performance
   */
  async getNetworkMetrics(): Promise<Record<string, any>> {
    try {
      const networkMetrics = await this.page.evaluate(() => {
        const resources = performance.getEntriesByType('resource');
        const metrics = {
          totalRequests: resources.length,
          totalSize: 0,
          averageTime: 0,
          slowestRequest: { name: '', duration: 0 },
        };

        let totalTime = 0;
        for (const resource of resources) {
          const perfResource = resource as PerformanceResourceTiming;
          const size = perfResource.transferSize || perfResource.encodedBodySize || 0;
          metrics.totalSize += size;
          const duration = perfResource.duration;
          totalTime += duration;

          if (duration > metrics.slowestRequest.duration) {
            metrics.slowestRequest = {
              name: perfResource.name,
              duration: Math.round(duration),
            };
          }
        }

        metrics.averageTime = resources.length > 0 ? Math.round(totalTime / resources.length) : 0;
        metrics.totalSize = Math.round(metrics.totalSize / 1024); // Convert to KB

        return metrics;
      });

      this.logger.info('Network metrics', networkMetrics);
      return networkMetrics;
    } catch (error) {
      this.logger.error('Failed to get network metrics', { error });
      throw error;
    }
  }

  /**
   * Benchmark operation multiple times
   */
  async benchmarkOperation<T>(
    operation: () => Promise<T>,
    operationName: string,
    iterations: number = 10
  ): Promise<{ mean: number; median: number; min: number; max: number; stdDev: number }> {
    const durations: number[] = [];

    this.logger.info(`Benchmarking operation: ${operationName} (${iterations} iterations)`);

    for (let i = 0; i < iterations; i++) {
      const startTime = performance.now();
      await operation();
      const duration = performance.now() - startTime;
      durations.push(duration);
    }

    // Calculate statistics
    const sorted = [...durations].sort((a, b) => a - b);
    const mean = durations.reduce((a, b) => a + b, 0) / durations.length;
    const median = sorted[Math.floor(sorted.length / 2)];
    const min = sorted[0];
    const max = sorted[sorted.length - 1];

    const variance = durations.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / durations.length;
    const stdDev = Math.sqrt(variance);

    const result = {
      mean: Number(mean.toFixed(2)),
      median: Number(median.toFixed(2)),
      min: Number(min.toFixed(2)),
      max: Number(max.toFixed(2)),
      stdDev: Number(stdDev.toFixed(2)),
    };

    this.logger.info(`Benchmark results for ${operationName}`, result);
    return result;
  }

  /**
   * Set custom thresholds
   */
  setThresholds(thresholds: PerformanceThresholds): void {
    this.defaultThresholds = { ...this.defaultThresholds, ...thresholds };
    this.logger.debug('Performance thresholds updated', this.defaultThresholds);
  }

  /**
   * Get default thresholds
   */
  getThresholds(): PerformanceThresholds {
    return { ...this.defaultThresholds };
  }
}

/**
 * Helper function
 */
export async function assertPagePerformance(
  page: Page,
  logger: Logger,
  thresholds?: PerformanceThresholds
): Promise<PerformanceReport> {
  const tester = new PerformanceTester(page, logger);
  const report = await tester.assertPerformance(thresholds);

  if (!report.passed) {
    throw new Error(`Performance thresholds not met:\n${report.violations.join('\n')}`);
  }

  return report;
}
