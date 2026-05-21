/**
 * Stress Test — ramp 10→100 VU, 15 minutes
 *
 * Run: k6 run tests/performance/stress_test.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

export const options = {
  stages: [
    { duration: "3m", target: 10 },
    { duration: "5m", target: 50 },
    { duration: "4m", target: 100 },
    { duration: "3m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<1000"],
    http_req_failed: ["rate<0.05"],
  },
};

export function setup() {
  const token = login();
  const h = authHeaders(token);
  const proj = http.post(
    `${BASE}/api/v1/tspm/projects`,
    JSON.stringify({ name: `stress-${Date.now()}` }),
    h
  );
  check(proj, { "project created": (r) => r.status === 201 });
  return { token, projectId: proj.json("id") };
}

export default function (data) {
  const h = authHeaders(data.token);
  const pid = data.projectId;

  check(http.get(`${BASE}/api/v1/tspm/projects`, h), {
    "projects ok": (r) => r.status === 200,
  });

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/dashboard`, h), {
    "dashboard ok": (r) => r.status === 200,
  });

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/scenarios`, h), {
    "scenarios ok": (r) => r.status === 200,
  });

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/executions`, h), {
    "executions ok": (r) => r.status === 200,
  });

  const sc = http.post(
    `${BASE}/api/v1/tspm/projects/${pid}/scenarios`,
    JSON.stringify({ title: `stress-${__VU}-${__ITER}`, steps: [{ order: 0, text: "Adım" }] }),
    h
  );
  check(sc, { "create scenario 201": (r) => r.status === 201 });

  sleep(Math.random() * 2 + 1);
}
