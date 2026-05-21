import { expect, test } from "@playwright/test";

const healthPayload = {
  generated_at: "2026-05-17T08:00:00Z",
  sample_size: 250,
  runs_total: 4,
  active_runs: 2,
  by_status: {
    running: 1,
    pending_approval: 1,
    failed_validation: 1,
    completed: 1,
  },
  by_workflow_type: {
    test_generation: 3,
    review: 1,
  },
  event_counts: {
    artifact_downloaded: 2,
    artifact_integrity_failed: 1,
  },
  artifact_count: 5,
  artifact_bytes: 2048,
  approval_count: 2,
  dead_letters_total: 1,
  recent_dead_letters: [
    {
      dead_letter_id: "dlq-1",
      run_id: "run-1",
      queue_name: "ai_workflows",
      reason: "synthetic test failure",
      created_at: "2026-05-17T07:59:00Z",
    },
  ],
  queue_depth: 3,
  oldest_active_seconds: 125,
  cost_usd: 0.1234,
  tokens_used: 12345,
  llm_calls_count: 7,
};

const workflowPayload = {
  workflow_id: "wf-operator-1",
  run_id: "wf-operator-1",
  project_id: "project-operator",
  status: "pending_approval",
  input_source: "text",
  created_at: "2026-05-17T07:55:00Z",
  completed_at: null,
  error: null,
  event_count: 2,
  artifact_count: 1,
  approval_count: 0,
  cost_usd: 0.02,
  tokens_used: 1200,
  llm_calls_count: 2,
  errors: [],
  scenarios: [],
};

const eventPayload = {
  workflow_id: "wf-operator-1",
  events: [
    {
      event_type: "workflow_created",
      timestamp: "2026-05-17T07:55:00Z",
      message: "created",
    },
    {
      event_type: "approval_required",
      timestamp: "2026-05-17T07:56:00Z",
      message: "approval needed",
    },
  ],
};

const artifactPayload = {
  workflow_id: "wf-operator-1",
  artifacts: [
    {
      artifact_id: "artifact-1",
      kind: "excel_report",
      name: "run_report.xlsx",
      storage_path: "/tmp/run_report.xlsx",
      mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      size_bytes: 4096,
      created_at: "2026-05-17T07:57:00Z",
      metadata: { sha256: "abc" },
    },
  ],
};

test.describe("AI Workflow Health", () => {
  test("operasyon paneli health metriklerini ve DLQ durumunu gösterir", async ({ page }) => {
    await page.route("**/api/v1/ai/workflows/health?*", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(healthPayload),
      });
    });
    await page.route("**/api/v1/ai/workflows/wf-operator-1", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(workflowPayload),
      });
    });
    await page.route("**/api/v1/ai/workflows/wf-operator-1/events", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(eventPayload),
      });
    });
    await page.route("**/api/v1/ai/workflows/wf-operator-1/artifacts", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(artifactPayload),
      });
    });
    await page.route("**/api/v1/ai/workflows/wf-operator-1/approve", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workflow_id: "wf-operator-1",
          status: "queued",
          approval: { decision: "approved", actor_id: "approver" },
        }),
      });
    });
    await page.route("**/api/v1/ai/workflows/wf-operator-1/cancel", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          workflow_id: "wf-operator-1",
          run_id: "wf-operator-1",
          status: "cancelled",
        }),
      });
    });

    await page.goto("/ai-workflows");

    await expect(page.locator("[data-testid='ai-workflow-health-page']")).toBeVisible();
    await expect(page.getByRole("heading", { name: "AI Workflow Health" })).toBeVisible();
    await expect(page.locator("[data-testid='ai-workflow-metric-active']")).toContainText("2");
    await expect(page.locator("[data-testid='ai-workflow-metric-queue']")).toContainText("3");
    await expect(page.locator("[data-testid='ai-workflow-metric-dlq']")).toContainText("1");
    await expect(page.locator("[data-testid='ai-workflow-metric-artifact']")).toContainText("5 / 2.0 KB");
    await expect(page.locator("[data-testid='ai-workflow-status-failed_validation']")).toContainText("failed_validation");
    await expect(page.locator("[data-testid='ai-workflow-type-test_generation']")).toContainText("test_generation");
    await expect(page.locator("[data-testid='ai-workflow-event-artifact_integrity_failed']")).toContainText(
      "artifact_integrity_failed",
    );
    await expect(page.locator("[data-testid='ai-workflow-dlq-row']")).toContainText("synthetic test failure");

    await page.locator("[data-testid='ai-workflow-console-input']").fill("wf-operator-1");
    await page.locator("[data-testid='ai-workflow-console-load']").click();
    await expect(page.locator("[data-testid='ai-workflow-console-detail']")).toContainText("pending_approval");
    await expect(page.locator("[data-testid='ai-workflow-artifact-row']")).toContainText("run_report.xlsx");
    await expect(page.locator("[data-testid='ai-workflow-event-row']").first()).toContainText("approval_required");

    await page.locator("[data-testid='ai-workflow-approval-note']").fill("operator ok");
    await page.locator("[data-testid='ai-workflow-approve']").click();
    await expect(page.locator("[data-testid='ai-workflow-console-message']")).toContainText("Onaylandı: queued");
  });
});
