import { expect, test, type APIRequestContext } from "@playwright/test";
import { API_BASE } from "./config/runtime";
import { FakeAppiumServer } from "./helpers/fake-appium";

type MobileSession = {
  id: string;
  device_id: string;
  scenario_name: string;
  status: "queued" | "running" | "passed" | "failed" | "cancelled";
  mode: "simulation" | "appium";
  failure_category?: string | null;
  failure_message?: string | null;
  steps: Array<{ action: string; status: string; duration_ms: number; error_message?: string | null }>;
};

type MobileArtifact = {
  id: string;
  session_id: string;
  kind: "screenshot" | "page_source" | "stdout" | "appium_log" | "video" | "junit";
  size_bytes: number;
};

async function waitForTerminalSession(
  request: APIRequestContext,
  sessionId: string,
): Promise<MobileSession> {
  for (let i = 0; i < 40; i += 1) {
    const res = await request.get(`${API_BASE}/api/v1/mobile/sessions/${sessionId}`);
    expect(res.ok()).toBeTruthy();
    const session = (await res.json()) as MobileSession;
    if (["passed", "failed", "cancelled"].includes(session.status)) {
      return session;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Mobile Appium session did not finish: ${sessionId}`);
}

test.describe("Mobile Appium lifecycle", () => {
  test("enrolled cihazda appium session koşar ve artifact üretir", async ({ request }) => {
    const appium = new FakeAppiumServer();
    const appiumUrl = await appium.start();

    try {
      const enroll = await request.post(`${API_BASE}/api/v1/mobile/enroll-physical`, {
        data: {
          name: `E2E Fake Android ${Date.now()}`,
          platform: "android",
          os_version: "14",
          udid: `fake-${Date.now()}`,
          appium_url: appiumUrl,
          profile: "e2e_fake_android",
        },
      });
      expect(enroll.ok()).toBeTruthy();
      const device = (await enroll.json()) as { id: string; status: string; appium_url: string };
      expect(device.status).toBe("idle");
      expect(device.appium_url).toBe(appiumUrl);

      const create = await request.post(`${API_BASE}/api/v1/mobile/sessions`, {
        data: {
          scenario_name: "E2E Appium Artifact Smoke",
          prompt: "Fake Appium ile mobil web smoke koş",
          platform: "android",
          parallel: 1,
          mode: "appium",
          device_ids: [device.id],
          app: { type: "web", url: "https://example.test" },
          steps: [
            { action: "openUrl", url: "https://example.test" },
            { action: "screenshot" },
            { action: "pageSource" },
          ],
        },
      });
      expect(create.ok()).toBeTruthy();
      const created = (await create.json()) as MobileSession[];
      expect(created).toHaveLength(1);
      expect(created[0].device_id).toBe(device.id);
      expect(created[0].mode).toBe("appium");

      const finalSession = await waitForTerminalSession(request, created[0].id);
      expect(finalSession.status).toBe("passed");
      expect(finalSession.failure_category).toBeFalsy();
      expect(finalSession.steps.map((step) => step.status)).toEqual(["passed", "passed", "passed"]);

      const artifactsRes = await request.get(
        `${API_BASE}/api/v1/mobile/sessions/${created[0].id}/artifacts`,
      );
      expect(artifactsRes.ok()).toBeTruthy();
      const artifacts = (await artifactsRes.json()) as MobileArtifact[];
      expect(artifacts.map((artifact) => artifact.kind).sort()).toEqual(["page_source", "screenshot"]);
      expect(artifacts.every((artifact) => artifact.size_bytes > 0)).toBeTruthy();

      const screenshot = artifacts.find((artifact) => artifact.kind === "screenshot");
      expect(screenshot).toBeTruthy();
      const screenshotRes = await request.get(`${API_BASE}/api/v1/mobile/artifacts/${screenshot?.id}`);
      expect(screenshotRes.ok()).toBeTruthy();
      expect((await screenshotRes.body()).length).toBeGreaterThan(0);

      expect(appium.requests).toContain("POST /session");
      expect(appium.requests).toContain("POST /session/fake-session/url");
      expect(appium.requests).toContain("GET /session/fake-session/screenshot");
      expect(appium.requests).toContain("GET /session/fake-session/source");
      expect(appium.requests).toContain("DELETE /session/fake-session");
    } finally {
      await appium.stop();
    }
  });
});
