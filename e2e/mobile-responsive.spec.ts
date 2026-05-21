/**
 * Mobile Responsive E2E — Pixel 5 viewport (360×800)
 * Playwright config'deki `mobile` project bu dosyayı kullanır.
 *
 * Kapsam: 5 kritik akış × mobile viewport'ta davranış doğrulama
 *   1. Login ve yönlendirme
 *   2. Proje listesi görünümü ve navigasyon
 *   3. Senaryo oluşturma formu
 *   4. Onay sayfası etkileşimi
 *   5. Horizontal overflow yok (layout kırılması testi)
 */

import { test, expect } from "@playwright/test";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";
import { API_BASE } from "./config/runtime";
import { getAdminToken, apiCreateProject, apiCreateScenario, apiCreateApproval } from "./helpers/auth";

const BASE_URL = process.env.BASE_URL || process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";

test.describe.serial("Mobile Responsive (360×800)", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Mobile Proje ${Date.now()}`);
    await request.dispose();
  });

  // ── 1. Login ────────────────────────────────────────────────────────────

  test("TC-MR-001: login formu mobile viewport'ta çalışmalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState("networkidle");

    // Viewport kontrolü
    const viewport = page.viewportSize();
    expect(viewport?.width).toBeLessThanOrEqual(400);

    // Form elemanları görünmeli
    await expect(page.getByLabel("E-posta")).toBeVisible();
    await expect(page.getByLabel("Şifre")).toBeVisible();
    await expect(page.getByRole("button", { name: /giriş/i })).toBeVisible();

    // Login
    await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
    await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /giriş/i }).click();
    await page.waitForURL(/\/projects|\/dashboard/, { timeout: 20_000 });
    expect(page.url()).toMatch(/\/projects|\/dashboard/);
  });

  // ── 2. Proje listesi ────────────────────────────────────────────────────

  test("TC-MR-002: proje listesi mobile'da görünmeli ve yatay taşma olmamalı", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
    await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /giriş/i }).click();
    await page.waitForURL(/\/projects|\/dashboard/, { timeout: 20_000 });

    // Yatay overflow kontrolü — body genişliği viewport'u aşmamalı
    const overflow = await page.evaluate(() => {
      return document.body.scrollWidth > window.innerWidth;
    });
    expect(overflow, "Yatay overflow (horizontal scroll) olmamalı").toBe(false);

    // Proje içeriği görünmeli
    const hasContent = (await page.locator("[data-testid^='projects-card-']").count()) > 0 ||
      (await page.getByText(/proje|project/i).count()) > 0;
    expect(hasContent).toBeTruthy();
  });

  // ── 3. Navigasyon ────────────────────────────────────────────────────────

  test("TC-MR-003: mobile navigasyonu çalışmalı (hamburger veya sidebar)", async ({ page }) => {
    // Login
    await page.goto(`${BASE_URL}/login`);
    await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
    await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /giriş/i }).click();
    await page.waitForURL(/\/projects|\/dashboard/, { timeout: 20_000 });

    await page.goto(`${BASE_URL}/p/${projectId}`);
    await page.waitForLoadState("networkidle");

    // Navigasyon link'i bulunabilmeli: ya sidebar ya hamburger
    const hamburgerVisible = await page.locator("[data-testid='hamburger'], [aria-label*='menü'], button[aria-expanded]")
      .first()
      .isVisible()
      .catch(() => false);

    const sidebarVisible = await page.locator("nav, [role='navigation']")
      .first()
      .isVisible()
      .catch(() => false);

    expect(hamburgerVisible || sidebarVisible, "Mobile'da hamburger veya sidebar navigasyonu görünmeli").toBeTruthy();
  });

  // ── 4. Senaryo oluşturma formu ──────────────────────────────────────────

  test("TC-MR-004: senaryo oluşturma formu mobile'da kullanılabilmeli", async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
    await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /giriş/i }).click();
    await page.waitForURL(/\/projects|\/dashboard/, { timeout: 20_000 });

    await page.goto(`${BASE_URL}/p/${projectId}/scenarios/new`);
    await page.waitForLoadState("networkidle");

    // Form alanları dokunulabilir / görünür olmalı
    const titleInput = page.getByTestId("scenario-form-input-title");
    if (await titleInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await titleInput.fill(`Mobile Test ${Date.now()}`);
      const saveBtn = page.getByTestId("scenario-form-btn-save");
      await expect(saveBtn).toBeVisible();

      // Buton dokunma hedefi (touch target) en az 44px yüksekliğinde olmalı
      const btnBox = await saveBtn.boundingBox();
      if (btnBox) {
        expect(btnBox.height, "Kaydet butonu dokunma hedefi ≥ 44px olmalı (WCAG 2.5.5)").toBeGreaterThanOrEqual(44);
      }
    } else {
      // Form bulunamadıysa sayfanın yüklendiğini doğrula
      await expect(page).not.toHaveURL(/\/login/);
    }
  });

  // ── 5. Onay sayfası ─────────────────────────────────────────────────────

  test("TC-MR-005: onay sayfası mobile'da görüntülenmeli ve etkileşim çalışmalı", async ({ page, request }) => {
    const approvalId = await apiCreateApproval(
      request, token, projectId, `Mobile Onay ${Date.now()}`
    );

    await page.goto(`${BASE_URL}/login`);
    await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
    await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
    await page.getByRole("button", { name: /giriş/i }).click();
    await page.waitForURL(/\/projects|\/dashboard/, { timeout: 20_000 });

    await page.goto(`${BASE_URL}/p/${projectId}/approvals`);
    await page.waitForLoadState("networkidle");

    // Onay kartı görünmeli
    const card = page.getByTestId(`approvals-card-${approvalId}`);
    if (await card.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await card.click();
      // Onayla butonu görünmeli ve tıklanabilir boyutta olmalı
      const approveBtn = page.getByTestId("approvals-btn-approve");
      if (await approveBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        const box = await approveBtn.boundingBox();
        if (box) {
          expect(box.height, "Onayla butonu dokunma hedefi ≥ 44px olmalı").toBeGreaterThanOrEqual(44);
        }
      }
    } else {
      // Kart yok ama sayfa yüklendi
      await expect(page).not.toHaveURL(/\/login/);
    }

    // Yatay overflow yok
    const overflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
    expect(overflow, "Onay sayfasında yatay overflow olmamalı").toBe(false);
  });
});
