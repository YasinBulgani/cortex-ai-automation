# PHASE 3.1 Quick Start Guide

**Quick Reference for Team Members**

---

## What Is Phase 3.1?

Expansion of E2E test suite (28 spec files → 48 files) and creation of production-grade load testing framework (k6).

**Target:** 600+ E2E variants, 5 load test profiles, automated performance regression detection

**Timeline:** 3 weeks, 2 engineers

---

## Key Deliverables at a Glance

| Category | Deliverable | Status |
|----------|-------------|--------|
| **E2E Tests** | 20 new error/edge spec files | To implement |
| **Cross-Browser** | regression × Chrome/Firefox/Safari | To implement |
| **Mobile** | 5 device types (5 projects) | To implement |
| **Load Tests** | 5 k6 profiles (10/50/500/1000 VU + spike) | To implement |
| **Performance Dashboard** | k6 Cloud or Grafana integration | To implement |
| **CI Automation** | 2 nightly workflows (E2E + Perf) | To implement |

---

## Week 1: E2E Variants (20 new files)

### Files to Create (10 pairs)

Each workflow gets 2 new variants:
- **-error.spec.ts** — Invalid inputs, rate limits, permission denied
- **-edge.spec.ts** — Boundary conditions, concurrent access, edge cases

```bash
# Login
e2e/login-error.spec.ts   (invalid email, wrong password, rate limit)
e2e/login-edge.spec.ts    (unicode, long password, timeout, concurrent)

# Projects
e2e/projects-error.spec.ts
e2e/projects-edge.spec.ts

# Scenarios
e2e/scenarios-error.spec.ts
e2e/scenarios-edge.spec.ts

# Executions
e2e/executions-error.spec.ts
e2e/executions-edge.spec.ts

# Requirements
e2e/requirements-error.spec.ts
e2e/requirements-edge.spec.ts

# Test Data
e2e/test-data-error.spec.ts
e2e/test-data-edge.spec.ts

# Integrations
e2e/integrations-error.spec.ts
e2e/integrations-edge.spec.ts

# RBAC
e2e/rbac-error.spec.ts
e2e/rbac-edge.spec.ts

# AI Workflows
e2e/ai-workflows-error.spec.ts
e2e/ai-workflows-edge.spec.ts

# Reports
e2e/reports-error.spec.ts
e2e/reports-edge.spec.ts
```

### Template for Each File

```typescript
import { test, expect } from "./fixtures/pages.fixture";

test.describe("Login — Error Cases", () => {
  test("invalid email format should show validation error", async ({ loginPage }) => {
    await loginPage.goto();
    await loginPage.fillEmail("not-an-email");
    await loginPage.submit();
    await expect(loginPage.emailError).toContainText("Valid email required");
  });
  
  // Add 3-4 more tests per file
});
```

### Testing Locally

```bash
# Test all new files
npx playwright test e2e/*-error.spec.ts e2e/*-edge.spec.ts

# Test one file
npx playwright test e2e/login-error.spec.ts

# Update snapshots if needed
npx playwright test --update-snapshots
```

### PR for Week 1

```
Title: Week 1: E2E test variants (error/edge cases)

- 20 new spec files (login, projects, scenarios, executions, requirements, test-data, integrations, rbac, ai-workflows, reports)
- ~100 new test cases covering error paths and edge cases
- All tests passing locally
- Ready for cross-browser matrix in Week 2
```

---

## Week 2: Cross-Browser Matrix

### Update playwright.config.ts

Add to `projects` array:

```typescript
{
  name: "regression-firefox",
  testMatch: [/* all 22 regression files */],
  use: { ...devices["Desktop Firefox"] },
  retries: 2,
  timeout: 90_000,
},
{
  name: "regression-webkit",
  testMatch: [/* all 22 regression files */],
  use: { ...devices["Desktop Safari"] },
  retries: 2,
  timeout: 90_000,
},
```

### Testing Locally

```bash
# Chrome (existing)
npx playwright test --project=regression

# Firefox (new)
npx playwright test --project=regression-firefox

# Safari (new)
npx playwright test --project=regression-webkit
```

### CI Workflow

Create `.github/workflows/e2e-cross-browser-nightly.yml`:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:

jobs:
  e2e-matrix:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: [regression-chrome, regression-firefox, regression-webkit]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright test --project=${{ matrix.project }}
      - uses: actions/upload-artifact@v3
        with:
          name: e2e-report-${{ matrix.project }}
          path: reports/e2e-html/
```

### Expected Results

- **Chrome:** 120+ tests (22 files)
- **Firefox:** 120+ tests (same 22 files)
- **Safari:** 120+ tests (same 22 files)
- **Total:** 360 variants

---

## Week 3 Part A: Mobile Matrix

### Update playwright.config.ts

Add 4 new device projects:

```typescript
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
  name: "mobile-android",
  testMatch: ["mobile.spec.ts", "mobile-responsive.spec.ts", "navigation.spec.ts"],
  use: { ...devices["Galaxy Tab S4"], hasTouch: true },
  retries: 1,
},
```

### Testing Locally

```bash
# All mobile variants
npx playwright test --project=mobile-iphone-se
npx playwright test --project=mobile-iphone-pro
npx playwright test --project=mobile-ipad
npx playwright test --project=mobile-android

# Or run them all at once
npx playwright test --project=mobile-*
```

---

## Week 3 Part B: Performance Tests (k6)

### Files to Create (5 new k6 tests)

```
performance-tests/performance/
  ├── light-load.js        (50 VU, 5 min)
  ├── heavy-load.js        (500 VU, 10 min)
  ├── breakpoint.js        (1000 VU, 10 min)
  ├── db-load.js           (100 VU, database write/read)
  └── ui-render.js         (50 VU, page load time)
```

### Template for Each k6 Test

```javascript
/**
 * Light Load Test
 * - 50 Virtual Users
 * - 5 minute steady state
 * - Thresholds: p95 < 1.5s, error < 1%
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { login, authHeaders } from "./helpers/auth.js";

const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";

export const options = {
  stages: [
    { duration: "30s", target: 50 },
    { duration: "5m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95) < 1500"],
    http_req_failed: ["rate < 0.01"],
  },
};

export function setup() {
  return { token: login() };
}

export default function (data) {
  const headers = authHeaders(data.token);
  // ... test logic
}
```

### Testing k6 Locally

```bash
# Install k6 (if not already installed)
brew install k6

# Run a test
k6 run performance-tests/performance/critical-path.js

# Run with output to JSON
k6 run --out json=reports/critical-path.json performance-tests/performance/critical-path.js

# Run with higher verbosity
k6 run -v performance-tests/performance/critical-path.js
```

### Update Performance Baseline

**File: backend/perf_baseline.json**

Add entries for all 5 new tests:

```json
{
  "light-load": {
    "vus": 50,
    "duration": "5m",
    "metrics": {
      "p50": 500,
      "p95": 1500,
      "p99": 3000,
      "http_req_failed": 0.01
    }
  },
  // ... add for heavy-load, breakpoint, db-load, ui-render
}
```

### Performance Regression Detection

Update `scripts/check_perf_baseline.py`:

```bash
# Check if current metrics exceed baseline (10% threshold)
python scripts/check_perf_baseline.py --test critical-path

# Check all tests
python scripts/check_perf_baseline.py --test all

# Set custom threshold
python scripts/check_perf_baseline.py --test all --regression-threshold 0.15
```

### CI Workflow for Performance

Create `.github/workflows/performance-check.yml`:

```yaml
on:
  schedule:
    - cron: '0 3 * * *'  # 3 AM UTC daily
  workflow_dispatch:

jobs:
  perf-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm install -g k6
      - run: python scripts/check_perf_baseline.py --test all
      - uses: actions/upload-artifact@v3
        with:
          name: k6-results
          path: reports/k6-*.json
```

---

## Makefile Commands (Add These)

```bash
# E2E Test Sets
make test-e2e-smoke          # 5 critical tests, ~2 min
make test-e2e-regression     # 120+ tests, ~15 min
make test-e2e-cross-browser  # 360 tests (3 browsers), ~45 min
make test-e2e-mobile         # 15 tests (5 devices), ~10 min
make test-e2e-all            # Everything, ~2 hours

# Performance
make perf-baseline           # Run all 5 k6 tests
make perf-check              # Check against baseline
make perf-light              # 50 VU test
make perf-heavy              # 500 VU test
make perf-db                 # Database load test
```

Add to `Makefile`:

```makefile
.PHONY: test-e2e-regression
test-e2e-regression:
	npx playwright test --project=regression

.PHONY: test-e2e-cross-browser
test-e2e-cross-browser:
	npx playwright test --project=regression-chrome
	npx playwright test --project=regression-firefox
	npx playwright test --project=regression-webkit

.PHONY: perf-baseline
perf-baseline:
	k6 run performance-tests/performance/critical-path.js
	k6 run performance-tests/performance/light-load.js
	k6 run performance-tests/performance/heavy-load.js
	k6 run performance-tests/performance/db-load.js
	k6 run performance-tests/performance/ui-render.js

.PHONY: perf-check
perf-check:
	python scripts/check_perf_baseline.py --test all
```

---

## Common Issues & Fixes

### E2E Tests Flaking

**Problem:** Tests pass locally but fail in CI

**Solution:**
```typescript
// Add explicit waits instead of arbitrary sleep
await page.waitForLoadState('networkidle');
await page.waitForSelector('.my-element');
await expect(element).toBeVisible({ timeout: 10000 });
```

### Cross-Browser Failures

**Firefox-specific:**
- CSS padding/margin differs
- WebDriver event handling differs
- Solution: Add browser-specific CSS overrides, use platform detection

**Safari-specific:**
- -webkit- prefixes needed
- Touch events behave differently
- Solution: Playwright handles most transparently; test on real Safari if critical

### k6 Authentication Errors

**Problem:** k6 tests fail with 401 Unauthorized

**Solution:** Ensure `helpers/auth.js` properly handles token generation

```javascript
export function login() {
  const loginRes = http.post(`${BASE}/auth/login`, {
    email: "admin@example.com",
    password: "admin123",
  });
  
  if (loginRes.status !== 200) {
    throw new Error(`Login failed: ${loginRes.body}`);
  }
  
  const body = JSON.parse(loginRes.body);
  return body.token;
}
```

### Performance Baseline Regression

**Problem:** Tests fail with "p95 regression > 10%"

**Investigation:**
1. Check if backend service is under load
2. Check database connection pool
3. Compare k6 results with baseline file
4. If intentional, update baseline and document reason

```bash
# Compare two results
diff reports/baseline.json reports/current.json
```

---

## Testing Checklist Before Merging

### E2E Variant PRs (Week 1)

- [ ] All 20 new files created
- [ ] Each file has 4+ test cases
- [ ] All tests pass locally: `npm run test:e2e`
- [ ] No hardcoded waits (use explicit waits)
- [ ] Tests use page object fixtures
- [ ] No test interdependencies
- [ ] PR description lists all 20 files
- [ ] CI passes

### Cross-Browser PRs (Week 2)

- [ ] `regression-firefox` project added to config
- [ ] `regression-webkit` project added to config
- [ ] All 22 regression files run on Firefox
- [ ] All 22 regression files run on Safari
- [ ] Browser-specific bugs fixed
- [ ] CI workflow file created
- [ ] CI passes

### Mobile + Performance PRs (Week 3)

- [ ] 4 new mobile device projects added
- [ ] 5 new k6 load tests created
- [ ] Baseline file updated with all new test metrics
- [ ] Regression detection script tested locally
- [ ] CI workflows created and triggered once
- [ ] All tests passing

---

## Documentation to Update

- [ ] `docs/PHASE_3_1_E2E_PERFORMANCE_EXPANSION.md` (done)
- [ ] `docs/PHASE_3_1_IMPLEMENTATION_CHECKLIST.md` (done)
- [ ] `performance-tests/README.md` (add new tests)
- [ ] `e2e/README.md` or `README.md` (document all 48 spec files)
- [ ] `Makefile` (add test commands)

---

## Success Metrics

**After Week 1:** 28 base + 20 new = 48 spec files, ~250 E2E tests

**After Week 2:** 48 files × 3 browsers (smoke) = 60+ variants

**After Week 3:** 
- 60+ E2E variants (cross-browser smoke)
- 360 regression variants (22 files × 3 browsers)
- 15 mobile variants (3 files × 5 devices)
- **Total: 435+ E2E test variants**
- 5 k6 load test profiles with automated regression detection

**Level 4 Readiness:** ✅ Automated testing, trend detection, comprehensive coverage

---

## Links & Resources

- **Main Spec:** docs/PHASE_3_1_E2E_PERFORMANCE_EXPANSION.md
- **Implementation Checklist:** docs/PHASE_3_1_IMPLEMENTATION_CHECKLIST.md
- **Playwright Docs:** https://playwright.dev
- **k6 Docs:** https://k6.io/docs
- **k6 Cloud:** https://app.k6.io
- **Current Config:** playwright.config.ts
- **Baseline File:** backend/perf_baseline.json

---

**Version:** 1.0  
**Created:** 2026-06-09  
**For:** Team Implementation
