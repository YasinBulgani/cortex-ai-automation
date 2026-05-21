import { expect, test } from "./fixtures/pages.fixture";

/**
 * GAP-001 — Sidebar Keyboard Accessibility (WCAG 2.1 AA)
 *
 * Bu suite AppShell'deki a11y implementasyonunu keyboard-only kullanıcı
 * perspektifinden doğrular. axe-core yerine Playwright'ın native ARIA
 * assertion'larıyla çalışır — ek npm bağımlılığı eklemeden deterministic.
 *
 * Kapsam (GAP-001 design.md A11y Checklist):
 *   - Skip-to-content link tab ile erişilebilir + main'e atlatır
 *   - <nav> role + aria-label doğru
 *   - Aktif link aria-current="page" taşır
 *   - Arrow Up/Down ana nav list'te fokus hareket ettirir
 *   - Collapsible button'lar aria-expanded + aria-controls
 *   - Mobile drawer Escape ile kapanır (hamburger'a focus geri döner)
 *   - Focus-visible ring klavye fokusunda (class kontrolü)
 */

const API = process.env.API_BASE || "http://127.0.0.1:8765";

test.describe("GAP-001 — Sidebar a11y", () => {
  const email = `a11y_${Date.now()}@example.com`;
  const password = "SecurePass123!";

  test.beforeAll(async ({ request }) => {
    const reg = await request.post(`${API}/api/v1/auth/register`, {
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({
        email,
        password,
        password_confirm: password,
        first_name: "A11y",
        last_name: "Tester",
      }),
    });
    expect(reg.ok()).toBeTruthy();
  });

  test("skip-to-content link main'e atlatır", async ({ page, loginPage }) => {
    await loginPage.login(email, password);
    await page.goto("/portfolio");

    const skipLink = page.getByTestId("skip-to-content");
    await expect(skipLink).toHaveAttribute("href", "#main-content");

    // Focus + Enter → main'e atla ve fokus oraya geçmeli
    await skipLink.focus();
    await expect(skipLink).toBeFocused();
    await page.keyboard.press("Enter");

    const mainFocused = await page.evaluate(
      () => (document.activeElement as HTMLElement | null)?.id,
    );
    expect(mainFocused).toBe("main-content");
  });

  test("nav semantic + aktif link aria-current='page'", async ({
    page,
    loginPage,
  }) => {
    await loginPage.login(email, password);
    await page.goto("/portfolio");

    const nav = page.getByTestId("sidebar-nav");
    await expect(nav).toHaveAttribute("aria-label", "Ana navigasyon");

    // Portföy linki aktif olmalı (aria-current="page")
    const activeLink = page.getByTestId("sidebar-link-dashboard");
    await expect(activeLink).toHaveAttribute("aria-current", "page");

    // Diğer link'ler aria-current TAŞIMAMALI
    const otherLink = page.getByTestId("sidebar-link-projects");
    await expect(otherLink).not.toHaveAttribute("aria-current", /.*/);
  });

  test("Arrow Up/Down ana nav list'te fokusu hareket ettirir", async ({
    page,
    loginPage,
  }) => {
    await loginPage.login(email, password);
    await page.goto("/portfolio");

    // İlk nav link'e focus ver
    const first = page.getByTestId("sidebar-link-dashboard");
    await first.focus();
    await expect(first).toBeFocused();

    // ArrowDown → bir sonraki data-nav-item'a geç
    await page.keyboard.press("ArrowDown");
    const afterDown = await page.evaluate(
      () => (document.activeElement as HTMLElement | null)?.getAttribute("data-testid"),
    );
    expect(afterDown).toBe("sidebar-link-bgtest-wizard");

    // ArrowUp → başa dön
    await page.keyboard.press("ArrowUp");
    await expect(first).toBeFocused();
  });

  test("Tools toggle button aria-expanded + aria-controls", async ({
    page,
    loginPage,
  }) => {
    await loginPage.login(email, password);
    await page.goto("/portfolio");

    const toggle = page.getByTestId("sidebar-tools-toggle");
    await expect(toggle).toHaveAttribute("aria-controls", "sidebar-tools-panel");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#sidebar-tools-panel")).toBeVisible();
  });

  test("mobile drawer Escape ile kapanır, hamburger'a focus döner", async ({
    page,
    loginPage,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await loginPage.login(email, password);
    await page.goto("/portfolio");

    // Hamburger focus + aç
    const hamburger = page.getByRole("button", { name: "Menüyü aç" });
    await hamburger.focus();
    await hamburger.press("Enter");
    await expect(page.getByTestId("sidebar")).toHaveAttribute("aria-modal", "true");

    // Escape → drawer kapanır + focus hamburger'a geri döner
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("sidebar")).not.toHaveAttribute("aria-modal", /.*/);
    await expect(hamburger).toBeFocused();
  });

  test("focus-visible ring — klavye odağı için görünür outline", async ({
    page,
    loginPage,
  }) => {
    await loginPage.login(email, password);
    await page.goto("/portfolio");

    const link = page.getByTestId("sidebar-link-projects");
    await link.focus();
    // Tailwind class'ı uygulanmış mı (focus-visible:ring-2)
    const hasFocusRing = await link.evaluate((el) =>
      el.className.includes("focus-visible:ring-2"),
    );
    expect(hasFocusRing).toBe(true);
  });
});
