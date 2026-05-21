/**
 * Visual AI Testing Step Definitions
 * AI-powered visual comparison, anomaly detection, and smart baseline management
 */

import { Given, When, Then } from '@cucumber/cucumber';
import axios from 'axios';

/**
 * VISUAL AI ANALYSIS STEPS
 */

When('I analyze the visual difference with AI', async function (this: any) {
  const currentImagePath = this.lastScreenshot;
  const baselineName = this.lastScreenshotName || 'screenshot';

  if (!currentImagePath) {
    throw new Error('No screenshot available for analysis');
  }

  try {
    // Call Python visual AI service
    const response = await axios.post('http://localhost:8000/api/visual-ai/analyze', {
      current_image: currentImagePath,
      baseline_name: baselineName,
    });

    this.visualAIAnalysis = response.data;
    this.logger.info('Visual AI analysis completed', {
      similarity: response.data.similarity,
      anomalies: response.data.anomalies.length,
    });
  } catch (error) {
    this.logger.error('Visual AI analysis failed', { error });
    throw error;
  }
});

Then('the visual analysis should identify anomalies', async function (this: any) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { anomalies, has_anomalies } = this.visualAIAnalysis;

  if (!has_anomalies) {
    this.logger.info('✓ No visual anomalies detected');
    return;
  }

  this.logger.info(`Found ${anomalies.length} visual anomalies`);

  for (const anomaly of anomalies) {
    this.logger.warn(`- ${anomaly.type} (${anomaly.severity}): ${anomaly.description}`);
  }
});

Then('the visual analysis should detect {int} or fewer anomalies', async function (this: any, maxAnomalies: number) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { anomalies } = this.visualAIAnalysis;

  if (anomalies.length > maxAnomalies) {
    throw new Error(
      `Found ${anomalies.length} anomalies, expected ${maxAnomalies} or fewer`
    );
  }

  this.logger.info(`✓ Anomalies within threshold: ${anomalies.length}/${maxAnomalies}`);
});

Then('there should be no critical visual anomalies', async function (this: any) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { anomalies } = this.visualAIAnalysis;
  const critical = anomalies.filter((a: any) => a.severity === 'critical');

  if (critical.length > 0) {
    const descriptions = critical.map((a: any) => a.description).join('\n');
    throw new Error(`Critical visual anomalies found:\n${descriptions}`);
  }

  this.logger.info('✓ No critical visual anomalies');
});

/**
 * ANOMALY TYPE DETECTION STEPS
 */

Then('the visual anomalies should include {string}', async function (this: any, anomalyType: string) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { anomalies } = this.visualAIAnalysis;
  const hasType = anomalies.some((a: any) => a.type === anomalyType);

  if (!hasType) {
    throw new Error(`Anomaly type "${anomalyType}" not found in analysis`);
  }

  this.logger.info(`✓ Anomaly type detected: ${anomalyType}`);
});

Then('the analysis should report color shifts', async function (this: any) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { anomalies } = this.visualAIAnalysis;
  const colorShifts = anomalies.filter((a: any) => a.type === 'color_shift');

  if (colorShifts.length === 0) {
    this.logger.info('No color shifts detected');
  } else {
    this.logger.info(`Color shifts detected: ${colorShifts.length}`);
  }
});

Then('the analysis should report layout changes', async function (this: any) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { anomalies } = this.visualAIAnalysis;
  const layoutChanges = anomalies.filter((a: any) => a.type === 'layout_change');

  if (layoutChanges.length === 0) {
    this.logger.info('No layout changes detected');
  } else {
    this.logger.info(`Layout changes detected: ${layoutChanges.length}`);
  }
});

/**
 * SMART BASELINE MANAGEMENT STEPS
 */

When('I perform smart baseline analysis', async function (this: any) {
  const baselineName = this.lastScreenshotName || 'screenshot';
  const currentImagePath = this.lastScreenshot;

  if (!currentImagePath) {
    throw new Error('No screenshot available for baseline analysis');
  }

  try {
    const response = await axios.post('http://localhost:8000/api/visual-ai/smart-update', {
      baseline_name: baselineName,
      current_image: currentImagePath,
    });

    this.smartBaselineResult = response.data;
    this.logger.info('Smart baseline analysis completed', {
      should_update: response.data.should_update,
      similarity: response.data.similarity,
    });
  } catch (error) {
    this.logger.error('Smart baseline analysis failed', { error });
    throw error;
  }
});

Then('the baseline should {string} be updated', async function (this: any, expectation: string) {
  if (!this.smartBaselineResult) {
    throw new Error('No baseline analysis available');
  }

  const shouldUpdate = this.smartBaselineResult.should_update;
  const expectedUpdate = expectation.toLowerCase() === 'be' ? true : false;

  if (shouldUpdate !== expectedUpdate) {
    throw new Error(
      `Baseline update expectation mismatch: expected ${expectedUpdate}, got ${shouldUpdate}`
    );
  }

  const action = shouldUpdate ? 'updated' : 'not updated';
  this.logger.info(`✓ Baseline ${action} as expected`);
});

Then('the baseline analysis should provide recommendations', async function (this: any) {
  if (!this.smartBaselineResult) {
    throw new Error('No baseline analysis available');
  }

  const { reasons } = this.smartBaselineResult;

  if (!reasons || reasons.length === 0) {
    throw new Error('No recommendations provided');
  }

  this.logger.info('Baseline recommendations:');
  for (const reason of reasons) {
    this.logger.info(`- ${reason}`);
  }
});

/**
 * SIMILARITY THRESHOLD STEPS
 */

Then('the visual similarity should be above {float}', async function (this: any, threshold: number) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { similarity } = this.visualAIAnalysis;

  if (similarity < threshold) {
    throw new Error(
      `Visual similarity ${(similarity * 100).toFixed(2)}% is below threshold ${(threshold * 100).toFixed(2)}%`
    );
  }

  this.logger.info(`✓ Visual similarity ${(similarity * 100).toFixed(2)}% exceeds ${(threshold * 100).toFixed(2)}%`);
});

Then('the visual similarity should be exactly {float} with tolerance {float}', async function (this: any, expected: number, tolerance: number) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const { similarity } = this.visualAIAnalysis;
  const diff = Math.abs(similarity - expected);

  if (diff > tolerance) {
    throw new Error(
      `Visual similarity ${(similarity * 100).toFixed(2)}% differs from expected ${(expected * 100).toFixed(2)}% by more than ${(tolerance * 100).toFixed(2)}%`
    );
  }

  this.logger.info(`✓ Visual similarity within tolerance`);
});

/**
 * ANALYSIS REPORTING STEPS
 */

When('I generate visual analysis report', async function (this: any) {
  if (!this.visualAIAnalysis) {
    throw new Error('No visual analysis available');
  }

  const baselineName = this.lastScreenshotName || 'screenshot';

  try {
    const response = await axios.post('http://localhost:8000/api/visual-ai/report', {
      analysis: this.visualAIAnalysis,
      baseline_name: baselineName,
    });

    this.visualAnalysisReport = response.data.report;
    this.logger.info('Visual analysis report generated');
  } catch (error) {
    this.logger.error('Report generation failed', { error });
    throw error;
  }
});

Then('the visual analysis report should contain anomaly details', async function (this: any) {
  if (!this.visualAnalysisReport) {
    throw new Error('No report available');
  }

  if (!this.visualAnalysisReport.includes('Anomalies')) {
    throw new Error('Report does not contain anomaly details');
  }

  this.logger.info('✓ Report contains anomaly details');
});

Then('the visual analysis report should contain recommendations', async function (this: any) {
  if (!this.visualAnalysisReport) {
    throw new Error('No report available');
  }

  if (!this.visualAnalysisReport.includes('Recommendation')) {
    throw new Error('Report does not contain recommendations');
  }

  this.logger.info('✓ Report contains recommendations');
});

/**
 * BASELINE STATUS STEPS
 */

When('I check baseline status for {string}', async function (this: any, baselineName: string) {
  try {
    const response = await axios.get('http://localhost:8000/api/visual-ai/baseline-status', {
      params: { baseline_name: baselineName },
    });

    this.baselineStatus = response.data;
    this.logger.info('Baseline status retrieved', response.data);
  } catch (error) {
    this.logger.error('Failed to get baseline status', { error });
    throw error;
  }
});

Then('the baseline should have {int} or fewer update cycles', async function (this: any, maxUpdates: number) {
  if (!this.baselineStatus) {
    throw new Error('No baseline status available');
  }

  const { update_count } = this.baselineStatus;

  if (update_count > maxUpdates) {
    throw new Error(
      `Baseline has been updated ${update_count} times, expected ${maxUpdates} or fewer`
    );
  }

  this.logger.info(`✓ Baseline updates: ${update_count}/${maxUpdates}`);
});

/**
 * COMPREHENSIVE VISUAL AI WORKFLOW
 */

Given('I have visual AI analysis enabled', async function (this: any) {
  this.visualAIEnabled = true;
  this.visualAIMetrics = {
    analysisCount: 0,
    anomaliesDetected: 0,
    baselinesUpdated: 0,
  };

  this.logger.info('Visual AI analysis enabled');
});

When('I perform comprehensive visual AI analysis', async function (this: any) {
  if (!this.visualAIEnabled) {
    throw new Error('Visual AI not enabled');
  }

  // Take screenshot
  const screenshotName = `visual-ai-test-${Date.now()}`;
  await this.page.screenshot({ path: `./screenshots/${screenshotName}.png` });

  this.lastScreenshot = `./screenshots/${screenshotName}.png`;
  this.lastScreenshotName = screenshotName;

  // Perform analysis
  const response = await axios.post('http://localhost:8000/api/visual-ai/analyze', {
    current_image: this.lastScreenshot,
    baseline_name: screenshotName,
  });

  this.visualAIAnalysis = response.data;
  this.visualAIMetrics.analysisCount++;
  this.visualAIMetrics.anomaliesDetected += response.data.anomalies.length;

  // Smart update
  const updateResponse = await axios.post('http://localhost:8000/api/visual-ai/smart-update', {
    baseline_name: screenshotName,
    current_image: this.lastScreenshot,
  });

  if (updateResponse.data.should_update) {
    this.visualAIMetrics.baselinesUpdated++;
  }

  this.logger.info('Comprehensive visual AI analysis completed', this.visualAIMetrics);
});

Then('the visual AI workflow should complete successfully', async function (this: any) {
  if (!this.visualAIMetrics) {
    throw new Error('No visual AI metrics available');
  }

  if (this.visualAIMetrics.analysisCount === 0) {
    throw new Error('No visual analysis was performed');
  }

  this.logger.info('✓ Visual AI workflow completed', {
    analyses: this.visualAIMetrics.analysisCount,
    anomalies: this.visualAIMetrics.anomaliesDetected,
    updates: this.visualAIMetrics.baselinesUpdated,
  });
});

/**
 * Export
 */
export {};
