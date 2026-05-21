import { expect, test } from "@playwright/test";
import { API_BASE } from "./config/runtime";

test.describe("AI Quality Dashboard", () => {
  test("eval quality gate backend özetiyle görünmeli", async ({ page, request }) => {
    const summary = await request.get(`${API_BASE}/api/v1/evals/summary?limit=30`);
    expect(summary.ok()).toBeTruthy();
    const body = (await summary.json()) as {
      summary?: { status?: string; total_runs?: number };
    };
    expect(body.summary).toBeTruthy();

    await page.goto("/ai-quality");

    await expect(page.getByRole("heading", { name: "AI Quality Dashboard" })).toBeVisible();
    await expect(page.getByTestId("ai-quality-eval-gate")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Eval Quality Gate")).toBeVisible();
    await expect(page.getByText(/PASS|WARN|FAIL|UNKNOWN/).first()).toBeVisible();
  });
});
