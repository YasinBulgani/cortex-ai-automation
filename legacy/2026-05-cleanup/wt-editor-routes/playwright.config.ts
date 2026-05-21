import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

process.env.PLAYWRIGHT_BROWSERS_PATH =
  process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(__dirname, ".pw-browsers");

const TEST_ENV = process.env.TEST_ENV || "local";

const ENV_MAP: Record<string, { apiPort: number; appUrl: string; dbUrl: string }> = {
  local: {
    apiPort: 8765,
    appUrl: APP_URL_OVERRIDE || `http://127.0.0.1:${APP_PORT_OVERRIDE || "3000"}`,
    dbUrl:
      process.env.LOCAL_DB_URL ||
      "postgresql+psycopg2://twai_user:twai_pass@127.0.0.1:5432/syndata_db",
  },
  staging: {
    apiPort: 8765,
    appUrl: process.env.STAGING_URL || "https://staging.bgtest.dev",
    dbUrl: process.env.STAGING_DB_URL || "",
  },
  ci: {
    apiPort: 8765,
    appUrl: "http://127.0.0.1:3000",
    dbUrl: "postgresql+psycopg2://test_user:test_password@localhost:5432/syndata_test",
  },
};

const env = ENV_MAP[TEST_ENV] || ENV_MAP.local;
const API_BASE = `http://127.0.0.1:${env.apiPort}`;
const ENGINE_PORT = 5001;
const ENGINE_BASE = `http://127.0.0.1:${ENGINE_PORT}`;

const isExternalEnv = TEST_ENV === "staging";

// CI ortamında sistem python'unu kullan; lokalde venv
const PYTHON_CMD = process.env.CI ? "python" : ".venv/bin/python";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  workers: process.env.CI ? 1 : 2,
  timeout: 60_000,
  expect: { timeout: 10_000 },

  retries: process.env.CI ? 2 : 0,

  reporter: process.env.CI
    ? [
        ["html", { outputFolder: "reports/e2e-html", open: "never" }],
        ["json", { outputFile: "reports/e2e-results.json" }],
        ["junit", { outputFile: "reports/e2e-junit.xml" }],
        ["list"],
      ]
    : [["html", { outputFolder: "reports/e2e-html", open: "on-failure" }], ["list"]],

  outputDir: "reports/e2e-artifacts",

  globalSetup: "./e2e/global-setup.ts",

  use: {
    ...devices["Desktop Chrome"],
    baseURL: env.appUrl,
    storageState: "e2e/.auth/admin.json",

    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: process.env.CI ? "on-first-retry" : "off",

    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "setup",
      testMatch: /global-setup\.ts/,
      teardown: "teardown",
    },
    {
      name: "teardown",
      testMatch: /global-teardown\.ts/,
    },

    // ── Smoke: kritik akış, hızlı geri bildirim ──
    {
      name: "smoke",
      testMatch: ["smoke.spec.ts", "login.spec.ts"],
      retries: 1,
      timeout: 45_000,
    },

    // ── Service: yalnızca API katmanı (UI yok) ──
    {
      name: "service",
      testMatch: ["**/login.spec.ts"],
      grep: /@api|Backend Auth API/,
      use: { ...devices["Desktop Chrome"] },
      retries: 1,
      timeout: 30_000,
    },

    // ── Regression: mevcut özellik doğrulama ──
    {
      name: "regression",
      testMatch: [
        "regression.spec.ts",
        "projects.spec.ts",
        "scenarios.spec.ts",
        "approvals.spec.ts",
        "executions.spec.ts",
        "flows.spec.ts",
        "import.spec.ts",
        "requirements.spec.ts",
        "schedules.spec.ts",
        "test-data.spec.ts",
        "integrations.spec.ts",
        "bdd-generate.spec.ts",
        "navigation.spec.ts",
        "api-tests.spec.ts",
        "scenario-versions.spec.ts",
        "reports.spec.ts",
      ],
      retries: 2,
      timeout: 90_000,
    },

    // ── Full: tüm testler ──
    {
      name: "full",
      testMatch: ["**/*.spec.ts"],
      retries: 2,
      timeout: 120_000,
    },

    // ── Mobile: responsive doğrulama ──
    {
      name: "mobile",
      testMatch: ["smoke.spec.ts", "login.spec.ts"],
      use: { ...devices["Pixel 5"] },
      retries: 1,
    },
  ],

  ...(isExternalEnv
    ? {}
    : {
        webServer: [
          {
            command: `${PYTHON_CMD} -m uvicorn app.main:app --host 127.0.0.1 --port ${env.apiPort}`,
            cwd: path.join(__dirname, "backend"),
            env: {
              ...process.env,
              DEBUG: "true",
              // DATABASE_URL'i zorla override etmiyoruz; backend `.env`den
              // (backend/.env → ../.env symlink) doğru kredensiyali okusun.
              // Gerekirse LOCAL_DB_URL env değişkeniyle override edilebilir.
              ...(process.env.LOCAL_DB_URL ? { DATABASE_URL: process.env.LOCAL_DB_URL } : {}),
              PYTHONPATH: ".",
              // E2E testleri kendi kullanıcısını register edebilsin:
              ALLOW_SELF_REGISTRATION: "true",
            },
            url: `${API_BASE}/health`,
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
          },
          {
            command: "npm run dev",
            cwd: `${__dirname}/apps/web`,
            env: {
              ...process.env,
              NEXT_PUBLIC_API_BASE: API_BASE,
              NEXT_PUBLIC_ENGINE_BASE: ENGINE_BASE,
            },
            url: env.appUrl,
            reuseExistingServer: !process.env.CI,
            timeout: 120_000,
          },
          {
            command: `${PYTHON_CMD} app.py`,
            cwd: path.join(__dirname, "engine"),
            env: {
              ...process.env,
              ENGINE_PORT: String(ENGINE_PORT),
              PYTHONPATH: ".",
            },
            url: `${ENGINE_BASE}/health`,
            reuseExistingServer: !process.env.CI,
            timeout: 60_000,
          },
        ],
      }),
});
