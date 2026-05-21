import { type AIProvider } from './ai-config.js';

interface ProviderConfig {
  name: string;
  baseUrl: string;
  models: string[];
  costPer1kTokens: { input: number; output: number };
  rateLimit: { requestsPerMinute: number; tokensPerMinute: number };
  features: string[];
}

export const PROVIDERS: Record<AIProvider, ProviderConfig> = {
  anthropic: {
    name: 'Anthropic',
    baseUrl: 'https://api.anthropic.com',
    models: [
      'claude-sonnet-4-20250514',
      'claude-4-opus-20260312',
    ],
    costPer1kTokens: { input: 0.003, output: 0.015 },
    rateLimit: { requestsPerMinute: 50, tokensPerMinute: 100_000 },
    features: ['code-generation', 'analysis', 'vision'],
  },

  openai: {
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    models: ['gpt-4o', 'gpt-4o-mini', 'o3-mini'],
    costPer1kTokens: { input: 0.005, output: 0.015 },
    rateLimit: { requestsPerMinute: 60, tokensPerMinute: 150_000 },
    features: ['code-generation', 'analysis', 'vision', 'function-calling'],
  },

  google: {
    name: 'Google AI',
    baseUrl: 'https://generativelanguage.googleapis.com',
    models: ['gemini-2.5-pro', 'gemini-2.5-flash'],
    costPer1kTokens: { input: 0.002, output: 0.010 },
    rateLimit: { requestsPerMinute: 60, tokensPerMinute: 200_000 },
    features: ['code-generation', 'analysis', 'vision', 'long-context'],
  },

  local: {
    name: 'Ollama (Local)',
    baseUrl: 'http://localhost:11434',
    models: ['codellama:34b', 'deepseek-coder-v2:latest', 'qwen2.5-coder:32b'],
    costPer1kTokens: { input: 0, output: 0 },
    rateLimit: { requestsPerMinute: 10, tokensPerMinute: 10_000 },
    features: ['code-generation', 'offline', 'privacy'],
  },
};

/**
 * Hassas veri içeren isteklerde lokal model'e fallback yap.
 * Dış API kullanılamıyorsa yine lokal'e düş.
 */
export function selectProvider(
  preferred: AIProvider,
  containsSensitiveData: boolean,
): AIProvider {
  if (containsSensitiveData) return 'local';
  return preferred;
}

export function estimateCost(
  provider: AIProvider,
  inputTokens: number,
  outputTokens: number,
): number {
  const config = PROVIDERS[provider];
  return (
    (inputTokens / 1000) * config.costPer1kTokens.input +
    (outputTokens / 1000) * config.costPer1kTokens.output
  );
}
