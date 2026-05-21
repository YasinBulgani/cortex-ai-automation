import { test, expect } from '@playwright/test';

// Başarılı çıkış testi
test('geçerli kimlik ile giriş yapabilmeli', async ({ page }) => {
  await page.goto('/dashboard');
  await page.getByTestId('logout-button').click();
  await expect(page).toHaveURL('/login');
  await expect(page.getByText('Giriş Yap')).toBeVisible();
});