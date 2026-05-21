import { test } from "./fixtures/pages.fixture";
import { getAdminToken, apiCreateProject, loginAsAdmin } from "./helpers/auth";

test.describe.serial("BDD Senaryo Üretimi", () => {
  let projectId: string;

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    const token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `BDD Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("BDD üretim sayfası yüklenmeli", async ({ page, bddGeneratePage }) => {
    await page.goto(`/p/${projectId}/scenarios/generate`);
    await bddGeneratePage.assertPageLoaded();
  });

  test("kısa metin için hata mesajı gösterilmeli", async ({ page, bddGeneratePage }) => {
    await page.goto(`/p/${projectId}/scenarios/generate`);
    await bddGeneratePage.fillAnalysis("Kısa");
    await bddGeneratePage.generate();
    await bddGeneratePage.assertMinLengthErrorVisible();
  });

  test("analiz metni ile üretim başlatılabilmeli", async ({ page, bddGeneratePage }) => {
    await page.goto(`/p/${projectId}/scenarios/generate`);
    await bddGeneratePage.generateFromText(
      "Kullanıcı sisteme e-posta ve şifre ile giriş yapabilmelidir. Başarısız giriş denemeleri 5'ten fazla ise hesap kilitlenir. Şifre en az 8 karakter olmalıdır."
    );
    await bddGeneratePage.assertGenerationStarted();
  });
});
