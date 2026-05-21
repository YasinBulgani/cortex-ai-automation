/**
 * Configuration Management for BGTS_Test_Donusum
 *
 * Centralized configuration loading and validation
 * Supports environment variables, .env files, and environment-specific configs
 */

import * as dotenv from 'dotenv';
import * as fs from 'fs';
import * as path from 'path';
import { ConfigError } from '../utils/errors';

/**
 * Browser configuration types
 */
export type BrowserType = 'chromium' | 'firefox' | 'webkit';

interface BrowserConfig {
  type: BrowserType;
  headless: boolean;
  slowMo: number;
  timeout: number;
  viewport: {
    width: number;
    height: number;
  };
}

/**
 * API Configuration
 */
interface APIConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
  retryDelay: number;
  headers: Record<string, string>;
}

/**
 * Database Configuration
 */
interface DatabaseConfig {
  type: 'sqlite' | 'postgresql';
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database: string;
  synchronize: boolean;
  logging: boolean;
}

/**
 * LLM Provider Configuration
 */
interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'deepseek' | 'ollama';
  apiKey?: string;
  model: string;
  temperature: number;
  maxTokens: number;
  timeout: number;
}

/**
 * Main Configuration Object
 */
export interface AppConfig {
  // Environment
  environment: 'development' | 'test' | 'staging' | 'production';
  debug: boolean;

  // Logging
  logLevel: 'error' | 'warn' | 'info' | 'debug';
  logDir: string;

  // Browser automation
  browser: BrowserConfig;

  // Test execution
  timeout: number;
  retries: number;
  parallelWorkers: number;

  // API testing
  api: APIConfig;

  // Database
  database: DatabaseConfig;

  // AI/LLM
  llm: LLMConfig;

  // Paths
  paths: {
    features: string;
    steps: string;
    pages: string;
    reports: string;
    screenshots: string;
  };

  // Feature flags
  features: {
    aiTesting: boolean;
    visualRegression: boolean;
    accessibility: boolean;
    performance: boolean;
  };
}

/**
 * Configuration class
 * Loads and validates configuration from environment variables and .env files
 */
export class Config {
  private static instance: Config;
  private appConfig: AppConfig;

  private constructor() {
    this.loadEnvironmentVariables();
    this.appConfig = this.buildConfig();
    this.validate();
  }

  /**
   * Get singleton instance
   */
  static getInstance(): Config {
    if (!Config.instance) {
      Config.instance = new Config();
    }
    return Config.instance;
  }

  /**
   * Get configuration
   */
  getConfig(): AppConfig {
    return this.appConfig;
  }

  /**
   * Get specific config value
   */
  get<T = any>(key: string): T {
    const parts = key.split('.');
    let value: any = this.appConfig;

    for (const part of parts) {
      if (value[part] === undefined) {
        throw new ConfigError(key, `Configuration key not found: ${key}`);
      }
      value = value[part];
    }

    return value;
  }

  /**
   * Load environment variables from .env files
   */
  private loadEnvironmentVariables(): void {
    const env = process.env.NODE_ENV || 'development';

    // Load base .env file
    const envFile = path.resolve(process.cwd(), '.env');
    if (fs.existsSync(envFile)) {
      dotenv.config({ path: envFile });
    }

    // Load environment-specific .env file
    const envSpecificFile = path.resolve(process.cwd(), `.env.${env}`);
    if (fs.existsSync(envSpecificFile)) {
      dotenv.config({ path: envSpecificFile, override: true });
    }

    // Load .env.local (git-ignored, local overrides)
    const envLocalFile = path.resolve(process.cwd(), '.env.local');
    if (fs.existsSync(envLocalFile)) {
      dotenv.config({ path: envLocalFile, override: true });
    }
  }

  /**
   * Build configuration object from environment variables
   */
  private buildConfig(): AppConfig {
    return {
      // Environment
      environment: (process.env.NODE_ENV as any) || 'development',
      debug: process.env.DEBUG === 'true',

      // Logging
      logLevel: (process.env.LOG_LEVEL as any) || 'info',
      logDir: process.env.LOG_DIR || './logs',

      // Browser configuration
      browser: {
        type: (process.env.BROWSER as BrowserType) || 'chromium',
        headless: process.env.HEADLESS !== 'false',
        slowMo: parseInt(process.env.SLOW_MO || '0', 10),
        timeout: parseInt(process.env.BROWSER_TIMEOUT || '30000', 10),
        viewport: {
          width: parseInt(process.env.VIEWPORT_WIDTH || '1280', 10),
          height: parseInt(process.env.VIEWPORT_HEIGHT || '720', 10),
        },
      },

      // Test execution
      timeout: parseInt(process.env.TEST_TIMEOUT || '60000', 10),
      retries: parseInt(process.env.TEST_RETRIES || '1', 10),
      parallelWorkers: parseInt(process.env.PARALLEL_WORKERS || '1', 10),

      // API configuration
      api: {
        baseUrl: process.env.BASE_URL || 'https://paribu.com',
        timeout: parseInt(process.env.API_TIMEOUT || '30000', 10),
        retries: parseInt(process.env.API_RETRIES || '3', 10),
        retryDelay: parseInt(process.env.API_RETRY_DELAY || '1000', 10),
        headers: {
          'User-Agent': process.env.USER_AGENT || 'BGTS-Test-Donusum/1.0',
          'Accept': 'application/json',
        },
      },

      // Database configuration
      database: {
        type: (process.env.DATABASE_TYPE as any) || 'sqlite',
        host: process.env.DATABASE_HOST,
        port: process.env.DATABASE_PORT ? parseInt(process.env.DATABASE_PORT, 10) : undefined,
        username: process.env.DATABASE_USER,
        password: process.env.DATABASE_PASSWORD,
        database: process.env.DATABASE_NAME || './bgts.sqlite',
        synchronize: process.env.DATABASE_SYNC === 'true',
        logging: process.env.DATABASE_LOGGING === 'true',
      },

      // LLM configuration
      llm: {
        provider: (process.env.LLM_PROVIDER as any) || 'openai',
        apiKey: process.env.LLM_API_KEY,
        model: process.env.LLM_MODEL || 'gpt-4',
        temperature: parseFloat(process.env.LLM_TEMPERATURE || '0.7'),
        maxTokens: parseInt(process.env.LLM_MAX_TOKENS || '2000', 10),
        timeout: parseInt(process.env.LLM_TIMEOUT || '60000', 10),
      },

      // Paths
      paths: {
        features: process.env.FEATURES_PATH || './features',
        steps: process.env.STEPS_PATH || './core/typescript/steps',
        pages: process.env.PAGES_PATH || './core/typescript/pages',
        reports: process.env.REPORTS_PATH || './reports',
        screenshots: process.env.SCREENSHOTS_PATH || './screenshots',
      },

      // Feature flags
      features: {
        aiTesting: process.env.FEATURE_AI_TESTING === 'true',
        visualRegression: process.env.FEATURE_VISUAL_REGRESSION === 'true',
        accessibility: process.env.FEATURE_ACCESSIBILITY === 'true',
        performance: process.env.FEATURE_PERFORMANCE === 'true',
      },
    };
  }

  /**
   * Validate configuration
   * Checks that all required environment variables are set
   */
  private validate(): void {
    const errors: string[] = [];

    // Required environment variables
    const required = [
      'BASE_URL',
      'NODE_ENV',
    ];

    for (const envVar of required) {
      if (!process.env[envVar]) {
        errors.push(`Missing required environment variable: ${envVar}`);
      }
    }

    // Validate browser type
    const validBrowsers: BrowserType[] = ['chromium', 'firefox', 'webkit'];
    if (!validBrowsers.includes(this.appConfig.browser.type)) {
      errors.push(`Invalid BROWSER value: ${this.appConfig.browser.type}. Must be one of: ${validBrowsers.join(', ')}`);
    }

    // Validate database configuration
    if (this.appConfig.database.type === 'postgresql') {
      if (!this.appConfig.database.host) {
        errors.push('DATABASE_HOST is required for PostgreSQL');
      }
      if (!this.appConfig.database.username) {
        errors.push('DATABASE_USER is required for PostgreSQL');
      }
    }

    // Validate LLM configuration
    if (this.appConfig.features.aiTesting) {
      const validProviders = ['openai', 'anthropic', 'deepseek', 'ollama'];
      if (!validProviders.includes(this.appConfig.llm.provider)) {
        errors.push(`Invalid LLM_PROVIDER: ${this.appConfig.llm.provider}`);
      }

      if (this.appConfig.llm.provider !== 'ollama' && !this.appConfig.llm.apiKey) {
        errors.push(`LLM_API_KEY is required for ${this.appConfig.llm.provider}`);
      }
    }

    // Throw error if validation failed
    if (errors.length > 0) {
      throw new ConfigError('VALIDATION', errors.join('\n'));
    }
  }

  /**
   * Check if configuration is valid (no errors)
   */
  isValid(): boolean {
    try {
      this.validate();
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get validation errors (if any)
   */
  getValidationErrors(): string[] {
    try {
      this.validate();
      return [];
    } catch (error) {
      if (error instanceof ConfigError) {
        return error.context.message ? [error.context.message] : [];
      }
      return [String(error)];
    }
  }

  /**
   * Reset singleton (useful for testing)
   */
  static reset(): void {
    Config.instance = undefined!;
  }
}

/**
 * Export configured instance
 */
export const config = Config.getInstance();

/**
 * Helper function to get config value
 */
export function getConfig(): AppConfig {
  return config.getConfig();
}

/**
 * Helper function to get specific config value
 */
export function getConfigValue<T = any>(key: string): T {
  return config.get<T>(key);
}

/**
 * Environment helpers
 */
export const isProduction = (): boolean => config.get<string>('environment') === 'production';
export const isDevelopment = (): boolean => config.get<string>('environment') === 'development';
export const isTest = (): boolean => config.get<string>('environment') === 'test';
export const isDebug = (): boolean => config.get<boolean>('debug');
