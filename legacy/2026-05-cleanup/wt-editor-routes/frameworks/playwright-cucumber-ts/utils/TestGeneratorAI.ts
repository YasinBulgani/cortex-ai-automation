/**
 * Test Generator AI
 * AI-powered test generation utilities
 */

import { llmClient } from './LLMClient';
import { Logger } from './Logger';
import * as fs from 'fs';
import * as path from 'path';

export interface TestGenerationOptions {
  testType: 'api' | 'web';
  featureName?: string;
  outputPath?: string;
}

export class TestGeneratorAI {
  /**
   * Generate test scenario from natural language
   */
  static async generateTestScenario(
    description: string,
    options: TestGenerationOptions
  ): Promise<string | null> {
    if (!llmClient.isAvailable()) {
      Logger.warn('LLM not available. Cannot generate test scenario.');
      return null;
    }

    try {
      Logger.info('Generating test scenario with AI', { description: description.substring(0, 100) });
      
      const scenario = await llmClient.generateTestScenario(description, options.testType);
      
      if (scenario && options.outputPath) {
        const outputDir = path.dirname(options.outputPath);
        if (!fs.existsSync(outputDir)) {
          fs.mkdirSync(outputDir, { recursive: true });
        }
        fs.writeFileSync(options.outputPath, scenario, 'utf-8');
        Logger.info('Test scenario saved', { path: options.outputPath });
      }
      
      return scenario;
    } catch (error) {
      Logger.error('Test scenario generation failed', error);
      throw error;
    }
  }

  /**
   * Generate multiple test scenarios from a list of descriptions
   */
  static async generateMultipleScenarios(
    descriptions: string[],
    options: TestGenerationOptions
  ): Promise<Array<{ description: string; scenario: string | null }>> {
    const results: Array<{ description: string; scenario: string | null }> = [];
    
    for (const description of descriptions) {
      const scenario = await this.generateTestScenario(description, options);
      results.push({ description, scenario });
    }
    
    return results;
  }

  /**
   * Analyze test failure and get suggestions
   */
  static async analyzeFailure(
    errorMessage: string,
    testScenario: string,
    screenshotPath?: string
  ): Promise<string | null> {
    if (!llmClient.isAvailable()) {
      Logger.warn('LLM not available. Cannot analyze failure.');
      return null;
    }

    try {
      Logger.info('Analyzing test failure with AI');
      const analysis = await llmClient.analyzeTestFailure(errorMessage, testScenario, screenshotPath);
      return analysis;
    } catch (error) {
      Logger.error('Failure analysis failed', error);
      return null;
    }
  }

  /**
   * Generate step definitions for a scenario
   */
  static async generateStepDefinitions(scenario: string): Promise<string | null> {
    if (!llmClient.isAvailable()) {
      Logger.warn('LLM not available. Cannot generate step definitions.');
      return null;
    }

    try {
      Logger.info('Generating step definitions with AI');
      const stepDefinitions = await llmClient.generateStepDefinitions(scenario);
      return stepDefinitions;
    } catch (error) {
      Logger.error('Step definition generation failed', error);
      return null;
    }
  }

  /**
   * Get code improvement suggestions
   */
  static async getImprovements(testCode: string): Promise<string | null> {
    if (!llmClient.isAvailable()) {
      Logger.warn('LLM not available. Cannot get improvement suggestions.');
      return null;
    }

    try {
      Logger.info('Getting improvement suggestions from AI');
      const suggestions = await llmClient.suggestTestImprovements(testCode);
      return suggestions;
    } catch (error) {
      Logger.error('Improvement suggestion failed', error);
      return null;
    }
  }

  /**
   * Generate Page Object Model class
   */
  static async generatePageObject(
    pageDescription: string,
    selectors?: Record<string, string>
  ): Promise<string | null> {
    if (!llmClient.isAvailable()) {
      Logger.warn('LLM not available. Cannot generate page object.');
      return null;
    }

    try {
      Logger.info('Generating Page Object Model with AI');
      const pageObject = await llmClient.generatePageObject(pageDescription, selectors);
      return pageObject;
    } catch (error) {
      Logger.error('Page Object generation failed', error);
      return null;
    }
  }
}
