# PHASE 3.1 Implementation Checklist

**Project:** Cortex AI Automation (Neurex)  
**Phase:** 3.1 — E2E Expansion + Performance Test  
**Timeline:** 3 weeks  
**Team:** 2 engineers  
**Start Date:** [To be filled]  
**Target Completion:** [To be filled]

---

## WEEK 1: E2E TEST VARIANTS

### Monday: Login, Projects, Scenarios Error/Edge Cases

- [ ] Create `e2e/login-error.spec.ts`
  - [ ] Invalid email format test
  - [ ] Wrong password test
  - [ ] Non-existent user test
  - [ ] Rate limiting test (5 failed attempts)
  - [ ] Test passes locally
  - [ ] Commit with message: `feat(e2e): login error scenarios`

- [ ] Create `e2e/login-edge.spec.ts`
  - [ ] Unicode email test
  - [ ] Very long password test
  - [ ] Session timeout during form fill test
  - [ ] Concurrent login test
  - [ ] Test passes locally
  - [ ] Commit with message: `feat(e2e): login edge cases`

- [ ] Create `e2e/projects-error.spec.ts`
  - [ ] Duplicate project name test
  - [ ] Invalid project name (empty/special chars) test
  - [ ] Permission denied test (non-admin user)
  - [ ] Malformed API payload test
  - [ ] Test passes locally
  - [ ] Commit with message: `feat(e2e): projects error scenarios`

- [ ] Create `e2e/projects-edge.spec.ts`
  - [ ] Project name with unicode test
  - [ ] Max-length project description test
  - [ ] Concurrent project creation test
  - [ ] Delete project with active executions test
  - [ ] Test passes locally
  - [ ] Commit with message: `feat(e2e): projects edge cases`

- [ ] Create `e2e/scenarios-error.spec.ts`
  - [ ] Duplicate scenario name test
  - [ ] Invalid scenario structure test
  - [ ] Permission denied test
  - [ ] Test passes locally
  - [ ] Commit with message: `feat(e2e): scenarios error scenarios`

- [ ] Create `e2e/scenarios-edge.spec.ts`
  - [ ] Empty scenario steps test
  - [ ] Max-length scenario description test
  - [ ] Concurrent scenario edit test
  - [ ] Test passes locally
  - [ ] Commit with message: `feat(e2e): scenarios edge cases`

**Monday Checklist Complete:** 6 new spec files, 24+ new test cases ✅

---

### Tuesday: Test Execution, Requirements Error/Edge Cases

- [ ] Create `e2e/executions-error.spec.ts`
  - [ ] Invalid test case reference test
  - [ ] Execution with unavailable environment test
  - [ ] Permission denied to execute test
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): executions error scenarios`

- [ ] Create `e2e/executions-edge.spec.ts`
  - [ ] Concurrent execution of same test case test
  - [ ] Execution timeout test
  - [ ] Execution with network failure test
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): executions edge cases`

- [ ] Create `e2e/requirements-error.spec.ts`
  - [ ] Invalid requirement reference test
  - [ ] Duplicate requirement ID test
  - [ ] Permission denied test
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): requirements error scenarios`

- [ ] Create `e2e/requirements-edge.spec.ts`
  - [ ] Requirement with max-length description test
  - [ ] Requirement dependency cycle test
  - [ ] Delete requirement with coverage mappings test
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): requirements edge cases`

**Tuesday Checklist Complete:** 4 new spec files, 12+ new test cases ✅

---

### Wednesday: Remaining 5 Workflows (10 new files)

- [ ] Create `e2e/test-data-error.spec.ts` + `test-data-edge.spec.ts`
  - [ ] Invalid test data format
  - [ ] Duplicate test data entry
  - [ ] Max payload size
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): test-data error and edge cases`

- [ ] Create `e2e/integrations-error.spec.ts` + `integrations-edge.spec.ts`
  - [ ] Invalid API key
  - [ ] Integration with unavailable service
  - [ ] Concurrent integration update
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): integrations error and edge cases`

- [ ] Create `e2e/rbac-error.spec.ts` + `rbac-edge.spec.ts`
  - [ ] Privilege escalation attempt
  - [ ] Invalid role assignment
  - [ ] Permission denial scenarios
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): rbac error and edge cases`

- [ ] Create `e2e/ai-workflows-error.spec.ts` + `ai-workflows-edge.spec.ts`
  - [ ] Invalid LLM prompt
  - [ ] LLM service timeout
  - [ ] Invalid AI model selection
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): ai-workflows error and edge cases`

- [ ] Create `e2e/reports-error.spec.ts` + `reports-edge.spec.ts`
  - [ ] Invalid report filter
  - [ ] Report generation timeout
  - [ ] Concurrent report export
  - [ ] Test passes locally
  - [ ] Commit: `feat(e2e): reports error and edge cases`

**Wednesday Checklist Complete:** 10 new spec files, 30+ new test cases ✅

---

### Thursday: Verification & Fixing

- [ ] Run all 20 new spec files locally
  - [ ] `npm run test:e2e 2>&1 | tee week1-results.txt`
  - [ ] Document any failures
  - [ ] Fix flaky tests (add explicit waits, retry logic)

- [ ] Verify test count
  - [ ] Total: ~100+ new test cases across 20 files
  - [ ] All tests passing locally
  - [ ] Screenshot/video evidence of test runs

- [ ] Code review checklist
  - [ ] All new files follow naming convention (kebab-case)
  - [ ] All tests use page object model (pages fixtures)
  - [ ] All tests have descriptive `test.describe()` blocks
  - [ ] No hardcoded wait times (use explicit waits)
  - [ ] No test interdependencies

- [ ] Create PR: "Week 1: E2E test variants (error/edge cases)"
  - [ ] Description includes list of 20 new files
  - [ ] Links to this checklist
  - [ ] CI passes (all tests green)

**Thursday Checklist Complete:** All 20 files verified, PR created ✅

---

### Friday: Playwright Config & CI Setup

- [ ] Update `playwright.config.ts`
  - [ ] Verify all 28 original + 20 new files in regression project
  - [ ] Update testMatch patterns if needed
  - [ ] Local test run: `npx playwright test --project=regression`
  - [ ] All 120+ tests passing

- [ ] Create `.github/workflows/e2e-variant-test.yml`
  - [ ] Trigger on pull_request and schedule (nightly at 2 AM UTC)
  - [ ] Runs all 20 new spec files
  - [ ] Uploads HTML report to artifacts
  - [ ] Test workflow file locally with act (if possible)

- [ ] Update `Makefile`
  - [ ] Add: `make test-e2e-variants`
  - [ ] Add: `make test-e2e-all`

- [ ] Merge PR to feature branch
  - [ ] All CI checks passing
  - [ ] Code review approved

**Friday Checklist Complete:** Config updated, CI ready for Week 2 ✅

---

## WEEK 2: CROSS-BROWSER MATRIX

### Monday: Firefox Regression Project

- [ ] Update `playwright.config.ts`
  - [ ] Add new project: `regression-firefox`
  - [ ] Copy testMatch from regression project
  - [ ] Set device to `devices["Desktop Firefox"]`
  - [ ] Set retries: 2, timeout: 90_000
  - [ ] Set fullyParallel: !process.env.CI

```typescript
// Add to projects array:
{
  name: "regression-firefox",
  testMatch: [
    "regression.spec.ts", "projects.spec.ts", "scenarios.spec.ts",
    // ... (all 22 files)
  ],
  use: { ...devices["Desktop Firefox"] },
  fullyParallel: !process.env.CI,
  retries: 2,
  timeout: 90_000,
},
```

- [ ] Local test run
  - [ ] `npx playwright test --project=regression-firefox`
  - [ ] Document any failures (CSS, event handling)

- [ ] Fix Firefox-specific issues
  - [ ] [ ] CSS padding/margin difference (if any)
  - [ ] [ ] WebDriver compatibility (if any)
  - [ ] [ ] Unicode input handling (if any)
  - [ ] Create bug fixes commit: `fix(e2e): firefox compatibility issues`

- [ ] Verify all tests passing
  - [ ] Run full regression-firefox suite again
  - [ ] All 120+ tests green

**Monday Checklist Complete:** Firefox regression working ✅

---

### Tuesday: Safari (WebKit) Regression Project

- [ ] Update `playwright.config.ts`
  - [ ] Add new project: `regression-webkit`
  - [ ] Copy testMatch from regression project
  - [ ] Set device to `devices["Desktop Safari"]`
  - [ ] Set retries: 2, timeout: 90_000

- [ ] Local test run
  - [ ] `npx playwright test --project=regression-webkit`
  - [ ] Document any failures (CSS Grid, touch events)

- [ ] Fix WebKit-specific issues
  - [ ] [ ] -webkit- vendor prefix handling
  - [ ] [ ] CSS Grid differences
  - [ ] [ ] Touch event simulation
  - [ ] Create bug fixes commit: `fix(e2e): webkit compatibility issues`

- [ ] Verify all tests passing
  - [ ] All 120+ tests green in webkit

**Tuesday Checklist Complete:** Safari regression working ✅

---

### Wednesday: Cross-Browser Smoke Tests

- [ ] Verify existing smoke-firefox and smoke-webkit projects
  - [ ] `npx playwright test --project=smoke-firefox`
  - [ ] `npx playwright test --project=smoke-webkit`
  - [ ] All passing (3 files × 2 browsers = 6 variants)

- [ ] Run all smoke tests across browsers locally
  - [ ] Chrome: `npx playwright test --project=smoke`
  - [ ] Firefox: `npx playwright test --project=smoke-firefox`
  - [ ] WebKit: `npx playwright test --project=smoke-webkit`
  - [ ] Document results

**Wednesday Checklist Complete:** Cross-browser smoke verified ✅

---

### Thursday: CI Workflow Setup

- [ ] Create `.github/workflows/e2e-cross-browser-nightly.yml`

```yaml
name: E2E Cross-Browser Nightly
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
        with:
          node-version: 18
      - run: npm ci
      - run: npm run build:e2e || true
      - run: npx playwright test --project=${{ matrix.project }}
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-report-${{ matrix.project }}
          path: reports/e2e-html/
          retention-days: 30
```

- [ ] Test workflow locally with `act` (or skip if not available)
- [ ] Push to feature branch
- [ ] Verify workflow shows up in GitHub Actions
- [ ] Manually trigger workflow to verify execution

**Thursday Checklist Complete:** Nightly CI active ✅

---

### Friday: PR & Merge Preparation

- [ ] Update `playwright.config.ts` final version
  - [ ] All 3 browser projects configured
  - [ ] All 22 regression files in each project
  - [ ] Documented in comments

- [ ] Update `README.md` (test section)
  - [ ] Add cross-browser test instructions
  - [ ] Add run times for each browser
  - [ ] Add troubleshooting section (browser-specific issues)

- [ ] Create PR: "Week 2: Cross-browser regression matrix (Firefox + Safari)"
  - [ ] Description: Matrix coverage, known issues, CI integration
  - [ ] CI must pass (all 3 browsers × smoke tests)
  - [ ] Code review approved

- [ ] Merge to feature branch

**Friday Checklist Complete:** Cross-browser matrix complete & merged ✅

---

## WEEK 3: MOBILE EXPANSION & PERFORMANCE TESTS

### Monday-Tuesday: Mobile Device Matrix

- [ ] Update `playwright.config.ts` with 5 device projects

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

- [ ] Run mobile tests locally on all devices
  - [ ] `npx playwright test --project=mobile-iphone-se`
  - [ ] `npx playwright test --project=mobile-iphone-pro`
  - [ ] `npx playwright test --project=mobile-ipad`
  - [ ] `npx playwright test --project=mobile-android`
  - [ ] Document failures and fix

- [ ] Fix responsive issues
  - [ ] Layout shifts on small screens
  - [ ] Touch target sizes (min 44×44px)
  - [ ] Viewport-based CSS issues
  - [ ] Create commit: `fix(e2e): mobile responsive compatibility`

- [ ] Verify all mobile tests passing
  - [ ] All 5 devices × 3 files = 15 variants green

**Monday-Tuesday Checklist Complete:** Mobile matrix working ✅

---

### Tuesday-Wednesday: Performance Test Expansion

- [ ] Create `performance-tests/performance/light-load.js`
  - [ ] 50 VU, 5 min steady state
  - [ ] Thresholds: p95 < 1.5s, error < 1%
  - [ ] Test locally: `k6 run performance-tests/performance/light-load.js`

- [ ] Create `performance-tests/performance/heavy-load.js`
  - [ ] 500 VU, 10 min steady state
  - [ ] Thresholds: p95 < 2s, error < 2%
  - [ ] Test locally: `k6 run performance-tests/performance/heavy-load.js`

- [ ] Create `performance-tests/performance/breakpoint.js`
  - [ ] 1000 VU, 10 min sustained
  - [ ] Find system failure point
  - [ ] Test locally: `k6 run performance-tests/performance/breakpoint.js`

- [ ] Create `performance-tests/performance/db-load.js`
  - [ ] Write-heavy + read-heavy workloads
  - [ ] Monitor query latency
  - [ ] Test locally: `k6 run performance-tests/performance/db-load.js`

- [ ] Create `performance-tests/performance/ui-render.js`
  - [ ] Page load time under concurrent load
  - [ ] Measure FCP, LCP
  - [ ] Test locally: `k6 run performance-tests/performance/ui-render.js`

**Wednesday Checklist Complete:** 5 k6 load test files created ✅

---

### Wednesday-Thursday: Performance Baseline & Monitoring

- [ ] Update `backend/perf_baseline.json`
  - [ ] Add entries for all 5 new tests
  - [ ] Document baseline metrics (p50, p95, p99, error_rate)
  - [ ] Include notes on platform (darwin-arm64, ubuntu-latest, etc.)

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
  }
  // ... add for heavy-load, breakpoint, db-load, ui-render
}
```

- [ ] Enhance `scripts/check_perf_baseline.py`
  - [ ] Add support for all 5 new tests
  - [ ] Implement regression detection (threshold: 10%)
  - [ ] Add JSON result parsing from k6 output
  - [ ] Test locally: `python scripts/check_perf_baseline.py --test critical-path`

- [ ] Create `.github/workflows/performance-check.yml`
  - [ ] Nightly schedule (3 AM UTC)
  - [ ] Runs all 5 load tests
  - [ ] Uploads results to artifacts
  - [ ] Posts summary to PR (if on PR branch)

- [ ] Update `Makefile`
  - [ ] Add: `make perf-baseline`
  - [ ] Add: `make perf-check`
  - [ ] Add: `make perf-light`
  - [ ] Add: `make perf-heavy`
  - [ ] Add: `make perf-db`

**Thursday Checklist Complete:** Performance baseline & CI ready ✅

---

### Thursday-Friday: k6 Cloud Integration (Optional but Recommended)

- [ ] Sign up for k6 Cloud (free tier available)
  - [ ] Create account: https://app.k6.io
  - [ ] Generate API token
  - [ ] Save token to `.k6.env` (DO NOT COMMIT)

- [ ] Configure k6 Cloud in project
  - [ ] `npm install -g @grafana/k6` (already installed)
  - [ ] Run one test with cloud output: `k6 cloud performance-tests/performance/critical-path.js`
  - [ ] Verify results appear at https://app.k6.io

- [ ] Setup Grafana dashboard (local alternative)
  - [ ] Optional: Use local Grafana + InfluxDB stack
  - [ ] `docker-compose -f infra/docker-compose.monitoring.yml up`
  - [ ] Configure k6 InfluxDB output
  - [ ] Import dashboard: `infra/grafana/dashboards/k6-perf.json`

**Friday Checklist Complete:** Performance dashboard live ✅

---

### Friday: Final Testing & PR

- [ ] Run full Phase 3.1 verification locally
  - [ ] `make test-e2e-regression` (all 28 base + 20 variants)
  - [ ] `make test-e2e-cross-browser` (3 browsers)
  - [ ] `make test-e2e-mobile` (5 devices)
  - [ ] `make perf-baseline` (run all 5 load tests)
  - [ ] Document results

- [ ] Update documentation
  - [ ] `docs/PHASE_3_1_E2E_PERFORMANCE_EXPANSION.md` (finalize)
  - [ ] `performance-tests/README.md` (update with new tests)
  - [ ] `e2e/README.md` (create if not exists, document all 48 spec files)

- [ ] Create final PR: "Phase 3.1 Complete: Mobile expansion + Performance tests"
  - [ ] Checklist of all deliverables
  - [ ] Links to all new files
  - [ ] Performance baseline results
  - [ ] Mobile variant results

- [ ] Merge to main branch
  - [ ] All CI checks passing
  - [ ] Code review approved

**Friday Checklist Complete:** Phase 3.1 Complete ✅ 🎉

---

## POST-IMPLEMENTATION

### Testing & Validation (1 week)

- [ ] Run nightly CI for 7 days
  - [ ] Monitor e2e-cross-browser-nightly.yml
  - [ ] Monitor performance-check.yml
  - [ ] Document any intermittent failures

- [ ] Fix intermittent failures
  - [ ] Increase timeouts if needed
  - [ ] Add explicit waits
  - [ ] Fix environment setup issues

- [ ] Manual testing (optional but recommended)
  - [ ] Test on real iOS device (iPhone SE, Pro)
  - [ ] Test on real iPad
  - [ ] Test on real Android device

### Documentation & Handoff

- [ ] Create runbook for teams
  - [ ] "How to run E2E tests locally"
  - [ ] "How to debug failing E2E test"
  - [ ] "How to add new E2E test variant"

- [ ] Create performance monitoring guide
  - [ ] "How to read k6 Cloud dashboard"
  - [ ] "How to investigate p95 regression"
  - [ ] "How to update baseline"

- [ ] Schedule knowledge transfer session
  - [ ] 1h for QA team
  - [ ] 1h for DevOps team (CI/CD)
  - [ ] 30min for frontend team

---

## SIGN-OFF

| Role | Name | Date | Status |
|------|------|------|--------|
| **Project Lead** | [ ] | [ ] | [ ] |
| **QA Lead** | [ ] | [ ] | [ ] |
| **DevOps Lead** | [ ] | [ ] | [ ] |
| **Product Owner** | [ ] | [ ] | [ ] |

---

## NOTES & COMMENTS

```
Use this section to track:
- Blockers encountered
- Dependencies
- Changes from original plan
- Lessons learned
```

---

**Document Version:** 1.0  
**Created:** 2026-06-09  
**Last Updated:** 2026-06-09  
**Status:** Ready for Team Assignment
