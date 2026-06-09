import { Page, expect } from "@playwright/test";

/**
 * Common test utilities and helpers
 */

/**
 * Wait for API request matching pattern
 */
export async function waitForApiCall(page: Page, pattern: string | RegExp, timeout = 10000) {
  return page.waitForResponse((response) => {
    if (typeof pattern === "string") {
      return response.url().includes(pattern);
    }
    return pattern.test(response.url());
  });
}

/**
 * Get all cookies
 */
export async function getCookies(page: Page) {
  return page.context().cookies();
}

/**
 * Check if session cookie exists
 */
export async function hasSessionCookie(page: Page): Promise<boolean> {
  const cookies = await getCookies(page);
  return cookies.some((c) => c.name === "twai_session" || c.name.includes("session"));
}

/**
 * Check if token exists in localStorage
 */
export async function hasTokenInStorage(page: Page): Promise<boolean> {
  const token = await page.evaluate(() => localStorage.getItem("access_token"));
  return !!token;
}

/**
 * Extract JWT payload (without verification)
 */
export function decodeJwt(token: string): any {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid JWT format");

  const payload = parts[1];
  const decoded = Buffer.from(payload, "base64").toString("utf-8");
  return JSON.parse(decoded);
}

/**
 * Check if JWT is expired
 */
export function isJwtExpired(token: string): boolean {
  try {
    const payload = decodeJwt(token);
    if (!payload.exp) return false;

    const expirationTime = payload.exp * 1000; // Convert to milliseconds
    return Date.now() > expirationTime;
  } catch {
    return true;
  }
}

/**
 * Fill form field with retry
 */
export async function fillInputWithRetry(
  page: Page,
  selector: string,
  value: string,
  maxAttempts = 3
) {
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      const input = page.locator(selector);
      await input.fill(value);

      const inputValue = await input.inputValue();
      if (inputValue === value) {
        return;
      }
    } catch {
      // Retry
    }

    attempts++;
    await page.waitForTimeout(100);
  }

  throw new Error(`Failed to fill input at ${selector} with value: ${value}`);
}

/**
 * Click with retry
 */
export async function clickWithRetry(page: Page, selector: string, maxAttempts = 3) {
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      await page.locator(selector).click();
      return;
    } catch {
      attempts++;
      await page.waitForTimeout(100);
    }
  }

  throw new Error(`Failed to click element: ${selector}`);
}

/**
 * Wait for element and get text
 */
export async function waitForElementText(
  page: Page,
  selector: string,
  timeout = 5000
): Promise<string> {
  const element = page.locator(selector);
  await element.waitFor({ state: "visible", timeout });
  return (await element.textContent()) || "";
}

/**
 * Check element contains text
 */
export async function expectElementContainsText(
  page: Page,
  selector: string,
  text: string | RegExp,
  timeout = 5000
) {
  const element = page.locator(selector);
  await element.waitFor({ state: "visible", timeout });
  await expect(element).toContainText(text);
}

/**
 * Get all input values as object
 */
export async function getFormValues(
  page: Page,
  selectors: { [key: string]: string }
): Promise<{ [key: string]: string }> {
  const values: { [key: string]: string } = {};

  for (const [key, selector] of Object.entries(selectors)) {
    const input = page.locator(selector);
    values[key] = await input.inputValue();
  }

  return values;
}

/**
 * Take screenshot on failure (utility)
 */
export async function takeFailureScreenshot(page: Page, testName: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  await page.screenshot({
    path: `test-results/failures/${testName}-${timestamp}.png`,
    fullPage: true,
  });
}

/**
 * Intercept and mock API response
 */
export async function mockApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  responseData: any,
  statusCode = 200
) {
  await page.route(urlPattern, (route) => {
    route.abort("blockedbyclient");
  });

  await page.addInitScript(
    (pattern: string, data: any, code: number) => {
      const originalFetch = window.fetch;
      (window as any).fetch = function (...args: any[]) {
        const url = args[0];
        if (typeof url === "string" && url.includes(pattern)) {
          return Promise.resolve(
            new Response(JSON.stringify(data), {
              status: code,
              headers: { "Content-Type": "application/json" },
            })
          );
        }
        return originalFetch.apply(this, args);
      };
    },
    typeof urlPattern === "string" ? urlPattern : urlPattern.source,
    responseData,
    statusCode
  );
}

/**
 * Check if network request was made
 */
export async function expectNetworkCall(
  page: Page,
  pattern: string | RegExp,
  timeout = 5000
): Promise<boolean> {
  try {
    await page.waitForResponse((response) => {
      if (typeof pattern === "string") {
        return response.url().includes(pattern);
      }
      return pattern.test(response.url());
    }, { timeout });
    return true;
  } catch {
    return false;
  }
}
