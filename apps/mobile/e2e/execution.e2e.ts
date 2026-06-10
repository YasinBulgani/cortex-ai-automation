describe('Test Execution Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
    // Login first
    await element(by.id('email-input')).typeText('test@example.com');
    await element(by.id('password-input')).typeText('SecurePass123');
    await element(by.id('login-button')).multiTap();
    await waitFor(element(by.id('dashboard-screen')))
      .toBeVisible()
      .withTimeout(5000);
  });

  it('should start test execution', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    await waitFor(element(by.id('execution-screen')))
      .toBeVisible()
      .withTimeout(5000);
  });

  it('should display execution progress', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    await expect(element(by.id('execution-progress'))).toBeVisible();
    await expect(element(by.id('progress-bar'))).toBeVisible();
  });

  it('should show execution logs', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    // Wait for logs to appear
    await waitFor(element(by.id('execution-logs')))
      .toBeVisible()
      .withTimeout(3000);
  });

  it('should pause execution', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    // Click pause button
    await element(by.id('pause-button')).multiTap();

    await expect(element(by.text(/paused/i))).toBeVisible();
  });

  it('should stop execution', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    // Click stop button
    await element(by.id('stop-button')).multiTap();

    await waitFor(element(by.text(/stopped/i)))
      .toBeVisible()
      .withTimeout(3000);
  });

  it('should display execution results', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    // Wait for execution to complete
    await waitFor(element(by.id('execution-result-screen')))
      .toBeVisible()
      .withTimeout(10000);

    await expect(element(by.id('result-summary'))).toBeVisible();
  });

  it('should show execution statistics', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('run-button')).multiTap();

    // Wait for execution to complete
    await waitFor(element(by.id('execution-result-screen')))
      .toBeVisible()
      .withTimeout(10000);

    await expect(element(by.id('passed-count'))).toBeVisible();
    await expect(element(by.id('failed-count'))).toBeVisible();
    await expect(element(by.id('duration-display'))).toBeVisible();
  });
});
