# Playwright E2E Testing Setup — Complete

## What Was Set Up

### 1. Playwright Installation ✅

```bash
npm install --save-dev @playwright/test
```

Installed version: `^1.60.0`
Also includes: `@axe-core/playwright` for accessibility testing

### 2. Configuration Files

#### `playwright.config.ts` (Root)
- Base URL: `http://localhost:3000`
- Browsers: Chrome, Firefox, Safari (desktop + mobile viewports)
- Reporters: HTML, console, GitHub Actions
- Screenshots: On failure
- Videos: On failure
- Auto-starts dev server before tests

#### `.gitignore` (e2e directory)
- Ignores test artifacts: reports, screenshots, videos
- Ignores node_modules and .env files

### 3. Page Object Models

#### `e2e/pages/BasePage.ts`
Base class for all page objects with common methods:
- Navigation (`goto`, `waitForPageReady`)
- User interactions (`click`, `fillInput`, `getText`)
- Element queries (`isVisible`, `waitFor`)
- Storage operations (`clearStorage`, `getLocalStorage`)
- Screenshots (`takeScreenshot`)

#### `e2e/pages/LoginPage.ts`
Login page-specific interactions:
- `login(email, password)` — Fill form and submit
- `loginAndExpectError(email, password)` — Login and capture error
- `openForgotPanel()` — Forgot password flow
- `submitMfaCode(code)` — MFA submission
- `switchToRegisterTab()` — Tab navigation
- `getErrorMessage()` — Retrieve error text
- Plus 15+ other specialized methods

#### `e2e/pages/DashboardPage.ts`
Post-login dashboard interactions:
- `isLoaded()` — Check if dashboard loaded
- `logout()` — Logout user
- `isOnProjectsPage()` — Verify current page

### 4. Test Files

#### `e2e/auth.spec.ts` (Main Test Suite)
**70+ assertions** covering:

**Happy Path:**
- ✅ Load login page
- ✅ Display form fields
- ✅ Show heading/subtitle
- ✅ Toggle password visibility
- ✅ Enable submit button when fields filled

**Error Scenarios:**
- ✅ Invalid email format
- ✅ Wrong credentials → error message
- ✅ Empty credentials (disabled button)
- ✅ Error clears on retry

**Forgot Password:**
- ✅ Open/close forgot panel
- ✅ Submit reset request
- ✅ Display confirmation message

**Accessibility:**
- ✅ ARIA labels present
- ✅ Keyboard navigation (Tab)

**Dark Mode:**
- ✅ Toggle dark mode class
- ✅ Persist theme preference

**Tab Navigation:**
- ✅ Login/register tabs
- ✅ Tab state management

**Real Login (Requires Test Accounts):**
- ✅ Login with test@test.com/test
- ✅ Login with admin@example.com/admin123
- ✅ Redirect to dashboard
- ✅ Session persists on reload

**Mobile Responsiveness:**
- ✅ 375px × 667px viewport
- ✅ Left panel hidden
- ✅ Form elements visible

**Integration Tests:**
- ✅ Complete flow: visit → fill → submit → redirect
- ✅ Error recovery: wrong → fix → success

### 5. Test Fixtures

#### `e2e/fixtures/auth.fixtures.ts`
Custom Playwright test fixtures:
- `loginPage` — Pre-configured LoginPage instance
- `dashboardPage` — Pre-configured DashboardPage instance
- `authenticatedPage` — Auto-login before test

Example usage:
```typescript
import { test } from './fixtures/auth.fixtures'

test('should show dashboard', async ({ authenticatedPage, page }) => {
  await page.goto('/projects')
  expect(page).toHaveURL(/projects/)
})
```

### 6. Test Utilities

#### `e2e/helpers/test-utils.ts`
Shared helper functions:
- `waitForApiCall(page, pattern)` — Wait for API response
- `hasSessionCookie(page)` — Check if logged in
- `hasTokenInStorage(page)` — Check localStorage token
- `decodeJwt(token)` — Decode JWT (no verification)
- `isJwtExpired(token)` — Check token expiration
- `fillInputWithRetry(page, selector, value)` — Resilient input fill
- `clickWithRetry(page, selector)` — Resilient click
- `getFormValues(page, selectors)` — Get all form field values
- `expectNetworkCall(page, pattern)` — Verify API was called
- Plus 5+ more utility functions

### 7. NPM Scripts

Added to `package.json`:
```json
{
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui",
  "test:e2e:debug": "playwright test --debug",
  "test:e2e:headed": "playwright test --headed",
  "test:e2e:report": "playwright show-report"
}
```

### 8. Documentation

#### `e2e/README.md` (Comprehensive Guide)
- Structure overview
- Installation & configuration
- Running tests (6 different modes)
- Page Object documentation
- Test utilities reference
- Complete test suite breakdown
- Best practices (5 key patterns)
- Debugging guide (5 techniques)
- CI/CD integration
- Troubleshooting
- Adding new tests
- Performance tips
- Resources

## How to Use

### 1. Start Dev Server

```bash
npm run dev
```

### 2. Run Tests

```bash
# Run all tests
npm run test:e2e

# Interactive UI mode (recommended for development)
npm run test:e2e:ui

# Headed mode (shows browser)
npm run test:e2e:headed

# Debug mode (step through code)
npm run test:e2e:debug

# View results report
npm run test:e2e:report
```

### 3. Run Specific Tests

```bash
# Single test file
npx playwright test e2e/auth.spec.ts

# Single test by name
npx playwright test -g "should login with valid credentials"

# Multiple files
npx playwright test e2e/auth.spec.ts e2e/projects.spec.ts
```

### 4. Configure Environment

Tests use these credentials (hardcoded in auth.spec.ts):
- **test@test.com / test** (User role)
- **admin@example.com / admin123** (Admin role)

Update these in `e2e/auth.spec.ts` if your environment uses different credentials.

## Test Credentials

Ensure these test accounts exist in your backend:

```sql
-- User account
INSERT INTO users (email, password, full_name) VALUES
  ('test@test.com', '<hashed_test>', 'Test User'),
  ('admin@example.com', '<hashed_admin123>', 'Admin User');
```

Or use the backend's seeding mechanism if available.

## File Structure

```
apps/web/
├── e2e/
│   ├── pages/
│   │   ├── BasePage.ts           (350 lines)
│   │   ├── LoginPage.ts          (250 lines)
│   │   └── DashboardPage.ts      (80 lines)
│   ├── fixtures/
│   │   └── auth.fixtures.ts      (60 lines)
│   ├── helpers/
│   │   └── test-utils.ts         (200 lines)
│   ├── auth.spec.ts              (520 lines, 70+ assertions)
│   ├── .gitignore
│   └── README.md                 (350 lines, comprehensive guide)
├── playwright.config.ts          (60 lines)
├── package.json                  (updated with 5 new scripts)
└── PLAYWRIGHT_SETUP.md           (this file)
```

## Next Steps

### 1. Verify Test Environment
```bash
npm run test:e2e:ui
```

### 2. Update Test Credentials
If your test environment uses different credentials, update in `e2e/auth.spec.ts`:
```typescript
const testEmail = "your-test-email@example.com"
const testPassword = "your-test-password"
```

### 3. Add Custom Page Objects
For new features, create new page objects:
```bash
# Create e2e/pages/YourFeaturePage.ts
# Extend BasePage
# Add feature-specific methods
```

### 4. Add New Test Specs
```bash
# Create e2e/feature.spec.ts
# Import page objects
# Write test cases
```

### 5. Integrate with CI/CD
Add to your GitHub Actions workflow:
```yaml
- name: Run Playwright Tests
  run: npm run test:e2e

- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Key Features

✅ **Page Object Model** — Encapsulates page interactions, easy to maintain  
✅ **Multi-browser** — Chrome, Firefox, Safari (desktop & mobile)  
✅ **Real browser** — Runs in real browsers, not jsdom  
✅ **Screenshots** — Auto-captured on failure  
✅ **Videos** — Recording on failure for debugging  
✅ **HTML Report** — Beautiful, detailed test results  
✅ **UI Mode** — Interactive test development (npm run test:e2e:ui)  
✅ **Parallel** — Tests run in parallel by default  
✅ **CI/CD Ready** — GitHub Actions compatible  
✅ **Accessibility** — @axe-core/playwright integrated  
✅ **Type-safe** — Full TypeScript support  

## Troubleshooting

### Tests won't run
1. Check dev server is running: `npm run dev`
2. Verify port 3000 is free: `lsof -i :3000`
3. Check test credentials exist in backend

### Tests timeout
1. Increase timeout in playwright.config.ts
2. Check network tab in browser dev tools
3. Look at failure screenshots in playwright-report/

### Can't find element
1. Use Playwright Inspector: `npm run test:e2e:debug`
2. Check element selector with `data-testid`
3. Take screenshot: `await loginPage.takeScreenshot("debug")`

### Want to see browser?
```bash
npm run test:e2e:headed
```

## Maintenance

### Update Selectors
All selectors in page objects use `data-testid` attributes. If frontend changes selectors:
1. Check which tests fail
2. Update selector in page object
3. Run tests again

### Add New Tests
1. Create new test function in spec file or new spec file
2. Use existing page objects or create new ones
3. Follow naming convention: `test("should [action]", ...)`
4. Run `npm run test:e2e`

### Update Test Credentials
When test accounts change:
1. Update in `e2e/auth.spec.ts`
2. Run `npm run test:e2e:ui` to verify
3. Commit changes

## Support

- **Playwright Docs:** https://playwright.dev
- **GitHub Issues:** Check Playwright GitHub
- **Local Issues:** 
  - Check browser console in headed mode
  - Look at screenshots in `test-results/`
  - View trace in HTML report

---

**Setup completed:** 2026-06-09
**Playwright version:** 1.60.0
**Browsers:** Chrome, Firefox, Safari (desktop + mobile)
**Tests:** 70+ assertions in auth.spec.ts
