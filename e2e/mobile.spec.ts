/**
 * Visium Farm E2E Tests
 * TC-VF-001..TC-VF-008
 *
 * Covered:
 *   - Mobil test sayfası yüklenmesi
 *   - Cihaz kartlarının görüntülenmesi
 *   - Platform tab filtresi (iOS / Android)
 *   - API üzerinden mobil koşum oluşturma
 *   - Koşum listesinde iOS/Android badge'i
 *   - Koşum listesinde platform filtre tab'ları
 *   - Mobil Geçmiş sayfası navigasyonu
 *   - Mobil Geçmiş: cihaza göre gruplama toggle'ı
 */

import { test, expect } from "@playwright/test";
import {
  loginAsAdmin,
  getAdminToken,
  apiCreateProject,
  apiCreateScenario,
} from "./helpers/auth";
import { API_BASE } from "./config/runtime";

const API = API_BASE;

// ── Helpers ────────────────────────────────────────────────────────────────────

async function apiCreateMobileExecution(
  request: Parameters<typeof getAdminToken>[0],
  token: string,
  projectId: string,
  platform: "ios" | "android",
  deviceName: string
): Promise<string> {
  const res = await request.post(
    `${API}/api/v1/tspm/projects/${projectId}/executions`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        name: `${platform.toUpperCase()} E2E ${Date.now()}`,
        platform,
        device_name: deviceName,
        scenario_ids: [],
      },
    }
  );
  const body = await res.json();
  return body.id;
}

// ── Test Suite ─────────────────────────────────────────────────────────────────

test.describe.serial("Visium Farm", () => {
  let projectId: string;
  let token: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(
      request,
      token,
      `Visium E2E ${Date.now()}`
    );
    await apiCreateScenario(request, token, projectId, "Mobil Senaryo A");
    await apiCreateScenario(request, token, projectId, "Mobil Senaryo B");
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  // TC-VF-001
  test("mobil test sayfası yüklenmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/mobile`);
    await expect(page.getByTestId("mobile-page")).toBeVisible({ timeout: 10_000 });
  });

  // TC-VF-002
  test("Visium Farm sayfasında cihaz kartları görünmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/mobile`);
    // DeviceCard bileşeni data-testid="device-card-*" kullanıyor
    await expect(
      page.locator("[data-testid^='device-card-']").first()
    ).toBeVisible({ timeout: 10_000 });
  });

  // TC-VF-003
  test("sidebar'da Visium Farm linki görünmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/scenarios`);
    const link = page.getByRole("link", { name: /visium farm/i });
    await expect(link).toBeVisible({ timeout: 5_000 });
    await link.click();
    await expect(page).toHaveURL(/\/mobile$/);
  });

  // TC-VF-004
  test("sidebar'da Mobil Geçmiş linki görünmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/scenarios`);
    const link = page.getByRole("link", { name: /mobil geçmiş/i });
    await expect(link).toBeVisible({ timeout: 5_000 });
    await link.click();
    await expect(page).toHaveURL(/\/mobile\/history$/);
  });

  // TC-VF-005
  test("execution listesinde platform tab bar görünmeli", async ({ page }) => {
    await page.goto(`/p/${projectId}/executions`);
    await expect(page.getByRole("button", { name: /tümü/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /masaüstü/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /ios/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /android/i })).toBeVisible();
  });

  // TC-VF-006
  test("iOS mobile execution oluşturulunca listede badge görünmeli", async ({
    page,
    playwright,
  }) => {
    const request = await playwright.request.newContext();
    await apiCreateMobileExecution(request, token, projectId, "ios", "iPhone 14");
    await request.dispose();

    await page.goto(`/p/${projectId}/executions`);
    // iOS badge bekleniyor
    await expect(
      page.locator("span", { hasText: "iOS" }).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  // TC-VF-007
  test("iOS platform tab filtresi sadece iOS koşumları göstermeli", async ({
    page,
    playwright,
  }) => {
    const request = await playwright.request.newContext();
    await apiCreateMobileExecution(request, token, projectId, "ios", "iPhone 15 Pro");
    await apiCreateMobileExecution(request, token, projectId, "android", "Pixel 7 Pro");
    await request.dispose();

    await page.goto(`/p/${projectId}/executions`);
    await page.getByRole("button", { name: /^🍎\s*ios$/i }).click();

    // Sayfada Android badge olmamalı
    const androidBadges = page.locator("span", { hasText: "Android" });
    await expect(androidBadges).toHaveCount(0, { timeout: 5_000 });
  });

  // TC-VF-008
  test("Mobil Geçmiş sayfası yüklenmeli ve stat kartları görünmeli", async ({
    page,
    playwright,
  }) => {
    const request = await playwright.request.newContext();
    await apiCreateMobileExecution(request, token, projectId, "ios", "iPad Pro");
    await apiCreateMobileExecution(request, token, projectId, "android", "Pixel 6a");
    await request.dispose();

    await page.goto(`/p/${projectId}/mobile/history`);
    await expect(page.getByTestId("mobile-history-page")).toBeVisible({ timeout: 10_000 });

    // Stat kartları
    await expect(page.getByText(/toplam koşum/i)).toBeVisible();
    await expect(page.getByText(/ios/i).first()).toBeVisible();
    await expect(page.getByText(/android/i).first()).toBeVisible();
  });

  // TC-VF-009 — cihaza göre gruplama toggle'ı
  test("Mobil Geçmiş'te cihaza göre gruplama toggle çalışmalı", async ({
    page,
    playwright,
  }) => {
    const request = await playwright.request.newContext();
    await apiCreateMobileExecution(request, token, projectId, "ios", "iPhone 14");
    await request.dispose();

    await page.goto(`/p/${projectId}/mobile/history`);
    await expect(page.getByTestId("mobile-history-page")).toBeVisible({ timeout: 10_000 });

    const toggleBtn = page.getByRole("button", { name: /cihaza göre grupla/i });
    await expect(toggleBtn).toBeVisible({ timeout: 5_000 });
    await toggleBtn.click();

    // Grup başlığı görünmeli (cihaz adı veya platform)
    await expect(
      page.locator("text=/iPhone|Pixel|iPad|Samsung/i").first()
    ).toBeVisible({ timeout: 5_000 });
  });
});
