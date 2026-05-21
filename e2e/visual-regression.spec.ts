/**
 * Görsel Regresyon — Playwright `toHaveScreenshot` baseline.
 *
 * Amaç
 *   Kritik ekranların görsel olarak bozulmadığını yakalamak. Her test ilk
 *   kez çalıştığında baseline (snapshot) üretir; sonraki koşumlar pixel
 *   karşılaştırması yapar.
 *
 * Baseline dizin yapısı (Playwright otomatik yönetir):
 *   e2e/visual-regression.spec.ts-snapshots/
 *     ├─ login-desktop-chromium-darwin.png
 *     ├─ dashboard-desktop-chromium-darwin.png
 *     └─ ...
 *
 * Baseline nasıl güncellenir?
 *   - Local:   npx playwright test e2e/visual-regression.spec.ts --update-snapshots
 *   - CI:      yeni baseline'ı üretip commit'leyin (kasıtlı UI değişiminde).
 *
 * Diff artefaktları `reports/e2e-artifacts/` altına düşer; HTML rapor "Image
 * diff" sekmesinde fark bölgelerini vurgular.
 *
 * NOT: Baseline'lar platform/browser'a göre farklıdır. CI'da yalnızca
 *   linux-chromium baseline'ları güvenilir; developer lokalde `--update` ile
 *   yeni baseline üretmek ister, bunu **commit etmemeli** (aksi halde CI
 *   kırılır). `.gitignore` bunu önlemek için darwin/win32 baseline'larını
 *   yok sayar.
 */

import { test, expect } from "@playwright/test";

// Varsayılan görsel karşılaştırma eşiği — küçük font rendering farkları
// için %1 piksel toleransı. UI değişikliğinde baseline'ı güncelleyin.
const VISUAL_DEFAULTS = {
  maxDiffPixelRatio: 0.01,
  threshold: 0.2,
  animations: "disabled" as const,
};

test.describe("Visual Regression — kritik ekranlar", () => {
  // Anonim login sayfası — en kritik entry point
  test.describe("anonim sayfalar", () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test("login sayfası görsel baseline", async ({ page }) => {
      await page.goto("/login");
      // Animasyonlar bitmeden screenshot flaky olur; form'un tam render
      // olmasını bekle.
      await expect(page.locator("[data-testid='login-form'], form").first()).toBeVisible();
      await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});
      await expect(page).toHaveScreenshot("login.png", VISUAL_DEFAULTS);
    });
  });

  // Authenticated ekranlar — admin storageState otomatik yüklenir
  test.describe("authenticated ana ekranlar", () => {
    test("projeler listesi baseline", async ({ page }) => {
      await page.goto("/");
      await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});
      // Sidebar + ana içerik render oldu mu doğrula
      await expect(page.locator("[data-testid='sidebar-nav']")).toBeVisible({
        timeout: 10_000,
      });
      await expect(page).toHaveScreenshot("projects-list.png", {
        ...VISUAL_DEFAULTS,
        // Dinamik zaman damgası/sayaç gibi alanları maskele — snapshot
        // tüketilebilir olsun diye. Proje kart sayısı ve isimleri de
        // zaman içinde değişir; tüm ana listeyi maskeliyoruz.
        mask: [
          page.locator("[data-testid='project-card-updated-at']"),
          page.locator("[data-testid='last-run-badge']"),
        ],
      });
    });
  });
});
