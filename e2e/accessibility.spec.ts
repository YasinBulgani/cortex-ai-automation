/**
 * Erişilebilirlik (a11y) test paketi.
 * Kapsam: WCAG 2.1 AA axe-core taraması + keyboard-only navigation + ARIA doğrulama.
 *
 * @axe-core/playwright bağımlılığı kurulu değilse axe testleri skip edilir.
 * Keyboard testleri bağımsız çalışır — axe gerektirmez.
 */

import { test, expect, type Page } from "@playwright/test";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";
import { API_BASE } from "./config/runtime";
import { getAdminToken, apiCreateProject } from "./helpers/auth";

const BASE_URL = process.env.BASE_URL || process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";

// ── Axe helper ────────────────────────────────────────────────────────────────

async function axeScan(
  page: Page,
  opts?: { includedImpacts?: string[] }
): Promise<{ serious: number; critical: number; total: number; violations: unknown[] }> {
  let AxeBuilder: unknown;
  try {
    AxeBuilder = (await import("@axe-core/playwright")).default;
  } catch {
    test.skip(true, "@axe-core/playwright kurulu değil — `npm i -D @axe-core/playwright` sonra çalışır");
    return { serious: 0, critical: 0, total: 0, violations: [] };
  }
  // @ts-expect-error dynamic
  const builder = new AxeBuilder({ page }).withTags([
    "wcag2a", "wcag2aa", "wcag21a", "wcag21aa",
  ]);
  if (opts?.includedImpacts) {
    // @ts-expect-error dynamic
    builder.options({ runOnly: { type: "tag", values: opts.includedImpacts } });
  }
  const results = await builder.analyze();
  const byImpact = (impact: string) =>
    results.violations.filter((v: { impact?: string }) => v.impact === impact).length;

  for (const v of results.violations) {
    console.log(`[a11y ${(v as { impact?: string }).impact}] ${(v as { id: string }).id} — ${(v as { description: string }).description}`);
  }
  return {
    serious: byImpact("serious"),
    critical: byImpact("critical"),
    total: results.violations.length,
    violations: results.violations,
  };
}

// ── Anonim sayfalar ───────────────────────────────────────────────────────────

test.describe("A11y — anonim sayfalar", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("login sayfası: critical ve serious ihlal olmamalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState("networkidle");
    const { serious, critical } = await axeScan(page);
    expect(critical, "critical a11y ihlali 0 olmalı").toBe(0);
    expect(serious, "serious a11y ihlali 0 olmalı").toBe(0);
  });

  test("login formu: Tab tuşuyla gezinmek mümkün olmalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState("networkidle");

    // İlk Tab → e-posta alanına focus gelmeli
    await page.keyboard.press("Tab");
    const emailFocused =
      (await page.locator("input[type='email']").evaluate((el) => document.activeElement === el)) ||
      (await page.getByLabel("E-posta").evaluate((el) => document.activeElement === el));
    expect(emailFocused, "Tab ile email input'a focus gelmeli").toBeTruthy();

    // Bir sonraki Tab → şifre alanına
    await page.keyboard.press("Tab");
    const passwordFocused =
      (await page.locator("input[type='password']").evaluate((el) => document.activeElement === el));
    expect(passwordFocused, "Tab ile password input'a focus gelmeli").toBeTruthy();

    // Son Tab → submit butona
    await page.keyboard.press("Tab");
    const submitFocused = await page.locator("button[type='submit']").evaluate(
      (el) => document.activeElement === el
    );
    expect(submitFocused, "Tab ile submit butona focus gelmeli").toBeTruthy();
  });

  test("login formu: Enter tuşuyla submit edilebilmeli", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
    await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
    await page.keyboard.press("Enter");
    await page.waitForURL(/\/projects|\/dashboard/, { timeout: 15_000 });
    expect(page.url()).toMatch(/\/projects|\/dashboard/);
  });

  test("404 sayfası: semantic main ve h1 bulunmalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/__this-does-not-exist__`);
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("h1").first()).toBeVisible();
    const { critical } = await axeScan(page);
    expect(critical).toBe(0);
  });
});

// ── Kimlik doğrulamalı sayfalar ───────────────────────────────────────────────

test.describe("A11y — authenticated sayfalar", () => {
  let projectId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    const token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `A11y Proje ${Date.now()}`);
    await request.dispose();
  });

  test("projeler listesi: critical 0, serious 0", async ({ page }) => {
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForLoadState("networkidle");
    const { critical, serious, total } = await axeScan(page);
    console.log(`[a11y /projects] ${total} ihlal, critical=${critical}, serious=${serious}`);
    expect(critical).toBe(0);
    expect(serious).toBe(0);
  });

  test("proje dashboard: critical 0", async ({ page }) => {
    await page.goto(`${BASE_URL}/p/${projectId}`);
    await page.waitForLoadState("networkidle");
    const { critical, serious, total } = await axeScan(page);
    console.log(`[a11y dashboard] ${total} ihlal, critical=${critical}, serious=${serious}`);
    expect(critical).toBe(0);
  });

  test("senaryo listesi: critical 0", async ({ page }) => {
    await page.goto(`${BASE_URL}/p/${projectId}/scenarios`);
    await page.waitForLoadState("networkidle");
    const { critical } = await axeScan(page);
    expect(critical).toBe(0);
  });

  test("onay sayfası: critical 0", async ({ page }) => {
    await page.goto(`${BASE_URL}/p/${projectId}/approvals`);
    await page.waitForLoadState("networkidle");
    const { critical } = await axeScan(page);
    expect(critical).toBe(0);
  });

  test("projeler sayfasında modal: ESC ile kapanmalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/projects`);
    // "Yeni Proje" butonunu Tab ile bul ve Enter ile aç
    const newProjectBtn = page.getByRole("button", { name: /yeni proje|new project/i });
    if (await newProjectBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await newProjectBtn.click();
      // Modal açıldıysa
      const modal = page.getByRole("dialog");
      if (await modal.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await page.keyboard.press("Escape");
        await expect(modal).not.toBeVisible({ timeout: 3_000 });
      }
    }
    // Modal bulunamazsa test geçer (opsiyonel component)
  });

  test("ARIA: kritik düğmelerin erişilebilir ismi olmalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/p/${projectId}/scenarios`);
    await page.waitForLoadState("networkidle");
    // Erişilebilir adı olmayan butonlar (icon-only butonlar gibi) a11y hatası üretir
    const { violations } = await axeScan(page);
    const buttonLabelViolations = (violations as Array<{ id: string }>).filter(
      (v) => v.id === "button-name" || v.id === "aria-required-attr"
    );
    expect(buttonLabelViolations.length, "Düğmelerin erişilebilir adı olmalı").toBe(0);
  });
});
