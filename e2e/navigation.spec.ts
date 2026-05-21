import { test, expect } from "@playwright/test";
import { loginAsAdmin, getAdminToken, apiCreateProject } from "./helpers/auth";

test.describe("Navigasyon ve Genel UI", () => {
  let projectId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    const token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `Nav Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("sidebar tüm menü öğelerini göstermeli", async ({ page }) => {
    await page.goto(`/p/${projectId}`);
    const sidebar = page.locator("[data-testid='sidebar-nav']");
    await expect(sidebar).toBeVisible();

    for (const label of [
      "Aktivite Monitörü",
      "Projeler",
      "Senaryo Oluşturucu",
      "Veri Merkezi",
      "Ayarlar",
    ]) {
      await expect(sidebar.getByText(label).first()).toBeVisible();
    }
  });

  test("proje özet sayfası yüklenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}`);
    await expect(page.getByText(/özet|senaryo|koşu/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("tema değiştirme çalışmalı", async ({ page }) => {
    await page.goto(`/p/${projectId}`);
    const themeBtn = page.locator("[data-testid='header-btn-theme']");
    // Tema butonu bu projenin varsayılan UI iskeletinde mevcut olmalı.
    // Eskiden `if (isVisible)` ile sessizce atlanıyordu — bu durumda UI
    // regression'ı da test yeşil dönüyordu. Artık buton bulunamazsa test
    // açıkça fail eder.
    await expect(themeBtn).toBeVisible({ timeout: 5_000 });

    // `html` elementindeki sınıf/veri-bayrağından hangi temanın aktif
    // olduğunu türet; tıklama sonrası bu değer değişmelidir.
    const themeSignature = async (): Promise<string> => {
      return page.evaluate(() => {
        const root = document.documentElement;
        return [
          root.classList.contains("dark") ? "class:dark" : "class:light",
          root.getAttribute("data-theme") ?? "",
          root.style.colorScheme ?? "",
        ].join("|");
      });
    };

    const before = await themeSignature();
    await themeBtn.click();
    // Tema butonu aynı tıkta state güncellemeli → polling ile doğrula,
    // sabit bir waitForTimeout kullanma (flake kaynağı).
    await expect
      .poll(themeSignature, { timeout: 5_000 })
      .not.toBe(before);

    const after = await themeSignature();
    await themeBtn.click();
    await expect.poll(themeSignature, { timeout: 5_000 }).not.toBe(after);
  });

  test("kullanıcı menüsü açılmalı", async ({ page }) => {
    await page.goto(`/p/${projectId}`);
    await page.locator("[data-testid='header-btn-user-menu']").click();
    await expect(page.locator("[data-testid='user-menu-link-profile']")).toBeVisible();
    // Logout UI'da link değil button olarak render ediliyor.
    await expect(page.locator("[data-testid='user-menu-btn-logout']")).toBeVisible();
  });

  test("logout işlemi login sayfasına yönlendirmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}`);
    await page.locator("[data-testid='header-btn-user-menu']").click();
    await page.locator("[data-testid='user-menu-btn-logout']").click();
    await expect(page).toHaveURL(/\/login|\/logout/, { timeout: 10_000 });
  });

  test("404 sayfası gösterilmeli", async ({ page }) => {
    await page.goto("/nonexistent-page-xyz");
    await expect(page.getByText(/404|bulunamadı|not found/i).first()).toBeVisible({ timeout: 10_000 });
  });

  test("profil sayfası yüklenmeli", async ({ page }) => {
    await page.goto("/profile");
    // PageHeader'ın data-testid prop'u şu an forward edilmediği için
    // sayfa root'undaki `profile-page` testid'sini kullanıyoruz.
    await expect(page.locator("[data-testid='profile-page']")).toBeVisible({ timeout: 10_000 });
  });

  test("analitik sayfası yüklenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/analytics`);
    await expect(page.getByText(/analitik|analytics|trend/i).first()).toBeVisible({ timeout: 10_000 });
  });
});
