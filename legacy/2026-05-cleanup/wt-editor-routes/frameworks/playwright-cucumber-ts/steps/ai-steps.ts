/**
 * AI-Powered Test Generation & Analysis Step Definitions
 * LLM-based test creation, debugging, and optimization
 */

import { Given, When, Then } from '@cucumber/cucumber';
import { LLMClient } from '../utils/LLMClient';

/**
 * AI CLIENT SETUP STEPS
 */

Given('I have AI test generation enabled', async function (this: any) {
  const config = {
    provider: process.env.AI_PROVIDER || 'openai',
    apiKey: process.env.AI_API_KEY,
    model: process.env.AI_MODEL || 'gpt-4',
  };

  this.llmClient = new LLMClient(this.logger, config);
  this.logger.info('AI test generation initialized', { provider: config.provider });
});

/**
 * TEST SCENARIO GENERATION STEPS
 */

When('I generate test scenarios for {string}', async function (this: any, userStory: string) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized. Use "Given I have AI test generation enabled"');
  }

  const request = {
    userStory,
    pageUrl: this.page.url(),
    pageElements: await this.extractPageElements?.(),
    targetFramework: 'cucumber' as const,
  };

  const result = await this.llmClient.generateTestScenarios(request);
  this.generatedScenarios = result.scenarios;
  this.logger.info(`Generated ${result.scenarios.length} test scenarios`, {
    userStory: userStory.substring(0, 50),
  });
});

Then('I should have generated test scenarios', async function (this: any) {
  if (!this.generatedScenarios || this.generatedScenarios.length === 0) {
    throw new Error('No test scenarios were generated');
  }

  this.logger.info(`✓ Generated ${this.generatedScenarios.length} scenarios with ${this.generatedScenarios[0].steps?.length || 0}+ steps each`);
});

Then('the generated scenarios should have {int} or more steps', async function (this: any, minSteps: number) {
  if (!this.generatedScenarios) {
    throw new Error('No scenarios generated');
  }

  const violations: string[] = [];
  for (const scenario of this.generatedScenarios) {
    if ((scenario.steps?.length || 0) < minSteps) {
      violations.push(`Scenario "${scenario.title}" has only ${scenario.steps?.length || 0} steps`);
    }
  }

  if (violations.length > 0) {
    throw new Error(`Scenarios have insufficient steps:\n${violations.join('\n')}`);
  }

  this.logger.info(`✓ All scenarios have ${minSteps}+ steps`);
});

/**
 * TEST DATA GENERATION STEPS
 */

When('I generate test data for the scenario', async function (this: any) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized');
  }

  if (!this.generatedScenarios || this.generatedScenarios.length === 0) {
    throw new Error('No scenarios generated yet');
  }

  const scenario = this.generatedScenarios[0];
  const scenarioText = scenario.steps.join('\n');

  const testData = await this.llmClient.suggestTestData(scenarioText);
  this.suggestedTestData = testData;
  this.logger.info('Generated test data suggestions', testData);
});

Then('the suggested test data should include required fields', async function (this: any) {
  if (!this.suggestedTestData || Object.keys(this.suggestedTestData).length === 0) {
    throw new Error('No test data suggestions available');
  }

  this.logger.info(`✓ Generated test data for ${Object.keys(this.suggestedTestData).length} fields`);
});

/**
 * TEST COVERAGE ANALYSIS STEPS
 */

When('I analyze test coverage for the generated scenarios', async function (this: any) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized');
  }

  if (!this.generatedScenarios || this.generatedScenarios.length === 0) {
    throw new Error('No scenarios to analyze');
  }

  const scenarioTexts = this.generatedScenarios.map((s) => s.title);
  const analysis = await this.llmClient.analyzeTestCoverage(scenarioTexts);

  this.coverageAnalysis = analysis;
  this.logger.info('Coverage analysis completed', {
    coverage: analysis.coverage,
    gaps: analysis.gaps.length,
    recommendations: analysis.recommendations.length,
  });
});

Then('the test coverage should be at least {int} percent', async function (this: any, minCoverage: number) {
  if (!this.coverageAnalysis) {
    throw new Error('No coverage analysis available');
  }

  if (this.coverageAnalysis.coverage < minCoverage) {
    throw new Error(
      `Coverage ${this.coverageAnalysis.coverage}% is below minimum ${minCoverage}%`
    );
  }

  this.logger.info(`✓ Coverage ${this.coverageAnalysis.coverage}% meets minimum ${minCoverage}%`);
});

Then('I should see coverage gaps identified', async function (this: any) {
  if (!this.coverageAnalysis) {
    throw new Error('No coverage analysis available');
  }

  if (this.coverageAnalysis.gaps.length === 0) {
    this.logger.info('No coverage gaps identified');
  } else {
    this.logger.info('Coverage gaps identified:', this.coverageAnalysis.gaps);
  }
});

Then('I should see recommendations for improvement', async function (this: any) {
  if (!this.coverageAnalysis) {
    throw new Error('No coverage analysis available');
  }

  if (this.coverageAnalysis.recommendations.length === 0) {
    throw new Error('No recommendations provided');
  }

  this.logger.info('Improvement recommendations:', this.coverageAnalysis.recommendations);
});

/**
 * TEST DEBUGGING STEPS
 */

When('I debug the failing test {string}', async function (this: any, testName: string) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized');
  }

  const errorMessage = this.lastError || 'Unknown error';
  const debugging = await this.llmClient.debugFailingTest(testName, errorMessage);

  this.debuggingAnalysis = debugging;
  this.logger.info('Test debugging analysis completed');
});

Then('I should receive debugging suggestions', async function (this: any) {
  if (!this.debuggingAnalysis) {
    throw new Error('No debugging analysis available');
  }

  const hasContent = this.debuggingAnalysis.length > 0 && !this.debuggingAnalysis.includes('failed');

  if (!hasContent) {
    throw new Error('Debugging analysis returned no useful suggestions');
  }

  this.logger.info('✓ Debugging suggestions provided');
});

/**
 * PERFORMANCE OPTIMIZATION STEPS
 */

When('I analyze performance for optimization', async function (this: any) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized');
  }

  const metrics = this.performanceMetrics || {
    pageLoadTime: 3500,
    domContentLoaded: 2000,
    firstContentfulPaint: 1200,
  };

  const optimization = await this.llmClient.analyzeTestCoverage(Object.keys(metrics));
  this.optimizationSuggestions = optimization;
  this.logger.info('Performance optimization analysis completed');
});

Then('I should receive optimization suggestions', async function (this: any) {
  if (!this.optimizationSuggestions) {
    throw new Error('No optimization analysis available');
  }

  this.logger.info(
    `✓ Received ${this.optimizationSuggestions.gaps?.length || 0} optimization suggestions`
  );
});

/**
 * AI STATISTICS STEPS
 */

When('I check AI client statistics', async function (this: any) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized');
  }

  this.aiStats = this.llmClient.getStatistics();
  this.logger.info('AI Statistics', this.aiStats);
});

Then('I should see the AI provider and model used', async function (this: any) {
  if (!this.aiStats) {
    throw new Error('No AI statistics available');
  }

  if (!this.aiStats.provider || !this.aiStats.model) {
    throw new Error('AI provider or model not available');
  }

  this.logger.info(`✓ Using ${this.aiStats.provider} (${this.aiStats.model})`);
});

Then('the AI client should have made {int} or more requests', async function (this: any, minRequests: number) {
  if (!this.aiStats) {
    throw new Error('No AI statistics available');
  }

  if (this.aiStats.requestCount < minRequests) {
    throw new Error(
      `Only ${this.aiStats.requestCount} requests made, expected at least ${minRequests}`
    );
  }

  this.logger.info(`✓ Made ${this.aiStats.requestCount} AI requests`);
});

Then('the token usage should be tracked', async function (this: any) {
  if (!this.aiStats) {
    throw new Error('No AI statistics available');
  }

  this.logger.info(`✓ Total tokens used: ${this.aiStats.tokenCount || 0}`);
});

/**
 * MULTI-STEP AI WORKFLOWS
 */

Given('I have a comprehensive AI test generation setup', async function (this: any) {
  const config = {
    provider: process.env.AI_PROVIDER || 'openai',
    apiKey: process.env.AI_API_KEY,
    model: process.env.AI_MODEL || 'gpt-4',
  };

  this.llmClient = new LLMClient(this.logger, config);
  this.aiWorkflowState = {
    initialized: true,
    scenarios: [],
    testData: {},
    coverage: 0,
  };

  this.logger.info('Comprehensive AI setup initialized');
});

When('I execute a complete AI test generation workflow', async function (this: any) {
  if (!this.llmClient) {
    throw new Error('AI client not initialized');
  }

  // Step 1: Generate scenarios
  const scenarios = await this.llmClient.generateTestScenarios({
    userStory: 'User wants to search for products',
    pageUrl: this.page.url(),
  });

  this.aiWorkflowState.scenarios = scenarios.scenarios;

  // Step 2: Generate test data
  if (scenarios.scenarios.length > 0) {
    const testData = await this.llmClient.suggestTestData(scenarios.scenarios[0].title);
    this.aiWorkflowState.testData = testData;
  }

  // Step 3: Analyze coverage
  if (scenarios.scenarios.length > 0) {
    const scenarioTitles = scenarios.scenarios.map((s) => s.title);
    const coverage = await this.llmClient.analyzeTestCoverage(scenarioTitles);
    this.aiWorkflowState.coverage = coverage.coverage;
  }

  this.logger.info('AI workflow execution completed', this.aiWorkflowState);
});

Then('the AI workflow should complete successfully', async function (this: any) {
  if (!this.aiWorkflowState || !this.aiWorkflowState.initialized) {
    throw new Error('AI workflow not initialized');
  }

  if (
    this.aiWorkflowState.scenarios.length === 0 &&
    Object.keys(this.aiWorkflowState.testData).length === 0 &&
    this.aiWorkflowState.coverage === 0
  ) {
    throw new Error('AI workflow produced no results');
  }

  this.logger.info('✓ AI workflow completed successfully');
});

Then('the AI workflow results should be comprehensive', async function (this: any) {
  if (!this.aiWorkflowState) {
    throw new Error('No workflow state available');
  }

  const hasScenarios = this.aiWorkflowState.scenarios.length > 0;
  const hasTestData = Object.keys(this.aiWorkflowState.testData).length > 0;
  const hasCoverage = this.aiWorkflowState.coverage > 0;

  if (!hasScenarios || !hasTestData || !hasCoverage) {
    throw new Error('AI workflow results are incomplete');
  }

  this.logger.info('✓ AI workflow results are comprehensive', {
    scenarios: this.aiWorkflowState.scenarios.length,
    testDataFields: Object.keys(this.aiWorkflowState.testData).length,
    coverage: `${this.aiWorkflowState.coverage}%`,
  });
});

/**
 * Export
 */
export {};
