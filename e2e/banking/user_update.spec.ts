import { test, expect } from '@playwright/test';

const validJwt = 'valid.jwt.token';
const userUpdateData = {
  name: 'New Name',
  email: 'new.email@example.com'
};

test.describe('Kullanıcı Bilgilerini Güncelleme (Happy Path)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/api/v1/api-testing/projects/{project_id}/environments');
    await page.getByRole('button', { name: 'Giriş' }).click();
    await page.fill('#email-input', 'admin@test.com');
    await page.fill('#password-input', 'Admin123!');
    await page.click('#login-button');
  });

  test('Kullanıcı bilgileri başarıyla güncellendi ve 200 OK döner', async ({ page }) => {
    await page.goto('/api/v1/api-testing/projects/{project_id}/environments/{env_id}/users/{user_id}');
    await page.fill('#name-input', userUpdateData.name);
    await page.fill('#email-input', userUpdateData.email);
    await page.click('#update-button');
    const response = await page.request('POST', '/api/v1/api-testing/projects/{project_id}/environments/{env_id}/users/{user_id}', {
      headers: { 'Authorization': `Bearer ${validJwt}` },
      data: userUpdateData
    });
    expect(response.status()).toBe(200);
  });
});