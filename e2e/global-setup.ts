import { chromium, type FullConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { ADMIN_EMAIL, ADMIN_PASSWORD, API_BASE, APP_BASE_URL } from "./config/runtime";
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

  let authRes: Response;
  try {
    authRes = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
    });
  } catch (err) {
    throw new Error(
      `[global-setup] Backend sunucusuna ulaşılamadı (${API_BASE}). ` +
      `Sunucunun çalıştığından emin olun. Hata: ${err}`
    );
  }
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
    {
      ...cookieBase,
      name: "twai_session",
      value: "1",
      httpOnly: false,
    },
    ...(auth.refresh_token
      ? [
          {
            ...cookieBase,
            name: "bgts_refresh_token",
            value: auth.refresh_token,
            httpOnly: true,
          },
        ]
      : []),
  ]);

  await page.goto(`${APP_BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate(({ accessToken, refreshToken }) => {
    localStorage.setItem("tspm_access_token", accessToken);
    localStorage.setItem("onboarded", "true");
    localStorage.setItem("neurex_onboarding_done", String(Date.now()));
    if (refreshToken) {
      localStorage.setItem("tspm_refresh_token", refreshToken);
    }
  }, {
    accessToken: auth.access_token,
    refreshToken: auth.refresh_token ?? null,
  });

  await page.goto(`${APP_BASE_URL}/projects`, { waitUntil: "domcontentloaded" });
  await page.waitForURL(/\/projects/, { timeout: 30_000 });

  await context.storageState({ path: STATE_FILE });
  await browser.close();

  console.log(`[global-setup] Auth state saved → ${STATE_FILE}`);
}

export default globalSetup;
