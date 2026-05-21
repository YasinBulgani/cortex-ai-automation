import { getEnvConfig } from "./environments";

const env = getEnvConfig();

export const APP_BASE_URL =
  process.env.APP_URL ||
  process.env.BASE_URL ||
  process.env.PLAYWRIGHT_BASE_URL ||
  env.appUrl;
export const API_BASE = process.env.API_BASE || env.apiUrl;
export const ENGINE_BASE = process.env.ENGINE_BASE || env.engineUrl;
export const ADMIN_EMAIL = process.env.ADMIN_EMAIL || env.adminEmail;
export const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || env.adminPassword;
