/**
 * LLM (Large Language Model) Client
 * Multi-provider support for AI-powered test generation and analysis
 */

import axios, { AxiosInstance } from 'axios';
import { Logger } from './Logger';

interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'deepseek' | 'ollama';
  apiKey?: string;
  baseURL?: string;
  model: string;
  temperature?: number;
  maxTokens?: number;
}

interface LLMRequest {
  systemPrompt?: string;
  userPrompt: string;
  context?: Record<string, any>;
}

interface LLMResponse {
  success: boolean;
  content: string;
  model: string;
  provider: string;
  tokensUsed?: number;
  error?: string;
}

interface TestGenerationRequest {
  userStory: string;
  pageUrl: string;
  pageElements?: Array<{ selector: string; type: string }>;
  targetFramework?: 'cucumber' | 'jest' | 'playwright';
}

interface TestGenerationResponse {
  scenarios: Array<{
    title: string;
    steps: string[];
    tags: string[];
  }>;
  stepDefinitions?: string[];
  pageObject?: string;
}

/**
 * LLM Client Class
 */
export class LLMClient {
  private config: LLMConfig;
  private logger: Logger;
  private client: AxiosInstance;
  private requestCount: number = 0;
  private tokenCount: number = 0;

  constructor(logger: Logger, config: LLMConfig) {
    this.logger = logger;
    this.config = {
      temperature: 0.7,
      maxTokens: 2000,
      ...config,
    };

    this.client = axios.create({
      baseURL: this.config.baseURL || this.getDefaultBaseURL(),
      timeout: 30000,
      headers: this.getHeaders(),
    });

    this.logger.info(`LLM Client initialized: ${this.config.provider} (${this.config.model})`);
  }

  /**
   * Get default base URL by provider
   */
  private getDefaultBaseURL(): string {
    switch (this.config.provider) {
      case 'openai':
        return 'https://api.openai.com/v1';
      case 'anthropic':
        return 'https://api.anthropic.com/v1';
      case 'deepseek':
        return 'https://api.deepseek.com/v1';
      case 'ollama':
        return 'http://localhost:11434/api';
      default:
        throw new Error(`Unknown provider: ${this.config.provider}`);
    }
  }

  /**
   * Get headers by provider
   */
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    switch (this.config.provider) {
      case 'openai':
      case 'deepseek':
        headers['Authorization'] = `Bearer ${this.config.apiKey}`;
        break;
      case 'anthropic':
        headers['x-api-key'] = this.config.apiKey || '';
        headers['anthropic-version'] = '2023-06-01';
        break;
      case 'ollama':
        // Ollama doesn't require API key
        break;
    }

    return headers;
  }

  /**
   * Send request to LLM
   */
  async query(request: LLMRequest): Promise<LLMResponse> {
    this.logger.info(`Querying ${this.config.provider}`, {
      model: this.config.model,
      userPromptLength: request.userPrompt.length,
    });

    try {
      const payload = this.buildPayload(request);
      const response = await this.client.post('', payload);

      const content = this.extractContent(response.data);
      const tokensUsed = this.extractTokens(response.data);

      this.requestCount++;
      this.tokenCount += tokensUsed || 0;

      this.logger.info('LLM query successful', {
        provider: this.config.provider,
        tokensUsed,
        totalTokens: this.tokenCount,
      });

      return {
        success: true,
        content,
        model: this.config.model,
        provider: this.config.provider,
        tokensUsed,
      };
    } catch (error: any) {
      const errorMessage = error.response?.data?.error?.message || error.message;
      this.logger.error(`LLM query failed: ${errorMessage}`, { error });

      return {
        success: false,
        content: '',
        model: this.config.model,
        provider: this.config.provider,
        error: errorMessage,
      };
    }
  }

  /**
   * Build request payload by provider
   */
  private buildPayload(request: LLMRequest): any {
    const { systemPrompt, userPrompt, context } = request;

    const messages = [];
    if (systemPrompt) {
      messages.push({ role: 'system', content: systemPrompt });
    }
    messages.push({ role: 'user', content: userPrompt });

    switch (this.config.provider) {
      case 'openai':
      case 'deepseek':
        return {
          model: this.config.model,
          messages,
          temperature: this.config.temperature,
          max_tokens: this.config.maxTokens,
        };

      case 'anthropic':
        return {
          model: this.config.model,
          max_tokens: this.config.maxTokens,
          system: systemPrompt,
          messages: messages.filter((m) => m.role !== 'system'),
          temperature: this.config.temperature,
        };

      case 'ollama':
        return {
          model: this.config.model,
          prompt: userPrompt,
          stream: false,
          temperature: this.config.temperature,
        };

      default:
        throw new Error(`Unknown provider: ${this.config.provider}`);
    }
  }

  /**
   * Extract content from response by provider
   */
  private extractContent(data: any): string {
    switch (this.config.provider) {
      case 'openai':
      case 'deepseek':
        return data.choices?.[0]?.message?.content || '';

      case 'anthropic':
        return data.content?.[0]?.text || '';

      case 'ollama':
        return data.response || '';

      default:
        return '';
    }
  }

  /**
   * Extract token count from response
   */
  private extractTokens(data: any): number {
    switch (this.config.provider) {
      case 'openai':
      case 'deepseek':
        return data.usage?.total_tokens || 0;

      case 'anthropic':
        return data.usage?.input_tokens + data.usage?.output_tokens || 0;

      case 'ollama':
        return 0; // Ollama doesn't provide token count

      default:
        return 0;
    }
  }

  /**
   * Generate test scenarios from user story
   */
  async generateTestScenarios(
    request: TestGenerationRequest
  ): Promise<TestGenerationResponse> {
    const elementsInfo = request.pageElements
      ? request.pageElements.map((e) => `- ${e.type}: ${e.selector}`).join('\n')
      : 'No elements provided';

    const systemPrompt = `You are an expert QA engineer and test automation specialist.
Generate high-quality BDD test scenarios in Gherkin format.
Focus on functional, accessibility, and performance aspects.
Return valid Gherkin syntax that can be executed with Cucumber.`;

    const userPrompt = `Generate test scenarios for the following requirement:

User Story: ${request.userStory}
Page URL: ${request.pageUrl}

Page Elements:
${elementsInfo}

Requirements:
1. Generate 3-5 realistic test scenarios
2. Include positive and negative cases
3. Add accessibility and performance checks
4. Use proper Gherkin syntax (Scenario Outline where applicable)
5. Include appropriate tags (@smoke, @critical, etc.)

Format the response as valid Gherkin:
Scenario: [description]
  Given [precondition]
  When [action]
  Then [assertion]`;

    const response = await this.query({
      systemPrompt,
      userPrompt,
      context: request,
    });

    if (!response.success) {
      throw new Error(`Test generation failed: ${response.error}`);
    }

    return this.parseTestGeneration(response.content, request.targetFramework);
  }

  /**
   * Parse test generation response
   */
  private parseTestGeneration(
    content: string,
    framework?: string
  ): TestGenerationResponse {
    const scenarios: TestGenerationResponse['scenarios'] = [];

    // Parse Gherkin scenarios
    const scenarioRegex = /Scenario:?\s+(.+?)(?=Scenario|$)/gs;
    let match;

    while ((match = scenarioRegex.exec(content)) !== null) {
      const scenarioBlock = match[1];
      const titleMatch = scenarioBlock.match(/^(.+?)(?:\n|@)/);
      const title = titleMatch ? titleMatch[1].trim() : 'Untitled Scenario';

      const stepsMatch = scenarioBlock.match(/(Given|When|Then|And|But).+/g) || [];
      const steps = stepsMatch.map((s) => s.trim());

      const tagsMatch = content.match(/@\w+/g) || [];
      const tags = Array.from(new Set(tagsMatch));

      scenarios.push({
        title,
        steps,
        tags,
      });
    }

    return {
      scenarios: scenarios.length > 0 ? scenarios : this.generateDefaultScenarios(),
      stepDefinitions: this.extractStepDefinitions(content, framework),
    };
  }

  /**
   * Generate default scenarios if parsing fails
   */
  private generateDefaultScenarios(): TestGenerationResponse['scenarios'] {
    return [
      {
        title: 'User completes basic flow',
        steps: [
          'Given I am on the application',
          'When I perform the expected action',
          'Then the result should be successful',
        ],
        tags: ['@smoke', '@e2e'],
      },
    ];
  }

  /**
   * Extract step definitions from response
   */
  private extractStepDefinitions(content: string, framework?: string): string[] {
    // Simple extraction of step definition code blocks
    const codeBlocks = content.match(/```[\s\S]*?```/g) || [];
    return codeBlocks.map((block) => block.replace(/```/g, '').trim());
  }

  /**
   * Analyze test coverage
   */
  async analyzeTestCoverage(testScenarios: string[]): Promise<{
    coverage: number;
    gaps: string[];
    recommendations: string[];
  }> {
    const userPrompt = `Analyze the test coverage of these test scenarios and identify gaps:

${testScenarios.join('\n\n')}

Provide:
1. Coverage percentage (0-100)
2. Identified gaps
3. Recommendations for additional tests`;

    const response = await this.query({
      systemPrompt:
        'You are a test coverage analysis expert. Analyze test scenarios and identify coverage gaps.',
      userPrompt,
    });

    if (!response.success) {
      throw new Error(`Coverage analysis failed: ${response.error}`);
    }

    return this.parseCoverageAnalysis(response.content);
  }

  /**
   * Parse coverage analysis response
   */
  private parseCoverageAnalysis(content: string): {
    coverage: number;
    gaps: string[];
    recommendations: string[];
  } {
    const coverageMatch = content.match(/(\d+)%/);
    const coverage = coverageMatch ? parseInt(coverageMatch[1]) : 50;

    const gaps = content.match(/Gap[s]?:?\s*([^\n]+)/gi)?.map((g) => g.replace(/Gap[s]?:?\s*/i, '')) || [];

    const recommendations =
      content
        .match(/Recommendation[s]?:?\s*([^\n]+)/gi)
        ?.map((r) => r.replace(/Recommendation[s]?:?\s*/i, '')) || [];

    return { coverage, gaps, recommendations };
  }

  /**
   * Suggest test data
   */
  async suggestTestData(testScenario: string): Promise<Record<string, any>> {
    const userPrompt = `For this test scenario:

${testScenario}

Suggest realistic test data values.
Return as JSON format with field names and example values.`;

    const response = await this.query({
      systemPrompt: 'You are a test data generation specialist.',
      userPrompt,
    });

    if (!response.success) {
      throw new Error(`Test data suggestion failed: ${response.error}`);
    }

    try {
      const jsonMatch = response.content.match(/\{[\s\S]*\}/);
      return jsonMatch ? JSON.parse(jsonMatch[0]) : {};
    } catch (error) {
      this.logger.warn('Failed to parse suggested test data as JSON');
      return {};
    }
  }

  /**
   * Debug failing test
   */
  async debugFailingTest(testName: string, errorMessage: string): Promise<string> {
    const userPrompt = `Help debug this failing test:

Test: ${testName}
Error: ${errorMessage}

Provide:
1. Root cause analysis
2. Potential fixes
3. Prevention strategies`;

    const response = await this.query({
      systemPrompt: 'You are an expert in debugging test automation issues.',
      userPrompt,
    });

    if (!response.success) {
      throw new Error(`Test debugging failed: ${response.error}`);
    }

    return response.content;
  }

  /**
   * Get statistics
   */
  getStatistics(): {
    provider: string;
    model: string;
    requestCount: number;
    tokenCount: number;
  } {
    return {
      provider: this.config.provider,
      model: this.config.model,
      requestCount: this.requestCount,
      tokenCount: this.tokenCount,
    };
  }

  /**
   * Reset statistics
   */
  resetStatistics(): void {
    this.requestCount = 0;
    this.tokenCount = 0;
  }
}

/**
 * Helper function to create LLM client
 */
export function createLLMClient(logger: Logger, config: LLMConfig): LLMClient {
  return new LLMClient(logger, config);
}

/**
 * Singleton instance
 */
let globalLLMClient: LLMClient | null = null;

/**
 * Get or create global LLM client
 */
export function getLLMClient(logger: Logger, config?: LLMConfig): LLMClient {
  if (!globalLLMClient && config) {
    globalLLMClient = new LLMClient(logger, config);
  }
  return globalLLMClient || new LLMClient(logger, config || { provider: 'openai', model: 'gpt-4' });
}

/**
 * Reset LLM client
 */
export function resetLLMClient(): void {
  globalLLMClient = null;
}
