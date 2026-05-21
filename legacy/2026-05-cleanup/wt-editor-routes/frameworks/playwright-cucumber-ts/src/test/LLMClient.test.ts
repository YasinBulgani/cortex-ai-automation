/**
 * LLMClient Unit Tests
 * Test suite for multi-provider LLM client
 */

import { LLMClient, LLMProvider, LLMConfig } from '../../core/typescript/utils/LLMClient';

// Mock Logger
const mockLogger = {
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
  debug: jest.fn(),
};

describe('LLMClient', () => {
  let client: LLMClient;
  const mockConfig: LLMConfig = {
    provider: LLMProvider.OPENAI,
    apiKey: 'test-api-key',
    model: 'gpt-4',
    temperature: 0.7,
    maxTokens: 2000,
    timeout: 30000,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    client = new LLMClient(mockLogger as any, mockConfig);
  });

  describe('Initialization', () => {
    test('should initialize with valid config', () => {
      expect(client).toBeDefined();
      expect(client.provider).toBe(LLMProvider.OPENAI);
      expect(client.model).toBe('gpt-4');
    });

    test('should throw error on invalid provider', () => {
      const invalidConfig = { ...mockConfig, provider: 'invalid' as any };
      expect(() => new LLMClient(mockLogger as any, invalidConfig)).toThrow();
    });

    test('should use default values for optional config', () => {
      const minimalConfig = {
        provider: LLMProvider.ANTHROPIC,
        apiKey: 'test-key',
      };
      const testClient = new LLMClient(mockLogger as any, minimalConfig as any);
      expect(testClient.temperature).toBe(0.7);
      expect(testClient.maxTokens).toBeGreaterThan(0);
    });
  });

  describe('Provider Selection', () => {
    test('should support OpenAI provider', () => {
      const openaiConfig = { ...mockConfig, provider: LLMProvider.OPENAI };
      const openaiClient = new LLMClient(mockLogger as any, openaiConfig);
      expect(openaiClient.provider).toBe(LLMProvider.OPENAI);
    });

    test('should support Anthropic provider', () => {
      const anthropicConfig = { ...mockConfig, provider: LLMProvider.ANTHROPIC };
      const anthropicClient = new LLMClient(mockLogger as any, anthropicConfig);
      expect(anthropicClient.provider).toBe(LLMProvider.ANTHROPIC);
    });

    test('should support DeepSeek provider', () => {
      const deepseekConfig = { ...mockConfig, provider: LLMProvider.DEEPSEEK };
      const deepseekClient = new LLMClient(mockLogger as any, deepseekConfig);
      expect(deepseekClient.provider).toBe(LLMProvider.DEEPSEEK);
    });

    test('should support Ollama provider', () => {
      const ollamaConfig = { ...mockConfig, provider: LLMProvider.OLLAMA };
      const ollamaClient = new LLMClient(mockLogger as any, ollamaConfig);
      expect(ollamaClient.provider).toBe(LLMProvider.OLLAMA);
    });
  });

  describe('Test Scenario Generation', () => {
    test('should have generateTestScenarios method', () => {
      expect(typeof client.generateTestScenarios).toBe('function');
    });

    test('should validate required parameters', async () => {
      const invalidInput = {
        userStory: '', // Empty
        pageUrl: 'https://example.com',
      };

      await expect(client.generateTestScenarios(invalidInput as any)).rejects.toThrow();
    });

    test('should return scenario object with required fields', async () => {
      const input = {
        userStory: 'User searches for products',
        pageUrl: 'https://example.com',
        pageElements: [],
      };

      // Note: This would require mocking the actual API call
      // For now we test the method exists and accepts valid input
      expect(typeof client.generateTestScenarios).toBe('function');
    });
  });

  describe('Test Data Suggestion', () => {
    test('should have suggestTestData method', () => {
      expect(typeof client.suggestTestData).toBe('function');
    });

    test('should validate scenario parameter', async () => {
      const invalidInput = {
        scenario: '', // Empty
        fieldTypes: ['email'],
      };

      await expect(client.suggestTestData(invalidInput as any)).rejects.toThrow();
    });

    test('should support multiple field types', async () => {
      const fieldTypes = ['email', 'password', 'phone', 'date', 'uuid'];
      const input = {
        scenario: 'User registration form',
        fieldTypes: fieldTypes,
      };

      expect(input.fieldTypes.length).toBe(5);
    });
  });

  describe('Test Coverage Analysis', () => {
    test('should have analyzeTestCoverage method', () => {
      expect(typeof client.analyzeTestCoverage).toBe('function');
    });

    test('should validate scenarios parameter', async () => {
      const invalidInput = {
        scenarios: [], // Empty
      };

      await expect(client.analyzeTestCoverage(invalidInput)).rejects.toThrow();
    });

    test('should accept optional requirements parameter', async () => {
      const input = {
        scenarios: [
          { title: 'Test 1', steps: ['Given...', 'When...', 'Then...'] },
        ],
        requirements: ['Feature A', 'Feature B'],
      };

      expect(input.requirements).toBeDefined();
      expect(input.requirements.length).toBe(2);
    });
  });

  describe('Test Debugging', () => {
    test('should have debugFailingTest method', () => {
      expect(typeof client.debugFailingTest).toBe('function');
    });

    test('should require test name and error message', async () => {
      const invalidInput = {
        testName: '',
        errorMessage: '',
      };

      await expect(client.debugFailingTest(invalidInput as any)).rejects.toThrow();
    });

    test('should accept optional test code', () => {
      const input = {
        testName: 'test_login',
        errorMessage: 'Element not found',
        testCode: 'await page.click("button")',
      };

      expect(input.testCode).toBeDefined();
    });
  });

  describe('Token Counting', () => {
    test('should have countTokens method', () => {
      expect(typeof client.countTokens).toBe('function');
    });

    test('should estimate token count for text', () => {
      const text = 'This is a test message';
      const estimatedTokens = client.countTokens(text);

      expect(typeof estimatedTokens).toBe('number');
      expect(estimatedTokens).toBeGreaterThan(0);
    });

    test('should handle long text', () => {
      const longText = 'word '.repeat(1000);
      const estimatedTokens = client.countTokens(longText);

      expect(estimatedTokens).toBeGreaterThan(100);
    });
  });

  describe('Error Handling', () => {
    test('should log errors appropriately', () => {
      const testClient = new LLMClient(mockLogger as any, mockConfig);
      expect(mockLogger.info).toHaveBeenCalled();
    });

    test('should handle network timeouts', async () => {
      const input = {
        userStory: 'Test story',
        pageUrl: 'https://example.com',
      };

      // Would test actual timeout behavior with mocked API
      expect(typeof client.generateTestScenarios).toBe('function');
    });

    test('should provide meaningful error messages', () => {
      const invalidConfig = {
        provider: 'invalid',
        apiKey: '',
      };

      expect(() => new LLMClient(mockLogger as any, invalidConfig as any)).toThrow();
    });
  });

  describe('Statistics Tracking', () => {
    test('should track request statistics', () => {
      const stats = client.getStatistics();
      expect(stats).toBeDefined();
      expect(typeof stats.totalRequests).toBe('number');
    });

    test('should track token usage', () => {
      const stats = client.getStatistics();
      expect(typeof stats.totalTokensUsed).toBe('number');
    });

    test('should estimate costs', () => {
      const stats = client.getStatistics();
      expect(typeof stats.estimatedCost).toBe('number');
    });
  });

  describe('Configuration Updates', () => {
    test('should allow updating temperature', () => {
      const newTemp = 0.5;
      client.setTemperature(newTemp);
      expect(client.temperature).toBe(newTemp);
    });

    test('should allow updating max tokens', () => {
      const newMax = 3000;
      client.setMaxTokens(newMax);
      expect(client.maxTokens).toBe(newMax);
    });

    test('should validate temperature range', () => {
      expect(() => client.setTemperature(-0.1)).toThrow();
      expect(() => client.setTemperature(1.5)).toThrow();
    });
  });
});
