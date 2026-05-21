import { type Page, type APIRequestContext } from "@playwright/test";
import { API_BASE } from "../config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "../config/auth";

const API = API_BASE;

export async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.getByLabel("E-posta").fill(ADMIN_EMAIL);
  await page.getByLabel("Şifre").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Giriş" }).click();
  await page.waitForURL(/\/projects/);
}

export async function getAdminToken(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API}/api/v1/auth/login`, {
    data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
  });
  const body = await res.json();
  return body.access_token;
}

export async function apiCreateProject(
  request: APIRequestContext,
  token: string,
  name: string
): Promise<string> {
  const res = await request.post(`${API}/api/v1/tspm/projects`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, description: "E2E test" },
  });
  const body = await res.json();
  return body.id;
}

export async function apiCreateScenario(
  request: APIRequestContext,
  token: string,
  projectId: string,
  title: string
): Promise<string> {
  const res = await request.post(`${API}/api/v1/tspm/projects/${projectId}/scenarios`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { title, description: "E2E test scenario", steps: [{ order: 0, text: "Adım 1" }] },
  });
  const body = await res.json();
  return body.id;
}

export async function apiCreateApproval(
  request: APIRequestContext,
  token: string,
  projectId: string,
  title: string,
  scenarioId?: string
): Promise<string> {
  const res = await request.post(`${API}/api/v1/tspm/projects/${projectId}/approvals`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { title, scenario_id: scenarioId },
  });
  const body = await res.json();
  return body.id;
}

export async function apiCreateRequirement(
  request: APIRequestContext,
  token: string,
  projectId: string,
  externalId: string,
  title: string
): Promise<string> {
  const res = await request.post(`${API}/api/v1/tspm/projects/${projectId}/requirements`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { external_id: externalId, title, priority: "medium" },
  });
  const body = await res.json();
  return body.id;
}

export async function apiCreateFlow(
  request: APIRequestContext,
  token: string,
  projectId: string,
  name: string
): Promise<string> {
  const res = await request.post(`${API}/api/v1/tspm/projects/${projectId}/flows`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, description: "E2E test flow" },
  });
  const body = await res.json();
  return body.id;
}
