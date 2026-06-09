import { Page, expect } from "@playwright/test";
import { BasePage } from "./BasePage";

/**
 * ProjectPage - Page Object for project management workflows
 * Handles: list, create, edit, delete, navigate
 *
 * Critical paths:
 * - Admin creates project (create-project workflow)
 * - Admin deletes project (cleanup)
 * - Navigation to project detail
 */
export class ProjectPage extends BasePage {
  // ── Selectors ──────────────────────────────────────────────────────────

  // Page-level
  readonly projectsHeading = '[data-testid="projects-heading"]';
  readonly projectPageContainer = '[data-testid="projects-page"]';
  readonly newProjectBtn = '[data-testid="new-project-btn"]';
  readonly projectList = '[data-testid="project-list"]';
  readonly projectItem = '[data-testid="project-item"]';
  readonly emptyState = '[data-testid="projects-empty-state"]';

  // Create/Edit modal
  readonly projectModal = '[data-testid="project-modal"]';
  readonly projectNameInput = '[data-testid="project-form-name"]';
  readonly projectDescInput = '[data-testid="project-form-description"]';
  readonly projectTemplateSelect = '[data-testid="project-form-template"]';
  readonly projectAccessSelect = '[data-testid="project-form-access"]';
  readonly saveProjectBtn = '[data-testid="project-form-save"]';
  readonly cancelProjectBtn = '[data-testid="project-form-cancel"]';
  readonly projectFormError = '[data-testid="project-form-error"]';

  // Project item actions
  readonly deleteProjectBtn = '[data-testid="project-delete-btn"]';
  readonly editProjectBtn = '[data-testid="project-edit-btn"]';
  readonly projectSettingsBtn = '[data-testid="project-settings-btn"]';
  readonly confirmDeleteBtn = '[data-testid="confirm-delete"]';
  readonly confirmDeleteModal = '[data-testid="delete-confirm-modal"]';
  readonly cancelDeleteBtn = '[data-testid="cancel-delete"]';

  // Project detail page
  readonly projectDetailContainer = '[data-testid="project-detail"]';
  readonly projectTitle = '[data-testid="project-title"]';
  readonly projectStats = '[data-testid="project-stats"]';

  // Filters & search
  readonly projectSearch = '[data-testid="project-search"]';
  readonly filterButton = '[data-testid="project-filter-btn"]';
  readonly sortButton = '[data-testid="project-sort-btn"]';

  constructor(page: Page) {
    super(page);
  }

  /**
   * Navigate to projects list page
   */
  async goto() {
    await super.goto("/projects");
    await this.waitForPageReady();
  }

  /**
   * Check if projects page is loaded
   */
  async isLoaded(): Promise<boolean> {
    return this.isVisible(this.projectPageContainer);
  }

  /**
   * Create a new project via UI
   *
   * @param name - Project name
   * @param description - Project description
   * @param template - Template name (default: "blank")
   * @param access - Access level (default: "private")
   */
  async createProject(
    name: string,
    description: string,
    template = "blank",
    access = "private"
  ): Promise<void> {
    // 1. Click new project button
    await this.click(this.newProjectBtn);

    // 2. Wait for modal to appear
    await this.waitFor(this.projectModal, 10000);

    // 3. Fill form
    await this.fillInput(this.projectNameInput, name);
    await this.fillInput(this.projectDescInput, description);
    await this.page.selectOption(this.projectTemplateSelect, template);
    await this.page.selectOption(this.projectAccessSelect, access);

    // 4. Submit form
    await this.click(this.saveProjectBtn);

    // 5. Wait for modal to close and list to update
    await this.page.waitForSelector(this.projectModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Get project item element by name
   *
   * @param name - Project name to find
   * @returns Project item locator or null
   */
  async getProjectByName(name: string) {
    const items = this.page.locator(this.projectItem);
    const count = await items.count();

    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const text = await item.textContent();
      if (text?.includes(name)) {
        return item;
      }
    }
    return null;
  }

  /**
   * Open a project by name
   *
   * @param name - Project name to open
   */
  async openProject(name: string): Promise<void> {
    const item = await this.getProjectByName(name);
    if (!item) {
      throw new Error(`Project not found: ${name}`);
    }

    await item.click();
    await this.waitForPageReady();
  }

  /**
   * Delete a project by name
   *
   * @param name - Project name to delete
   */
  async deleteProject(name: string): Promise<void> {
    const item = await this.getProjectByName(name);
    if (!item) {
      throw new Error(`Project not found: ${name}`);
    }

    // Find delete button in project item
    const deleteBtn = item.locator(this.deleteProjectBtn);
    if (await deleteBtn.count() === 0) {
      throw new Error("Delete button not found");
    }

    await deleteBtn.click();

    // Wait for confirmation modal
    await this.waitFor(this.confirmDeleteModal, 5000);

    // Confirm deletion
    await this.click(this.confirmDeleteBtn);

    // Wait for modal to close
    await this.page.waitForSelector(this.confirmDeleteModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Edit a project
   *
   * @param name - Project name to edit
   * @param updates - Fields to update
   */
  async editProject(
    name: string,
    updates: { name?: string; description?: string; access?: string }
  ): Promise<void> {
    const item = await this.getProjectByName(name);
    if (!item) {
      throw new Error(`Project not found: ${name}`);
    }

    // Click edit button
    const editBtn = item.locator(this.editProjectBtn);
    await editBtn.click();

    // Wait for modal
    await this.waitFor(this.projectModal, 10000);

    // Update fields if provided
    if (updates.name) {
      await this.page.fill(this.projectNameInput, updates.name);
    }
    if (updates.description) {
      await this.page.fill(this.projectDescInput, updates.description);
    }
    if (updates.access) {
      await this.page.selectOption(this.projectAccessSelect, updates.access);
    }

    // Save
    await this.click(this.saveProjectBtn);

    // Wait for update
    await this.page.waitForSelector(this.projectModal, { state: "hidden", timeout: 10000 }).catch(() => {});
    await this.waitForPageReady();
  }

  /**
   * Search for projects
   *
   * @param query - Search query
   */
  async searchProjects(query: string): Promise<void> {
    await this.fillInput(this.projectSearch, query);
    await this.page.waitForTimeout(500); // Wait for debounce
    await this.waitForPageReady();
  }

  /**
   * Get list of all visible projects
   *
   * @returns Array of project names
   */
  async getProjectList(): Promise<string[]> {
    const items = this.page.locator(this.projectItem);
    const count = await items.count();
    const projects: string[] = [];

    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      const text = await item.textContent();
      if (text) {
        projects.push(text.trim());
      }
    }

    return projects;
  }

  /**
   * Check if project creation form has validation error
   *
   * @returns Error message or empty string
   */
  async getFormError(): Promise<string> {
    const errorEl = this.page.locator(this.projectFormError);
    if (await errorEl.isVisible()) {
      return this.getText(this.projectFormError);
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
   * Get project statistics
   *
   * @returns Stats object with counts
   */
  async getProjectStats(): Promise<{
    testCases: number;
    runs: number;
    passRate: string;
  } | null> {
    const statsEl = this.page.locator(this.projectStats);
    if (await statsEl.count() === 0) {
      return null;
    }

    const text = await statsEl.textContent();
    // Parse stats from text (format depends on UI)
    // This is a stub implementation
    return {
      testCases: 0,
      runs: 0,
      passRate: "0%",
    };
  }

  /**
   * Check if project exists in list
   */
  async projectExists(name: string): Promise<boolean> {
    const item = await this.getProjectByName(name);
    return item !== null;
  }
}
