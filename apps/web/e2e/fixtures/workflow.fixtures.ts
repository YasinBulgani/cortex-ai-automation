import { test as baseTest } from "@playwright/test";
import { LoginPage } from "../pages/LoginPage";
import { ProjectPage } from "../pages/ProjectPage";
import { TestCasePage } from "../pages/TestCasePage";
import { RunPage } from "../pages/RunPage";
import { DefectPage } from "../pages/DefectPage";
import { SettingsPage } from "../pages/SettingsPage";
import { DashboardPage } from "../pages/DashboardPage";

/**
 * Workflow Fixtures - Extended test fixtures for critical path tests
 *
 * Provides:
 * - Page objects for all major workflows
 * - Pre-authenticated sessions (admin, tester, manager)
 * - Test data seeding helpers
 * - API client for backend calls
 */

type WorkflowFixtures = {
  // Page Objects
  loginPage: LoginPage;
  projectPage: ProjectPage;
  testCasePage: TestCasePage;
  runPage: RunPage;
  defectPage: DefectPage;
  settingsPage: SettingsPage;
  dashboardPage: DashboardPage;

  // Authenticated Sessions
  adminSession: void;
  testerSession: void;
  managerSession: void;
  developerSession: void;

  // API helpers
  apiClient: APIClient;
  seedTestData: SeededData;
};

/**
 * Simple API client for backend calls
 */
class APIClient {
  constructor(private baseURL = "http://localhost:8000") {}

  async post<T = any>(path: string, body: any): Promise<T> {
    const response = await fetch(`${this.baseURL}/api/v1${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.getToken()}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async get<T = any>(path: string): Promise<T> {
    const response = await fetch(`${this.baseURL}/api/v1${path}`, {
      headers: {
        Authorization: `Bearer ${this.getToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async delete(path: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/api/v1${path}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${this.getToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
  }

  private getToken(): string {
    // In a real scenario, retrieve from localStorage or session
    return process.env.TEST_AUTH_TOKEN || "";
  }
}

/**
 * Seeded test data structure
 */
interface SeededData {
  projectId: string;
  projectName: string;
  testCaseId: string;
  testCaseName: string;
  runId?: string;
}

/**
 * Session credentials
 */
const CREDENTIALS = {
  admin: { email: "admin@example.com", password: "admin123" },
  tester: { email: "tester@example.com", password: "testerpass" },
  manager: { email: "manager@example.com", password: "managerpass" },
  developer: { email: "developer@example.com", password: "developerpass" },
};

/**
 * Custom test fixture with extended capabilities
 */
export const test = baseTest.extend<WorkflowFixtures>({
  // ── Page Objects ─────────────────────────────────────────────────────

  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },

  projectPage: async ({ page }, use) => {
    await use(new ProjectPage(page));
  },

  testCasePage: async ({ page }, use) => {
    await use(new TestCasePage(page));
  },

  runPage: async ({ page }, use) => {
    await use(new RunPage(page));
  },

  defectPage: async ({ page }, use) => {
    await use(new DefectPage(page));
  },

  settingsPage: async ({ page }, use) => {
    await use(new SettingsPage(page));
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },

  // ── Authenticated Sessions ──────────────────────────────────────────

  adminSession: async ({ page, loginPage }, use) => {
    // Login as admin
    await loginPage.goto();
    await loginPage.login(CREDENTIALS.admin.email, CREDENTIALS.admin.password);

    // Wait for redirect
    await page.waitForURL(/.*/, { timeout: 10000 });

    // Verify we're not on login page
    if (page.url().includes("/login")) {
      throw new Error("Failed to authenticate as admin");
    }

    await use();

    // Logout (optional cleanup)
    // await page.goto("/logout");
  },

  testerSession: async ({ page, loginPage }, use) => {
    await loginPage.goto();
    await loginPage.login(CREDENTIALS.tester.email, CREDENTIALS.tester.password);
    await page.waitForURL(/.*/, { timeout: 10000 });

    if (page.url().includes("/login")) {
      throw new Error("Failed to authenticate as tester");
    }

    await use();
  },

  managerSession: async ({ page, loginPage }, use) => {
    await loginPage.goto();
    await loginPage.login(CREDENTIALS.manager.email, CREDENTIALS.manager.password);
    await page.waitForURL(/.*/, { timeout: 10000 });

    if (page.url().includes("/login")) {
      throw new Error("Failed to authenticate as manager");
    }

    await use();
  },

  developerSession: async ({ page, loginPage }, use) => {
    await loginPage.goto();
    await loginPage.login(CREDENTIALS.developer.email, CREDENTIALS.developer.password);
    await page.waitForURL(/.*/, { timeout: 10000 });

    if (page.url().includes("/login")) {
      throw new Error("Failed to authenticate as developer");
    }

    await use();
  },

  // ── API Client ──────────────────────────────────────────────────────

  apiClient: async ({}, use) => {
    const client = new APIClient();
    await use(client);
  },

  // ── Seeded Test Data ────────────────────────────────────────────────

  seedTestData: async ({ adminSession, apiClient }, use) => {
    // Create test project via API
    const projectRes = await apiClient.post("/projects", {
      name: `E2E Test Project ${Date.now()}`,
      description: "Auto-seeded by E2E fixtures",
    });

    // Create test case via API
    const testCaseRes = await apiClient.post(
      `/projects/${projectRes.id}/test-cases`,
      {
        title: `E2E Test Case ${Date.now()}`,
        description: "Auto-seeded test case",
        steps: [
          {
            action: "click",
            selector: "button.login",
            expected: "modal visible",
          },
          {
            action: "fill",
            selector: "input.email",
            value: "test@test.com",
          },
        ],
      }
    );

    const seededData: SeededData = {
      projectId: projectRes.id,
      projectName: projectRes.name,
      testCaseId: testCaseRes.id,
      testCaseName: testCaseRes.title,
    };

    await use(seededData);

    // Cleanup: Delete test data after test
    try {
      await apiClient.delete(`/projects/${seededData.projectId}`);
    } catch (error) {
      console.warn("Failed to cleanup test data:", error);
    }
  },
});

/**
 * Export expect for assertions
 */
export { expect } from "@playwright/test";

/**
 * Usage Examples:
 *
 * 1. Simple workflow test:
 *    test("admin creates project", async ({ adminSession, projectPage }) => {
 *      await projectPage.goto();
 *      await projectPage.createProject("Test", "Desc");
 *    });
 *
 * 2. Multi-step workflow:
 *    test("complete workflow", async ({
 *      adminSession,
 *      projectPage,
 *      testCasePage,
 *      runPage,
 *    }) => {
 *      // Admin creates project
 *      await projectPage.goto();
 *      await projectPage.createProject("Test", "Desc");
 *
 *      // Admin creates test case
 *      await testCasePage.gotoProject(projectId);
 *      await testCasePage.createTestCase({ title: "Test", ... });
 *
 *      // Admin runs test
 *      await runPage.runTestCase();
 *      const status = await runPage.pollRunCompletion(60000);
 *    });
 *
 * 3. With seeded data:
 *    test("run seeded test case", async ({
 *      adminSession,
 *      runPage,
 *      seedTestData,
 *    }) => {
 *      // Data already created
 *      const { projectId, testCaseId } = seedTestData;
 *
 *      // Just test the run flow
 *      await runPage.goto(projectId, testCaseId, runId);
 *      const result = await runPage.getResultDetail();
 *    });
 *
 * 4. RBAC test:
 *    test("tester cannot create project", async ({
 *      testerSession,
 *      page,
 *    }) => {
 *      await page.goto("/projects");
 *      const newProjectBtn = page.locator('[data-testid="new-project-btn"]');
 *      expect(await newProjectBtn.isVisible()).toBe(false);
 *    });
 */
