/**
 * Spike Test — sudden 0→100→0, 5 minutes
 *
 * Run: k6 run tests/performance/spike_test.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

export const options = {
  stages: [
    { duration: "30s", target: 0 },
    { duration: "30s", target: 100 },
    { duration: "1m", target: 100 },
    { duration: "30s", target: 0 },
    { duration: "2m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    http_req_failed: ["rate<0.10"],
  },
};

export function setup() {
  return { token: login() };
}

export default function (data) {
  const h = authHeaders(data.token);

  check(http.get(`${BASE}/api/v1/tspm/projects`, h), {
    "spike ok": (r) => r.status === 200,
  });

  check(http.get(`${BASE}/health`), {
    "health ok": (r) => r.status === 200,
  });

  sleep(0.5);
}
