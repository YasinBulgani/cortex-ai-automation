import { test, expect } from '@playwright/test';

const invalidEmail = '';
const validPassword = 'Admin123!';

// Boş e-posta ile giriş denemesi
test('boş e-posta ile giriş denemesi', async ({ page }) => {
  await page.goto('/login');
  await page.getByTestId('email-input').fill(invalidEmail);
  await page.getByTestId('password-input').fill(validPassword);
  await page.getByRole('button', { name: 'Giriş' }).click();
  await expect(page).toHaveURL('/login');
  await expect(page.getByText('Validation Error')).toBeVisible();
});