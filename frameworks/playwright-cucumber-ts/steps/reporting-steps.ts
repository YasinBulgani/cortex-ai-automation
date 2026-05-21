/**
 * Reporting & Analytics Step Definitions
 * Comprehensive test reporting and analytics workflows
 */

import { Given, When, Then } from '@cucumber/cucumber';
import axios from 'axios';

/**
 * REPORT GENERATION STEPS
 */

When('I generate a test report in {string} format', async function (this: any, format: string) {
  if (!this.lastTestRun) {
    throw new Error('No test run available for report generation');
  }

  try {
    const response = await axios.post('http://localhost:8000/api/reporting/generate-report', {
      test_run: this.lastTestRun,
      formats: [format],
      include_charts: true,
    });

    this.generatedReport = response.data;
    this.reportFormat = format;

    this.logger.info('Test report generated', {
      format: format,
      run_id: response.data.run_id,
      success_rate: response.data.summary.success_rate,
    });
  } catch (error) {
    this.logger.error('Report generation failed', { error });
    throw error;
  }
});

When('I generate test reports in multiple formats', async function (this: any) {
  if (!this.lastTestRun) {
    throw new Error('No test run available for report generation');
  }

  try {
    const formats = ['html', 'json', 'markdown', 'csv'];
    const response = await axios.post('http://localhost:8000/api/reporting/generate-report', {
      test_run: this.lastTestRun,
      formats: formats,
      include_charts: true,
    });

    this.generatedReports = response.data;
    this.reportFormats = formats;

    this.logger.info('Multi-format reports generated', {
      formats: Object.keys(response.data.reports),
      run_id: response.data.run_id,
    });
  } catch (error) {
    this.logger.error('Multi-format report generation failed', { error });
    throw error;
  }
});

Then('the generated report should contain summary metrics', async function (this: any) {
  if (!this.generatedReport) {
    throw new Error('No generated report available');
  }

  const { summary } = this.generatedReport;

  if (!summary || !summary.total_tests) {
    throw new Error('Report missing summary metrics');
  }

  this.logger.info('✓ Report contains summary metrics', {
    total_tests: summary.total_tests,
    passed: summary.passed,
    failed: summary.failed,
    success_rate: summary.success_rate,
  });
});

Then('the report should have success rate above {float}%', async function (this: any, threshold: number) {
  if (!this.generatedReport) {
    throw new Error('No generated report available');
  }

  const successRate = parseFloat(this.generatedReport.summary.success_rate);

  if (successRate < threshold) {
    throw new Error(
      `Report success rate ${successRate}% is below threshold ${threshold}%`
    );
  }

  this.logger.info(`✓ Report success rate ${successRate}% exceeds ${threshold}%`);
});

Then('the report should include {int} test cases', async function (this: any, expectedCount: number) {
  if (!this.lastTestRun) {
    throw new Error('No test run available');
  }

  const actualCount = this.lastTestRun.test_cases.length;

  if (actualCount !== expectedCount) {
    throw new Error(
      `Report contains ${actualCount} test cases, expected ${expectedCount}`
    );
  }

  this.logger.info(`✓ Report includes ${actualCount} test cases`);
});

/**
 * ANALYTICS & TRENDS STEPS
 */

When('I analyze test trends for the last {int} hours', async function (this: any, hours: number) {
  try {
    const response = await axios.get('http://localhost:8000/api/reporting/analytics/trends', {
      params: { hours: hours },
    });

    this.testTrends = response.data.trends;
    this.trendAnalysisPeriod = hours;

    this.logger.info(`Test trends analyzed for last ${hours} hours`, {
      metrics_tracked: Object.keys(response.data.trends).length,
    });
  } catch (error) {
    this.logger.error('Trend analysis failed', { error });
    throw error;
  }
});

When('I perform risk assessment for the test suite', async function (this: any) {
  try {
    const response = await axios.get('http://localhost:8000/api/reporting/analytics/risk-assessment', {
      params: { hours: 24 },
    });

    this.riskAssessment = response.data.risk_assessment;

    this.logger.info('Risk assessment completed', {
      risk_level: response.data.risk_assessment.level,
      risk_score: response.data.risk_assessment.score,
      failing_tests: response.data.risk_assessment.failing_tests.length,
    });
  } catch (error) {
    this.logger.error('Risk assessment failed', { error });
    throw error;
  }
});

When('I get failure predictions', async function (this: any) {
  try {
    const response = await axios.get('http://localhost:8000/api/reporting/analytics/predictions', {
      params: { days: 7 },
    });

    this.failurePredictions = response.data.predictions;

    this.logger.info('Failure predictions generated', {
      probable_failures: response.data.predictions.probable_failures.length,
      confidence: response.data.predictions.confidence,
    });
  } catch (error) {
    this.logger.error('Failed to get predictions', { error });
    throw error;
  }
});

Then('the risk level should be {string}', async function (this: any, expectedLevel: string) {
  if (!this.riskAssessment) {
    throw new Error('No risk assessment available');
  }

  const actualLevel = this.riskAssessment.level;

  if (actualLevel !== expectedLevel.toLowerCase()) {
    throw new Error(
      `Risk level is ${actualLevel}, expected ${expectedLevel.toLowerCase()}`
    );
  }

  this.logger.info(`✓ Risk level is ${actualLevel}`);
});

Then('the risk score should be below {int}', async function (this: any, maxScore: number) {
  if (!this.riskAssessment) {
    throw new Error('No risk assessment available');
  }

  const riskScore = this.riskAssessment.score;

  if (riskScore > maxScore) {
    throw new Error(
      `Risk score ${riskScore} exceeds maximum ${maxScore}`
    );
  }

  this.logger.info(`✓ Risk score ${riskScore} is below ${maxScore}`);
});

Then('the risk assessment should provide recommendations', async function (this: any) {
  if (!this.riskAssessment) {
    throw new Error('No risk assessment available');
  }

  const { recommendations } = this.riskAssessment;

  if (!recommendations || recommendations.length === 0) {
    throw new Error('No recommendations provided in risk assessment');
  }

  this.logger.info('Recommendations provided:');
  for (const recommendation of recommendations) {
    this.logger.info(`- ${recommendation}`);
  }
});

Then('there should be {int} or fewer failing tests', async function (this: any, maxFailing: number) {
  if (!this.riskAssessment) {
    throw new Error('No risk assessment available');
  }

  const failingCount = this.riskAssessment.failing_tests.length;

  if (failingCount > maxFailing) {
    throw new Error(
      `Found ${failingCount} failing tests, expected ${maxFailing} or fewer`
    );
  }

  this.logger.info(`✓ Failing tests: ${failingCount}/${maxFailing}`);
});

/**
 * PERFORMANCE ANALYSIS STEPS
 */

When('I analyze performance trends', async function (this: any) {
  try {
    const response = await axios.get('http://localhost:8000/api/reporting/analytics/performance', {
      params: { hours: 24 },
    });

    this.performanceTrends = response.data.performance;

    this.logger.info('Performance trends analyzed', {
      average_duration: response.data.performance.average_duration_ms,
      max_duration: response.data.performance.max_duration_ms,
      trend_direction: response.data.performance.trend_direction,
    });
  } catch (error) {
    this.logger.error('Performance analysis failed', { error });
    throw error;
  }
});

Then('average test duration should be below {int}ms', async function (this: any, maxDuration: number) {
  if (!this.performanceTrends) {
    throw new Error('No performance trends available');
  }

  const avgDuration = this.performanceTrends.average_duration_ms;

  if (avgDuration > maxDuration) {
    throw new Error(
      `Average duration ${avgDuration}ms exceeds ${maxDuration}ms`
    );
  }

  this.logger.info(`✓ Average duration ${avgDuration}ms is below ${maxDuration}ms`);
});

Then('performance should be {string}', async function (this: any, expectedTrend: string) {
  if (!this.performanceTrends) {
    throw new Error('No performance trends available');
  }

  const actualTrend = this.performanceTrends.trend_direction;

  if (!actualTrend.includes(expectedTrend.toLowerCase())) {
    throw new Error(
      `Performance trend is ${actualTrend}, expected ${expectedTrend}`
    );
  }

  this.logger.info(`✓ Performance trend: ${actualTrend}`);
});

/**
 * ANALYTICS REPORT STEPS
 */

When('I generate comprehensive analytics report', async function (this: any) {
  try {
    const response = await axios.get('http://localhost:8000/api/reporting/analytics/report', {
      params: { export: 'json' },
    });

    this.analyticsReport = response.data;

    this.logger.info('Comprehensive analytics report generated', {
      report_id: response.data.report_id,
      risk_level: response.data.risk_level,
      timestamp: response.data.timestamp,
    });
  } catch (error) {
    this.logger.error('Analytics report generation failed', { error });
    throw error;
  }
});

Then('the analytics report should contain trend analysis', async function (this: any) {
  if (!this.analyticsReport) {
    throw new Error('No analytics report available');
  }

  const { trends_summary } = this.analyticsReport;

  if (!trends_summary || Object.keys(trends_summary).length === 0) {
    throw new Error('Report missing trend analysis');
  }

  this.logger.info('✓ Report contains trend analysis', {
    trends: Object.keys(trends_summary).length,
  });
});

Then('the analytics report should contain recommendations', async function (this: any) {
  if (!this.analyticsReport) {
    throw new Error('No analytics report available');
  }

  const { recommendations } = this.analyticsReport;

  if (!recommendations || recommendations.length === 0) {
    throw new Error('Report missing recommendations');
  }

  this.logger.info('✓ Report contains recommendations');
  for (const rec of recommendations) {
    this.logger.info(`  - ${rec}`);
  }
});

/**
 * TEST RUN RECORDING STEPS
 */

When('I record test run results', async function (this: any) {
  if (!this.lastTestRun) {
    throw new Error('No test run data available');
  }

  try {
    const response = await axios.post('http://localhost:8000/api/reporting/record-run', {
      run_id: this.lastTestRun.run_id,
      environment: this.lastTestRun.environment,
      browser: this.lastTestRun.browser,
      total_tests: this.lastTestRun.total_tests,
      passed: this.lastTestRun.passed,
      failed: this.lastTestRun.failed,
      skipped: this.lastTestRun.skipped,
      duration_ms: this.lastTestRun.duration_ms,
    });

    this.recordedRun = response.data;

    this.logger.info('Test run recorded', {
      run_id: response.data.run_id,
      success_rate: response.data.success_rate,
    });
  } catch (error) {
    this.logger.error('Failed to record test run', { error });
    throw error;
  }
});

When('I record a failed test', async function (this: any) {
  if (!this.lastTestName) {
    throw new Error('No test name available for failure recording');
  }

  try {
    const response = await axios.post('http://localhost:8000/api/reporting/record-failure', {
      test_name: this.lastTestName,
      run_id: this.lastTestRun?.run_id || 'unknown',
      error_message: this.lastErrorMessage || 'Unknown error',
      duration_ms: this.lastTestDuration || 0,
    });

    this.failureRecorded = response.data;

    this.logger.info('Failed test recorded', {
      test_name: response.data.test_name,
    });
  } catch (error) {
    this.logger.error('Failed to record failure', { error });
    throw error;
  }
});

Then('the test run should be recorded successfully', async function (this: any) {
  if (!this.recordedRun) {
    throw new Error('Test run not recorded');
  }

  if (!this.recordedRun.success) {
    throw new Error('Test run recording failed');
  }

  this.logger.info('✓ Test run recorded successfully');
});

/**
 * COMPLETE REPORTING WORKFLOW
 */

Given('I have a test run with results', async function (this: any) {
  // Create a sample test run
  this.lastTestRun = {
    run_id: `test-run-${Date.now()}`,
    environment: 'staging',
    browser: 'chromium',
    start_time: new Date().toISOString(),
    end_time: new Date(Date.now() + 60000).toISOString(),
    total_tests: 50,
    passed: 45,
    failed: 3,
    skipped: 2,
    duration_ms: 60000,
    test_cases: Array(50).fill(null).map((_, i) => ({
      test_id: `test-${i}`,
      name: `Test Case ${i + 1}`,
      status: i < 45 ? 'passed' : i < 48 ? 'failed' : 'skipped',
      duration_ms: Math.random() * 2000,
      timestamp: new Date().toISOString(),
      feature: 'Feature Name',
      tags: ['tag1', 'tag2'],
      steps: [],
      attachments: [],
      error_message: i >= 45 ? 'Assertion failed' : undefined,
    })),
    metrics: {},
  };

  this.logger.info('Test run prepared for reporting', {
    run_id: this.lastTestRun.run_id,
    total_tests: this.lastTestRun.total_tests,
  });
});

When('I perform comprehensive reporting workflow', async function (this: any) {
  if (!this.lastTestRun) {
    throw new Error('No test run available');
  }

  // Generate reports
  await this.runStepDefinition('I generate test reports in multiple formats');

  // Record run
  await this.runStepDefinition('I record test run results');

  // Analyze trends
  await this.runStepDefinition('I analyze test trends for the last {int} hours', [24]);

  // Risk assessment
  await this.runStepDefinition('I perform risk assessment for the test suite');

  // Generate analytics report
  await this.runStepDefinition('I generate comprehensive analytics report');

  this.logger.info('✓ Comprehensive reporting workflow completed');
});

Then('the reporting workflow should complete successfully', async function (this: any) {
  if (!this.generatedReports && !this.analyticsReport) {
    throw new Error('Reporting workflow incomplete');
  }

  this.logger.info('✓ Reporting workflow completed successfully', {
    reports_generated: this.reportFormats?.length || 0,
    analytics_generated: this.analyticsReport ? true : false,
    risk_assessed: this.riskAssessment ? true : false,
  });
});

/**
 * Export
 */
export {};
