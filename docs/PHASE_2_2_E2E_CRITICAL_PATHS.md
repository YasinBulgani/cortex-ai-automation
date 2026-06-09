# Phase 2.2: UI E2E Critical Paths — Implementation Plan

**Status:** Draft  
**Date:** 2026-06-09  
**Project:** Neurex (Cortex AI Automation)  
**Scope:** 5 critical user workflows (login → run → results)  
**Timeline:** 2 weeks (3 engineers)  
**Output:** 5 .spec.ts files, Page Object expansion, 0 flakiness

---

## Executive Summary

Phase 2.2 builds end-to-end test coverage for 5 critical user workflows in Neurex. Foundation already exists (Playwright, auth fixtures, LoginPage/DashboardPage POMs, 28 E2E specs). This phase adds:

- **5 workflow scenarios** (admin create project → test case → run → defect → settings)
- **Page Object expansion** (TestCasePage, ProjectPage, RunPage, DefectPage, SettingsPage)
- **Multi-role RBAC verification** (admin, tester, manager, developer)
- **Async operation polling** (test run wait, export polling)
- **Error recovery** (retry on failure, clear errors, form reset)
- **Integration points** (Jira link, API proxy verification)

**Current State:**
- ✅ auth.spec.ts complete (31 test cases, all passing)
- ✅ Playwright config (chromium, firefox, webkit, mobile viewports)
- ✅ Fixture setup (auth, dashboard, custom fixtures)
- ✅ BasePage abstraction (click, fillInput, getText, waitFor, etc.)
- 🔴 ProjectPage, TestCasePage, RunPage, DefectPage, SettingsPage — **NOT YET**
- 🔴 Integration workflows — **NOT YET**
- 🔴 RBAC edge cases (permission denied, scope isolation) — **PARTIAL**

---

## Scenario Breakdown

### 1. Admin Complete Workflow (admin-workflow.spec.ts)

**Role:** Admin (all permissions)  
**Path:** login → projects → create project → test cases → create test case → run → view results → export report

**Test Cases (8-10):**

```
✅ Step 1: Login
  - admin@example.com / admin123
  - Redirect to /dashboard or /projects

✅ Step 2: Create Project
  - Navigate to projects
  - Click "New Project"
  - Fill form: name, description, template
  - Submit
  - Verify project in list

✅ Step 3: Create Test Case
  - Enter project
  - Navigate to Test Cases
  - Click "New Test Case"
  - Fill multi-step form:
    - Title: "Admin Test Case"
    - Description: "Multi-step test"
    - Steps: 3 steps (click, verify, wait)
  - Assign tags
  - Submit
  - Verify in list

✅ Step 4: Run Test
  - Select test case
  - Click "Run"
  - Wait for execution (polling)
  - Verify status transitions: pending → running → passed/failed
  - Check execution time, logs

✅ Step 5: View Result & Export
  - Click result detail
  - Verify all tabs: overview, logs, attachments, metrics
  - Click "Export Report"
  - Verify PDF download

⚠️ Error Recovery:
  - Form validation errors
  - Network timeout during run
  - Retry button functionality
```

**Page Objects Needed:**
- `ProjectPage` (list, create, delete, edit)
- `TestCasePage` (list, create, edit, delete, run)
- `RunPage` (status polling, result view, export)

---

### 2. Tester Workflow (tester-workflow.spec.ts)

**Role:** Tester (limited permissions)  
**Path:** login → assigned work → create defect → comment → assign to developer

**Test Cases (8-10):**

```
✅ Step 1: Login as Tester
  - tester@example.com / testerpass
  - Verify RBAC: can see assigned work only

✅ Step 2: View Assigned Work Queue
  - Navigate to "My Work"
  - Filter: "Assigned to Me"
  - Verify test cases in list
  - Check assignment metadata (date, priority)

✅ Step 3: Run Assigned Test
  - Select test case
  - Click "Run"
  - Poll for completion
  - Capture screenshot on failure

✅ Step 4: Create Defect
  - From result view: "Report Defect"
  - Fill defect form:
    - Title: "Critical login issue"
    - Description: "MFA step fails"
    - Severity: Critical
    - Reproduce steps: auto-linked to test run
  - Submit
  - Verify defect created

✅ Step 5: Comment & Assign
  - Open defect detail
  - Add comment: "Blocking QA sign-off"
  - Assign to: developer@example.com
  - Verify notification sent (check backend)

⚠️ RBAC Edge Cases:
  - Cannot create project (403)
  - Cannot view other team member's work
  - Cannot edit defect assigned to others
```

**Page Objects Needed:**
- `DefectPage` (list, create, detail, comment, assign)
- `MyWorkPage` (queue, filters, status tracking)

---

### 3. Manager Workflow (manager-workflow.spec.ts)

**Role:** Manager (read + analytics)  
**Path:** login → dashboard → view metrics → export report → share link

**Test Cases (6-8):**

```
✅ Step 1: Login as Manager
  - manager@example.com / managerpass
  - Verify dashboard loads

✅ Step 2: View Dashboard
  - Verify all metric cards:
    - Total tests, pass rate, flaky tests
    - Team capacity, velocity
    - Risk matrix, coverage heatmap
  - Verify charts responsive

✅ Step 3: Filter & Drill Down
  - Click on metric card (e.g., "40 Flaky")
  - Verify drill-down list
  - Apply filters: date range, team, project
  - Verify results update

✅ Step 4: Export Report
  - Click "Export Report"
  - Select format: PDF or CSV
  - Configure scope: last 30 days, all projects
  - Download
  - Verify file size > 0

✅ Step 5: Share Link
  - Click "Share"
  - Generate shareable link
  - Copy to clipboard (verify toast)
  - Share link accessible without login

⚠️ Edge Cases:
  - Cannot modify team assignments
  - Cannot create projects
  - Cannot view sensitive logs
```

**Page Objects Needed:**
- `DashboardPage` (metrics, charts, filters)
- `ReportPage` (export, share, scheduling)

---

### 4. Integration Workflow (integration-workflow.spec.ts)

**Role:** Admin (integration scope)  
**Path:** test case → Jira issue → link → sync status → verify bidirectional

**Test Cases (7-9):**

```
✅ Step 1: Create Test Case (as before)

✅ Step 2: Link to Jira Issue
  - Open test case detail
  - Click "Link to Jira"
  - Modal appears: issue picker
  - Search: "PROJ-123"
  - Select issue
  - Verify link confirmed

✅ Step 3: Verify Link UI
  - Test case now shows Jira badge
  - Click badge → external link to Jira
  - Jira issue shows Neurex link (if webhook configured)

✅ Step 4: Run & Sync Status
  - Run test case
  - Wait for completion
  - Verify Jira issue status auto-updated:
    - Test passed → comment "✅ Test passed"
    - Test failed → comment "❌ Test failed + logs"

✅ Step 5: Bidirectional Sync
  - Update Jira issue status to "In Progress"
  - Wait 30s for webhook
  - Verify Neurex shows "Jira: In Progress"

✅ Step 6: Unlink
  - Test case detail → "Unlink Jira"
  - Verify link removed
  - Jira issue still has record (read-only)

⚠️ Error Cases:
  - Jira unreachable → fallback UI
  - Invalid issue key → error message
  - Sync conflict → manual resolution UI
  - Rate limit → retry with exponential backoff
```

**Page Objects Needed:**
- `JiraIntegrationPage` (link picker, sync status)
- API mock helpers (Jira webhook simulation)

---

### 5. Settings Workflow (settings-workflow.spec.ts)

**Role:** User (any role)  
**Path:** login → settings → profile → notifications → save → verify

**Test Cases (7-9):**

```
✅ Step 1: Login & Navigate
  - Login as any user
  - Click user avatar → Settings
  - Verify Settings page loads

✅ Step 2: Profile Section
  - Update profile:
    - Name: "New Name"
    - Avatar: upload image
    - Timezone: "Europe/Istanbul"
  - Click "Save"
  - Verify success toast
  - Reload page → verify persisted

✅ Step 3: Password Change
  - Click "Change Password"
  - Modal appears
  - Enter old password, new password, confirm
  - Submit
  - Verify error if old password wrong
  - Verify success on correct

✅ Step 4: Notifications Settings
  - Check notification preferences:
    - Email notifications: toggle
    - Slack integration: connect/disconnect
    - Daily digest: on/off
    - Frequency: immediate / daily / weekly
  - Change multiple preferences
  - Save
  - Verify toast

✅ Step 5: API Keys (if admin)
  - Section: API Keys
  - Generate new key
  - Copy key (toast feedback)
  - Revoke key (confirm modal)
  - Verify key list updated

✅ Step 6: Team Management (if manager/admin)
  - Invite new member
  - Fill: email, role, projects
  - Send invite
  - Verify member in pending list
  - Verify email sent

⚠️ RBAC:
  - Tester: cannot see team management
  - Manager: can see team only, not org settings
  - Admin: all sections visible
```

**Page Objects Needed:**
- `SettingsPage` (profile, password, notifications, API, team)
- Form validation helpers

---

## Page Object Architecture

### File Structure

```
apps/web/e2e/pages/
├── BasePage.ts              (existing: waitFor, click, fillInput, etc.)
├── LoginPage.ts             (existing: login, forgotPassword, etc.)
├── DashboardPage.ts         (existing: navigate, metrics)
├── ProjectPage.ts           (NEW: list, create, edit, delete, navigate)
├── TestCasePage.ts          (NEW: create, list, edit, run, detail)
├── RunPage.ts               (NEW: poll status, view result, export)
├── DefectPage.ts            (NEW: create, list, comment, assign)
├── MyWorkPage.ts            (NEW: queue, filter, status)
├── SettingsPage.ts          (NEW: profile, password, notifications, api, team)
├── ReportPage.ts            (NEW: export, share, schedule)
└── JiraIntegrationPage.ts   (NEW: link picker, sync UI)
```

### BasePage Pattern (Existing — Reuse)

```typescript
export class BasePage {
  constructor(protected page: Page) {}

  async goto(path: string) {
    await this.page.goto(`http://localhost:3000${path}`);
  }

  async waitFor(selector: string, timeout = 10000) {
    await this.page.waitForSelector(selector, { timeout });
  }

  async click(selector: string) {
    await this.page.click(selector);
  }

  async fillInput(selector: string, value: string) {
    await this.page.fill(selector, value);
  }

  async getText(selector: string): Promise<string> {
    return this.page.textContent(selector) || "";
  }

  async isVisible(selector: string): Promise<boolean> {
    return this.page.isVisible(selector);
  }

  async waitForPageReady(timeout = 10000) {
    await this.page.waitForLoadState("networkidle", { timeout }).catch(() => {});
  }
}
```

### Example: ProjectPage (NEW)

```typescript
import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

export class ProjectPage extends BasePage {
  // Selectors
  readonly projectsHeading = '[data-testid="projects-heading"]';
  readonly newProjectBtn = '[data-testid="new-project-btn"]';
  readonly projectList = '[data-testid="project-list"]';
  readonly projectItem = '[data-testid="project-item"]';
  readonly projectNameInput = '[data-testid="project-form-name"]';
  readonly projectDescInput = '[data-testid="project-form-description"]';
  readonly projectTemplateSelect = '[data-testid="project-form-template"]';
  readonly saveProjectBtn = '[data-testid="project-form-save"]';
  readonly projectDetailContainer = '[data-testid="project-detail"]';
  readonly deleteBtn = '[data-testid="project-delete-btn"]';
  readonly confirmDeleteBtn = '[data-testid="confirm-delete"]';

  async goto() {
    await super.goto("/projects");
    await this.waitForPageReady();
  }

  async createProject(name: string, description: string, template = "blank") {
    // 1. Click new project button
    await this.click(this.newProjectBtn);
    
    // 2. Wait for modal/form
    await this.waitFor(this.projectNameInput);
    
    // 3. Fill form
    await this.fillInput(this.projectNameInput, name);
    await this.fillInput(this.projectDescInput, description);
    await this.page.selectOption(this.projectTemplateSelect, template);
    
    // 4. Submit
    await this.click(this.saveProjectBtn);
    
    // 5. Wait for success (toast or redirect)
    await this.waitForPageReady();
  }

  async getProjectByName(name: string) {
    const items = this.page.locator(this.projectItem);
    const count = await items.count();
    
    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const text = await item.textContent();
      if (text?.includes(name)) {
        return item;
      }
    }
    return null;
  }

  async openProject(name: string) {
    const item = await this.getProjectByName(name);
    if (item) {
      await item.click();
      await this.waitForPageReady();
    }
  }

  async deleteProject(name: string) {
    const item = await this.getProjectByName(name);
    if (item) {
      // Find delete button in this item
      const deleteBtn = item.locator(this.deleteBtn);
      await deleteBtn.click();
      
      // Confirm deletion
      await this.click(this.confirmDeleteBtn);
      await this.waitForPageReady();
    }
  }
}
```

---

## Fixture Pattern (Extend auth.fixtures.ts)

```typescript
import { test as baseTest } from "@playwright/test";
import { LoginPage } from "../pages/LoginPage";
import { ProjectPage } from "../pages/ProjectPage";
import { TestCasePage } from "../pages/TestCasePage";
import { RunPage } from "../pages/RunPage";
import { DefectPage } from "../pages/DefectPage";
import { SettingsPage } from "../pages/SettingsPage";

type WorkflowFixtures = {
  loginPage: LoginPage;
  projectPage: ProjectPage;
  testCasePage: TestCasePage;
  runPage: RunPage;
  defectPage: DefectPage;
  settingsPage: SettingsPage;
  
  // Fixtures that auto-login
  adminSession: void;
  testerSession: void;
  managerSession: void;
  
  // Factory for creating test data
  seedProject: (name: string) => Promise<{ id: string; name: string }>;
};

export const test = baseTest.extend<WorkflowFixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },

  projectPage: async ({ page }, use) => {
    await use(new ProjectPage(page));
  },

  adminSession: async ({ page }, use) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.login("admin@example.com", "admin123");
    await page.waitForURL(/.*/, { timeout: 10000 });
    await use();
  },

  testerSession: async ({ page }, use) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.login("tester@example.com", "testerpass");
    await page.waitForURL(/.*/, { timeout: 10000 });
    await use();
  },

  managerSession: async ({ page }, use) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.login("manager@example.com", "managerpass");
    await page.waitForURL(/.*/, { timeout: 10000 });
    await use();
  },

  seedProject: async ({ adminSession }, use) => {
    const createProject = async (name: string) => {
      // Call API to create project (faster than UI)
      // POST /api/v1/projects
      return { id: "proj_123", name };
    };
    await use(createProject);
  },
});
```

---

## Async Operation Polling Pattern

Key challenge: test runs are async. Solution: poll with timeout.

```typescript
// In RunPage.ts
async pollRunCompletion(testCaseId: string, timeout = 60000): Promise<"passed" | "failed" | "timeout"> {
  const startTime = Date.now();
  const pollInterval = 2000; // 2s between polls

  while (Date.now() - startTime < timeout) {
    const status = await this.getRunStatus(testCaseId);
    
    if (status === "passed" || status === "failed") {
      return status;
    }
    
    // Wait before polling again
    await this.page.waitForTimeout(pollInterval);
  }

  return "timeout";
}

async getRunStatus(testCaseId: string): Promise<string> {
  const statusEl = this.page.locator(`[data-testid="run-status-${testCaseId}"]`);
  const status = await statusEl.textContent();
  return status?.toLowerCase() || "unknown";
}
```

---

## Error Recovery Strategy

### Form Validation Errors

```typescript
async createProjectWithValidation(name: string, description: string) {
  // Try to submit empty form
  await this.click(this.saveProjectBtn);
  
  // Verify error message
  const errorMsg = await this.getText('[data-testid="form-error-name"]');
  expect(errorMsg).toContain("required");
  
  // Fix and retry
  await this.fillInput(this.projectNameInput, name);
  await this.click(this.saveProjectBtn);
  await this.waitForPageReady();
}
```

### Network Timeout Recovery

```typescript
async runWithNetworkRetry(maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await this.click(this.runBtn);
      await this.waitFor(this.runStatusLoading, 5000);
      return; // Success
    } catch (error) {
      if (i < maxRetries - 1) {
        await this.page.waitForTimeout(2000); // Wait before retry
        await this.page.reload();
      } else {
        throw error;
      }
    }
  }
}
```

---

## RBAC Verification Pattern

```typescript
test.describe("RBAC: Tester", () => {
  test.use({ testerSession: true });

  test("should NOT see project creation button", async ({ page, testCasePage }) => {
    await testCasePage.goto();
    
    const newProjectBtn = page.locator('[data-testid="new-project-btn"]');
    expect(await newProjectBtn.isVisible()).toBe(false);
  });

  test("should get 403 on create project API", async ({ page }) => {
    const response = await page.request.post("http://localhost:8000/api/v1/projects", {
      data: { name: "Unauthorized" },
    });
    
    expect(response.status()).toBe(403);
  });

  test("should NOT see other team member work", async ({ page }) => {
    await page.goto("/my-work");
    
    const items = page.locator('[data-testid="work-item"]');
    const count = await items.count();
    
    // Should only see items assigned to current user
    for (let i = 0; i < count; i++) {
      const assignee = await items.nth(i).getAttribute("data-assignee");
      expect(assignee).toBe("tester@example.com");
    }
  });
});
```

---

## Test Data Seeding Strategy

**Fast:** Use API calls (1-2 sec per resource)  
**Slow:** Use UI (5-10 sec per resource)

```typescript
// fixtures/seed.ts
export async function seedTestEnvironment(apiClient: APIClient) {
  // Create project via API
  const project = await apiClient.post("/projects", {
    name: "E2E Test Project",
    description: "Auto-seeded",
  });

  // Create test cases via API
  const testCase = await apiClient.post(`/projects/${project.id}/test-cases`, {
    title: "E2E Test Case",
    steps: [
      { action: "click", selector: "button.login" },
      { action: "fill", selector: "input.password", value: "test123" },
      { action: "click", selector: "button.submit" },
    ],
  });

  return { project, testCase };
}
```

Use in tests:

```typescript
test("admin workflow", async ({ page, seedProject }) => {
  const project = await seedProject("Admin Project");
  
  // Now just verify UI/interact, don't create from scratch
  await page.goto(`/projects/${project.id}`);
});
```

---

## Flakiness Prevention

### 1. Explicit Waits

```typescript
// ❌ BAD: Fragile sleep
await page.waitForTimeout(5000);
await click(saveBtn);

// ✅ GOOD: Wait for element
await waitFor('[data-testid="success-toast"]', 10000);
```

### 2. Network Idle

```typescript
// ❌ BAD: Just wait arbitrary time
await page.waitForTimeout(3000);

// ✅ GOOD: Wait for network idle
await page.waitForLoadState("networkidle", { timeout: 10000 });
```

### 3. Polling with Timeout

```typescript
// ❌ BAD: Infinite loop
while (true) {
  if (await getStatus() === "done") break;
}

// ✅ GOOD: Timeout protection
const result = await pollWithTimeout(
  () => getStatus(),
  "done",
  60000 // 60 second timeout
);
```

### 4. Element Availability

```typescript
// ❌ BAD: Element might not be in DOM yet
const el = page.locator(selector);
await el.click();

// ✅ GOOD: Wait for element + visibility
await page.waitForSelector(selector, { timeout: 10000 });
await page.locator(selector).click();
```

---

## Test Scenario Examples

### Example 1: Admin Complete Workflow

```typescript
// admin-workflow.spec.ts
import { test, expect } from "@playwright/test";
import { LoginPage } from "./pages/LoginPage";
import { ProjectPage } from "./pages/ProjectPage";
import { TestCasePage } from "./pages/TestCasePage";
import { RunPage } from "./pages/RunPage";

test.describe("Admin: Complete Workflow", () => {
  let loginPage: LoginPage;
  let projectPage: ProjectPage;
  let testCasePage: TestCasePage;
  let runPage: RunPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    projectPage = new ProjectPage(page);
    testCasePage = new TestCasePage(page);
    runPage = new RunPage(page);

    // Login as admin
    await loginPage.goto();
    await loginPage.login("admin@example.com", "admin123");
    await page.waitForURL(/.*/, { timeout: 10000 });
  });

  test("should complete admin workflow: create project → test case → run → export", async ({
    page,
  }) => {
    // Step 1: Navigate to projects
    await projectPage.goto();
    expect(page.url()).toContain("/projects");

    // Step 2: Create project
    await projectPage.createProject("Admin Workflow Test", "E2E test project");
    const newProject = await projectPage.getProjectByName("Admin Workflow Test");
    expect(newProject).toBeTruthy();

    // Step 3: Open project and create test case
    await projectPage.openProject("Admin Workflow Test");
    await testCasePage.createTestCase({
      title: "Login Test",
      description: "Test login flow",
      steps: [
        { action: "click", selector: "button.login", expected: "modal visible" },
        { action: "fill", selector: "input.email", value: "test@test.com" },
      ],
    });

    // Step 4: Run test case
    const testCase = await testCasePage.getTestCaseByTitle("Login Test");
    await testCasePage.openTestCase(testCase);
    await runPage.runTestCase();

    // Step 5: Wait for execution
    const status = await runPage.pollRunCompletion("test_123", 60000);
    expect(status).toBe("passed");

    // Step 6: Verify result view
    const resultDetail = await runPage.getResultDetail();
    expect(resultDetail.status).toBe("passed");
    expect(resultDetail.duration).toBeGreaterThan(0);

    // Step 7: Export report
    await runPage.exportReport("pdf");
    // (Browser should trigger download)
  });
});
```

### Example 2: Tester Workflow with RBAC

```typescript
// tester-workflow.spec.ts
import { test, expect } from "./fixtures/workflow.fixtures";

test.describe("Tester: Workflow", () => {
  test.use({ testerSession: true });

  test("should not create project", async ({ page }) => {
    await page.goto("/projects");
    
    const newProjectBtn = page.locator('[data-testid="new-project-btn"]');
    expect(await newProjectBtn.isVisible()).toBe(false);
  });

  test("should create defect from test result", async ({ page, runPage, defectPage }) => {
    // Navigate to My Work
    await page.goto("/my-work");

    // Find and run a test case
    const testItem = page.locator('[data-testid="work-item"]').first();
    await testItem.click();

    // Run test
    await runPage.runTestCase();
    const status = await runPage.pollRunCompletion("test_123", 60000);

    // Report defect
    await runPage.click('[data-testid="report-defect-btn"]');
    await defectPage.createDefect({
      title: "Login fails on MFA",
      severity: "critical",
      description: "Test case failed at MFA step",
    });

    // Verify defect created
    const defectCreated = await page.locator('[data-testid="defect-created-toast"]');
    expect(await defectCreated.isVisible()).toBe(true);
  });
});
```

---

## Success Criteria

### Code Quality
- [ ] 0 TypeScript errors
- [ ] 0 ESLint violations (apps/web)
- [ ] 100% type coverage in .spec.ts files
- [ ] Page Objects fully typed (Playwright best practices)

### Test Coverage
- [ ] 40+ test cases across 5 workflows
- [ ] All happy paths covered
- [ ] All error scenarios with recovery
- [ ] RBAC edge cases for each workflow
- [ ] Mobile viewport tests (iPhone 12, Pixel 5)

### Reliability
- [ ] 0% flakiness on CI (run 3x, all pass)
- [ ] All polls have timeout protection
- [ ] Network errors handled gracefully
- [ ] Form validation errors tested

### Performance
- [ ] Each test < 30 seconds (excluding polling)
- [ ] Parallel execution: 5 workers
- [ ] CI run time: < 10 minutes (full suite)

### Documentation
- [ ] Each .spec.ts file has docstring
- [ ] Each Page Object method documented
- [ ] README with setup/run instructions
- [ ] RBAC matrix documented

---

## Implementation Timeline

### Week 1 (Days 1-5)

**Day 1-2: Page Object Foundation**
- Create ProjectPage, TestCasePage, RunPage
- Add selectors, basic interactions
- Type all page objects
- Add to fixtures

**Day 3: Admin Workflow**
- Implement admin-workflow.spec.ts
- 8-10 test cases
- Async polling tests
- Export/download verification

**Day 4-5: Tester & Manager**
- Tester workflow (8-10 tests)
- Manager workflow (6-8 tests)
- RBAC verification
- Error recovery tests

### Week 2 (Days 6-10)

**Day 6-7: Integration & Settings**
- Integration workflow (7-9 tests, Jira mock)
- Settings workflow (7-9 tests)
- Full RBAC matrix validation
- Mobile viewport tests

**Day 8-9: Polish & Hardening**
- Flakiness root-cause analysis
- Timeout tuning
- Network error handling
- CI integration

**Day 10: Documentation & Handoff**
- Complete README
- RBAC matrix spreadsheet
- Test data seeding guide
- Known flaky tests log

---

## Resource Allocation

**3 Engineers:**

- **Engineer 1 (Lead):** Page Objects, fixture design, async polling patterns, CI setup
- **Engineer 2:** Admin + Tester workflows, RBAC testing, error recovery
- **Engineer 3:** Manager + Integration + Settings workflows, flakiness debugging

---

## Integration with CI/CD

### GitHub Actions

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: "18"
      
      - name: Start Docker containers
        run: docker-compose up -d
      
      - name: Run E2E tests
        run: cd apps/web && npm run test:e2e
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: apps/web/playwright-report/
```

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Test data cleanup | Pollution between runs | Use unique IDs, API cleanup fixtures |
| Network flakiness | Intermittent failures | Explicit waits, retry with backoff |
| Jira webhook delays | Integration test timing | Mock Jira API, don't rely on webhook |
| Browser caching | State leakage | Clear storage per test, incognito context |
| Viewport size | Mobile test failures | Test all 5 viewports, screenshots on fail |
| MFA prompt | Authentication timeout | Skip MFA in test env, use bypass token |

---

## References

- Existing auth.spec.ts: `/apps/web/e2e/auth.spec.ts`
- Playwright docs: https://playwright.dev/docs/intro
- Page Object Model: https://playwright.dev/docs/pom
- Best practices: https://playwright.dev/docs/best-practices

---

**Next Steps:**
1. ✅ Finalize Page Object structure
2. ⏳ Implement ProjectPage, TestCasePage, RunPage
3. ⏳ Write admin-workflow.spec.ts
4. ⏳ Extend to tester, manager, integration, settings
5. ⏳ Hardening & flakiness fixes
6. ⏳ CI integration
7. ⏳ Handoff documentation
