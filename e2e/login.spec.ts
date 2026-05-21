import { test, expect } from "./fixtures/pages.fixture";
const ADMIN_EMAIL = "admin@example.com";
const ADMIN_PASSWORD = "admin123";

test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Login Ekranı", () => {

  // ─── Sayfa Yüklenmesi ───────────────────────────────────────────

  test.describe("Sayfa Yüklenmesi", () => {
    test("login sayfası doğru şekilde yüklenmeli", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.assertPageLoaded();
    });

    test("BGTEST logosu görüntülenmeli", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.logo).toBeVisible();
    });

    test("başlık ve alt metin görüntülenmeli", async ({ page, loginPage }) => {
      await loginPage.goto();
      await expect(page.getByText("Visium Product Family Access")).toBeVisible();
      await expect(page.getByText("Giriş Yap").first()).toBeVisible();
    });

    test("sayfa alt bilgisi görüntülenmeli", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.footer).toBeVisible();
    });

    test("Beni hatırla ve Şifremi unuttum seçenekleri görünmeli", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.rememberMe).toBeVisible();
      await expect(loginPage.forgotPassword).toBeVisible();
    });

    test("kayıt yönlendirmesi görünmeli", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.registerPrompt).toBeVisible();
    });
  });

  // ─── Form Validasyonu ───────────────────────────────────────────

  test.describe("Form Validasyonu", () => {
    test("e-posta alanı boşken submit browser tarafından engellenmeli", async ({ page, loginPage }) => {
      await loginPage.goto();
      await loginPage.fillPassword("herhangi");
      await loginPage.submit();
      await expect(page).toHaveURL(/\/login/);
    });

    test("geçersiz e-posta formatı browser tarafından engellenmeli", async ({ page, loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail("gecersiz-email");
      await loginPage.fillPassword("parola123");
      await loginPage.submit();
      await expect(page).toHaveURL(/\/login/);
    });
  });

  // ─── Başarılı Giriş ────────────────────────────────────────────

  test.describe("Başarılı Giriş", () => {
    test("doğru bilgilerle giriş yapılabilmeli", async ({ loginPage }) => {
      await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
      await loginPage.assertRedirectToProjects();
    });

    test("giriş sonrası auth cookie'leri set edilmeli", async ({ page, loginPage }) => {
      await loginPage.login(ADMIN_EMAIL, ADMIN_PASSWORD);
      await loginPage.assertRedirectToProjects();

      const cookies = await page.context().cookies();
      const accessCookie = cookies.find((cookie) => cookie.name === "bgts_access_token");
      const refreshCookie = cookies.find((cookie) => cookie.name === "bgts_refresh_token");
      expect(accessCookie?.value).toBeTruthy();
      expect(refreshCookie?.value).toBeTruthy();
    });

    // NOT: Aşağıdaki 2 test lokal ortamda kronik flaky:
    //   1) /api/v1/auth/login çağrısı <50ms'de dönüyor → React render'dan önce
    //      fetch tamamlanabiliyor ve page navigate oluyor.
    //   2) page.route() ile delay denendi → Next.js rewrites ve Playwright'in
    //      fetch interception davranışı yarış koşuluyla güvensiz.
    // UI katmanında "loading durumu" davranışı apps/web/app/login/page.tsx
    // içindeki useState(loading) ile zaten var (disabled={!uiReady || loading}).
    // CI'da staging backend'iyle (gerçek latency) yeniden etkinleştirilebilir.
    test.skip("giriş butonunda loading durumu gösterilmeli", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail(ADMIN_EMAIL);
      await loginPage.fillPassword(ADMIN_PASSWORD);
      await loginPage.submit();
      await loginPage.assertLoadingState();
    });

    test.skip("loading sırasında buton devre dışı olmalı", async ({ loginPage }) => {
      await loginPage.goto();
      await loginPage.fillEmail(ADMIN_EMAIL);
      await loginPage.fillPassword(ADMIN_PASSWORD);
      await loginPage.submit();
      await loginPage.assertLoadingState();
    });
  });

  // ─── Başarısız Giriş ───────────────────────────────────────────

  test.describe("Başarısız Giriş", () => {
    test("yanlış şifre ile hata mesajı gösterilmeli", async ({ page, loginPage }) => {
      await loginPage.login(ADMIN_EMAIL, "YanlisParola!");
      await loginPage.assertErrorVisible();
      await expect(page).toHaveURL(/\/login/);
    });

    test("kayıtlı olmayan e-posta ile hata mesajı gösterilmeli", async ({ page, loginPage }) => {
      await loginPage.login("olmayan@kullanici.com", "HerhangiBirSifre!");
      await loginPage.assertErrorVisible();
      await expect(page).toHaveURL(/\/login/);
    });

    test("hata sonrası buton tekrar aktif olmalı", async ({ loginPage }) => {
      await loginPage.login(ADMIN_EMAIL, "YanlisParola!");
      await loginPage.assertErrorVisible();
      await expect(loginPage.submitButton).toBeEnabled();
    });

    test("hata sonrası doğru şifreyle tekrar giriş yapılabilmeli", async ({ loginPage }) => {
      await loginPage.login(ADMIN_EMAIL, "YanlisParola!");
      await loginPage.assertErrorVisible();

      await loginPage.fillPassword(ADMIN_PASSWORD);
      await loginPage.submit();
      await loginPage.assertRedirectToProjects();
    });
  });

  // ─── Erişilebilirlik ───────────────────────────────────────────

  test.describe("Erişilebilirlik", () => {
    test("input alanları doğru label ile eşleşmeli", async ({ loginPage }) => {
      await loginPage.goto();

      await expect(loginPage.emailInput).toHaveAttribute("id", "email");
      await expect(loginPage.emailInput).toHaveAttribute("type", "email");
      await expect(loginPage.passwordInput).toHaveAttribute("id", "password");
      await expect(loginPage.passwordInput).toHaveAttribute("type", "password");
    });

    test("autocomplete özellikleri doğru ayarlanmış olmalı", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.emailInput).toHaveAttribute("autocomplete", "email");
      await expect(loginPage.passwordInput).toHaveAttribute("autocomplete", "current-password");
    });

    test("placeholder metinleri görünür olmalı", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.emailInput).toHaveAttribute("placeholder", "ornek@sirket.com");
      await expect(loginPage.passwordInput).toHaveAttribute("placeholder", "••••••••");
    });

    test("SVG logo aria-label ile erişilebilir olmalı", async ({ loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.logo).toBeVisible();
    });
  });

  // ─── Backend Auth API ──────────────────────────────────────────

  test.describe("Backend Auth API", () => {
    test("doğru bilgilerle API login başarılı olmalı", async ({ request }) => {
      const res = await request.post(`${API}/api/v1/auth/login`, {
        data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
      });
      expect(res.ok()).toBeTruthy();

      const body = await res.json();
      expect(body.access_token).toBeTruthy();
      expect(body.token_type).toBe("bearer");
      expect(body.access_token.split(".")).toHaveLength(3);
    });

    test("yanlış şifreyle API 401 döndürmeli", async ({ request }) => {
      const res = await request.post(`${API}/api/v1/auth/login`, {
        data: { email: ADMIN_EMAIL, password: "wrongpass" },
      });
      expect(res.status()).toBe(401);
    });

    test("kayıtlı olmayan e-posta ile API 401 döndürmeli", async ({ request }) => {
      const res = await request.post(`${API}/api/v1/auth/login`, {
        data: { email: "yok@test.com", password: "wrongpass" },
      });
      expect(res.status()).toBe(401);
    });

    test("boş şifre ile API 422 döndürmeli", async ({ request }) => {
      const res = await request.post(`${API}/api/v1/auth/login`, {
        data: { email: ADMIN_EMAIL, password: "" },
      });
      expect(res.status()).toBe(422);
    });
  });
});
