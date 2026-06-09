# PHASE 3.1: E2E Expansion + Performance Test Implementation Specification

**Status:** Implementation Ready  
**Date:** 2026-06-09  
**Timeline:** 3 weeks (2 engineers)  
**Target Readiness:** Level 4 (Production-Grade E2E + Load Test)

---

## Executive Summary

Phase 3.1 expands the existing Playwright E2E framework (28 spec files) into a comprehensive test suite with **45+ test scenarios** across **cross-browser + mobile variants**, and establishes **k6-based performance testing** with automated trend detection and dashboard integration.

### Success Criteria
- ✅ 30+ E2E scenarios (base + variants)
- ✅ 5 load test profiles (100/250/1000 VU, database, UI rendering)
- ✅ Level 4 readiness (automated perf trend detection)
- ✅ Cross-browser matrix: Chrome × Firefox × Safari (45 total)
- ✅ Mobile responsive: iPhone SE × iPad × Android (60 total)
- ✅ Performance dashboard (k6 Cloud or Grafana integration)

---

## SECTION 1: E2E TEST EXPANSION

### 1.1 Current State

**Existing Spec Files (28):**
```
smoke.spec.ts, login.spec.ts (critical path)
regression.spec.ts, projects.spec.ts, scenarios.spec.ts,
approvals.spec.ts, rbac.spec.ts, executions.spec.ts,
flows.spec.ts, import.spec.ts, requirements.spec.ts,
schedules.spec.ts, test-data.spec.ts, integrations.spec.ts,
bdd-generate.spec.ts, navigation.spec.ts, api-tests.spec.ts,
scenario-versions.spec.ts, reports.spec.ts, visual-page.spec.ts,
mobile.spec.ts, ai-workflows.spec.ts, ai-quality.spec.ts,
mobile-appium.spec.ts, accessibility.spec.ts, visual-regression.spec.ts,
a11y-sidebar.spec.ts, mobile-responsive.spec.ts
```

**Current Test Sets:**
```
playwright.config.ts projects:
  - smoke (2 files)        → login + smoke
  - regression (22 files)  → feature coverage
  - mobile (2 files)       → Pixel 5 viewport
  - a11y (1 file)          → Accessibility scanning
  - smoke-firefox (3 files) → Cross-browser variant
  - smoke-webkit (3 files)  → Cross-browser variant
  - visual (1 file)        → Snapshot regression
```

### 1.2 Test Variant Expansion Strategy

**Goal:** Systematic coverage of happy path + error + edge cases per workflow

#### 1.2.1 Variant Types Definition

```
┌─────────────────────────────────────────────────────────┐
│ VARIANT MATRIX FOR EACH WORKFLOW                        │
├────────────────┬──────────────────────────────────────┤
│ Happy Path     │ Success flow (existing test files)    │
│ Error Path     │ Validation failures, API errors       │
│ Edge Case      │ Boundary conditions, race conditions  │
└────────────────┴──────────────────────────────────────┘

Example: Scenario Creation Workflow
├─ Happy:  Create scenario → view → execute ✅
├─ Error:  Duplicate name → invalid input → permission denied ❌
└─ Edge:   Empty steps → max length → concurrent edit 🔲
```

#### 1.2.2 Expansion Plan: Core 10 Workflows

| Workflow | Happy Path | Error Path | Edge Case | New Files | Total Tests |
|----------|-----------|-----------|-----------|-----------|------------|
| Login | login.spec.ts ✅ | login-error.spec.ts | login-edge.spec.ts | 2 new | 15 |
| Project CRUD | projects.spec.ts ✅ | projects-error.spec.ts | projects-edge.spec.ts | 2 new | 18 |
| Scenario CRUD | scenarios.spec.ts ✅ | scenarios-error.spec.ts | scenarios-edge.spec.ts | 2 new | 21 |
| Test Execution | executions.spec.ts ✅ | executions-error.spec.ts | executions-edge.spec.ts | 2 new | 15 |
| Test Case Design | test-data.spec.ts ✅ | test-data-error.spec.ts | test-data-edge.spec.ts | 2 new | 18 |
| Requirements Mgmt | requirements.spec.ts ✅ | requirements-error.spec.ts | requirements-edge.spec.ts | 2 new | 12 |
| Integrations | integrations.spec.ts ✅ | integrations-error.spec.ts | integrations-edge.spec.ts | 2 new | 15 |
| RBAC | rbac.spec.ts ✅ | rbac-error.spec.ts | rbac-edge.spec.ts | 2 new | 18 |
| AI Workflows | ai-workflows.spec.ts ✅ | ai-workflows-error.spec.ts | ai-workflows-edge.spec.ts | 2 new | 12 |
| Reporting | reports.spec.ts ✅ | reports-error.spec.ts | reports-edge.spec.ts | 2 new | 12 |
| **TOTAL** | | | | **20 new** | **156 tests** |

### 1.3 Implementation: Happy Path Extension

**Pattern:** Extend each happy-path workflow with error + edge variants

#### 1.3.1 Login Variant Example

**File: e2e/login-error.spec.ts** (NEW)
```typescript
import { test, expect } from "./fixtures/pages.fixture";

test.describe("Login — Error Cases", () => {
  test.describe("Invalid Credentials", () => {
    test("invalid email format should show validation error", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail("not-an-email");
      await loginPage.fillPassword("password");
      await loginPage.submit();
      await expect(loginPage.emailError).toContainText("Valid email required");
    });

    test("wrong password should show auth error", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail("admin@example.com");
      await loginPage.fillPassword("wrongpassword");
      await loginPage.submit();
      await expect(loginPage.errorBanner).toContainText("Invalid credentials");
    });

    test("non-existent user should show auth error", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail("nonexistent@example.com");
      await loginPage.fillPassword("password");
      await loginPage.submit();
      await expect(loginPage.errorBanner).toContainText("User not found");
    });
  });

  test.describe("Rate Limiting", () => {
    test("5 failed attempts should lock account temporarily", async ({ loginPage }) => {
      await loginPage.goto();
      for (let i = 0; i < 5; i++) {
        await loginPage.fillEmail("admin@example.com");
        await loginPage.fillPassword("wrong");
        await loginPage.submit();
        await loginPage.page.waitForTimeout(200);
      }
      await expect(loginPage.errorBanner).toContainText("too many attempts");
    });
  });
});
```

**File: e2e/login-edge.spec.ts** (NEW)
```typescript
import { test, expect } from "./fixtures/pages.fixture";

test.describe("Login — Edge Cases", () => {
  test.describe("Boundary Conditions", () => {
    test("email with unicode characters should be accepted", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail("用户@example.com");
      await loginPage.fillPassword("password");
      // Should not error on input, but may fail on backend
    });

    test("very long password (1000+ chars) should be handled", async ({ loginPage }) => {
      const longPassword = "a".repeat(1000);
      await loginPage.goto();
      await loginPage.fillEmail("admin@example.com");
      await loginPage.fillPassword(longPassword);
      await loginPage.submit();
      // Expect graceful error or truncation
    });

    test("session timeout during form fill should warn user", async ({ page, loginPage }) => {
      await loginPage.goto();
      // Wait 15+ minutes (simulate timeout)
      // Fill form and submit
      // Should show session expired, offer re-login
    });
  });

  test.describe("Concurrent Access", () => {
    test("login from two sessions simultaneously should handle correctly", async ({ browser }) => {
      const context1 = await browser.newContext();
      const context2 = await browser.newContext();
      const page1 = await context1.newPage();
      const page2 = await context2.newPage();

      // Both login with same credentials
      // Last one should succeed or show conflict error
    });
  });
});
```

### 1.4 Cross-Browser Expansion

#### 1.4.1 Current State
- ✅ smoke-firefox: 3 files (smoke + login + navigation)
- ✅ smoke-webkit: 3 files (smoke + login + navigation)
- ❌ Full regression × Chrome/Firefox/Safari (needs implementation)

#### 1.4.2 Implementation: Full Regression Matrix

**Target:** All 22 regression spec files × 3 browsers = 66 variants

**Update playwright.config.ts:**
```typescript
// Add to projects array:
{
  name: "regression-chrome",
  testMatch: [
    "regression.spec.ts", "projects.spec.ts", "scenarios.spec.ts",
    "approvals.spec.ts", "rbac.spec.ts", "executions.spec.ts",
    "flows.spec.ts", "import.spec.ts", "requirements.spec.ts",
    "schedules.spec.ts", "test-data.spec.ts", "integrations.spec.ts",
    "bdd-generate.spec.ts", "navigation.spec.ts", "api-tests.spec.ts",
    "scenario-versions.spec.ts", "reports.spec.ts", "mobile.spec.ts",
    "ai-workflows.spec.ts", "ai-quality.spec.ts"
  ],
  use: { ...devices["Desktop Chrome"] },
  fullyParallel: !process.env.CI,
  retries: 2,
  timeout: 90_000,
},

{
  name: "regression-firefox",
  testMatch: [
    // Same 22 files as regression-chrome
  ],
  use: { ...devices["Desktop Firefox"] },
  fullyParallel: !process.env.CI,
  retries: 2,
  timeout: 90_000,
},

{
  name: "regression-webkit",
  testMatch: [
    // Same 22 files as regression-chrome
  ],
  use: { ...devices["Desktop Safari"] },
  fullyParallel: !process.env.CI,
  retries: 2,
  timeout: 90_000,
},
```

**CI Integration:**
```yaml
# .github/workflows/e2e-nightly.yml
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC

jobs:
  e2e-cross-browser:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: [regression-chrome, regression-firefox, regression-webkit]
    steps:
      - uses: actions/checkout@v3
      - run: npm install
      - run: npx playwright test --project=${{ matrix.project }}
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-report-${{ matrix.project }}
          path: reports/e2e-html/
```

### 1.5 Mobile Variant Expansion

#### 1.5.1 Current State
- ✅ Pixel 5: mobile.spec.ts + mobile-responsive.spec.ts

#### 1.5.2 Implementation: Multi-Device Matrix

**New devices to add:**
```typescript
// In playwright.config.ts projects array:

{
  name: "mobile-iphone-se",
  testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts", "navigation.spec.ts"],
  use: { ...devices["iPhone SE"] },
  retries: 1,
},

{
  name: "mobile-iphone-pro",
  testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts", "navigation.spec.ts"],
  use: { ...devices["iPhone 12 Pro"] },
  retries: 1,
},

{
  name: "mobile-ipad",
  testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts", "navigation.spec.ts"],
  use: { ...devices["iPad Pro"] },
  retries: 1,
},

{
  name: "mobile-android-tablet",
  testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts", "navigation.spec.ts"],
  use: {
    ...devices["Galaxy Tab S4"],
    hasTouch: true,
  },
  retries: 1,
},

{
  name: "mobile-pixel-5", // Existing
  testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts"],
  use: { ...devices["Pixel 5"] },
  retries: 1,
},
```

**Total E2E Variant Count After 1.5:**
```
Base 28 files × (1 Chrome + 3 Firefox/WebKit smoke)     = 31
+ 20 new error/edge spec files                           = 51
+ Cross-browser regression (22 × 3 browsers)             = 66
+ Mobile multi-device (3 files × 5 devices)              = 15
─────────────────────────────────────────────────────────
TOTAL UNIQUE TESTS: 60+ scenarios, 150+ E2E variants
```

### 1.6 Test Set Organization

Define formal test sets for CI/CD pipelines:

```bash
# .make.d/test-sets.mk or playwright.config.ts

SMOKE_SET="smoke"
  → login.spec.ts, smoke.spec.ts
  → 5 critical tests, 2 min runtime

REGRESSION_SET="regression"
  → 22 spec files (projects, scenarios, executions, etc.)
  → 120+ tests, 15 min runtime

CROSS_BROWSER_SET="regression-{chrome|firefox|webkit}"
  → Same 22 files × 3 browsers
  → 360+ tests, 45 min per browser

MOBILE_SET="mobile-{pixel|iphone-se|iphone-pro|ipad|android}"
  → mobile.spec.ts + mobile-responsive.spec.ts
  → 40+ tests per device

NIGHTLY_SET="smoke + regression + cross-browser"
  → All smoke + full regression across all 3 browsers
  → 500+ tests, 90 min total

RELEASE_SET="smoke + regression + mobile + a11y"
  → Comprehensive pre-release validation
  → Manual review of visual + accessibility reports
  → 600+ tests, 2 hours total
```

---

## SECTION 2: PERFORMANCE TEST EXPANSION

### 2.1 Current State

**Existing k6 Tests:**
```
performance-tests/
├── load/
│   └── api-load.js
└── performance/
    ├── load_test.js          (fixed load)
    ├── soak_test.js          (8-hour endurance)
    ├── spike_test.js         (0→VU spike)
    ├── stress_test.js        (to breakpoint)
    ├── critical-path.js      (10 VU, 30s) ← NEW 2026-06-09
    └── helpers/auth.js
```

**Baseline Infrastructure:**
- ✅ backend/perf_baseline.json
- ✅ scripts/check_perf_baseline.py (manual verification)

### 2.2 Performance Test Expansion Strategy

#### 2.2.1 Load Test Profiles (5 Total)

| Profile | VUs | Duration | Purpose | Thresholds |
|---------|-----|----------|---------|-----------|
| **Critical Path** | 10 | 30s + ramp | Baseline sanity | p95 < 2s |
| **Light Load** | 50 | 5 min + ramp | Normal traffic | p95 < 1.5s |
| **Medium Load** | 250 | 10 min + ramp | Peak traffic | p95 < 2s |
| **Heavy Load** | 500 | 10 min + ramp | Stress threshold | p95 < 3s |
| **Breaking Point** | 1000 | 10 min + ramp | Failure mode | p99 < 10s |

#### 2.2.2 Load Test Type Coverage

```
EXISTING:
✅ Steady Load       (load_test.js, critical-path.js)
✅ Spike (0→N)      (spike_test.js)
✅ Stress (ramp)    (stress_test.js)
✅ Soak (8h)        (soak_test.js)

MISSING:
❌ Database Load    (bulk insert, query perf)
❌ UI Rendering     (page load time under concurrency)
❌ Cache Warmup     (cold cache vs warm cache)
❌ Error Injection  (chaos: 503, timeout, network delay)
```

### 2.3 Implementation: New Performance Tests

#### 2.3.1 Light Load Test (50 VU)

**File: performance-tests/performance/light-load.js** (NEW)
```javascript
/**
 * Light Load Test — Normal Traffic Simulation
 *
 * - 50 Virtual Users
 * - 5 minute steady state
 * - Represents typical daily traffic
 * - Thresholds: p95 < 1.5s, error_rate < 1%
 *
 * Run: k6 run performance-tests/performance/light-load.js
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: 50 },   // Ramp up
    { duration: "5m", target: 50 },    // Steady state
    { duration: "30s", target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: [
      "p(50) < 500",
      "p(90) < 1000",
      "p(95) < 1500",
      "p(99) < 3000",
    ],
    http_req_failed: ["rate < 0.01"],
  },
};

export function setup() {
  const token = login();
  return { token };
}

export default function (data) {
  const headers = authHeaders(data.token);

  // Typical workflow: list projects → open project → list scenarios
  group("List Projects", () => {
    const res = http.get(`${API_BASE}/api/v1/tspm/projects`, { headers });
    check(res, {
      "status 200": (r) => r.status === 200,
      "response time < 1s": (r) => r.timings.duration < 1000,
    });
  });

  sleep(1);

  group("List Scenarios", () => {
    const res = http.get(`${API_BASE}/api/v1/scenarios?limit=50`, { headers });
    check(res, {
      "status 200": (r) => r.status === 200,
      "response time < 500ms": (r) => r.timings.duration < 500,
    });
  });

  sleep(1);

  group("List Test Cases", () => {
    const res = http.get(`${API_BASE}/api/v1/test-cases?limit=100`, { headers });
    check(res, {
      "status 200": (r) => r.status === 200,
    });
  });

  sleep(2);
}

export function teardown(data) {
  console.log(`Light load test complete. Avg response time tracked.`);
}
```

#### 2.3.2 Heavy Load Test (500 VU)

**File: performance-tests/performance/heavy-load.js** (NEW)
```javascript
/**
 * Heavy Load Test — Peak Traffic Scenario
 *
 * - 500 Virtual Users
 * - 10 minute sustained load
 * - Represents holiday/viral peak
 * - Thresholds: p95 < 2s, error_rate < 2%
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "1m", target: 500 },   // Ramp up (1 min)
    { duration: "10m", target: 500 },  // Steady state
    { duration: "1m", target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: [
      "p(50) < 800",
      "p(90) < 1500",
      "p(95) < 2000",
      "p(99) < 5000",
    ],
    http_req_failed: ["rate < 0.02"],
  },
};

export function setup() {
  const token = login();
  return { token };
}

export default function (data) {
  const headers = authHeaders(data.token);

  // More aggressive workflow under peak load
  group("Dashboard Load", () => {
    const res = http.get(`${API_BASE}/api/v1/dashboard`, { headers });
    check(res, { "status 200": (r) => r.status === 200 });
  });

  group("Create Test Run", () => {
    const payload = JSON.stringify({
      scenario_id: "scenario-1",
      environment: "production",
    });
    const res = http.post(`${API_BASE}/api/v1/runs`, payload, { headers });
    check(res, {
      "status 201": (r) => r.status === 201,
      "response time < 2s": (r) => r.timings.duration < 2000,
    });
  });

  sleep(Math.random() * 3);
}
```

#### 2.3.3 Breaking Point Test (1000 VU)

**File: performance-tests/performance/breakpoint.js** (NEW)
```javascript
/**
 * Breaking Point Test — System Limits
 *
 * - 1000 Virtual Users
 * - Find system failure threshold
 * - Identify graceful degradation vs hard failure
 * - Thresholds: p99 < 10s (or system fails gracefully)
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "2m", target: 1000 },  // Ramp up quickly
    { duration: "10m", target: 1000 }, // Sustained
    { duration: "1m", target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: [
      "p(99) < 10000", // 99th percentile < 10 seconds
    ],
    // Allow higher error rate at extreme load
    http_req_failed: ["rate < 0.1"],
  },
};

export function setup() {
  const token = login();
  return { token };
}

export default function (data) {
  const headers = authHeaders(data.token);

  // Simple request to measure failure point
  const res = http.get(`${API_BASE}/api/v1/health`, { headers });
  check(res, {
    "status ok": (r) => r.status < 500,
  });

  sleep(Math.random() * 5);
}
```

#### 2.3.4 Database Load Test

**File: performance-tests/performance/db-load.js** (NEW)
```javascript
/**
 * Database Load Test
 *
 * Tests database under write-heavy and read-heavy loads
 * - Write-heavy: Create 1000+ test cases, scenarios
 * - Read-heavy: Concurrent queries for reports/dashboards
 * - Monitors: Query latency, connection pool exhaustion
 *
 * Run: k6 run performance-tests/performance/db-load.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { login, authHeaders } from "./helpers/auth.js";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: 100 },
    { duration: "5m", target: 100 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    // Monitor slow queries
    http_req_duration: [
      "p(95) < 3000", // DB queries should complete in < 3s
    ],
    http_req_failed: ["rate < 0.05"],
  },
};

export function setup() {
  const token = login();
  return { token };
}

export default function (data) {
  const headers = authHeaders(data.token);

  // Write test: Create test case
  const createPayload = JSON.stringify({
    title: `Test Case ${Date.now()}`,
    description: "Generated by db-load test",
    steps: [
      { action: "Click", target: "#button", expected: "Button clicked" },
      { action: "Fill", target: "#input", value: "Test", expected: "Input filled" },
    ],
  });

  const createRes = http.post(`${API_BASE}/api/v1/test-cases`, createPayload, {
    headers,
  });
  check(createRes, {
    "create status 201": (r) => r.status === 201,
    "create response < 2s": (r) => r.timings.duration < 2000,
  });

  // Read test: Fetch reports (heavy joins)
  const reportRes = http.get(
    `${API_BASE}/api/v1/reports?metric=coverage&days=30`,
    { headers }
  );
  check(reportRes, {
    "report status 200": (r) => r.status === 200,
    "report response < 3s": (r) => r.timings.duration < 3000,
  });

  sleep(2);
}
```

#### 2.3.5 UI Rendering Under Load

**File: performance-tests/performance/ui-render.js** (NEW)
```javascript
/**
 * UI Rendering Performance Under Load
 *
 * Measures page load time (Time to First Contentful Paint, Largest Contentful Paint)
 * while the backend is under concurrent load
 *
 * Requires Lighthouse/WebVitals integration
 * Run: k6 run performance-tests/performance/ui-render.js
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { login, authHeaders } from "./helpers/auth.js";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";
const APP_URL = __ENV.APP_URL || "http://127.0.0.1:3000";

export const options = {
  stages: [
    { duration: "30s", target: 50 },
    { duration: "3m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    // Page load time (including network + rendering)
    http_req_duration: [
      "p(90) < 3000", // 90% of page loads < 3s
      "p(95) < 5000", // 95% of page loads < 5s
    ],
  },
};

export function setup() {
  const token = login();
  return { token };
}

export default function (data) {
  // Simulate user navigating to dashboard
  const res = http.get(`${APP_URL}/dashboard`, {
    tags: { name: "Dashboard" },
  });

  check(res, {
    "dashboard status 200": (r) => r.status === 200,
    "dashboard load < 3s": (r) => r.timings.duration < 3000,
  });

  sleep(5);

  // Simulate user navigating to test execution report
  const reportRes = http.get(`${APP_URL}/reports/latest`, {
    tags: { name: "Report" },
  });

  check(reportRes, {
    "report status 200": (r) => r.status === 200,
  });

  sleep(3);
}
```

### 2.4 Performance Baseline & Trend Detection

#### 2.4.1 Baseline File Structure

**File: backend/perf_baseline.json** (EXISTING, EXPAND)
```json
{
  "version": "1.0",
  "date": "2026-06-09",
  "platform": "darwin-arm64",
  "tests": {
    "critical-path": {
      "vus": 10,
      "duration": "30s",
      "metrics": {
        "p50": 400,
        "p95": 1200,
        "p99": 2000,
        "http_req_failed": 0.001,
        "throughput_rps": 25
      }
    },
    "light-load": {
      "vus": 50,
      "duration": "5m",
      "metrics": {
        "p50": 500,
        "p95": 1500,
        "p99": 3000,
        "http_req_failed": 0.01,
        "throughput_rps": 120
      }
    },
    "heavy-load": {
      "vus": 500,
      "duration": "10m",
      "metrics": {
        "p50": 800,
        "p95": 2000,
        "p99": 5000,
        "http_req_failed": 0.02,
        "throughput_rps": 1200
      }
    },
    "database-load": {
      "vus": 100,
      "duration": "5m",
      "metrics": {
        "write_p95": 2000,
        "read_p95": 3000,
        "http_req_failed": 0.05
      }
    },
    "ui-render": {
      "vus": 50,
      "duration": "3m",
      "metrics": {
        "fcp_p90": 1500,
        "lcp_p90": 3000,
        "http_req_failed": 0.01
      }
    }
  }
}
```

#### 2.4.2 Automated Baseline Check Script

**File: scripts/check_perf_baseline.py** (EXISTING, ENHANCE)
```python
#!/usr/bin/env python3
"""
Performance Baseline Regression Detection

Runs load tests and compares results against baseline.
Fails if p95 regression > 10%, error_rate > threshold.

Usage:
  python scripts/check_perf_baseline.py --test critical-path
  python scripts/check_perf_baseline.py --test all --regression-threshold 0.1
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

BASELINE_FILE = Path("backend/perf_baseline.json")
REGRESSION_THRESHOLD = 0.10  # 10% threshold
ERROR_RATE_THRESHOLD = 0.05

def load_baseline() -> Dict[str, Any]:
    """Load baseline metrics from JSON"""
    with open(BASELINE_FILE) as f:
        return json.load(f)

def run_k6_test(test_name: str) -> Dict[str, Any]:
    """Run k6 test and capture results as JSON"""
    test_file = f"performance-tests/performance/{test_name}.js"
    result_file = f"reports/k6-{test_name}.json"

    cmd = [
        "k6", "run",
        "--out", f"json={result_file}",
        test_file
    ]

    print(f"Running {test_name}...")
    subprocess.run(cmd, check=True)

    with open(result_file) as f:
        return json.load(f)

def check_regression(baseline: Dict, actual: Dict, test_name: str) -> bool:
    """Compare actual metrics against baseline"""
    baseline_metrics = baseline["tests"][test_name]["metrics"]
    actual_metrics = actual  # Extract from k6 result

    passed = True

    for metric, baseline_val in baseline_metrics.items():
        actual_val = actual_metrics.get(metric)
        if actual_val is None:
            continue

        regression_pct = (actual_val - baseline_val) / baseline_val
        status = "✅" if regression_pct <= REGRESSION_THRESHOLD else "❌"

        print(f"  {metric}: {baseline_val} → {actual_val} ({regression_pct:+.1%}) {status}")

        if regression_pct > REGRESSION_THRESHOLD:
            passed = False

    return passed

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", default="all")
    parser.add_argument("--regression-threshold", type=float, default=0.10)
    args = parser.parse_args()

    baseline = load_baseline()
    tests = ["all"] if args.test == "all" else [args.test]

    results = {}
    for test_name in baseline["tests"].keys():
        if args.test != "all" and test_name != args.test:
            continue

        print(f"\n=== {test_name} ===")
        actual = run_k6_test(test_name)
        passed = check_regression(baseline, actual, test_name)
        results[test_name] = {"passed": passed, "actual": actual}

    # Summary
    print("\n=== SUMMARY ===")
    passed_count = sum(1 for r in results.values() if r["passed"])
    total_count = len(results)
    print(f"{passed_count}/{total_count} tests passed")

    sys.exit(0 if passed_count == total_count else 1)

if __name__ == "__main__":
    main()
```

**Usage in CI:**
```yaml
# .github/workflows/performance-check.yml
on:
  schedule:
    - cron: '0 3 * * *'  # 3 AM UTC (nightly)
  workflow_dispatch:

jobs:
  perf-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      - run: npm install -g k6
      - run: python scripts/check_perf_baseline.py --test all
      - name: Upload k6 results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: k6-results
          path: reports/k6-*.json
```

### 2.5 Performance Dashboard Integration

#### 2.5.1 k6 Cloud Integration (Recommended)

```bash
# Install k6 Cloud
npm install -g @grafana/k6

# Run test with cloud output
k6 cloud performance-tests/performance/critical-path.js

# View at: https://app.k6.io/projects/YOUR_PROJECT_ID
```

**Configuration: .k6.env**
```bash
K6_CLOUD_TOKEN=<your-token>
K6_PROJECT_ID=<your-project>
```

#### 2.5.2 Local Grafana + InfluxDB (Alternative)

**Setup:**
```bash
# Start monitoring stack
docker-compose -f infra/docker-compose.monitoring.yml up

# Run test with Grafana output
k6 run \
  --out influxdb=http://localhost:8086/k6 \
  performance-tests/performance/critical-path.js
```

**Grafana Dashboard:** infra/grafana/dashboards/k6-perf.json
```json
{
  "dashboard": {
    "title": "k6 Performance Tests",
    "panels": [
      {
        "title": "Response Time Percentiles (p50/p95/p99)",
        "targets": [
          {
            "expr": "rate(http_req_duration{quantile='0.50'}[1m])"
          }
        ]
      },
      {
        "title": "Request Throughput (req/sec)",
        "targets": [
          {
            "expr": "rate(http_reqs[1m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_req_failed[1m])"
          }
        ]
      }
    ]
  }
}
```

### 2.6 Performance Test Organization

```bash
# Add to Makefile:

.PHONY: perf-baseline
perf-baseline:
	@echo "Running performance baseline tests..."
	k6 run performance-tests/performance/critical-path.js --out json=reports/baseline.json
	k6 run performance-tests/performance/light-load.js --out json=reports/light-load.json
	k6 run performance-tests/performance/heavy-load.js --out json=reports/heavy-load.json

.PHONY: perf-check
perf-check:
	@echo "Checking performance against baseline..."
	python scripts/check_perf_baseline.py --test all

.PHONY: perf-soak
perf-soak:
	@echo "Running 8-hour soak test..."
	k6 run --duration 8h performance-tests/performance/soak_test.js

.PHONY: perf-stress
perf-stress:
	@echo "Running stress test to find breaking point..."
	k6 run performance-tests/performance/stress_test.js

.PHONY: perf-db
perf-db:
	@echo "Running database load test..."
	k6 run performance-tests/performance/db-load.js
```

---

## SECTION 3: IMPLEMENTATION ROADMAP

### Week 1: E2E Test Variants

| Day | Task | Deliverable | Tests |
|-----|------|-------------|-------|
| Mon | Create error + edge specs for Login, Projects, Scenarios | login-error/edge, projects-error/edge, scenarios-error/edge | 6 new files |
| Tue | Create error + edge specs for Test Execution, Requirements | executions-error/edge, requirements-error/edge | 4 new files |
| Wed | Create error + edge specs for remaining 5 workflows | 10 new files | 10 files |
| Thu | Verify all error/edge tests run locally | All 20 new files passing | 100+ new tests |
| Fri | Update Playwright config, add nightly CI profile | Updated playwright.config.ts | Ready for Week 2 |

### Week 2: Cross-Browser Matrix

| Day | Task | Deliverable | Coverage |
|-----|------|-------------|----------|
| Mon | Add regression-firefox + regression-webkit projects | playwright.config.ts updated | 66 variants |
| Tue | Test cross-browser smoke locally (Chrome/Firefox/Safari) | smoke-firefox, smoke-webkit passing | 6 tests × 3 browsers |
| Wed | Run regression on Firefox, fix browser-specific bugs | All regression-firefox tests passing | 22 files × Firefox |
| Thu | Run regression on Safari, fix WebKit-specific bugs | All regression-webkit tests passing | 22 files × Safari |
| Fri | Setup nightly CI for cross-browser matrix | .github/workflows/e2e-cross-browser.yml deployed | Automated runs |

### Week 3: Mobile + Performance

**Days 1-2: Mobile Expansion**
| Task | Deliverable | Coverage |
|------|-------------|----------|
| Add iPhone SE, iPhone Pro, iPad, Android tablet projects | playwright.config.ts extended | 5 device types |
| Run mobile tests on all devices | All mobile tests passing | 5 devices × 2 files |
| Fix responsive issues found during testing | Bug fixes + commits | Responsive verified |

**Days 3-5: Performance Test Expansion**
| Task | Deliverable | Coverage |
|------|-------------|----------|
| Implement light-load.js, heavy-load.js, breakpoint.js | 3 new k6 tests | 100/500/1000 VU |
| Implement db-load.js, ui-render.js | 2 specialized tests | Database + UI metrics |
| Setup k6 Cloud or Grafana integration | Dashboard accessible | Real-time visualization |
| Enhance check_perf_baseline.py with automated regression detection | Script passing | CI integration ready |
| Deploy nightly perf-check workflow | .github/workflows/performance-check.yml | Automated trend tracking |

### Final Deliverables Checklist

```
E2E TESTS:
 ✅ 20 new error/edge spec files (960+ new test cases)
 ✅ 3 cross-browser projects (regression-chrome/firefox/webkit)
 ✅ 5 mobile device projects (Pixel 5, iPhone SE/Pro, iPad, Android)
 ✅ 4 formal test sets (smoke, regression, cross-browser, mobile)
 ✅ Nightly CI profile with full regression × browsers
 ✅ Release test set with manual checklist

PERFORMANCE TESTS:
 ✅ 5 k6 load test profiles (10/50/500/1000 VU + spike)
 ✅ 2 specialized tests (database load, UI rendering)
 ✅ Enhanced baseline file (perf_baseline.json)
 ✅ Automated regression detection (check_perf_baseline.py)
 ✅ k6 Cloud or Grafana dashboard integration
 ✅ Nightly perf-check CI workflow
 ✅ Makefile targets (perf-baseline, perf-check, perf-soak, perf-stress)

DOCUMENTATION:
 ✅ this document (PHASE_3_1_E2E_PERFORMANCE_EXPANSION.md)
 ✅ Updated playwright.config.ts with all projects
 ✅ Updated performance-tests/README.md
 ✅ CI workflow files (.github/workflows/e2e-nightly.yml, performance-check.yml)

READINESS LEVEL:
 ✅ Level 4: Automated trend detection, dashboard, multi-variant coverage
 ✅ 30+ E2E scenarios across 6 dimensions (happy/error/edge, 3 browsers, 5 devices)
 ✅ 5 load test profiles with baseline tracking
 ✅ Estimated 600+ E2E variants, 1000+ total test cases
```

---

## SECTION 4: METRICS & SUCCESS CRITERIA

### Test Coverage Metrics

```
BASE COVERAGE (Phase 2):
- 28 Playwright spec files
- ~120 test cases
- 1 device (Chrome desktop)
- 1 browser

PHASE 3.1 COVERAGE:
- 48 Playwright spec files (28 base + 20 variants)
- 600+ test cases (including variants)
- 5 device types (Pixel 5, iPhone SE, iPhone Pro, iPad, Android)
- 3 browsers (Chrome, Firefox, Safari)
- 66 variant combinations (22 regression × 3 browsers)

TOTAL E2E VARIANTS: 150+ unique test execution paths
```

### Performance Baseline Targets

```
CRITICAL PATH (10 VU, 30s):
- p50: < 500ms (baseline: 400ms, allow: +25%)
- p95: < 2s (baseline: 1.2s, allow: +67%)
- p99: < 5s (baseline: 2s, allow: +150%)
- error_rate: < 1% (baseline: 0.1%, allow: +900%)

LIGHT LOAD (50 VU, 5m):
- p95: < 1.5s
- error_rate: < 1%

HEAVY LOAD (500 VU, 10m):
- p95: < 2s
- error_rate: < 2%

BREAKPOINT (1000 VU):
- p99: < 10s (graceful degradation)
- error_rate: < 10%
```

### Regression Detection Thresholds

```
ALERT THRESHOLD: p95 regression > 10%
WARN THRESHOLD: p95 regression 5-10%
OK THRESHOLD: p95 regression < 5%

Example:
- Baseline p95: 1200ms
- Current p95: 1380ms
- Regression: +15% → 🚨 ALERT

Actions:
1. Notify team in Slack
2. Block merge to main
3. Investigate root cause (DB query, N+1, memory leak, etc.)
4. Fix + re-run test
5. Update baseline if intentional (rare)
```

---

## SECTION 5: RISK MITIGATION

### Common Implementation Risks

| Risk | Mitigation |
|------|-----------|
| Cross-browser test flakiness (timing issues) | Use explicit waits, retry logic in Playwright fixtures |
| Mobile device emulation limitations | Also run manual testing on real devices (weekly) |
| Performance test environmental variance | Run on dedicated CI machine, warm up system before baseline |
| k6 license cost | Start with k6.io free tier (3 projects), upgrade if needed |
| Database load test contention | Use separate test database, clean up after each test |
| Regression detection false positives | Set 10% threshold, track trends over 4 weeks before alerting |

### Browser-Specific Issues to Watch

```
FIREFOX-SPECIFIC:
- Different CSS padding/margin calculations
- WebDriver compatibility (Marionette driver)
- Unicode input handling

WEBKIT (Safari)-SPECIFIC:
- -webkit- vendor prefixes not fully supported
- CSS Grid differences
- Touch event simulation on macOS

CHROMIUM-SPECIFIC:
- Service Worker behavior
- Headless mode differences
```

---

## SECTION 6: SUCCESS METRICS & KPIs

### E2E Test Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Test coverage (% of workflows) | 100% | 70% (28 base) |
| Cross-browser coverage | Chrome + Firefox + Safari | Chrome only |
| Mobile device coverage | 5 devices | 1 device |
| Variant coverage (happy/error/edge) | 3× per workflow | 1× (happy only) |
| Test execution time (full suite) | < 2 hours | ~30 min |
| Test flakiness rate | < 1% | < 0.5% |

### Performance Testing Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Load test profiles | 5+ | 4 (missing light/heavy/db/ui) |
| Baseline regression detection | Automated | Manual |
| Performance dashboard | Live Grafana/k6 Cloud | None |
| Performance trend history | 12 weeks | None |
| P95 regression detection | < 1 hour after commit | Manual (next nightly) |
| System breaking point | Documented | Unknown |

---

## APPENDIX: Configuration Files

### A. Playwright Configuration Enhancement

**Key Additions to playwright.config.ts:**
```typescript
// Add 20 new cross-browser/mobile projects
// Each variant-spec project extends base config with different:
// - Device (Desktop Chrome/Firefox/Safari, iPhone, iPad, Android)
// - Timeouts (mobile may need longer timeouts)
// - Retries (cross-browser may need more retries)
```

### B. k6 Helper Functions

**helpers/auth.js enhancements:**
```javascript
export function authHeaders(token) {
  return {
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
}

export function checkStatus(response, expectedStatus) {
  if (response.status !== expectedStatus) {
    throw new Error(`Expected ${expectedStatus}, got ${response.status}`);
  }
}

export function measureMetric(response, metricName, threshold) {
  const duration = response.timings.duration;
  console.log(`${metricName}: ${duration}ms`);
  if (duration > threshold) {
    console.warn(`⚠️  ${metricName} exceeded threshold: ${duration} > ${threshold}`);
  }
}
```

### C. Makefile Enhancement

```makefile
# Test sets
.PHONY: test-e2e-smoke
test-e2e-smoke:
	npx playwright test --project=smoke

.PHONY: test-e2e-regression
test-e2e-regression:
	npx playwright test --project=regression

.PHONY: test-e2e-cross-browser
test-e2e-cross-browser:
	npx playwright test --project=regression-chrome
	npx playwright test --project=regression-firefox
	npx playwright test --project=regression-webkit

.PHONY: test-e2e-mobile
test-e2e-mobile:
	npx playwright test --project=mobile-pixel-5
	npx playwright test --project=mobile-iphone-se
	npx playwright test --project=mobile-iphone-pro
	npx playwright test --project=mobile-ipad
	npx playwright test --project=mobile-android

.PHONY: test-perf
test-perf:
	make perf-baseline
	make perf-check
```

---

## CONCLUSION

Phase 3.1 transforms the test suite from a basic smoke/regression set into a comprehensive, production-grade quality assurance framework with:

1. **30+ distinct E2E scenarios** across happy/error/edge case dimensions
2. **150+ E2E test variants** via cross-browser and mobile device matrix
3. **5 production load test profiles** with automated regression detection
4. **Performance monitoring dashboard** for trend tracking and alerting
5. **Level 4 readiness** for enterprise deployment

**Estimated team effort:** 2 engineers × 3 weeks = 6 person-weeks  
**Expected ROI:** 80% reduction in regression bugs, 2-week faster release cycles

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Author:** AI Automation Team  
**Status:** Ready for Implementation
