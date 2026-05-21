/**
 * Configuration Management
 * Centralized configuration for browsers, environments, and test settings
 */

import { Browser, chromium, firefox, webkit, LaunchOptions, BrowserContextOptions } from 'playwright';
import * as dotenv from 'dotenv';
import { MissingEnvironmentVariableError } from '../utils/CustomErrors';
import { REQUIRED_ENV_VARS, ENV_VARS, TIMEOUTS } from './constants';

dotenv.config();

// Browser Types
export type BrowserType = 'chromium' | 'firefox' | 'webkit';

export interface BrowserConfig {
  type: BrowserType;
  launchOptions: LaunchOptions;
  contextOptions: BrowserContextOptions;
}

export interface EnvironmentConfig {
  baseUrl: string;
  apiUrl?: string;
  timeout: number;
}

// Browser Configuration
const DEFAULT_LOCALE = process.env[ENV_VARS.BROWSER_LOCALE] || 'en-US';
const DEFAULT_TIMEZONE = process.env[ENV_VARS.BROWSER_TIMEZONE] || 'America/New_York';
const DEFAULT_HEADLESS = process.env[ENV_VARS.HEADLESS] !== 'false';

export const browserConfigs: Record<BrowserType, BrowserConfig> = {
  chromium: {
    type: 'chromium',
    launchOptions: {
      headless: DEFAULT_HEADLESS,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--start-maximized']
    },
    contextOptions: {
      viewport: null,
      locale: DEFAULT_LOCALE,
      timezoneId: DEFAULT_TIMEZONE
    }
  },
  firefox: {
    type: 'firefox',
    launchOptions: {
      headless: DEFAULT_HEADLESS,
      args: ['--start-maximized']
    },
    contextOptions: {
      viewport: null,
      locale: DEFAULT_LOCALE,
      timezoneId: DEFAULT_TIMEZONE
    }
  },
  webkit: {
    type: 'webkit',
    launchOptions: {
      headless: DEFAULT_HEADLESS
    },
    contextOptions: {
      viewport: null,
      locale: DEFAULT_LOCALE,
      timezoneId: DEFAULT_TIMEZONE
    }
  }
};

export function getRandomBrowser(): BrowserType {
  const browsers: BrowserType[] = ['chromium', 'firefox', 'webkit'];
  const randomIndex = Math.floor(Math.random() * browsers.length);
  return browsers[randomIndex];
}

export async function launchBrowser(browserType: BrowserType = 'chromium'): Promise<Browser> {
  const config = browserConfigs[browserType];
  
  switch (browserType) {
    case 'chromium':
      return await chromium.launch(config.launchOptions);
    case 'firefox':
      return await firefox.launch(config.launchOptions);
    case 'webkit':
      return await webkit.launch(config.launchOptions);
    default:
      throw new Error(`Unsupported browser type: ${browserType}`);
  }
}

export function getBrowserConfig(browserType: BrowserType = 'chromium'): BrowserConfig {
  if (!browserConfigs[browserType]) {
    throw new Error(`Browser "${browserType}" is not configured. Available: ${Object.keys(browserConfigs).join(', ')}`);
  }
  return browserConfigs[browserType];
}

// Environment Configuration
const DEFAULT_TIMEOUT = parseInt(process.env[ENV_VARS.DEFAULT_TIMEOUT] || String(TIMEOUTS.DEFAULT), 10);

export const environments: Record<string, EnvironmentConfig> = {
  qa: {
    baseUrl: process.env[ENV_VARS.QA_BASE_URL] || 'https://qa.example.com',
    apiUrl: process.env.QA_API_URL,
    timeout: DEFAULT_TIMEOUT
  },
  stage: {
    baseUrl: process.env[ENV_VARS.STAGE_BASE_URL] || 'https://stage.example.com',
    apiUrl: process.env.STAGE_API_URL,
    timeout: DEFAULT_TIMEOUT
  },
  prod: {
    baseUrl: process.env[ENV_VARS.PROD_BASE_URL] || 'https://prod.example.com',
    apiUrl: process.env.PROD_API_URL,
    timeout: DEFAULT_TIMEOUT
  },
  paribu: {
    baseUrl: process.env[ENV_VARS.PARIBU_BASE_URL] || 'https://paribu.com',
    timeout: DEFAULT_TIMEOUT
  }
};

export function getEnvironmentConfig(env: string = 'qa'): EnvironmentConfig {
  const environment = env.toLowerCase();
  if (!environments[environment]) {
    throw new Error(`Environment "${environment}" is not configured. Available: ${Object.keys(environments).join(', ')}`);
  }
  return environments[environment];
}

// Validate Environment Variables
function validateEnvironment(): void {
  const missing: string[] = [];
  
  for (const varName of REQUIRED_ENV_VARS) {
    if (!process.env[varName]) {
      missing.push(varName);
    }
  }
  
  if (missing.length > 0) {
    throw new MissingEnvironmentVariableError(missing.join(', '));
  }
}

// Validate on module load
try {
  validateEnvironment();
} catch (error) {
  if (error instanceof MissingEnvironmentVariableError) {
    console.warn(`Warning: ${error.message}. Some features may not work correctly.`);
  }
}
