import { type APIRequestContext } from "@playwright/test";
import { API_BASE } from "../config/runtime";

export interface TestUser {
  email: string;
  password: string;
  token: string;
}

export interface TestProject {
  id: string;
  name: string;
}

export interface TestScenario {
  id: string;
  title: string;
  projectId: string;
}

export class TestDataFactory {
  private request: APIRequestContext;
  private token: string;
  private cleanupIds: { type: string; id: string; projectId?: string }[] = [];

  constructor(request: APIRequestContext, token: string) {
    this.request = request;
    this.token = token;
  }

  private get headers() {
    return { Authorization: `Bearer ${this.token}` };
  }

  async createUser(prefix = "e2e"): Promise<TestUser> {
    const email = `${prefix}_${Date.now()}@test.bgtest.dev`;
    const password = "SecurePass123!";

    await this.request.post(`${API_BASE}/api/v1/auth/register`, {
      data: { email, password, password_confirm: password, first_name: "E2E", last_name: "User" },
    });

    const loginRes = await this.request.post(`${API_BASE}/api/v1/auth/login`, {
      data: { email, password },
    });
    const { access_token: token } = await loginRes.json();

    return { email, password, token };
  }

  async createProject(name?: string): Promise<TestProject> {
    const projectName = name || `Test Proje ${Date.now()}`;
    const res = await this.request.post(`${API_BASE}/api/v1/tspm/projects`, {
      headers: this.headers,
      data: { name: projectName, description: "Auto-generated test data" },
    });
    const body = await res.json();
    this.cleanupIds.push({ type: "project", id: body.id });
    return { id: body.id, name: projectName };
  }

  async createScenario(projectId: string, title?: string): Promise<TestScenario> {
    const scenarioTitle = title || `Test Senaryo ${Date.now()}`;
    const res = await this.request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios`, {
      headers: this.headers,
      data: { title: scenarioTitle, description: "Auto-generated", steps: [{ order: 0, text: "Adım 1" }] },
    });
    const body = await res.json();
    this.cleanupIds.push({ type: "scenario", id: body.id, projectId });
    return { id: body.id, title: scenarioTitle, projectId };
  }

  async createExecution(projectId: string, name?: string): Promise<string> {
    const execName = name || `Koşum ${Date.now()}`;
    const res = await this.request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/executions`, {
      headers: this.headers,
      data: { name: execName },
    });
    const body = await res.json();
    return body.id;
  }

  async createApproval(projectId: string, title: string, scenarioId?: string): Promise<string> {
    const res = await this.request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/approvals`, {
      headers: this.headers,
      data: { title, scenario_id: scenarioId },
    });
    const body = await res.json();
    return body.id;
  }

  async cleanup(): Promise<void> {
    for (const item of this.cleanupIds.reverse()) {
      try {
        if (item.type === "project") {
          await this.request.delete(`${API_BASE}/api/v1/tspm/projects/${item.id}`, {
            headers: this.headers,
          });
        }
      } catch {
        // best-effort cleanup
      }
    }
    this.cleanupIds = [];
  }
}

export const STATIC_TEST_DATA = {
  validUser: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  invalidUser: { email: "nonexistent@test.com", password: "wrong" },
  csvImportContent: "title,description,steps\nImport Senaryo,Açıklama,Adım 1|Adım 2",
  projectNames: {
    smoke: "Smoke Test Projesi",
    regression: "Regresyon Projesi",
    performance: "Performans Projesi",
  },
} as const;
