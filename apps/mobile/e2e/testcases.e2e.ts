describe('Test Cases Management', () => {
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

  beforeEach(async () => {
    await device.reloadReactNative();
  });

  it('should navigate to test cases', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await expect(element(by.id('test-cases-screen'))).toBeVisible();
  });

  it('should display test cases list', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await expect(element(by.id('test-case-list'))).toBeVisible();
  });

  it('should create new test case', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('create-button')).multiTap();

    await element(by.id('test-case-name-input')).typeText('Login Test Case');
    await element(by.id('test-case-description-input')).typeText('Verify user login flow');
    await element(by.id('save-button')).multiTap();

    await waitFor(element(by.text('Login Test Case')))
      .toBeVisible()
      .withTimeout(5000);
  });

  it('should search test cases', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('search-input')).typeText('Login');

    await expect(element(by.id('test-case-list'))).toBeVisible();
  });

  it('should filter test cases by status', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('filter-button')).multiTap();
    await element(by.text('Failed')).multiTap();
    await element(by.id('apply-filter-button')).multiTap();

    await expect(element(by.id('test-case-list'))).toBeVisible();
  });

  it('should view test case details', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();

    await expect(element(by.id('test-case-detail-screen'))).toBeVisible();
  });

  it('should edit test case', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).multiTap();
    await element(by.id('edit-button')).multiTap();

    await element(by.id('test-case-name-input')).clearText();
    await element(by.id('test-case-name-input')).typeText('Updated Test Case');
    await element(by.id('save-button')).multiTap();

    await waitFor(element(by.text('Updated Test Case')))
      .toBeVisible()
      .withTimeout(5000);
  });

  it('should delete test case', async () => {
    await element(by.id('test-cases-tab')).multiTap();
    await element(by.id('test-case-card-0')).longPress();
    await element(by.id('delete-button')).multiTap();
    await element(by.text('Delete')).multiTap();

    // Verify deletion
    await expect(element(by.id('test-case-list'))).toBeVisible();
  });
});
