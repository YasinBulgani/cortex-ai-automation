/**
 * LLM Client (Framework-level)
 * OpenAI API integration for AI-powered test automation features.
 *
 * NOT: Bu dosya framework içi basit OpenAI entegrasyonudur.
 * Çok-provider (Anthropic, DeepSeek, Ollama) tam motor için:
 * → ai-engine/src/shared/utils/LLMClient.ts
 */

import OpenAI from 'openai';
import { Logger } from './Logger';
import { ENV_VARS } from '../config/constants';

export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMResponse {
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
}

export class LLMClient {
  private client: OpenAI | null = null;
  private model: string;
  private temperature: number;
  private maxTokens: number;

  constructor() {
    const apiKey = process.env[ENV_VARS.OPENAI_API_KEY];
    this.model = process.env[ENV_VARS.OPENAI_MODEL] || 'gpt-4o-mini';
    this.temperature = parseFloat(process.env[ENV_VARS.OPENAI_TEMPERATURE] || '0.7');
    this.maxTokens = parseInt(process.env[ENV_VARS.OPENAI_MAX_TOKENS] || '2000', 10);

    if (apiKey) {
      this.client = new OpenAI({
        apiKey: apiKey
      });
      Logger.info('LLM Client initialized', { model: this.model });
    } else {
      Logger.warn('OpenAI API key not found. LLM features will be disabled.');
    }
  }

  /**
   * Check if LLM client is available
   */
  isAvailable(): boolean {
    return this.client !== null;
  }

  /**
   * Generate text using LLM
   */
  async generateText(prompt: string, systemPrompt?: string): Promise<string | null> {
    if (!this.client) {
      Logger.warn('LLM client not available. Cannot generate text.');
      return null;
    }

    try {
      const messages: LLMMessage[] = [];
      
      if (systemPrompt) {
        messages.push({ role: 'system', content: systemPrompt });
      }
      
      messages.push({ role: 'user', content: prompt });

      Logger.debug('Sending request to LLM', { model: this.model, promptLength: prompt.length });

      const completion = await this.client.chat.completions.create({
        model: this.model,
        messages: messages,
        temperature: this.temperature,
        max_tokens: this.maxTokens
      });

      const response = completion.choices[0]?.message?.content || null;

      if (completion.usage) {
        Logger.debug('LLM usage stats', {
          promptTokens: completion.usage.prompt_tokens,
          completionTokens: completion.usage.completion_tokens,
          totalTokens: completion.usage.total_tokens
        });
      }

      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      Logger.error('LLM request failed', error);
      throw new Error(`LLM request failed: ${errorMessage}`);
    }
  }

  /**
   * Generate test scenario from natural language description
   */
  async generateTestScenario(description: string, testType: 'api' | 'web' = 'web'): Promise<string | null> {
    const systemPrompt = `You are a test automation expert. Generate Cucumber Gherkin test scenarios based on descriptions.
Format your response as valid Gherkin syntax with Feature, Scenario, Given, When, Then steps.
Include appropriate tags (@api or @web).
Be concise and follow BDD best practices.`;

    const prompt = `Generate a ${testType} test scenario for the following requirement:
${description}

Provide only the Gherkin feature file content, no additional explanation.`;

    return await this.generateText(prompt, systemPrompt);
  }

  /**
   * Analyze test failure and suggest fixes
   */
  async analyzeTestFailure(
    errorMessage: string,
    testScenario: string,
    screenshotPath?: string
  ): Promise<string | null> {
    const systemPrompt = `You are a test automation debugging expert. Analyze test failures and provide actionable suggestions.
Focus on common issues like selector problems, timing issues, element visibility, and framework-specific problems.`;

    const prompt = `A test scenario failed with the following error:
Error: ${errorMessage}

Test Scenario:
${testScenario}

${screenshotPath ? `Screenshot available at: ${screenshotPath}` : ''}

Please analyze the failure and provide:
1. Likely root cause
2. Specific fix suggestions
3. Best practices to prevent similar issues`;

    return await this.generateText(prompt, systemPrompt);
  }

  /**
   * Generate step definitions for a test scenario
   */
  async generateStepDefinitions(scenario: string, framework: 'playwright' = 'playwright'): Promise<string | null> {
    const systemPrompt = `You are a TypeScript test automation expert. Generate Playwright step definitions for Cucumber scenarios.
Use the PlaywrightWorld context and follow the existing code patterns.
Include proper error handling and logging.`;

    const prompt = `Generate TypeScript step definitions for this Cucumber scenario:
${scenario}

Framework: ${framework}
Use Playwright API and TypeScript async/await patterns.
Include proper type annotations and error handling.`;

    return await this.generateText(prompt, systemPrompt);
  }

  /**
   * Suggest test improvements
   */
  async suggestTestImprovements(testCode: string): Promise<string | null> {
    const systemPrompt = `You are a test automation code review expert. Analyze test code and suggest improvements.
Focus on maintainability, readability, performance, and best practices.`;

    const prompt = `Review this test code and suggest improvements:
${testCode}

Provide specific, actionable suggestions with examples if possible.`;

    return await this.generateText(prompt, systemPrompt);
  }

  /**
   * Generate Page Object Model code
   */
  async generatePageObject(pageDescription: string, selectors?: Record<string, string>): Promise<string | null> {
    const systemPrompt = `You are a test automation expert. Generate Page Object Model classes for Playwright.
Follow SOLID principles and extend BasePage class.
Include proper TypeScript types and JSDoc comments.`;

    const selectorsText = selectors ? `\nKnown selectors:\n${JSON.stringify(selectors, null, 2)}` : '';
    
    const prompt = `Generate a Page Object Model class for:
${pageDescription}
${selectorsText}

Extend BasePage and include methods for page interactions.`;

    return await this.generateText(prompt, systemPrompt);
  }
}

// Export singleton instance
export const llmClient = new LLMClient();
