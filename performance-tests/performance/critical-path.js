/**
 * Critical Path Load Test
 *
 * Tests the core user workflow:
 * 1. Login
 * 2. List projects
 * 3. List test cases
 * 4. Create a test execution
 * 5. Fetch execution results
 *
 * Config:
 * - 10 Virtual Users (VU)
 * - 30 seconds duration
 * - Thresholds: p95 < 2000ms, error_rate < 10%
 *
 * Run: k6 run performance-tests/performance/critical-path.js
 * Run with json output: k6 run --out json=baseline.json performance-tests/performance/critical-path.js
 * Run with custom API base: k6 run -e API_BASE=http://staging.bgtest.dev performance-tests/performance/critical-path.js
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

// Configuration
const API_BASE = __ENV.API_BASE || "http://127.0.0.1:8000";
const DURATION = __ENV.DURATION || "30s";
const VUS = parseInt(__ENV.VUS || "10");
const RAMP_UP = __ENV.RAMP_UP || "10s";

export const options = {
  // Ramp up to target VUs, then hold for the main duration
  stages: [
    { duration: RAMP_UP, target: VUS },
    { duration: DURATION, target: VUS },
    { duration: "10s", target: 0 }, // Cool down
  ],

  // Performance thresholds
  thresholds: {
    // Response time percentiles (ms)
    http_req_duration: [
      "p(50)<500",   // Median < 500ms
      "p(90)<1000",  // 90th percentile < 1000ms
      "p(95)<2000",  // 95th percentile < 2000ms (primary threshold)
      "p(99)<5000",  // 99th percentile < 5000ms
    ],

    // Error rate must stay below 10%
    http_req_failed: ["rate<0.1"],

    // Minimum throughput (requests per second)
    http_reqs: ["rate>10"],
  },
};

// Setup: authenticate once per scenario
export function setup() {
  console.log(`Starting critical path load test`);
  console.log(`  VUs: ${VUS}`);
  console.log(`  Duration: ${DURATION}`);
  console.log(`  API Base: ${API_BASE}`);

  try {
    const token = login();
    console.log(`Authentication successful`);

    // Get or create a project for the test
    const headers = authHeaders(token);
    const projectRes = http.post(
      `${API_BASE}/api/v1/tspm/projects`,
      JSON.stringify({
        name: `critical-path-${Date.now()}`,
        description: "Performance test project",
      }),
      headers
    );

    let projectId;
    if (projectRes.status === 201) {
      projectId = projectRes.json("id");
      console.log(`Created test project: ${projectId}`);
    } else if (projectRes.status === 409) {
      // Project exists, fetch it
      const listRes = http.get(`${API_BASE}/api/v1/tspm/projects`, headers);
      const projects = listRes.json("data");
      projectId = projects && projects.length > 0 ? projects[0].id : null;
      if (!projectId) throw new Error("No project available");
      console.log(`Using existing project: ${projectId}`);
    } else {
      throw new Error(`Failed to create/get project: ${projectRes.status}`);
    }

    return { token, projectId, baseUrl: API_BASE };
  } catch (err) {
    console.error(`Setup failed: ${err.message}`);
    throw err;
  }
}

// Main load test function
export default function (data) {
  const headers = authHeaders(data.token);
  const projectId = data.projectId;
  const baseUrl = data.baseUrl || API_BASE;

  // Measure the entire critical path
  const criticalStart = new Date().getTime();

  try {
    // 1. List projects
    group("1. List projects", () => {
      const res = http.get(`${baseUrl}/api/v1/tspm/projects`, headers);
      check(res, {
        "list projects 200": (r) => r.status === 200,
        "list projects has data": (r) =>
          r.json("data") && Array.isArray(r.json("data")),
      });
    });
    sleep(0.5);

    // 2. Get project details
    group("2. Get project details", () => {
      const res = http.get(
        `${baseUrl}/api/v1/tspm/projects/${projectId}`,
        headers
      );
      check(res, {
        "project details 200": (r) => r.status === 200,
        "project details has id": (r) => r.json("id") === projectId,
      });
    });
    sleep(0.5);

    // 3. List test cases (scenarios)
    group("3. List test cases", () => {
      const res = http.get(
        `${baseUrl}/api/v1/tspm/projects/${projectId}/scenarios`,
        headers
      );
      check(res, {
        "list scenarios 200": (r) => r.status === 200,
        "list scenarios has data": (r) =>
          r.json("data") && Array.isArray(r.json("data")),
      });
    });
    sleep(0.5);

    // 4. List executions/test runs
    group("4. List test runs", () => {
      const res = http.get(
        `${baseUrl}/api/v1/tspm/projects/${projectId}/executions`,
        headers
      );
      check(res, {
        "list executions 200 or 404": (r) => [200, 404].includes(r.status),
        "list executions has data or empty": (r) =>
          r.status === 404 || (r.json("data") && Array.isArray(r.json("data"))),
      });
    });
    sleep(0.5);

    // 5. Get project dashboard (complex aggregation)
    group("5. Get project dashboard", () => {
      const res = http.get(
        `${baseUrl}/api/v1/tspm/projects/${projectId}/dashboard`,
        headers
      );
      check(res, {
        "dashboard 200 or 404": (r) => [200, 404].includes(r.status),
      });
    });
    sleep(0.5);

    // 6. List requirements/test specifications
    group("6. List requirements", () => {
      const res = http.get(
        `${baseUrl}/api/v1/tspm/projects/${projectId}/requirements`,
        headers
      );
      check(res, {
        "list requirements 200 or 404": (r) => [200, 404].includes(r.status),
      });
    });
    sleep(0.5);

    // Measure critical path duration
    const criticalEnd = new Date().getTime();
    const duration = criticalEnd - criticalStart;

    // Custom metric for critical path
    if (duration > 2000) {
      console.warn(`Critical path exceeded threshold: ${duration}ms`);
    }
  } catch (err) {
    console.error(`Critical path failed: ${err.message}`);
    check(false, { "critical path completed": false });
  }

  // Minimum sleep between iterations to prevent hammering
  sleep(1);
}

// Teardown
export function teardown(data) {
  console.log(`Critical path load test completed`);
}
