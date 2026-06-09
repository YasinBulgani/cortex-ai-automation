import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * DefectPage - Page Object for defect management
 * Handles: create, list, comment, assign, close
 *
 * Critical paths:
 * - Tester creates defect from test result
 * - Developer assigns to self
 * - Manager tracks defect metrics
 */

export interface CreateDefectInput {
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  category?: string;
  assignee?: string;
  linkedTestCaseId?: string;
}

export interface DefectDetail {
  id: string;
  title: string;
  status: string;
  severity: string;
  assignee: string;
  createdBy: string;
  createdAt: string;
  comments: number;
}

export class DefectPage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  // Page-level
  readonly defectsHeading = '[data-testid="defects-heading"]';
  readonly defectsPageContainer = '[data-testid="defects-page"]';
  readonly newDefectBtn = '[data-testid="new-defect-btn"]';
  readonly defectList = '[data-testid="defect-list"]';
  readonly defectItem = '[data-testid="defect-item"]';
  readonly emptyState = '[data-testid="defects-empty-state"]';

  // Create/Edit modal
  readonly defectModal = '[data-testid="defect-modal"]';
  readonly defectTitleInput = '[data-testid="defect-form-title"]';
  readonly defectDescInput = '[data-testid="defect-form-description"]';
  readonly defectSeveritySelect = '[data-testid="defect-form-severity"]';
  readonly defectCategorySelect = '[data-testid="defect-form-category"]';
  readonly defectAssigneeSelect = '[data-testid="defect-form-assignee"]';
  readonly defectLinkedTestSelect = '[data-testid="defect-form-linked-test"]';
  readonly saveDefectBtn = '[data-testid="defect-form-save"]';
  readonly cancelDefectBtn = '[data-testid="defect-form-cancel"]';
  readonly defectFormError = '[data-testid="defect-form-error"]';

  // Defect item actions
  readonly deleteDefectBtn = '[data-testid="defect-delete-btn"]';
  readonly editDefectBtn = '[data-testid="defect-edit-btn"]';
  readonly confirmDeleteBtn = '[data-testid="confirm-delete"]';
  readonly confirmDeleteModal = '[data-testid="delete-confirm-modal"]';

  // Defect detail page
  readonly defectDetailContainer = '[data-testid="defect-detail"]';
  readonly defectDetailTitle = '[data-testid="defect-detail-title"]';
  readonly defectDetailStatus = '[data-testid="defect-detail-status"]';
  readonly defectDetailSeverity = '[data-testid="defect-detail-severity"]';
  readonly defectDetailAssignee = '[data-testid="defect-detail-assignee"]';
  readonly defectDetailDescription = '[data-testid="defect-detail-description"]';
  readonly defectLinkedTest = '[data-testid="defect-linked-test"]';

  // Status & Assignment
  readonly statusSelect = '[data-testid="defect-status-select"]';
  readonly assigneeSelect = '[data-testid="defect-assignee-select"]';
  readonly severitySelect = '[data-testid="defect-severity-select"]';
  readonly assignToMeBtn = '[data-testid="assign-to-me-btn"]';

  // Comments
  readonly commentSection = '[data-testid="defect-comments"]';
  readonly commentInput = '[data-testid="comment-input"]';
  readonly commentSubmitBtn = '[data-testid="comment-submit"]';
  readonly commentItem = '[data-testid="comment-item"]';
  readonly commentList = '[data-testid="comment-list"]';

  // Filters & Search
  readonly defectSearch = '[data-testid="defect-search"]';
  readonly filterButton = '[data-testid="defect-filter-btn"]';
  readonly statusFilter = '[data-testid="filter-status"]';
  readonly severityFilter = '[data-testid="filter-severity"]';
  readonly assigneeFilter = '[data-testid="filter-assignee"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to defects list page
   */
  async goto() {
    await super.goto("/defects");
    await this.waitForPageReady();
  }

  /**
   * Navigate to defects within a project
   */
  async gotoProject(projectId: string) {
    await super.goto(`/projects/${projectId}/defects`);
    await this.waitForPageReady();
  }

  /**
   * Check if defects page is loaded
   */
  async isLoaded(): Promise<boolean> {
    return this.isVisible(this.defectsPageContainer);
  }

  /**
   * Create a new defect
   *
   * @param input - Defect details
   */
  async createDefect(input: CreateDefectInput): Promise<void> {
    // Click new defect button
    await this.click(this.newDefectBtn);

    // Wait for modal
    await this.waitFor(this.defectModal, 10000);

    // Fill form
    await this.fillInput(this.defectTitleInput, input.title);
    await this.fillInput(this.defectDescInput, input.description);
    await this.page.selectOption(this.defectSeveritySelect, input.severity);

    if (input.category) {
      await this.page.selectOption(this.defectCategorySelect, input.category);
    }

    if (input.assignee) {
      await this.page.selectOption(this.defectAssigneeSelect, input.assignee);
    }

    if (input.linkedTestCaseId) {
      await this.page.selectOption(this.defectLinkedTestSelect, input.linkedTestCaseId);
    }

    // Save
    await this.click(this.saveDefectBtn);

    // Wait for modal to close
    await this.page.waitForSelector(this.defectModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Get defect item by title
   */
  async getDefectByTitle(title: string) {
    const items = this.page.locator(this.defectItem);
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
   * Open a defect by title
   */
  async openDefect(title: string): Promise<void> {
    const item = await this.getDefectByTitle(title);
    if (!item) {
      throw new Error(`Defect not found: ${title}`);
    }

    await item.click();
    await this.waitForPageReady();
  }

  /**
   * Delete a defect by title
   */
  async deleteDefect(title: string): Promise<void> {
    const item = await this.getDefectByTitle(title);
    if (!item) {
      throw new Error(`Defect not found: ${title}`);
    }

    const deleteBtn = item.locator(this.deleteDefectBtn);
    await deleteBtn.click();

    // Confirm
    await this.waitFor(this.confirmDeleteModal, 5000);
    await this.click(this.confirmDeleteBtn);

    await this.page.waitForSelector(this.confirmDeleteModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Get defect detail information
   */
  async getDefectDetail(): Promise<DefectDetail> {
    const idEl = this.page.locator(this.defectDetailContainer);
    const id = await idEl.getAttribute("data-defect-id");

    const title = await this.getText(this.defectDetailTitle);
    const status = await this.getText(this.defectDetailStatus);
    const severity = await this.getText(this.defectDetailSeverity);
    const assignee = await this.getText(this.defectDetailAssignee);

    return {
      id: id || "",
      title,
      status,
      severity,
      assignee,
      createdBy: "",
      createdAt: "",
      comments: 0,
    };
  }

  /**
   * Update defect status
   */
  async updateStatus(newStatus: string): Promise<void> {
    await this.page.selectOption(this.statusSelect, newStatus);
    await this.waitForPageReady();
  }

  /**
   * Assign defect to user
   */
  async assignToUser(email: string): Promise<void> {
    await this.page.selectOption(this.assigneeSelect, email);
    await this.waitForPageReady();
  }

  /**
   * Assign defect to self
   */
  async assignToMe(): Promise<void> {
    await this.click(this.assignToMeBtn);
    await this.waitForPageReady();
  }

  /**
   * Update severity
   */
  async updateSeverity(severity: "low" | "medium" | "high" | "critical"): Promise<void> {
    await this.page.selectOption(this.severitySelect, severity);
    await this.waitForPageReady();
  }

  /**
   * Add comment to defect
   */
  async addComment(text: string): Promise<void> {
    await this.waitFor(this.commentInput, 5000);
    await this.fillInput(this.commentInput, text);
    await this.click(this.commentSubmitBtn);

    // Wait for comment to be added
    await this.page.waitForTimeout(500);
    await this.waitForPageReady();
  }

  /**
   * Get all comments
   */
  async getComments(): Promise<string[]> {
    const items = this.page.locator(this.commentItem);
    const count = await items.count();
    const comments: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        comments.push(text.trim());
      }
    }

    return comments;
  }

  /**
   * Search for defects
   */
  async searchDefects(query: string): Promise<void> {
    await this.fillInput(this.defectSearch, query);
    await this.page.waitForTimeout(500); // Debounce
    await this.waitForPageReady();
  }

  /**
   * Get list of all visible defects
   */
  async getDefectList(): Promise<string[]> {
    const items = this.page.locator(this.defectItem);
    const count = await items.count();
    const defects: string[] = [];

    for (let i = 0; i < count; i++) {
      const text = await items.nth(i).textContent();
      if (text) {
        defects.push(text.trim());
      }
    }

    return defects;
  }

  /**
   * Filter by status
   */
  async filterByStatus(status: string): Promise<void> {
    await this.page.selectOption(this.statusFilter, status);
    await this.waitForPageReady();
  }

  /**
   * Filter by severity
   */
  async filterBySeverity(severity: string): Promise<void> {
    await this.page.selectOption(this.severityFilter, severity);
    await this.waitForPageReady();
  }

  /**
   * Check if defect exists
   */
  async defectExists(title: string): Promise<boolean> {
    const item = await this.getDefectByTitle(title);
    return item !== null;
  }

  /**
   * Get form validation error
   */
  async getFormError(): Promise<string> {
    const errorEl = this.page.locator(this.defectFormError);
    if (await errorEl.isVisible()) {
      return this.getText(this.defectFormError);
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
   * Edit defect
   */
  async editDefect(
    title: string,
    updates: Partial<CreateDefectInput>
  ): Promise<void> {
    const item = await this.getDefectByTitle(title);
    if (!item) {
      throw new Error(`Defect not found: ${title}`);
    }

    const editBtn = item.locator(this.editDefectBtn);
    await editBtn.click();

    await this.waitFor(this.defectModal, 10000);

    if (updates.title) {
      await this.page.fill(this.defectTitleInput, updates.title);
    }
    if (updates.description) {
      await this.page.fill(this.defectDescInput, updates.description);
    }
    if (updates.severity) {
      await this.page.selectOption(this.defectSeveritySelect, updates.severity);
    }

    await this.click(this.saveDefectBtn);

    await this.page.waitForSelector(this.defectModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }
}
