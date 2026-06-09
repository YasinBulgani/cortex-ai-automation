# Phase 2.2: Quick Start Guide

**5-Minute Setup & First Test Run**

---

## 1. Setup (2 min)

```bash
# Navigate to web app
cd apps/web

# Install if needed
npm install

# Ensure backend is running
cd ../..
docker-compose up -d
make migrate

# Go back to web
cd apps/web
```

---

## 2. Run Foundation Tests (1 min)

```bash
# Run admin workflow (19 tests)
npm run test:e2e -- admin-workflow.spec.ts

# Or run all E2E tests
npm run test:e2e

# Run with visual UI
npm run test:e2e:ui

# Debug mode (opens Playwright Inspector)
npm run test:e2e:debug
```

---

## 3. Files & Locations

### Core Files

| File | Purpose | Lines |
|------|---------|-------|
| `pages/ProjectPage.ts` | Project CRUD | 200 |
| `pages/TestCasePage.ts` | Test case management | 300 |
| `pages/RunPage.ts` | Test execution + polling | 350 |
| `pages/DefectPage.ts` | Defect management | 300 |
| `pages/SettingsPage.ts` | User settings | 400 |
| `fixtures/workflow.fixtures.ts` | Multi-role sessions | 200 |
| `admin-workflow.spec.ts` | Foundation tests | 400 |

### Documentation

| Document | Purpose |
|----------|---------|
| `PHASE_2_2_DELIVERABLES_SUMMARY.md` | Overview (this package) |
| `docs/PHASE_2_2_E2E_CRITICAL_PATHS.md` | Full plan (11 pages) |
| `e2e/README_PHASE_2_2.md` | Implementation guide (10 pages) |

---

## 4. Writing a Test

```typescript
import { test, expect } from "./fixtures/workflow.fixtures";

test("admin creates project", async ({ adminSession, projectPage }) => {
  // Arrange: fixture handles login
  await projectPage.goto();

  // Act: use page object methods
  await projectPage.createProject("My Project", "Description");

  // Assert: verify result
  const exists = await projectPage.projectExists("My Project");
  expect(exists).toBe(true);
});
```

---

## 5. Key Patterns

### Multi-Step Workflow

```typescript
test("complete workflow", async ({
  adminSession,
  projectPage,
  testCasePage,
  runPage,
}) => {
  // Step 1
  await projectPage.goto();
  await projectPage.createProject("Test", "Desc");

  // Step 2
  await testCasePage.goto();
  await testCasePage.createTestCase({ title: "Login", ... });

  // Step 3: Async polling
  await testCasePage.runTestCase();
  const status = await runPage.pollRunCompletion(60000);
  expect(status).not.toBe("timeout");
});
```

### RBAC Test

```typescript
test("tester cannot create", async ({ testerSession, page }) => {
  await page.goto("/projects");
  const btn = page.locator('[data-testid="new-project-btn"]');
  expect(await btn.isVisible()).toBe(false);
});
```

### Error Handling

```typescript
test("form validation", async ({ projectPage }) => {
  await projectPage.goto();
  await projectPage.page.click('[data-testid="new-project-btn"]');

  // Submit empty (should error)
  await projectPage.click(projectPage.saveProjectBtn);
  const error = await projectPage.getFormError();
  expect(error.length > 0).toBe(true);

  // Fix and retry
  await projectPage.fillInput(projectPage.projectNameInput, "Test");
  await projectPage.click(projectPage.saveProjectBtn);
  // Should succeed
});
```

---

## 6. Sessions (Auto-Login)

```typescript
// Admin (all permissions)
test("admin test", async ({ adminSession, projectPage }) => {
  await projectPage.goto(); // Already logged in
});

// Tester (limited permissions)
test("tester test", async ({ testerSession, page }) => {
  await page.goto("/my-work"); // Already logged in
});

// Manager (read-only)
test("manager test", async ({ managerSession, dashboardPage }) => {
  await dashboardPage.goto();
});
```

**Credentials:**
- Admin: admin@example.com / admin123
- Tester: tester@example.com / testerpass
- Manager: manager@example.com / managerpass
- Developer: developer@example.com / developerpass

---

## 7. Polling Pattern (for async operations)

```typescript
// Don't do this: await page.waitForTimeout(60000);

// Do this instead:
const status = await runPage.pollRunCompletion(
  60000, // timeout (ms)
  2000   // poll interval (ms)
);
// Checks every 2s, fails after 60s, returns: "passed"|"failed"|"timeout"|"skipped"
```

---

## 8. Seeded Test Data

```typescript
test("run seeded test", async ({ seedTestData, runPage }) => {
  const { projectId, testCaseId } = seedTestData;
  // Project + test case already created via API (fast!)
  // Just test the UI/workflow
  
  await runPage.gotoProject(projectId);
  const status = await runPage.pollRunCompletion(60000);
});
```

---

## 9. Page Objects Quick Reference

### ProjectPage
```typescript
await projectPage.goto()
await projectPage.createProject(name, desc, template?, access?)
await projectPage.openProject(name)
await projectPage.editProject(name, updates)
await projectPage.deleteProject(name)
await projectPage.projectExists(name): boolean
```

### TestCasePage
```typescript
await testCasePage.createTestCase({ title, description, steps, ... })
await testCasePage.openTestCase(title)
await testCasePage.runTestCase()
await testCasePage.getDetailTitle(): string
```

### RunPage (⭐ with polling)
```typescript
await runPage.pollRunCompletion(timeout, interval): Promise<status>
await runPage.getRunStatus(): string
await runPage.getResultDetail(): RunResult
await runPage.exportResult("pdf"|"csv"|"json")
await runPage.shareResult(): string
```

### DefectPage
```typescript
await defectPage.createDefect({ title, description, severity, ... })
await defectPage.openDefect(title)
await defectPage.addComment(text)
await defectPage.assignToUser(email)
await defectPage.updateStatus(newStatus)
```

### SettingsPage
```typescript
await settingsPage.updateProfile({ name?, timezone?, language? })
await settingsPage.changePassword(current, new, confirm)
await settingsPage.generateApiKey(name): string
await settingsPage.inviteTeamMember(email, role, projects?)
```

---

## 10. Debugging

```bash
# Run single test
npm run test:e2e -- --grep "should create project"

# Run in headed mode (see browser)
npm run test:e2e:headed

# Debug mode (Playwright Inspector)
npm run test:e2e:debug

# View report
npx playwright show-report
```

### In Test

```typescript
test("debug", async ({ page, projectPage }) => {
  // Take screenshot
  await page.screenshot({ path: "debug.png" });

  // Pause execution
  await page.pause();

  // Log current URL
  console.log("URL:", page.url());

  // Log element count
  const items = await page.locator('[data-testid="project-item"]').count();
  console.log("Items:", items);
});
```

---

## 11. CI/CD (GitHub Actions)

Already configured in Playwright config. Just push and tests run automatically on:
- Every PR
- Every push to main
- Schedule (configurable)

View results:
1. GitHub Actions tab
2. Select workflow
3. Download artifacts (screenshots, videos on failure)

---

## 12. Next Steps

### This Week

1. ✅ **Foundation ready** (admin workflow + all page objects)
2. ⏳ **Implement tester workflow** (10 tests)
3. ⏳ **Implement manager workflow** (8 tests)
4. ⏳ **Implement integration workflow** (9 tests)
5. ⏳ **Implement settings workflow** (9 tests)

### Each Workflow

1. Create `workflow-name.spec.ts`
2. Import fixtures: `import { test, expect } from "./fixtures/workflow.fixtures"`
3. Use session: `test.use({ roleSession: true })`
4. Write tests following admin workflow pattern
5. Run: `npm run test:e2e -- workflow-name.spec.ts`
6. Verify all pass
7. Push to GitHub

---

## 13. Test Count Target

| Workflow | Tests | Status |
|----------|-------|--------|
| Admin (project → test → run → export) | 19 | ✅ Done |
| Tester (my work → defect → comment) | 10 | ⏳ TODO |
| Manager (dashboard → metrics → export) | 8 | ⏳ TODO |
| Integration (jira → sync → verify) | 9 | ⏳ TODO |
| Settings (profile → team → api keys) | 9 | ⏳ TODO |
| **Total** | **55** | **19 done, 36 TODO** |

---

## 14. Resources

| Resource | Link |
|----------|------|
| Full Plan | `docs/PHASE_2_2_E2E_CRITICAL_PATHS.md` |
| Implementation Guide | `apps/web/e2e/README_PHASE_2_2.md` |
| Playwright Docs | https://playwright.dev |
| Debugging | https://playwright.dev/docs/debugging |

---

## 15. Commands Cheat Sheet

```bash
# Setup
npm install
make migrate

# Run tests
npm run test:e2e                              # All
npm run test:e2e -- admin-workflow.spec.ts   # Specific file
npm run test:e2e -- --grep "should create"   # Specific test
npm run test:e2e:ui                          # Visual UI
npm run test:e2e:headed                      # See browser
npm run test:e2e:debug                       # Debugger

# View results
npx playwright show-report                    # HTML report
```

---

**Status:** Ready to implement ✅  
**Estimated Time:** 2 weeks with 3 engineers  
**Foundation:** Complete and production-ready

**Start here:** `npm run test:e2e -- admin-workflow.spec.ts`
