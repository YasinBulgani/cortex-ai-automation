# Playwright E2E Tests — Quick Start Guide

## 30-Second Setup

```bash
# 1. Install dependencies (if not already done)
npm install --save-dev @playwright/test

# 2. Start the dev server
npm run dev

# 3. In another terminal, run tests
npm run test:e2e:ui
```

Done! Browser opens with interactive test UI.

## Common Commands

| Command | What it does |
|---------|-------------|
| `npm run test:e2e` | Run all tests (headless) |
| `npm run test:e2e:ui` | Interactive UI mode ⭐ (best for development) |
| `npm run test:e2e:headed` | Run tests with visible browser |
| `npm run test:e2e:debug` | Step through tests with Inspector |
| `npm run test:e2e:report` | View HTML results report |

## Run Specific Tests

```bash
# Run one test file
npx playwright test e2e/auth.spec.ts

# Run tests matching a pattern
npx playwright test -g "should login"

# Run with verbose output
npx playwright test --verbose

# Run with trace debugging
npx playwright test --trace on
```

## What's Included

✅ **70+ test assertions** covering login page flows  
✅ **Happy path:** valid login → redirect to dashboard  
✅ **Error scenarios:** invalid credentials → error message  
✅ **Accessibility:** keyboard navigation, ARIA labels  
✅ **Mobile:** responsive design on 375px viewport  
✅ **Dark mode:** theme toggle functionality  
✅ **Forgot password:** password reset flow  
✅ **Session:** persistence across page reloads  

## Test Files

```
e2e/
├── auth.spec.ts          ← Main login tests (520 lines)
├── pages/
│   ├── LoginPage.ts      ← Login page interactions
│   ├── DashboardPage.ts  ← Dashboard page interactions
│   └── BasePage.ts       ← Shared page functionality
├── fixtures/
│   └── auth.fixtures.ts  ← Custom test fixtures
├── helpers/
│   └── test-utils.ts     ← Helper functions
└── README.md             ← Full documentation
```

## Directory Structure

```
apps/web/
├── e2e/                  ← All test files live here
├── playwright.config.ts  ← Test configuration
└── package.json          ← npm scripts
```

## Test Credentials

Tests use these accounts (update if needed):

```
Email: test@test.com
Password: test

Email: admin@example.com
Password: admin123
```

Make sure these accounts exist in your test backend.

## Update Selectors

If the login page HTML changes, update selectors in:
- `e2e/pages/LoginPage.ts` — All selectors use `data-testid` attributes
- Keep in sync with actual HTML `data-testid` values

## Debugging

### See what test is doing
```bash
npm run test:e2e:headed
```
Browser window opens and shows each action.

### Step through code
```bash
npm run test:e2e:debug
```
Playwright Inspector opens. Click "Step" to move line by line.

### Take screenshot for debugging
```typescript
await loginPage.takeScreenshot("my-debug-screenshot")
```
Screenshot saved to `screenshots/` folder.

### View test report
```bash
npm run test:e2e:report
```
Beautiful HTML report with:
- ✅ Pass/fail status
- 📸 Screenshots
- 🎥 Videos of failures
- 📊 Timeline of actions

## Add New Tests

### 1. Create test file
```typescript
// e2e/my-feature.spec.ts
import { test, expect } from "@playwright/test"
import { LoginPage } from "./pages/LoginPage"

test("should do something", async ({ page }) => {
  const loginPage = new LoginPage(page)
  await loginPage.goto()
  // ... test code
})
```

### 2. Run new test
```bash
npm run test:e2e:ui
```
Test appears in list, click to run.

## Troubleshooting

### "Can't find element"
→ Use UI mode to see what's happening:
```bash
npm run test:e2e:ui
```

### "Test times out"
→ Increase timeout in `playwright.config.ts`:
```typescript
use: {
  navigationTimeout: 30000,  // 30 seconds
}
```

### "Wrong credentials error"
→ Check test accounts exist in backend database
→ Update credentials in `e2e/auth.spec.ts`

### "Port 3000 already in use"
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Then run dev server again
npm run dev
```

## Next Steps

1. **Run tests:** `npm run test:e2e:ui`
2. **Read full guide:** See `e2e/README.md`
3. **Add new tests:** Copy existing test pattern
4. **Setup CI/CD:** Copy `.github-workflows-example.yml`
5. **Update for your app:** Modify `LoginPage.ts` selectors

## Key Concepts

### Page Object Model
Page objects encapsulate element selectors and interactions:

```typescript
class LoginPage extends BasePage {
  readonly emailInput = '[data-testid="login-input-email"]'
  
  async login(email: string, password: string) {
    await this.fillInput(this.emailInput, email)
    // ...
  }
}
```

Benefits:
- ✅ Easy to maintain (change selector in one place)
- ✅ Readable tests (clear action names)
- ✅ Reusable (all tests use same methods)

### Data-testid Selectors
Use stable selectors that won't break:
```html
<input data-testid="login-input-email" />
```

Not fragile class-based selectors:
```html
<input class="w-full px-4 py-2 border rounded" />
```

## Resources

- **Full Docs:** `e2e/README.md`
- **Setup Details:** `PLAYWRIGHT_SETUP.md`
- **Playwright Website:** https://playwright.dev
- **Best Practices:** https://playwright.dev/docs/best-practices

## Support

For issues:
1. Check `e2e/README.md` troubleshooting section
2. Look at failure screenshots in test report
3. Try debug mode: `npm run test:e2e:debug`
4. Check Playwright docs: https://playwright.dev

---

**Ready to go!** Start with: `npm run test:e2e:ui` 🚀
