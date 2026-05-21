import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

process.env.PLAYWRIGHT_BROWSERS_PATH =
  process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(__dirname, ".pw-browsers");

const TEST_ENV = process.env.TEST_ENV || "local";
const APP_URL_OVERRIDE = process.env.APP_URL || process.env.APP_BASE_URL || process.env.APP_URL_OVERRIDE;
const APP_PORT_OVERRIDE = process.env.APP_PORT || process.env.APP_PORT_OVERRIDE;

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
        // Allure — engine pytest tarafındaki Allure ile aynı aggregator'da
        // birleştirilebilsin diye. `allure-playwright` devDependency; paket
        // yoksa reporter sessizce devre dışı kalır (opt-in). Klasörü engine
        // `allure-results` ile karıştırmamak için ayrı dizin.
        ["allure-playwright", {
          detail: true,
          outputFolder: "reports/allure-e2e-results",
          suiteTitle: true,
        }],
        ["list"],
      ]
    : [["html", { outputFolder: "reports/e2e-html", open: "on-failure" }], ["list"]],

  outputDir: "reports/e2e-artifacts",

  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",

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
        "rbac.spec.ts",
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
        "visual-page.spec.ts",
        "mobile.spec.ts",
        "ai-workflows.spec.ts",
        "ai-quality.spec.ts",
        "mobile-appium.spec.ts",
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

    // ── Mobile: Visium Farm E2E (Pixel 5 viewport) ──
    {
      name: "mobile",
      testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts"],
      use: { ...devices["Pixel 5"] },
      retries: 1,
    },

    // ── a11y: Axe-core WCAG 2.1 AA taraması (kritik sayfalar) ──
    {
      name: "a11y",
      testMatch: ["accessibility.spec.ts"],
      retries: 0,
      timeout: 60_000,
    },

    // ── Cross-browser smoke: Firefox ──
    // Nightly CI'da çalışır; Chromium-özel bug'ları (ör. webkit-spesifik
    // CSS davranışları veya Firefox event bubbling farkları) erken yakalar.
    {
      name: "smoke-firefox",
      testMatch: ["smoke.spec.ts", "login.spec.ts", "navigation.spec.ts"],
      use: { ...devices["Desktop Firefox"] },
      retries: 1,
      timeout: 60_000,
    },

    // ── Cross-browser smoke: WebKit (Safari) ──
    {
      name: "smoke-webkit",
      testMatch: ["smoke.spec.ts", "login.spec.ts", "navigation.spec.ts"],
      use: { ...devices["Desktop Safari"] },
      retries: 1,
      timeout: 60_000,
    },

    // ── Visual regression ──
    // Nightly'de çalışır. Baseline farkı bulursa fail eder; kasıtlı UI
    // değişikliğinde `--update-snapshots` ile yeniden üretilir.
    {
      name: "visual",
      testMatch: ["visual-regression.spec.ts"],
      retries: 0,
      timeout: 45_000,
      use: {
        ...devices["Desktop Chrome"],
        // Font smoothing ve caret blink animasyonlarını kapat → daha
        // deterministik screenshot.
        deviceScaleFactor: 1,
      },
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
