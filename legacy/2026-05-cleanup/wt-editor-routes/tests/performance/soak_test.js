/**
 * Soak Test — 10 VU for 60 minutes (memory leak detection)
 *
 * Run: k6 run tests/performance/soak_test.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

export const options = {
  stages: [
    { duration: "2m", target: 10 },
    { duration: "56m", target: 10 },
    { duration: "2m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"],
    http_req_failed: ["rate<0.01"],
  },
};

export function setup() {
  const token = login();
  const h = authHeaders(token);
  const proj = http.post(
    `${BASE}/api/v1/tspm/projects`,
    JSON.stringify({ name: `soak-${Date.now()}` }),
    h
  );
  return { token, projectId: proj.json("id") };
}

export default function (data) {
  const h = authHeaders(data.token);
  const pid = data.projectId;

  check(http.get(`${BASE}/api/v1/tspm/projects`, h), { ok: (r) => r.status === 200 });
  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/dashboard`, h), { ok: (r) => r.status === 200 });
  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/scenarios`, h), { ok: (r) => r.status === 200 });

  sleep(3 + Math.random() * 5);
}
