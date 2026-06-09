# Phase 2.2: E2E Critical Paths — Implementation Guide

**Status:** Phase 2.2 Implementation Plan & Foundation Complete  
**Date:** 2026-06-09  
**Last Updated:** 2026-06-09

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Page Objects](#page-objects)
4. [Fixtures](#fixtures)
5. [Running Tests](#running-tests)
6. [Writing Tests](#writing-tests)
7. [Patterns & Best Practices](#patterns--best-practices)
8. [Implementation Status](#implementation-status)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Phase 2.2 implements end-to-end tests for 5 critical user workflows in Neurex:

### Scenarios

1. **Admin Workflow** (`admin-workflow.spec.ts`)
   - Login → Create Project → Create Test Case → Run → Export
   - Tests admin permissions, form validation, async polling, export

2. **Tester Workflow** (`tester-workflow.spec.ts`)
   - Login → View My Work → Run Test → Create Defect → Comment
   - Tests RBAC (limited permissions), defect creation, collaboration

3. **Manager Workflow** (`manager-workflow.spec.ts`)
   - Login → Dashboard → View Metrics → Export Report → Share Link
   - Tests analytics, reporting, read-only permissions

4. **Integration Workflow** (`integration-workflow.spec.ts`)
   - Create Test Case → Link Jira → Run → Sync Status → Verify Bidirectional
   - Tests Jira API integration, webhook simulation, status sync

5. **Settings Workflow** (`settings-workflow.spec.ts`)
   - Login → Profile → Password → Notifications → API Keys → Team
   - Tests user settings, security features, team management

### Key Features

- ✅ **Async Polling:** Test execution with timeout protection (2s poll interval, 60s timeout)
- ✅ **RBAC Verification:** Permission checks for each role
- ✅ **Error Recovery:** Form validation, network retries, error clearing
- ✅ **Multi-Role:** Admin, Tester, Manager, Developer sessions
- ✅ **Mobile Testing:** Viewport tests (iPhone 12, Pixel 5)
- ✅ **Flakiness Prevention:** Explicit waits, network idle, element availability

---

## Architecture

### File Structure

```
apps/web/e2e/
├── README_PHASE_2_2.md          ← This file
├── playwright.config.ts          ← Playwright configuration
├── auth.spec.ts                  ← Auth tests (existing)
├── admin-workflow.spec.ts        ← Admin workflow (NEW)
├── tester-workflow.spec.ts       ← Tester workflow (TODO)
├── manager-workflow.spec.ts      ← Manager workflow (TODO)
├── integration-workflow.spec.ts  ← Integration workflow (TODO)
├── settings-workflow.spec.ts     ← Settings workflow (TODO)
├── pages/
│   ├── BasePage.ts              ← Base class (existing)
│   ├── LoginPage.ts             ← Login page (existing)
│   ├── DashboardPage.ts         ← Dashboard page (existing)
│   ├── ProjectPage.ts           ← Projects management (NEW)
│   ├── TestCasePage.ts          ← Test cases management (NEW)
│   ├── RunPage.ts               ← Test execution & results (NEW)
│   ├── DefectPage.ts            ← Defect management (NEW)
│   └── SettingsPage.ts          ← User settings (NEW)
├── fixtures/
│   ├── auth.fixtures.ts         ← Auth fixtures (existing)
│   └── workflow.fixtures.ts     ← Workflow fixtures (NEW)
├── helpers/
│   ├── (to be created)
│   └── ...
└── playwright-report/           ← Test reports (auto-generated)
```

### Page Object Hierarchy

```
BasePage
  ├─ LoginPage          ✅ Auth & session
  ├─ DashboardPage      ✅ Dashboard metrics
  ├─ ProjectPage        📄 NEW: CRUD operations
  ├─ TestCasePage       📄 NEW: Create, list, run
  ├─ RunPage            📄 NEW: Polling, results, export
  ├─ DefectPage         📄 NEW: Defect management
  └─ SettingsPage       📄 NEW: Profile, security, team
```

### Fixture Hierarchy

```
Playwright BaseTest
  └─ workflow.fixtures.ts
      ├─ Page Objects (loginPage, projectPage, ...)
      ├─ Sessions (adminSession, testerSession, ...)
      ├─ API Client (for seeding)
      └─ Seeded Data (project, test case, etc.)
```

---

## Page Objects

### BasePage (Existing)

Base class with utility methods:

```typescript
// Navigation
async goto(path: string)
async waitForPageReady()

// Interaction
async click(selector: string)
async fillInput(selector: string, value: string)
async getText(selector: string): Promise<string>
async isVisible(selector: string): Promise<boolean>

// Wait helpers
async waitFor(selector: string, timeout?: number)
```

### ProjectPage (NEW)

Project CRUD operations:

```typescript
// Navigation & state
async goto()
async isLoaded(): Promise<boolean>

// CRUD
async createProject(name, description, template?, access?)
async openProject(name)
async editProject(name, updates)
async deleteProject(name)

// Query
async getProjectByName(name)
async getProjectList(): Promise<string[]>
async projectExists(name): Promise<boolean>

// Errors
async getFormError(): Promise<string>
```

**Selectors:**
- `[data-testid="new-project-btn"]` — Create button
- `[data-testid="project-item"]` — List item
- `[data-testid="project-form-name"]` — Name input

### TestCasePage (NEW)

Test case management:

```typescript
// CRUD
async createTestCase(input: CreateTestCaseInput)
async openTestCase(title)
async editTestCase(title, updates)
async deleteTestCase(title)

// Execution
async runTestCase()

// Query
async getTestCaseByTitle(title)
async getTestCaseList(): Promise<string[]>
async testCaseExists(title): Promise<boolean>

// Details
async getDetailTitle(): Promise<string>
async getDetailDescription(): Promise<string>
```

**Key interface:**

```typescript
interface CreateTestCaseInput {
  title: string;
  description: string;
  steps: TestStep[];
  tags?: string[];
  assignee?: string;
  priority?: "low" | "medium" | "high" | "critical";
}

interface TestStep {
  action: "click" | "fill" | "wait" | "verify" | "screenshot";
  selector?: string;
  value?: string;
  expected?: string;
  timeout?: number;
}
```

### RunPage (NEW)

**Critical pattern: Async Polling**

```typescript
// Execution
async runTestCase()
async pollRunCompletion(timeout = 60000, pollInterval = 2000)
  → Returns: "passed" | "failed" | "timeout" | "skipped"

// Status checking
async getRunStatus(): Promise<string>
async getRunDuration(): Promise<number>
async waitForStatus(expectedStatus, timeout?)

// Results
async getResultDetail(): Promise<RunResult>
async clickResultTab("overview" | "logs" | "attachments" | "metrics")
async getLogsText(): Promise<string>

// Export & Share
async exportResult("pdf" | "csv" | "json")
async shareResult(): Promise<string>

// Actions
async retryRun()
async stopRun()
async reportDefect()
```

**Polling Pattern:**

```typescript
// Instead of: await page.waitForTimeout(60000);
// Use polling with timeout:
const status = await runPage.pollRunCompletion(60000);
// Checks every 2s for: passed, failed, skipped, or timeout after 60s
```

### DefectPage (NEW)

Defect management:

```typescript
// CRUD
async createDefect(input: CreateDefectInput)
async openDefect(title)
async editDefect(title, updates)
async deleteDefect(title)

// Management
async updateStatus(newStatus)
async assignToUser(email)
async assignToMe()
async updateSeverity(severity)

// Comments
async addComment(text)
async getComments(): Promise<string[]>

// Query
async getDefectByTitle(title)
async getDefectList(): Promise<string[]>
async defectExists(title): Promise<boolean>

// Filters
async searchDefects(query)
async filterByStatus(status)
async filterBySeverity(severity)
```

### SettingsPage (NEW)

User settings across 5 sections:

```typescript
// Profile
async updateProfile(data: { name?, timezone?, language? })
async uploadAvatar(filePath)
async switchToProfile()

// Password
async changePassword(current, new, confirm)
async switchToProfile() // Same section

// Notifications
async toggleEmailNotifications()
async toggleDailyDigest()
async setNotificationFrequency("immediate" | "daily" | "weekly")
async connectSlack()
async disconnectSlack()

// API Keys
async generateApiKey(name): Promise<string>
async getApiKeyList(): Promise<string[]>
async revokeApiKey(name)

// Team
async inviteTeamMember(email, role, projects?)
async getTeamMembers(): Promise<string[]>
async getPendingInvites(): Promise<string[]>
async removeTeamMember(email)
async revokePendingInvite(email)

// Integrations
async connectJira()
async disconnectJira()
```

---

## Fixtures

### workflow.fixtures.ts (NEW)

Extended fixtures for critical path tests.

#### Page Objects

```typescript
test("example", async ({ loginPage, projectPage, testCasePage, runPage, defectPage, settingsPage }) => {
  // All page objects available automatically
});
```

#### Authenticated Sessions

**Admin Session:**
```typescript
test("admin only", async ({ adminSession, projectPage, page }) => {
  // Already logged in as admin@example.com
  // Can create projects, view team, etc.
  await projectPage.goto();
});
```

**Tester Session:**
```typescript
test("tester workflow", async ({ testerSession, page }) => {
  // Logged in as tester@example.com
  // Limited permissions: can see assigned work only
});
```

**Manager Session:**
```typescript
test("manager reports", async ({ managerSession, dashboardPage }) => {
  // Logged in as manager@example.com
  // Can view analytics, export reports
});
```

**Developer Session:**
```typescript
test("developer fixes", async ({ developerSession, defectPage }) => {
  // Logged in as developer@example.com
  // Can see assigned defects
});
```

#### Seeded Test Data

```typescript
test("run seeded test", async ({ adminSession, runPage, seedTestData }) => {
  const { projectId, projectName, testCaseId, testCaseName } = seedTestData;

  // Data already created via API (fast)
  // Just test the UI/workflow
  await runPage.gotoProject(projectId);
  const status = await runPage.pollRunCompletion(60000);
});
```

**How seeding works:**
1. Fixture creates project via API
2. Fixture creates test case via API
3. Test uses seeded data
4. Fixture cleans up after test (deletes project)

---

## Running Tests

### Setup

```bash
# Install dependencies
cd apps/web
npm install

# Ensure backend is running
docker-compose up -d

# Run migrations
cd ../..
make migrate
```

### Run All Tests

```bash
cd apps/web
npm run test:e2e
```

### Run Specific Test File

```bash
# Admin workflow only
npm run test:e2e -- admin-workflow.spec.ts

# Multiple files
npm run test:e2e -- auth.spec.ts admin-workflow.spec.ts
```

### Run Specific Test

```bash
npm run test:e2e -- --grep "should login as admin"
```

### Run with UI Mode

```bash
npm run test:e2e:ui
```

### Run in Headed Mode (See Browser)

```bash
npm run test:e2e:headed
```

### Debug Mode

```bash
npm run test:e2e:debug
```

### Run on Specific Browser

```bash
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
```

### Run Mobile Tests Only

```bash
npm run test:e2e -- --project="Mobile Chrome"
npm run test:e2e -- --project="Mobile Safari"
```

### View HTML Report

```bash
npx playwright show-report
```

---

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from "./fixtures/workflow.fixtures";

test.describe("Feature Name", () => {
  test("should do something", async ({ projectPage }) => {
    // Arrange
    await projectPage.goto();

    // Act
    await projectPage.createProject("Test", "Description");

    // Assert
    const exists = await projectPage.projectExists("Test");
    expect(exists).toBe(true);
  });
});
```

### Multi-Step Workflow

```typescript
test("complete workflow", async ({
  adminSession,
  projectPage,
  testCasePage,
  runPage,
}) => {
  // Step 1: Create project
  await projectPage.goto();
  await projectPage.createProject("E2E Test", "Description");
  await projectPage.openProject("E2E Test");

  // Step 2: Create test case
  await testCasePage.createTestCase({
    title: "Login Test",
    description: "Test login flow",
    steps: [
      { action: "click", selector: "button.login" },
      { action: "fill", selector: "input.email", value: "test@test.com" },
    ],
  });

  // Step 3: Run test
  const testCase = await testCasePage.getTestCaseByTitle("Login Test");
  await testCasePage.openTestCase("Login Test");
  await testCasePage.runTestCase();

  // Step 4: Wait for completion
  const status = await runPage.pollRunCompletion(60000);
  expect(status).not.toBe("timeout");

  // Step 5: Verify result
  const result = await runPage.getResultDetail();
  expect(["passed", "failed"]).toContain(result.status);
});
```

### RBAC Test

```typescript
test("tester cannot create project", async ({ testerSession, page }) => {
  await page.goto("/projects");

  const newProjectBtn = page.locator('[data-testid="new-project-btn"]');
  expect(await newProjectBtn.isVisible()).toBe(false);
});
```

### Error Recovery Test

```typescript
test("should handle form validation", async ({ projectPage }) => {
  await projectPage.goto();
  await projectPage.page.click('[data-testid="new-project-btn"]');
  await projectPage.waitFor(projectPage.projectModal);

  // Submit empty form
  await projectPage.click(projectPage.saveProjectBtn);

  // Should show error
  const error = await projectPage.getFormError();
  expect(error.length > 0).toBe(true);

  // Fix error
  await projectPage.fillInput(projectPage.projectNameInput, "Test Project");
  await projectPage.click(projectPage.saveProjectBtn);

  // Should succeed
  await projectPage.page.waitForSelector(projectPage.projectModal, {
    state: "hidden",
  });
});
```

### Async Polling Test

```typescript
test("should handle long-running test", async ({ runPage, seedTestData }) => {
  // Run test (takes time)
  const { projectId, testCaseId } = seedTestData;
  // ... trigger run ...

  // Poll for completion with timeout
  const startTime = Date.now();
  const status = await runPage.pollRunCompletion(
    60000, // 60 second timeout
    2000   // 2 second poll interval
  );

  const elapsed = Date.now() - startTime;

  expect(status).toBeTruthy();
  expect(elapsed < 60000).toBe(true);
});
```

---

## Patterns & Best Practices

### ✅ DO: Explicit Waits

```typescript
// Wait for element to be visible
await runPage.waitFor('[data-testid="run-status"]', 10000);

// Wait for element state
await page.waitForSelector(selector, { state: "hidden" });

// Wait for navigation
await page.waitForURL(/dashboard/, { timeout: 10000 });
```

### ❌ DON'T: Implicit Sleeps

```typescript
// Bad
await page.waitForTimeout(5000);

// Good
await runPage.waitForPageReady();
```

### ✅ DO: Polling with Timeout

```typescript
// Good: Timeout protection
const status = await runPage.pollRunCompletion(60000);

// Bad: Infinite loop risk
while (true) {
  if (await getStatus() === "done") break;
}
```

### ✅ DO: Use Fixtures for Setup

```typescript
// Good: Automatic login + page object
test("admin test", async ({ adminSession, projectPage }) => {
  await projectPage.goto();
});

// Bad: Manual login in every test
test("admin test", async ({ page, loginPage }) => {
  await loginPage.goto();
  await loginPage.login("admin@example.com", "admin123");
});
```

### ✅ DO: Use Seeding for Test Data

```typescript
// Good: Fast API-based creation
test("test with data", async ({ seedTestData }) => {
  const { projectId } = seedTestData;
  // Use existing data
});

// Bad: Create via UI (slow)
test("test with data", async ({ projectPage }) => {
  await projectPage.createProject("Test"); // Takes 5-10 seconds
});
```

### ✅ DO: Separate Concerns

```typescript
// Good: One thing per test
test("should create project", async ({ projectPage }) => {
  await projectPage.goto();
  await projectPage.createProject("Test", "Desc");
  expect(await projectPage.projectExists("Test")).toBe(true);
});

test("should edit project", async ({ projectPage }) => {
  await projectPage.goto();
  // Create, then edit (separate concerns)
});
```

### ✅ DO: Use Data-Testid Selectors

```typescript
// Good: Stable, explicit
const btn = page.locator('[data-testid="save-btn"]');

// Bad: Fragile, CSS dependent
const btn = page.locator('button.btn.btn-primary');
```

### ✅ DO: Handle Optional Elements

```typescript
// Good: Check existence first
const deleteBtn = page.locator('[data-testid="delete-btn"]');
if (await deleteBtn.count() > 0) {
  await deleteBtn.click();
}

// Bad: Assumes element exists
const deleteBtn = page.locator('[data-testid="delete-btn"]');
await deleteBtn.click(); // Fails if not found
```

---

## Implementation Status

### Phase 2.2 Deliverables

| Item | Status | File(s) |
|------|--------|---------|
| **Plan Document** | ✅ Complete | `PHASE_2_2_E2E_CRITICAL_PATHS.md` |
| **Page Objects** | | |
| — ProjectPage | ✅ Complete | `pages/ProjectPage.ts` |
| — TestCasePage | ✅ Complete | `pages/TestCasePage.ts` |
| — RunPage | ✅ Complete | `pages/RunPage.ts` |
| — DefectPage | ✅ Complete | `pages/DefectPage.ts` |
| — SettingsPage | ✅ Complete | `pages/SettingsPage.ts` |
| **Fixtures** | | |
| — workflow.fixtures.ts | ✅ Complete | `fixtures/workflow.fixtures.ts` |
| **Test Specs** | | |
| — admin-workflow.spec.ts | ✅ Foundation | `admin-workflow.spec.ts` (19 tests) |
| — tester-workflow.spec.ts | ⏳ TODO | (target: 10 tests) |
| — manager-workflow.spec.ts | ⏳ TODO | (target: 8 tests) |
| — integration-workflow.spec.ts | ⏳ TODO | (target: 9 tests) |
| — settings-workflow.spec.ts | ⏳ TODO | (target: 9 tests) |
| **Documentation** | | |
| — README_PHASE_2_2.md | ✅ Complete | This file |
| — Inline code comments | ✅ Complete | All .ts files |

### Test Coverage Target

| Scenario | Tests | Status |
|----------|-------|--------|
| Admin (Project → Test → Run → Export) | 19 | ✅ Foundation |
| Tester (Work → Run → Defect → Comment) | 10 | ⏳ TODO |
| Manager (Dashboard → Metrics → Export) | 8 | ⏳ TODO |
| Integration (Test → Jira → Sync) | 9 | ⏳ TODO |
| Settings (Profile → Password → Team) | 9 | ⏳ TODO |
| **Total** | **55** | **Foundation ready** |

### Timeline

- **Week 1 (Days 1-5):** Page Objects + Admin workflow ✅ DONE
- **Week 2 (Days 6-10):** Tester + Manager + Integration + Settings ⏳ IN PROGRESS

---

## Troubleshooting

### Test Timeouts

**Problem:** Test hangs waiting for element

```
Error: Timeout waiting for selector [data-testid="run-status"]
```

**Solution:**
```typescript
// 1. Check selector exists
await page.isVisible('[data-testid="run-status"]');

// 2. Increase timeout
await runPage.waitFor('[data-testid="run-status"]', 20000);

// 3. Add debug logging
console.log("Current URL:", page.url());
console.log("Page content:", await page.content());
```

### Flaky Tests

**Problem:** Test passes sometimes, fails sometimes

**Common causes:**
1. Insufficient wait time
2. Race conditions
3. Element visibility timing

**Solution:**
```typescript
// Wait for element to be fully visible and interactive
await page.waitForSelector(selector, { timeout: 10000 });
await page.locator(selector).click(); // Will wait for clickability

// Better: Use page object methods with built-in waits
await projectPage.click(projectPage.saveBtn); // Built-in wait
```

### Authentication Failures

**Problem:** `testerSession` fails with "Failed to authenticate as tester"

**Debug:**
```typescript
test.only("debug auth", async ({ page, loginPage }) => {
  await loginPage.goto();
  console.log("URL:", page.url());
  expect(page.url()).toContain("/login");

  await loginPage.login("tester@example.com", "testerpass");
  console.log("After login URL:", page.url());

  const emailInput = page.locator('[data-testid="login-input-email"]');
  console.log("Email field visible:", await emailInput.isVisible());
});
```

**Check:**
- Test user accounts exist in dev environment
- Passwords are correct
- Backend API is running

### Polling Never Completes

**Problem:** `pollRunCompletion` times out at 60s

**Solution:**
```typescript
// 1. Check run actually started
const isRunning = await runPage.isRunning();
console.log("Run status:", isRunning);

// 2. Check backend logs
docker logs neurex_backend

// 3. Reduce timeout for debugging
const status = await runPage.pollRunCompletion(10000); // 10s instead of 60s
```

### Element Not Found

**Problem:** `[data-testid="foo"]` not found

**Debug:**
```typescript
// 1. Check page navigation
console.log("Current URL:", page.url());

// 2. Get all matching elements
const elements = await page.locator('[data-testid^="project"]').count();
console.log("Found project elements:", elements);

// 3. Take screenshot
await page.screenshot({ path: 'debug.png' });

// 4. Print page HTML
console.log(await page.content());
```

### Form Submission Hangs

**Problem:** Form submit button doesn't trigger action

**Solution:**
```typescript
// Method 1: Check button is enabled
const saveBtn = page.locator('[data-testid="save-btn"]');
console.log("Button disabled:", await saveBtn.isDisabled());

// Method 2: Try filling all fields
await projectPage.fillInput(projectPage.projectNameInput, "Test");
await projectPage.fillInput(projectPage.projectDescInput, "Desc");

// Method 3: Use keyboard submit
await page.keyboard.press("Enter");

// Method 4: Check for validation errors
const error = await projectPage.getFormError();
console.log("Form error:", error);
```

---

## References

- **Playwright Docs:** https://playwright.dev
- **Playwright Best Practices:** https://playwright.dev/docs/best-practices
- **Page Object Model:** https://playwright.dev/docs/pom
- **Debugging:** https://playwright.dev/docs/debugging
- **CI/CD:** https://playwright.dev/docs/ci
- **Project Plan:** `/docs/PHASE_2_2_E2E_CRITICAL_PATHS.md`

---

## Contributing

### Adding a New Test

1. Choose the appropriate spec file (admin, tester, manager, integration, settings)
2. Add test to `test.describe()` block
3. Use page objects from fixtures
4. Follow naming: `should [action]`
5. Add comments for clarity
6. Run locally: `npm run test:e2e -- myfile.spec.ts`
7. Verify passes on CI

### Adding a New Page Object

1. Create `pages/NewPage.ts`
2. Extend `BasePage`
3. Add all selectors as `readonly` properties
4. Implement methods for user interactions
5. Type all return values
6. Add JSDoc comments
7. Add to fixtures: `export const test = baseTest.extend<{ newPage: NewPage }>`
8. Export from index (if exists)

### Debugging Tips

- Use `test.only()` to run single test
- Use `page.waitForTimeout(5000)` to pause execution
- Use `await page.screenshot()` to capture state
- Use `await page.pause()` to open debugger
- Check Playwright Inspector: `PWDEBUG=1 npm run test:e2e`

---

**Last Updated:** 2026-06-09  
**Next Review:** After completing all 5 workflows  
**Owners:** QA Team (Phase 2.2)
