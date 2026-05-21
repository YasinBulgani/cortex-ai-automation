export type AIProvider = 'anthropic' | 'openai' | 'google' | 'local';

export interface AIConfig {
  provider: AIProvider;
  model: string;
  apiKey: string;

  healing: {
    enabled: boolean;
    maxRetries: number;
    cacheEnabled: boolean;
    cacheTTL: number;
    fallbackStrategies: ('accessibility' | 'semantic' | 'structural' | 'ai')[];
    confidenceThreshold: number;
  };

  generation: {
    enabled: boolean;
    maxTokens: number;
    temperature: number;
    language: 'tr' | 'en';
    templateDir: string;
  };

  prioritization: {
    enabled: boolean;
    maxCIDuration: number;
    riskThreshold: number;
    historicalWindow: number;
  };

  anomaly: {
    enabled: boolean;
    flakyThreshold: number;
    slowdownMultiplier: number;
    windowSize: number;
    alertChannels: ('slack' | 'email' | 'jira')[];
  };

  privacy: {
    maskPII: boolean;
    useLocalModel: boolean;
    localModelEndpoint: string;
    auditLogEnabled: boolean;
  };
}

function env(key: string, fallback = ''): string {
  return process.env[key] ?? fallback;
}

export const defaultConfig: AIConfig = {
  provider: (env('AI_PROVIDER', 'anthropic') as AIProvider),
  model: env('AI_MODEL', 'claude-sonnet-4-20250514'),
  apiKey: env('AI_API_KEY'),

  healing: {
    enabled: env('SELF_HEAL', '1') === '1',
    maxRetries: 3,
    cacheEnabled: true,
    cacheTTL: 86_400,
    fallbackStrategies: ['accessibility', 'semantic', 'structural', 'ai'],
    confidenceThreshold: 0.8,
  },

  generation: {
    enabled: true,
    maxTokens: 4096,
    temperature: 0.3,
    language: 'tr',
    templateDir: './templates',
  },

  prioritization: {
    enabled: true,
    maxCIDuration: 600,
    riskThreshold: 30,
    historicalWindow: 30,
  },

  anomaly: {
    enabled: true,
    flakyThreshold: 0.3,
    slowdownMultiplier: 2.5,
    windowSize: 20,
    alertChannels: ['slack'],
  },

  privacy: {
    maskPII: true,
    useLocalModel: false,
    localModelEndpoint: 'http://localhost:11434',
    auditLogEnabled: true,
  },
};
