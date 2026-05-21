import type { APIRequestContext } from "@playwright/test";
import { test, expect } from "./fixtures/pages.fixture";
import { loginAsAdmin, getAdminToken, apiCreateProject } from "./helpers/auth";
import { API_BASE } from "./config/runtime";

test.describe.serial("API Testleri", () => {
  let projectId: string;
  let token: string;

  const specName = "E2E Banking API";
  const testCaseTitle = "E2E GET accounts success";
  const specContent = JSON.stringify({
    openapi: "3.0.3",
    info: { title: specName, version: "1.0.0" },
    paths: {
      "/accounts": {
        get: {
          operationId: "listAccounts",
          summary: "List accounts",
          tags: ["accounts"],
          responses: {
            "200": {
              description: "OK",
              content: {
                "application/json": {
                  schema: {
                    type: "array",
                    items: {
                      type: "object",
                      properties: {
                        id: { type: "string" },
                        balance: { type: "number" },
                      },
                    },
                  },
                },
              },
            },
          },
        },
      },
    },
  });

  async function importSpec(request: APIRequestContext) {
    const res = await request.post(
      `${API_BASE}/api/v1/api-testing/projects/${projectId}/specs/import`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: { content: specContent, name: specName },
      },
    );
    expect(res.status()).toBe(201);
    return res.json();
  }

  async function firstEndpointId(request: APIRequestContext): Promise<string> {
    const res = await request.get(
      `${API_BASE}/api/v1/api-testing/projects/${projectId}/endpoints`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(res.ok()).toBeTruthy();
    const endpoints = await res.json();
    expect(endpoints.length).toBeGreaterThan(0);
    return endpoints[0].id;
  }

  test.beforeAll(async ({ playwright }) => {
    const request = await playwright.request.newContext();
    token = await getAdminToken(request);
    projectId = await apiCreateProject(request, token, `APITest Proje ${Date.now()}`);
    await request.dispose();
  });

  test.beforeEach(async ({ page }) => { await loginAsAdmin(page); });

  test("API test sayfası yüklenmeli", async ({ page, apiTestsPage }) => {
    await page.goto(`/p/${projectId}/api-testing`);
    await apiTestsPage.assertPageLoaded();
  });

  test("OpenAPI spec import edildiğinde endpoint envanteri görünmeli", async ({ page, request, apiTestsPage }) => {
    await importSpec(request);
    await page.goto(`/p/${projectId}/api-testing`);
    await apiTestsPage.assertSpecVisible(specName);
    await apiTestsPage.assertEndpointVisible("GET", "/accounts");
  });

  test("endpoint için manuel test case eklenince listede görünmeli", async ({ page, request, apiTestsPage }) => {
    await importSpec(request);
    const endpointId = await firstEndpointId(request);

    const created = await request.post(
      `${API_BASE}/api/v1/api-testing/projects/${projectId}/test-cases`,
      {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          title: testCaseTitle,
          description: "E2E tarafından oluşturulan API test case",
          test_type: "positive",
          priority: "P1",
          endpoint_id: endpointId,
          request_method: "GET",
          request_path: "/accounts",
          request_headers: {},
          assertions: [{ type: "status_code", expected: 200 }],
        },
      },
    );
    expect(created.status()).toBe(201);

    await page.goto(`/p/${projectId}/api-testing`);
    await apiTestsPage.assertTestCaseVisible(testCaseTitle);
  });
});
