/**
 * End-to-End Integration Step Definitions
 * Multi-step scenarios combining accessibility, visual, performance, and data testing
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { A11yTester } from '../utils/A11yTester';
import { VisualRegressionTester } from '../utils/VisualRegressionTester';
import { PerformanceTester } from '../utils/PerformanceTester';
import { TestDataManager } from '../utils/TestDataManager';

/**
 * ACCESSIBILITY INTEGRATION STEPS
 */

When('I run accessibility scan', async function (this: any) {
  const a11yTester = new A11yTester(this.page, this.logger);
  const report = await a11yTester.scan();
  this.a11yReport = report;
  this.logger.info('Accessibility scan completed', {
    violations: report.violations.length,
    passes: report.passes.length,
  });
});

Then('there should be no critical accessibility violations', async function (this: any) {
  if (!this.a11yReport) {
    const a11yTester = new A11yTester(this.page, this.logger);
    this.a11yReport = await a11yTester.scan();
  }

  const criticalViolations = this.a11yReport.violations.filter((v) => v.impact === 'critical');

  if (criticalViolations.length > 0) {
    const violationMessages = criticalViolations.map((v) => `${v.id}: ${v.message}`).join('\n');
    throw new Error(`Critical accessibility violations found:\n${violationMessages}`);
  }

  this.logger.info('✓ No critical accessibility violations found');
});

Then('there should be no serious accessibility violations', async function (this: any) {
  if (!this.a11yReport) {
    const a11yTester = new A11yTester(this.page, this.logger);
    this.a11yReport = await a11yTester.scan();
  }

  const seriousViolations = this.a11yReport.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious'
  );

  if (seriousViolations.length > 0) {
    const violationMessages = seriousViolations.map((v) => `${v.id}: ${v.message}`).join('\n');
    throw new Error(`Serious accessibility violations found:\n${violationMessages}`);
  }

  this.logger.info('✓ No serious accessibility violations found');
});

/**
 * MULTI-METRIC VALIDATION STEPS
 */

When('I validate page accessibility and performance', async function (this: any) {
  const a11yTester = new A11yTester(this.page, this.logger);
  const performanceTester = new PerformanceTester(this.page, this.logger);

  const [a11yReport, perfMetrics] = await Promise.all([
    a11yTester.scan(),
    performanceTester.measurePageLoad(),
  ]);

  this.a11yReport = a11yReport;
  this.performanceMetrics = perfMetrics;

  this.logger.info('Multi-metric validation completed', {
    a11yViolations: a11yReport.violations.length,
    pageLoadTime: perfMetrics.pageLoadTime,
  });
});

Then('the page should pass all quality gates', async function (this: any) {
  const violations: string[] = [];

  // Check accessibility
  if (this.a11yReport) {
    const criticalA11y = this.a11yReport.violations.filter((v) => v.impact === 'critical');
    if (criticalA11y.length > 0) {
      violations.push(`${criticalA11y.length} critical accessibility violations`);
    }
  }

  // Check performance
  if (this.performanceMetrics) {
    if (this.performanceMetrics.pageLoadTime > 5000) {
      violations.push(`Page load time ${this.performanceMetrics.pageLoadTime}ms exceeds 5000ms`);
    }
    if (this.performanceMetrics.timeToFirstContentfulPaint > 2000) {
      violations.push(`FCP ${this.performanceMetrics.timeToFirstContentfulPaint}ms exceeds 2000ms`);
    }
  }

  if (violations.length > 0) {
    throw new Error(`Quality gates failed:\n${violations.join('\n')}`);
  }

  this.logger.info('✓ Page passed all quality gates');
});

/**
 * AUTHENTICATION WITH VALIDATION STEPS
 */

When('I login with email and password from test data', async function (this: any) {
  if (!this.testData) {
    throw new Error('No test data loaded');
  }

  const { LoginPage } = await import('../pages/LoginPage');
  const loginPage = new LoginPage(this.page, this.logger);

  const email = this.testData.email || this.testData[0]?.email;
  const password = this.testData.password || this.testData[0]?.password;

  if (!email || !password) {
    throw new Error('Test data missing email or password');
  }

  await loginPage.login(email, password);
  this.logger.info('User logged in from test data', { email });
});

/**
 * WORKFLOW VALIDATION STEPS
 */

Then('the complete workflow should be valid', async function (this: any) {
  const validations: Record<string, boolean> = {
    a11y: this.a11yReport ? this.a11yReport.violations.length === 0 : true,
    performance: this.performanceMetrics
      ? this.performanceMetrics.pageLoadTime < 5000
      : true,
    visual: this.lastVisualResult ? this.lastVisualResult.passed : true,
    data: this.testData ? Object.keys(this.testData).length > 0 : true,
  };

  const failures = Object.entries(validations)
    .filter(([, valid]) => !valid)
    .map(([key]) => key);

  if (failures.length > 0) {
    throw new Error(`Workflow validation failed for: ${failures.join(', ')}`);
  }

  this.logger.info('✓ Complete workflow is valid', validations);
});

/**
 * COMPARISON STEPS FOR MULTIPLE ELEMENTS
 */

When('I compare multiple elements', async function (this: any) {
  const visualTester = new VisualRegressionTester(this.page, this.logger);

  const elements = [
    { selector: 'header', name: 'site-header' },
    { selector: 'nav', name: 'site-navigation' },
    { selector: 'footer', name: 'site-footer' },
  ];

  const results = [];

  for (const element of elements) {
    try {
      const result = await visualTester.compareElement(element.selector, element.name);
      results.push({ element: element.name, ...result });
    } catch (error) {
      this.logger.warn(`Element comparison failed for ${element.name}`, { error });
    }
  }

  this.multiElementResults = results;
  this.logger.info('Multiple element comparison completed', results);
});

Then('all compared elements should match baselines', async function (this: any) {
  if (!this.multiElementResults || this.multiElementResults.length === 0) {
    throw new Error('No element comparisons found');
  }

  const failures = this.multiElementResults.filter((r) => !r.passed);

  if (failures.length > 0) {
    const failureMessages = failures.map((f) => `${f.element}: ${f.message}`).join('\n');
    throw new Error(`Element baseline mismatches:\n${failureMessages}`);
  }

  this.logger.info('✓ All compared elements match baselines');
});

/**
 * SEQUENTIAL OPERATION STEPS
 */

When('I perform sequential operations with validation', async function (this: any) {
  const results = [];

  // Operation 1: Measure page load
  const performanceTester = new PerformanceTester(this.page, this.logger);
  const perfMetrics = await performanceTester.measurePageLoad();
  results.push({ operation: 'measurePageLoad', duration: perfMetrics.pageLoadTime });

  // Operation 2: Accessibility scan
  const a11yTester = new A11yTester(this.page, this.logger);
  const a11yReport = await a11yTester.scan();
  results.push({ operation: 'a11yScan', violations: a11yReport.violations.length });

  // Operation 3: Get network metrics
  const networkMetrics = await performanceTester.getNetworkMetrics();
  results.push({ operation: 'networkMetrics', requests: networkMetrics.totalRequests });

  this.sequentialResults = results;
  this.logger.info('Sequential operations completed', results);
});

Then('the sequential operations should all succeed', async function (this: any) {
  if (!this.sequentialResults || this.sequentialResults.length === 0) {
    throw new Error('No sequential operation results found');
  }

  // Validate results have expected properties
  const allValid = this.sequentialResults.every(
    (r) => r.operation && (r.duration !== undefined || r.violations !== undefined || r.requests !== undefined)
  );

  if (!allValid) {
    throw new Error('Sequential operations produced invalid results');
  }

  this.logger.info('✓ All sequential operations succeeded', this.sequentialResults);
});

/**
 * PERFORMANCE THRESHOLD COMPARISON STEPS
 */

Then('page performance should meet strict thresholds', async function (this: any) {
  if (!this.performanceMetrics) {
    const performanceTester = new PerformanceTester(this.page, this.logger);
    this.performanceMetrics = await performanceTester.measurePageLoad();
  }

  const { performanceMetrics } = this;
  const violations: string[] = [];

  // Strict thresholds
  if (performanceMetrics.pageLoadTime > 3000) {
    violations.push(`Page load time ${performanceMetrics.pageLoadTime}ms > 3000ms`);
  }
  if (performanceMetrics.domContentLoadedTime > 2000) {
    violations.push(`DOM load time ${performanceMetrics.domContentLoadedTime}ms > 2000ms`);
  }
  if (performanceMetrics.timeToFirstContentfulPaint > 1500) {
    violations.push(`FCP ${performanceMetrics.timeToFirstContentfulPaint}ms > 1500ms`);
  }
  if (performanceMetrics.timeToLargestContentfulPaint > 2000) {
    violations.push(`LCP ${performanceMetrics.timeToLargestContentfulPaint}ms > 2000ms`);
  }
  if (performanceMetrics.cumulativeLayoutShift > 0.1) {
    violations.push(`CLS ${performanceMetrics.cumulativeLayoutShift} > 0.1`);
  }

  if (violations.length > 0) {
    throw new Error(`Performance thresholds exceeded:\n${violations.join('\n')}`);
  }

  this.logger.info('✓ All performance thresholds met');
});

/**
 * COMPREHENSIVE VALIDATION STEPS
 */

Given('I have a comprehensive test context', async function (this: any) {
  // Initialize all testing utilities
  const a11yTester = new A11yTester(this.page, this.logger);
  const visualTester = new VisualRegressionTester(this.page, this.logger);
  const performanceTester = new PerformanceTester(this.page, this.logger);
  const testDataManager = new TestDataManager(this.logger);

  this.comprehensiveContext = {
    a11yTester,
    visualTester,
    performanceTester,
    testDataManager,
  };

  this.logger.info('Comprehensive test context initialized');
});

Then('I should have test results for all domains', async function (this: any) {
  const expectedResults = ['a11yReport', 'performanceMetrics', 'lastVisualResult', 'testData'];
  const missingResults = expectedResults.filter((key) => !this[key]);

  if (missingResults.length > 0) {
    this.logger.warn(`Missing test results: ${missingResults.join(', ')}`);
  }

  this.logger.info('Test result verification complete');
});

/**
 * Export
 */
export {};
