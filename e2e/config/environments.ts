import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./auth";

export interface EnvironmentConfig {
  name: string;
  appUrl: string;
  apiUrl: string;
  engineUrl: string;
  dbUrl: string;
  adminEmail: string;
  adminPassword: string;
  headless: boolean;
  retries: number;
  timeout: number;
  features: {
    ai: boolean;
    syntheticData: boolean;
    videoRecording: boolean;
  };
}

const configs: Record<string, EnvironmentConfig> = {
  local: {
    name: "local",
    appUrl: process.env.APP_URL || process.env.BASE_URL || process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000",
    apiUrl: process.env.API_BASE || "http://127.0.0.1:8765",
    engineUrl: process.env.ENGINE_BASE || "http://127.0.0.1:5001",
    dbUrl: "postgresql+psycopg2://twai_user:twai_pass@127.0.0.1:55433/syndata_db",
    adminEmail: "admin@example.com",
    adminPassword: "admin123",
    headless: false,
    retries: 0,
    timeout: 60_000,
    features: { ai: false, syntheticData: true, videoRecording: false },
  },
  ci: {
    name: "ci",
    appUrl: process.env.APP_URL || process.env.BASE_URL || process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000",
    apiUrl: process.env.API_BASE || "http://127.0.0.1:8765",
    engineUrl: process.env.ENGINE_BASE || "http://127.0.0.1:5001",
    dbUrl: "postgresql+psycopg2://test_user:test_password@localhost:5432/syndata_test",
    adminEmail: "admin@example.com",
    adminPassword: "admin123",
    headless: true,
    retries: 2,
    timeout: 90_000,
    features: { ai: false, syntheticData: false, videoRecording: true },
  },
  staging: {
    name: "staging",
    appUrl: process.env.STAGING_URL || "https://staging.bgtest.dev",
    apiUrl: process.env.STAGING_API_URL || "https://staging-api.bgtest.dev",
    engineUrl: process.env.STAGING_ENGINE_URL || "https://staging-engine.bgtest.dev",
    dbUrl: "",
    adminEmail: process.env.STAGING_ADMIN_EMAIL || ADMIN_EMAIL,
    adminPassword: process.env.STAGING_ADMIN_PASSWORD || ADMIN_PASSWORD,
    headless: true,
    retries: 2,
    timeout: 120_000,
    features: { ai: true, syntheticData: true, videoRecording: true },
  },
};

export function getEnvConfig(env?: string): EnvironmentConfig {
  const name = env || process.env.TEST_ENV || "local";
  const config = configs[name];
  if (!config) throw new Error(`Unknown environment: ${name}. Available: ${Object.keys(configs).join(", ")}`);
  return config;
}
