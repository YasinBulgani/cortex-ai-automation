import { chromium, type FullConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { API_BASE } from "./config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

const API = API_BASE;
const AUTH_DIR = path.join(__dirname, ".auth");
const STATE_FILE = path.join(AUTH_DIR, "admin.json");

function resolveAppUrl(config: FullConfig) {
  if (process.env.APP_URL) return process.env.APP_URL;
  const smokeProject = config.projects.find((project) => project.name === "smoke");
  const baseURL = smokeProject?.use?.baseURL || config.projects[0]?.use?.baseURL;
  return typeof baseURL === "string" ? baseURL : "http://127.0.0.1:3417";
}

async function globalSetup(config: FullConfig) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  const appUrl = resolveAppUrl(config);

  const authRes = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
  });
  if (!authRes.ok) {
    const body = await authRes.text();
    throw new Error(`[global-setup] API login failed (${authRes.status}): ${body}`);
  }
  const auth = await authRes.json() as { access_token: string; refresh_token?: string | null };

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  const app = new URL(appUrl);
  const secure = app.protocol === "https:";
  const cookieBase = {
    domain: app.hostname,
    path: "/",
    sameSite: "Lax" as const,
    secure,
  };

  await context.addCookies([
    {
      ...cookieBase,
      name: "bgts_access_token",
      value: auth.access_token,
      httpOnly: true,
    },
    ...(auth.refresh_token ? [{
      ...cookieBase,
      name: "bgts_refresh_token",
      value: auth.refresh_token,
      httpOnly: true,
    }] : []),
  ]);

  await page.goto(`${appUrl}/projects`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/projects/, { timeout: 30_000 });

  await context.storageState({ path: STATE_FILE });
  await browser.close();

  console.log(`[global-setup] Auth state saved → ${STATE_FILE}`);
}

export default globalSetup;
