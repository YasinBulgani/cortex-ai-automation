import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * TestCasePage - Page Object for test case management
 * Handles: create, list, edit, delete, run, navigate
 *
 * Critical paths:
 * - Admin creates test case (create-test-case workflow)
 * - Tester runs test case (tester-workflow)
 * - Manager views test case analytics
 */
export interface TestStep {
  action: "click" | "fill" | "wait" | "verify" | "screenshot";
  selector?: string;
  value?: string;
  expected?: string;
  timeout?: number;
}

export interface CreateTestCaseInput {
  title: string;
  description: string;
  steps: TestStep[];
  tags?: string[];
  assignee?: string;
  priority?: "low" | "medium" | "high" | "critical";
}

export class TestCasePage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  // Page-level
  readonly testCasesHeading = '[data-testid="test-cases-heading"]';
  readonly testCasesPageContainer = '[data-testid="test-cases-page"]';
  readonly newTestCaseBtn = '[data-testid="new-test-case-btn"]';
  readonly testCaseList = '[data-testid="test-case-list"]';
  readonly testCaseItem = '[data-testid="test-case-item"]';
  readonly emptyState = '[data-testid="test-cases-empty-state"]';

  // Create/Edit modal
  readonly testCaseModal = '[data-testid="test-case-modal"]';
  readonly testCaseTitleInput = '[data-testid="test-case-form-title"]';
  readonly testCaseDescInput = '[data-testid="test-case-form-description"]';
  readonly testCasePrioritySelect = '[data-testid="test-case-form-priority"]';
  readonly testCaseTagsInput = '[data-testid="test-case-form-tags"]';
  readonly testCaseAssigneeSelect = '[data-testid="test-case-form-assignee"]';
  readonly addStepBtn = '[data-testid="test-case-add-step"]';
  readonly stepContainer = '[data-testid="test-case-steps"]';
  readonly stepItem = '[data-testid="test-case-step-item"]';
  readonly saveTestCaseBtn = '[data-testid="test-case-form-save"]';
  readonly cancelTestCaseBtn = '[data-testid="test-case-form-cancel"]';
  readonly testCaseFormError = '[data-testid="test-case-form-error"]';

  // Step editor
  readonly stepActionSelect = '[data-testid="step-form-action"]';
  readonly stepSelectorInput = '[data-testid="step-form-selector"]';
  readonly stepValueInput = '[data-testid="step-form-value"]';
  readonly stepExpectedInput = '[data-testid="step-form-expected"]';
  readonly removeStepBtn = '[data-testid="step-remove-btn"]';

  // Test case item actions
  readonly deleteTestCaseBtn = '[data-testid="test-case-delete-btn"]';
  readonly editTestCaseBtn = '[data-testid="test-case-edit-btn"]';
  readonly runTestCaseBtn = '[data-testid="test-case-run-btn"]';
  readonly confirmDeleteBtn = '[data-testid="confirm-delete"]';
  readonly confirmDeleteModal = '[data-testid="delete-confirm-modal"]';

  // Test case detail page
  readonly testCaseDetailContainer = '[data-testid="test-case-detail"]';
  readonly testCaseTitle = '[data-testid="test-case-title"]';
  readonly testCaseDescription = '[data-testid="test-case-description"]';
  readonly testCaseStepsSection = '[data-testid="test-case-steps-section"]';
  readonly runHistorySection = '[data-testid="test-case-run-history"]';

  // Search & filters
  readonly testCaseSearch = '[data-testid="test-case-search"]';
  readonly filterButton = '[data-testid="test-case-filter-btn"]';
  readonly statusFilter = '[data-testid="filter-status"]';
  readonly priorityFilter = '[data-testid="filter-priority"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to test cases list page
   */
  async goto() {
    await super.goto("/test-cases");
    await this.waitForPageReady();
  }

  /**
   * Navigate to test cases within a project
   */
  async gotoProject(projectId: string) {
    await super.goto(`/projects/${projectId}/test-cases`);
    await this.waitForPageReady();
  }

  /**
   * Check if test cases page is loaded
   */
  async isLoaded(): Promise<boolean> {
    return this.isVisible(this.testCasesPageContainer);
  }

  /**
   * Create a new test case via UI
   *
   * @param input - Test case details
   */
  async createTestCase(input: CreateTestCaseInput): Promise<void> {
    // 1. Click new test case button
    await this.click(this.newTestCaseBtn);

    // 2. Wait for modal
    await this.waitFor(this.testCaseModal, 10000);

    // 3. Fill basic fields
    await this.fillInput(this.testCaseTitleInput, input.title);
    await this.fillInput(this.testCaseDescInput, input.description);

    if (input.priority) {
      await this.page.selectOption(this.testCasePrioritySelect, input.priority);
    }

    if (input.tags && input.tags.length > 0) {
      // Add tags (might be multi-select)
      for (const tag of input.tags) {
        await this.fillInput(this.testCaseTagsInput, tag);
        await this.page.keyboard.press("Enter");
      }
    }

    if (input.assignee) {
      await this.page.selectOption(this.testCaseAssigneeSelect, input.assignee);
    }

    // 4. Add steps
    if (input.steps && input.steps.length > 0) {
      for (const step of input.steps) {
        await this.addStep(step);
      }
    }

    // 5. Save
    await this.click(this.saveTestCaseBtn);

    // Wait for modal to close
    await this.page.waitForSelector(this.testCaseModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Add a test step to the test case
   *
   * @param step - Step details
   */
  private async addStep(step: TestStep): Promise<void> {
    // Click add step button
    await this.click(this.addStepBtn);

    // Wait for step form
    await this.page.waitForTimeout(300); // Brief wait for form to appear

    // Fill step details
    await this.page.selectOption(this.stepActionSelect, step.action);

    if (step.selector) {
      await this.fillInput(this.stepSelectorInput, step.selector);
    }

    if (step.value) {
      await this.fillInput(this.stepValueInput, step.value);
    }

    if (step.expected) {
      await this.fillInput(this.stepExpectedInput, step.expected);
    }

    // Note: The step might be auto-added on blur or via submit button
    // Adjust based on actual UI
  }

  /**
   * Get test case item by title
   *
   * @param title - Test case title to find
   * @returns Test case item locator or null
   */
  async getTestCaseByTitle(title: string) {
    const items = this.page.locator(this.testCaseItem);
    const count = await items.count();

    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const text = await item.textContent();
      if (text?.includes(title)) {
        return item;
      }
    }
    return null;
  }

  /**
   * Open a test case by title
   *
   * @param title - Test case title to open
   */
  async openTestCase(title: string): Promise<void> {
    const item = await this.getTestCaseByTitle(title);
    if (!item) {
      throw new Error(`Test case not found: ${title}`);
    }

    await item.click();
    await this.waitForPageReady();
  }

  /**
   * Delete a test case by title
   *
   * @param title - Test case title to delete
   */
  async deleteTestCase(title: string): Promise<void> {
    const item = await this.getTestCaseByTitle(title);
    if (!item) {
      throw new Error(`Test case not found: ${title}`);
    }

    // Click delete button
    const deleteBtn = item.locator(this.deleteTestCaseBtn);
    await deleteBtn.click();

    // Confirm deletion
    await this.waitFor(this.confirmDeleteModal, 5000);
    await this.click(this.confirmDeleteBtn);

    // Wait for update
    await this.page.waitForSelector(this.confirmDeleteModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Run a test case
   */
  async runTestCase(): Promise<void> {
    const runBtn = this.page.locator(this.runTestCaseBtn);
    if (await runBtn.count() === 0) {
      throw new Error("Run button not found");
    }

    await runBtn.click();
    await this.waitForPageReady();
  }

  /**
   * Edit a test case
   *
   * @param title - Test case title to edit
   * @param updates - Fields to update
   */
  async editTestCase(
    title: string,
    updates: Partial<CreateTestCaseInput>
  ): Promise<void> {
    const item = await this.getTestCaseByTitle(title);
    if (!item) {
      throw new Error(`Test case not found: ${title}`);
    }

    // Click edit button
    const editBtn = item.locator(this.editTestCaseBtn);
    await editBtn.click();

    // Wait for modal
    await this.waitFor(this.testCaseModal, 10000);

    // Update fields if provided
    if (updates.title) {
      await this.page.fill(this.testCaseTitleInput, updates.title);
    }
    if (updates.description) {
      await this.page.fill(this.testCaseDescInput, updates.description);
    }
    if (updates.priority) {
      await this.page.selectOption(this.testCasePrioritySelect, updates.priority);
    }

    // Save
    await this.click(this.saveTestCaseBtn);

    // Wait for update
    await this.page.waitForSelector(this.testCaseModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Search for test cases
   *
   * @param query - Search query
   */
  async searchTestCases(query: string): Promise<void> {
    await this.fillInput(this.testCaseSearch, query);
    await this.page.waitForTimeout(500); // Wait for debounce
    await this.waitForPageReady();
  }

  /**
   * Get list of all visible test cases
   */
  async getTestCaseList(): Promise<string[]> {
    const items = this.page.locator(this.testCaseItem);
    const count = await items.count();
    const testCases: string[] = [];

    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const text = await item.textContent();
      if (text) {
        testCases.push(text.trim());
      }
    }

    return testCases;
  }

  /**
   * Get form validation error
   */
  async getFormError(): Promise<string> {
    const errorEl = this.page.locator(this.testCaseFormError);
    if (await errorEl.isVisible()) {
      return this.getText(this.testCaseFormError);
    }
    return "";
  }

  /**
   * Check if empty state is shown
   */
  async hasEmptyState(): Promise<boolean> {
    return this.isVisible(this.emptyState);
  }

  /**
   * Check if test case exists
   */
  async testCaseExists(title: string): Promise<boolean> {
    const item = await this.getTestCaseByTitle(title);
    return item !== null;
  }

  /**
   * Get test case detail view title
   */
  async getDetailTitle(): Promise<string> {
    return this.getText(this.testCaseTitle);
  }

  /**
   * Get test case detail view description
   */
  async getDetailDescription(): Promise<string> {
    return this.getText(this.testCaseDescription);
  }
}
