# Neurex QA — Playwright E2E Tests

End-to-end testing framework for the Neurex QA Platform using Playwright, with Page Object Model (POM) pattern for maintainability.

## Structure

```
e2e/
├── pages/
│   ├── BasePage.ts          # Base class with common page interactions
│   ├── LoginPage.ts         # Login page object model
│   └── DashboardPage.ts     # Dashboard page object model
├── fixtures/
│   └── auth.fixtures.ts     # Custom test fixtures for auth flow
├── helpers/
│   └── test-utils.ts        # Shared test utilities and helpers
├── auth.spec.ts             # Main authentication test suite
└── README.md                # This file
```

## Installation

Playwright is already installed as a dev dependency. If needed:

```bash
npm install --save-dev @playwright/test @axe-core/playwright
```

## Configuration

The Playwright configuration is in `playwright.config.ts` at the project root:

- **Base URL:** `http://localhost:3000`
- **Test Directory:** `./e2e`
- **Browsers:** Chrome, Firefox, Safari (desktop & mobile)
- **Reporter:** HTML report + GitHub Actions compatible
- **Artifacts:** Screenshots & videos on failure

## Running Tests

### Start Dev Server

```bash
npm run dev
```

### Run All E2E Tests

```bash
npm run test:e2e
```

### Run Tests in UI Mode (Recommended)

```bash
npm run test:e2e:ui
```

This opens an interactive UI where you can:
- Click through tests
- See live browser preview
- Step through failures
- View traces

### Run Tests in Headed Mode

```bash
npm run test:e2e:headed
```

Shows browser window while tests run.

### Run Tests in Debug Mode

```bash
npm run test:e2e:debug
```

Opens Playwright Inspector for step-by-step debugging.

### Run Specific Test File

```bash
npx playwright test e2e/auth.spec.ts
```

### Run Specific Test

```bash
npx playwright test -g "should successfully login with valid test credentials"
```

### View HTML Report

```bash
npm run test:e2e:report
```

## Page Objects

### BasePage

Base class with common interactions:

```typescript
class BasePage {
  goto(path: string)                  // Navigate to path
  waitForPageReady()                  // Wait for UI to render
  takeScreenshot(name: string)        // Capture screenshot
  isVisible(selector: string)         // Check if element visible
  fillInput(selector: string, value)  // Fill input field
  click(selector: string)             // Click element
  waitFor(selector: string)           // Wait for element
  getText(selector: string)           // Get text content
  clearStorage()                      // Clear localStorage/sessionStorage
  // ... and more
}
```

### LoginPage

Login-specific interactions:

```typescript
class LoginPage extends BasePage {
  goto()                              // Navigate to login page
  login(email, password)              // Fill form and submit
  loginAndExpectError(email, password)// Login and capture error
  hasError()                          // Check if error visible
  getErrorMessage()                   // Get error text
  openForgotPanel()                   // Open forgot password
  submitForgotPassword(email)         // Submit password reset
  submitMfaCode(code)                 // Submit MFA code
  // ... and more
}
```

### DashboardPage

Dashboard interactions:

```typescript
class DashboardPage extends BasePage {
  goto()                              // Navigate to dashboard
  isLoaded()                          // Check if dashboard loaded
  isOnProjectsPage()                  // Check if on projects page
  getCurrentUrl()                     // Get current URL
  logout()                            // Logout user
}
```

## Test Utilities

Helper functions in `helpers/test-utils.ts`:

```typescript
// Wait for API call
await waitForApiCall(page, "/api/v1/auth/login")

// Check session cookie
const hasSession = await hasSessionCookie(page)

// Check localStorage token
const hasToken = await hasTokenInStorage(page)

// Decode JWT (no verification)
const payload = decodeJwt(token)

// Check if JWT expired
const expired = isJwtExpired(token)

// Fill with retry logic
await fillInputWithRetry(page, selector, value)

// Get form values
const values = await getFormValues(page, {
  email: '[data-testid="login-input-email"]',
  password: '[data-testid="login-input-password"]'
})

// ... and more
```

## Test Suite: auth.spec.ts

### Login Page Tests

✅ Load login page  
✅ Display form with required fields  
✅ Show heading and subtitle  
✅ Toggle password visibility  
✅ Enable submit button only when fields filled  

### Error Scenario Tests

✅ Show error on invalid email format  
✅ Show error on wrong credentials  
✅ Show error on empty credentials  
✅ Clear error when modifying email  

### Forgot Password Tests

✅ Open forgot password panel  
✅ Close forgot password panel  
✅ Submit forgot password form  

### Accessibility Tests

✅ Proper ARIA labels  
✅ Keyboard navigation support  

### Dark Mode Tests

✅ Toggle dark mode  

### Tab Navigation Tests

✅ Support login/register tabs  

### Real Login Tests

✅ Successfully login with valid test credentials  
✅ Successfully login with admin credentials  

### Session Persistence Tests

✅ Persist session across page reloads  
✅ Redirect to login if not authenticated  

### Mobile Responsiveness Tests

✅ Responsive on mobile viewport  
✅ Hide left panel on mobile  

### Integration Tests

✅ Complete login flow: visit → fill → submit → redirect  
✅ Error flow and retry  

## Test Credentials

Ensure these accounts exist in your test environment:

| Email | Password | Role |
|-------|----------|------|
| test@test.com | test | User |
| admin@example.com | admin123 | Admin |

These are hardcoded in `e2e/auth.spec.ts`. Update them to match your test environment.

## Custom Fixtures

Use custom fixtures for authenticated state:

```typescript
import { test, expect } from "./fixtures/auth.fixtures"

test("should show dashboard for logged in user", async ({ authenticatedPage, page }) => {
  await page.goto("/projects")
  expect(page).toHaveURL(/.*projects/)
})
```

Available fixtures:
- `loginPage` - Pre-configured LoginPage instance
- `dashboardPage` - Pre-configured DashboardPage instance
- `authenticatedPage` - Auto-login with test credentials

## Best Practices

### 1. Use Selectors with `data-testid`

```typescript
// Good
await page.locator('[data-testid="login-input-email"]').fill("test@example.com")

// Avoid
await page.locator('input[type="email"]').fill("test@example.com")
```

All critical elements in the login page have `data-testid` attributes.

### 2. Wait Before Interacting

```typescript
// Good - wait for visibility
await page.locator(selector).waitFor({ state: "visible" })
await page.locator(selector).click()

// Avoid - race conditions
await page.locator(selector).click()
```

### 3. Prefer Page Object Methods

```typescript
// Good
await loginPage.login("test@example.com", "password")

// Avoid - leaks implementation details
await page.fill('[data-testid="login-input-email"]', "test@example.com")
await page.fill('[data-testid="login-input-password"]', "password")
```

### 4. Use Test Descriptions

```typescript
// Good
test("should show error on wrong credentials", async ({ page }) => {
  // test code
})

// Avoid
test("wrong creds", async ({ page }) => {
  // test code
})
```

### 5. Clean Up State

```typescript
test.beforeEach(async ({ page }) => {
  const loginPage = new LoginPage(page)
  await loginPage.clearStorage()
  await loginPage.goto()
})
```

## Debugging

### 1. Use UI Mode

```bash
npm run test:e2e:ui
```

Click through tests, see live browser, view traces.

### 2. Use Inspector

```bash
npm run test:e2e:debug
```

Step through code line by line.

### 3. Add Screenshots

```typescript
test("should login", async ({ page }) => {
  const loginPage = new LoginPage(page)
  await loginPage.goto()
  await loginPage.takeScreenshot("login-page")
  await loginPage.login("test@example.com", "test")
  await loginPage.takeScreenshot("after-login")
})
```

### 4. View HTML Report

```bash
npm run test:e2e:report
```

Shows full test results with traces, videos, and screenshots.

### 5. Print Debugging

```typescript
test("should login", async ({ page }) => {
  console.log("Current URL:", page.url())
  console.log("Page title:", await page.title())
  console.log("Cookies:", await page.context().cookies())
})
```

## CI/CD Integration

The Playwright config is set up for GitHub Actions:

```yaml
- name: Run Playwright Tests
  run: npm run test:e2e

- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Troubleshooting

### Tests timeout waiting for page

```typescript
// Increase timeout
await page.waitForSelector(selector, { timeout: 15000 })
```

### Can't find element

```typescript
// Check if element exists
const count = await page.locator(selector).count()
console.log(`Found ${count} elements`)

// Take screenshot to see state
await page.screenshot({ path: "debug.png" })
```

### API calls fail in test

```typescript
// Wait for API response
await page.waitForResponse(response => 
  response.url().includes("/api/v1/auth/login")
)
```

### Tests pass locally but fail in CI

Check for:
- Hard-coded credentials that don't exist in CI
- Timing assumptions (use waits, not sleeps)
- Environment variable differences
- Viewport/browser differences

## Adding New Tests

1. **Create Page Object** (if new page):

```typescript
// e2e/pages/ProjectsPage.ts
export class ProjectsPage extends BasePage {
  readonly addButton = '[data-testid="projects-add-button"]'
  
  async addProject(name: string) {
    await this.click(this.addButton)
    // ... more interactions
  }
}
```

2. **Create Test File** (if new feature):

```typescript
// e2e/projects.spec.ts
import { test, expect } from "@playwright/test"
import { ProjectsPage } from "./pages/ProjectsPage"

test.describe("Projects", () => {
  test("should add project", async ({ page }) => {
    const projectsPage = new ProjectsPage(page)
    await projectsPage.goto()
    await projectsPage.addProject("New Project")
    // ... assertions
  })
})
```

3. **Run new tests**:

```bash
npm run test:e2e
```

## Performance Tips

- Run tests in parallel (default)
- Use `fullyParallel: false` if tests conflict
- Cache static assets in test setup
- Use `waitForSelector` with specific timeouts
- Mock non-critical API calls

## Resources

- [Playwright Docs](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [POM Pattern](https://playwright.dev/docs/pom)
- [Test Reporter](https://playwright.dev/docs/test-reporters)

## Support

For issues or questions:
1. Check Playwright docs
2. Review existing tests in `auth.spec.ts`
3. Look at test traces in HTML report
4. Enable debug mode: `npm run test:e2e:debug`
