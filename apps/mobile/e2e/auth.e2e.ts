describe('Authentication Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should show login screen on app start', async () => {
    await expect(element(by.text('Welcome to Neurex'))).toBeVisible();
    await expect(element(by.id('email-input'))).toBeVisible();
    await expect(element(by.id('password-input'))).toBeVisible();
  });

  it('should validate email format', async () => {
    await element(by.id('email-input')).typeText('invalid-email');
    await element(by.id('login-button')).multiTap();

    await expect(element(by.text(/invalid email/i))).toBeVisible();
  });

  it('should complete login flow', async () => {
    await element(by.id('email-input')).typeText('test@example.com');
    await element(by.id('password-input')).typeText('SecurePass123');
    await element(by.id('login-button')).multiTap();

    // Wait for navigation to dashboard
    await waitFor(element(by.id('dashboard-screen')))
      .toBeVisible()
      .withTimeout(5000);
  });

  it('should enable biometric login if available', async () => {
    // Skip if biometric not available
    try {
      await expect(element(by.id('biometric-button'))).toBeVisible();
    } catch {
      // Biometric not available on this device
    }
  });

  it('should logout successfully', async () => {
    // Navigate to settings
    await element(by.id('settings-tab')).multiTap();

    // Tap logout
    await element(by.id('logout-button')).multiTap();

    // Confirm logout
    await element(by.text('Logout')).multiTap();

    // Should return to login screen
    await waitFor(element(by.id('login-screen')))
      .toBeVisible()
      .withTimeout(5000);
  });
});
