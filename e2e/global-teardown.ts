import { type FullConfig } from "@playwright/test";
import { request } from "@playwright/test";
import { API_BASE } from "./config/runtime";
import { ADMIN_EMAIL, ADMIN_PASSWORD } from "./config/auth";

async function globalTeardown(_config: FullConfig) {
  const apiContext = await request.newContext({ baseURL: API_BASE });

  try {
    const loginRes = await apiContext.post("/api/v1/auth/login", {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASSWORD },
    });

    if (loginRes.ok()) {
      const { access_token } = await loginRes.json();

      const projectsRes = await apiContext.get("/api/v1/tspm/projects", {
        headers: { Authorization: `Bearer ${access_token}` },
      });

      if (projectsRes.ok()) {
        const projects = await projectsRes.json();
        const testProjects = (projects.data || projects || []).filter(
          (p: { name: string }) =>
            p.name?.startsWith("E2E Test ") ||
            p.name?.startsWith("e2e-") ||
            p.name?.startsWith("Visium E2E ")
        );

        for (const project of testProjects) {
          await apiContext.delete(`/api/v1/tspm/projects/${project.id}`, {
            headers: { Authorization: `Bearer ${access_token}` },
          });
        }

        if (testProjects.length > 0) {
          console.log(
            `[global-teardown] ${testProjects.length} test project(s) cleaned up.`
          );
        }
      }
    }
  } catch {
    console.log("[global-teardown] Cleanup skipped (API unavailable).");
  } finally {
    await apiContext.dispose();
  }

  console.log("[global-teardown] Test suite completed.");
}

export default globalTeardown;
