import { test, expect } from '@playwright/test';

const invalidJwt = 'invalid.jwt.token';

test.describe('Geçersiz JWT ile Kullanıcı Silme', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/api/v1/api-testing/projects/{project_id}/environments');
    await page.getByRole('button', { name: 'Giriş' }).click();
    await page.fill('#email-input', 'admin@test.com');
    await page.fill('#password-input', 'Admin123!');
    await page.click('#login-button');
  });

  test('Geçersiz JWT ile kullanıcı silmeye denendiğinde 401 Unauthorized döner', async ({ page }) => {
    const response = await page.request('DELETE', '/api/v1/api-testing/projects/{project_id}/environments/{env_id}/users/{user_id}', {
      headers: { 'Authorization': `Bearer ${invalidJwt}` }
    });
    expect(response.status()).toBe(401);
  });
});