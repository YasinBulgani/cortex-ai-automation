import { type APIRequestContext, type Page, expect } from "@playwright/test";
import { API_BASE, ADMIN_EMAIL, ADMIN_PASSWORD } from "../config/runtime";

export async function loginAsAdmin(page: Page) {
  const cookies = await page.context().cookies();
  const hasSession = cookies.some((cookie) => cookie.name === "bgts_access_token");
  if (hasSession) return;

  await page.goto("/login");
  await page.evaluate(() => {
    localStorage.setItem("onboarded", "true");
    localStorage.setItem("neurex_onboarding_done", String(Date.now()));
  });
  await page.getByTestId("login-input-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-input-password").fill(ADMIN_PASSWORD);
  await page.getByTestId("login-btn-submit").click();
  await page.waitForURL((url) => url.pathname !== "/login", { timeout: 30_000 });
}

export async function getAdminToken(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${API_BASE}/api/v1/auth/login`, {
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
  const res = await request.post(`${API_BASE}/api/v1/tspm/projects`, {
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
  const res = await request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/scenarios`, {
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
  const res = await request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/approvals`, {
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
  const res = await request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/requirements`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { external_id: externalId, title, priority: "medium" },
  });
  const body = await res.json();
  return body.id;
}

export async function apiRegisterUser(
  request: APIRequestContext,
  email: string,
  password: string
): Promise<{ token: string; userId: string }> {
  const reg = await request.post(`${API_BASE}/api/v1/auth/register`, {
    headers: { "Content-Type": "application/json" },
    data: { email, password, password_confirm: password, first_name: "RBAC", last_name: "User" },
  });
  expect(reg.ok(), `register failed: ${await reg.text()}`).toBeTruthy();

  const login = await request.post(`${API_BASE}/api/v1/auth/login`, {
    data: { email, password },
  });
  const body = await login.json() as { access_token: string; user?: { id: string }; id?: string };
  return { token: body.access_token, userId: body.user?.id ?? body.id ?? "" };
}

export async function apiInviteProjectMember(
  request: APIRequestContext,
  adminToken: string,
  projectId: string,
  email: string,
  role: "viewer" | "editor" | "admin"
): Promise<void> {
  const res = await request.post(
    `${API_BASE}/api/v1/tspm/projects/${projectId}/members`,
    {
      headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      data: { email, role },
    }
  );
  expect([200, 201, 204], `invite member failed with ${res.status()}: ${await res.text()}`).toContain(res.status());
}

export async function apiCreateFlow(
  request: APIRequestContext,
  token: string,
  projectId: string,
  name: string
): Promise<string> {
  const res = await request.post(`${API_BASE}/api/v1/tspm/projects/${projectId}/flows`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, description: "E2E test flow" },
  });
  const body = await res.json();
  return body.id;
}
