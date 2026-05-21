import { test, expect } from '@playwright/test';

const validJwt = 'valid.jwt.token';

test.describe('Kullanıcı Silme (Happy Path)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/api/v1/api-testing/projects/{project_id}/environments');
    await page.getByRole('button', { name: 'Giriş' }).click();
    await page.fill('#email-input', 'admin@test.com');
    await page.fill('#password-input', 'Admin123!');
    await page.click('#login-button');
  });

  test('Kullanıcı başarıyla silinir ve 204 No Content döner', async ({ page }) => {
    const response = await page.request('DELETE', '/api/v1/api-testing/projects/{project_id}/environments/{env_id}/users/{user_id}', {
      headers: { 'Authorization': `Bearer ${validJwt}` }
    });
    expect(response.status()).toBe(204);
  });
});