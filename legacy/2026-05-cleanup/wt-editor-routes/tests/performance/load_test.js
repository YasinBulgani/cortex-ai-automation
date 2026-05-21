/**
 * Normal Load Test — 20 VU, 10 minutes
 * Simulates typical platform usage patterns.
 *
 * Run: k6 run tests/performance/load_test.js
 * Run with custom base: k6 run -e API_BASE=http://staging.bgtest.dev tests/performance/load_test.js
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { login, authHeaders, BASE } from "./helpers/auth.js";

export const options = {
  stages: [
    { duration: "2m", target: 20 },
    { duration: "6m", target: 20 },
    { duration: "2m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    http_req_failed: ["rate<0.01"],
    http_reqs: ["rate>100"],
  },
};

export function setup() {
  const token = login();
  const h = authHeaders(token);

  const proj = http.post(
    `${BASE}/api/v1/tspm/projects`,
    JSON.stringify({ name: `perf-${Date.now()}` }),
    h
  );
  check(proj, { "project created": (r) => r.status === 201 });

  const projectId = proj.json("id");

  // Seed: birkaç senaryo oluştur
  for (let i = 0; i < 3; i++) {
    const sc = http.post(
      `${BASE}/api/v1/tspm/projects/${projectId}/scenarios`,
      JSON.stringify({ title: `seed-sc-${i}`, steps: [{ order: 0, text: "Adım 1" }] }),
      h
    );
    check(sc, { "seed scenario created": (r) => r.status === 201 });
  }

  // Seed: bir gereksinim oluştur
  const req = http.post(
    `${BASE}/api/v1/tspm/projects/${projectId}/requirements`,
    JSON.stringify({ external_id: `REQ-perf-1`, title: "Perf Gereksinim", priority: "medium" }),
    h
  );
  check(req, { "seed requirement created": (r) => [201, 409].includes(r.status) });

  return { token, projectId };
}

export default function (data) {
  const h = authHeaders(data.token);
  const pid = data.projectId;

  // ── Sık kullanılan okuma endpoint'leri ──────────────────────────────────

  check(http.get(`${BASE}/api/v1/tspm/projects`, h), {
    "projects 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/dashboard`, h), {
    "dashboard 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/scenarios`, h), {
    "scenarios 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/executions`, h), {
    "executions 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/requirements`, h), {
    "requirements 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/coverage-matrix`, h), {
    "coverage 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/schedules`, h), {
    "schedules 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/flows`, h), {
    "flows 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/regression-sets`, h), {
    "regression-sets 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/approvals`, h), {
    "approvals 200": (r) => r.status === 200,
  });
  sleep(0.5);

  check(http.get(`${BASE}/api/v1/tspm/projects/${pid}/analytics`, h), {
    "analytics 200": (r) => [200, 404].includes(r.status),
  });
  sleep(0.5);

  // ── Yazma işlemleri (daha seyrek) ───────────────────────────────────────

  if (__ITER % 3 === 0) {
    const sc = http.post(
      `${BASE}/api/v1/tspm/projects/${pid}/scenarios`,
      JSON.stringify({ title: `perf-sc-${__VU}-${__ITER}`, steps: [{ order: 0, text: "Adım" }] }),
      h
    );
    check(sc, { "create scenario 201": (r) => r.status === 201 });
    sleep(1);
  }

  sleep(1);
}
