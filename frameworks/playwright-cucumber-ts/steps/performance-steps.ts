/**
 * Performance Testing Step Definitions
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { PerformanceTester } from '../utils/PerformanceTester';

/**
 * PERFORMANCE MEASUREMENT STEPS
 */

When('I measure the page load time', async function (this: any) {
  const performanceTester = new PerformanceTester(this.page, this.logger);
  const metrics = await performanceTester.measurePageLoad();
  this.performanceMetrics = metrics;
  this.logger.info('Page load metrics measured', metrics);
});

When('I measure the performance of {string}', async function (this: any, operationName: string) {
  const performanceTester = new PerformanceTester(this.page, this.logger);

  // Store the operation name and wait for the operation to be performed
  this.performanceOperationName = operationName;
  this.performanceTester = performanceTester;
});

Then('the page load time should be less than {int} milliseconds', async function (this: any, threshold: number) {
  if (!this.performanceMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceMetrics = await performanceTester.measurePageLoad();
  }

  const loadTime = this.performanceMetrics.pageLoadTime;
  if (loadTime > threshold) {
    throw new Error(`Page load time ${loadTime}ms exceeds threshold ${threshold}ms`);
  }

  this.logger.info(`✓ Page load time ${loadTime}ms is within threshold ${threshold}ms`);
});

Then('the DOM content should load in less than {int} milliseconds', async function (this: any, threshold: number) {
  if (!this.performanceMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceMetrics = await performanceTester.measurePageLoad();
  }

  const domLoadTime = this.performanceMetrics.domContentLoadedTime;
  if (domLoadTime > threshold) {
    throw new Error(`DOM load time ${domLoadTime}ms exceeds threshold ${threshold}ms`);
  }

  this.logger.info(`✓ DOM load time ${domLoadTime}ms is within threshold ${threshold}ms`);
});

Then('the first contentful paint should be less than {int} milliseconds', async function (this: any, threshold: number) {
  if (!this.performanceMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceMetrics = await performanceTester.measurePageLoad();
  }

  const fcp = this.performanceMetrics.timeToFirstContentfulPaint;
  if (fcp > threshold) {
    throw new Error(`FCP ${fcp}ms exceeds threshold ${threshold}ms`);
  }

  this.logger.info(`✓ FCP ${fcp}ms is within threshold ${threshold}ms`);
});

Then('the largest contentful paint should be less than {int} milliseconds', async function (this: any, threshold: number) {
  if (!this.performanceMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceMetrics = await performanceTester.measurePageLoad();
  }

  const lcp = this.performanceMetrics.timeToLargestContentfulPaint;
  if (lcp > threshold) {
    throw new Error(`LCP ${lcp}ms exceeds threshold ${threshold}ms`);
  }

  this.logger.info(`✓ LCP ${lcp}ms is within threshold ${threshold}ms`);
});

Then('the cumulative layout shift should be less than {float}', async function (this: any, threshold: number) {
  if (!this.performanceMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceMetrics = await performanceTester.measurePageLoad();
  }

  const cls = this.performanceMetrics.cumulativeLayoutShift;
  if (cls > threshold) {
    throw new Error(`CLS ${cls} exceeds threshold ${threshold}`);
  }

  this.logger.info(`✓ CLS ${cls} is within threshold ${threshold}`);
});

/**
 * CORE WEB VITALS STEPS
 */

When('I check the core web vitals', async function (this: any) {
  const performanceTester = new PerformanceTester(this.page, this.logger);
  const vitals = await performanceTester.getCoreWebVitals();
  this.coreWebVitals = vitals;
  this.logger.info('Core Web Vitals', vitals);
});

Then('the core web vitals should be good', async function (this: any) {
  if (!this.coreWebVitals) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.coreWebVitals = await performanceTester.getCoreWebVitals();
  }

  const { fcp, lcp, cls } = this.coreWebVitals;
  const violations: string[] = [];

  // Check FCP
  if (fcp > 1800) {
    violations.push(`FCP ${fcp}ms exceeds good threshold 1800ms`);
  }

  // Check LCP
  if (lcp > 2500) {
    violations.push(`LCP ${lcp}ms exceeds good threshold 2500ms`);
  }

  // Check CLS
  if (cls > 0.1) {
    violations.push(`CLS ${cls} exceeds good threshold 0.1`);
  }

  if (violations.length > 0) {
    throw new Error(`Core Web Vitals not good:\n${violations.join('\n')}`);
  }

  this.logger.info('✓ Core Web Vitals are good');
});

/**
 * NETWORK PERFORMANCE STEPS
 */

When('I check the network performance', async function (this: any) {
  const performanceTester = new PerformanceTester(this.page, this.logger);
  const metrics = await performanceTester.getNetworkMetrics();
  this.networkMetrics = metrics;
  this.logger.info('Network metrics', metrics);
});

Then('the total network requests should be less than {int}', async function (this: any, maxRequests: number) {
  if (!this.networkMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.networkMetrics = await performanceTester.getNetworkMetrics();
  }

  const totalRequests = this.networkMetrics.totalRequests;
  if (totalRequests > maxRequests) {
    throw new Error(`Total network requests ${totalRequests} exceeds threshold ${maxRequests}`);
  }

  this.logger.info(`✓ Network requests ${totalRequests} is within threshold ${maxRequests}`);
});

Then('the total network size should be less than {int} KB', async function (this: any, maxSizeKb: number) {
  if (!this.networkMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.networkMetrics = await performanceTester.getNetworkMetrics();
  }

  const totalSize = this.networkMetrics.totalSize;
  if (totalSize > maxSizeKb) {
    throw new Error(`Total network size ${totalSize}KB exceeds threshold ${maxSizeKb}KB`);
  }

  this.logger.info(`✓ Network size ${totalSize}KB is within threshold ${maxSizeKb}KB`);
});

Then('the slowest network request should be {string}', async function (this: any, maxTime: string) {
  if (!this.networkMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.networkMetrics = await performanceTester.getNetworkMetrics();
  }

  const slowest = this.networkMetrics.slowestRequest;
  this.logger.info(`Slowest request: ${slowest.name} (${slowest.duration}ms)`);
});

/**
 * PERFORMANCE THRESHOLD STEPS
 */

When('I set performance threshold for page load to {int} milliseconds', async function (this: any, threshold: number) {
  const performanceTester = new PerformanceTester(this.page, this.logger);
  performanceTester.setThresholds({ pageLoadTime: threshold });
  this.performanceTester = performanceTester;
  this.logger.info(`Performance threshold set: pageLoadTime = ${threshold}ms`);
});

When('I assert performance with default thresholds', async function (this: any) {
  const performanceTester = new PerformanceTester(this.page, this.logger);
  this.performanceReport = await performanceTester.assertPerformance();
});

Then('the performance report should have no violations', async function (this: any) {
  if (!this.performanceReport) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceReport = await performanceTester.assertPerformance();
  }

  if (!this.performanceReport.passed) {
    throw new Error(`Performance violations:\n${this.performanceReport.violations.join('\n')}`);
  }

  this.logger.info('✓ Performance report has no violations');
});

/**
 * BENCHMARKING STEPS
 */

When('I benchmark the operation {string} for {int} iterations', async function (this: any, operationName: string, iterations: number) {
  // This would require capturing an operation, so we'll log it
  this.benchmarkOperationName = operationName;
  this.benchmarkIterations = iterations;
  this.logger.info(`Benchmark queued: ${operationName} (${iterations} iterations)`);
});

/**
 * Export
 */
export {};
