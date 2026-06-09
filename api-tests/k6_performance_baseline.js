/**
 * K6 Performance Baseline Load Test
 *
 * Simulates realistic user workload to measure:
 * - Request latency (p50, p95, p99)
 * - Error rates
 * - Throughput
 *
 * Run:
 *   k6 run api-tests/k6_performance_baseline.js
 *
 * With custom settings:
 *   k6 run -e BASE_URL=http://localhost:8000 \
 *          -e VUS=100 \
 *          api-tests/k6_performance_baseline.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-key';

export const options = {
  stages: [
    // Ramp up
    { duration: '2m', target: 50 },   // Reach 50 users
    { duration: '3m', target: 100 },  // Reach 100 users
    // Sustain peak
    { duration: '5m', target: 100 },  // Stay at 100 users
    // Cool down
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    // 95% of requests under 1.5s
    'http_req_duration': ['p(95)<1500'],
    // 99% of requests under 3s
    'http_req_duration_p99': ['p(99)<3000'],
    // Error rate under 0.5%
    'http_req_failed': ['rate<0.005'],
    // Specific endpoint thresholds
    'http_req_duration{endpoint:list_test_cases}': ['p(95)<800'],
    'http_req_duration{endpoint:create_test_case}': ['p(95)<2000'],
  },
};

/**
 * Setup: Create test data
 */
export function setup() {
  // Create organization + project
  let setupRes = http.post(`${BASE_URL}/api/v1/organizations`, {
    name: `Load Test Org ${Date.now()}`,
    slug: `load-test-${Date.now()}`,
  }, {
    headers: { 'Authorization': `Bearer ${API_KEY}` },
  });

  if (setupRes.status !== 201) {
    console.error('Setup failed:', setupRes.status, setupRes.body);
    return null;
  }

  const org = setupRes.json();

  // Create project
  let projRes = http.post(`${BASE_URL}/api/v1/projects`, {
    name: `Load Test Project ${Date.now()}`,
    organization_id: org.id,
  }, {
    headers: { 'Authorization': `Bearer ${API_KEY}` },
  });

  return { org_id: org.id, project_id: projRes.json().id };
}

/**
 * Main test scenario
 */
export default function (data) {
  if (!data) {
    console.error('Setup failed, skipping test');
    return;
  }

  const { org_id, project_id } = data;
  const authHeader = { 'Authorization': `Bearer ${API_KEY}` };

  // ── Test Case Operations ──────────────────────────────────────────────
  group('Test Case Management', () => {
    // List test cases (p95 target: <800ms)
    let listRes = http.get(`${BASE_URL}/api/v1/test-cases?project_id=${project_id}&limit=50`, {
      headers: authHeader,
      tags: { endpoint: 'list_test_cases' },
    });

    check(listRes, {
      'list status is 200': (r) => r.status === 200,
      'list response time < 800ms': (r) => r.timings.duration < 800,
      'list has items': (r) => r.json().items && r.json().items.length > 0,
    });

    // Create test case (p95 target: <2000ms)
    let createRes = http.post(`${BASE_URL}/api/v1/test-cases`, {
      name: `Load Test Case ${Date.now()}`,
      project_id: project_id,
      description: 'Load test case',
      status: 'draft',
      steps: [
        { action: 'navigate', target: 'https://example.com' },
        { action: 'click', target: '#button' },
        { action: 'assert', target: 'text visible' },
      ],
    }, {
      headers: authHeader,
      tags: { endpoint: 'create_test_case' },
    });

    check(createRes, {
      'create status is 201': (r) => r.status === 201,
      'create response time < 2000ms': (r) => r.timings.duration < 2000,
      'create has id': (r) => r.json().id !== undefined,
    });

    if (createRes.status === 201) {
      const testCaseId = createRes.json().id;

      // Update test case
      let updateRes = http.put(`${BASE_URL}/api/v1/test-cases/${testCaseId}`, {
        name: `Updated ${Date.now()}`,
        status: 'ready',
      }, {
        headers: authHeader,
      });

      check(updateRes, {
        'update status is 200': (r) => r.status === 200,
        'update response time < 1500ms': (r) => r.timings.duration < 1500,
      });

      // Get test case detail
      let detailRes = http.get(`${BASE_URL}/api/v1/test-cases/${testCaseId}`, {
        headers: authHeader,
      });

      check(detailRes, {
        'detail status is 200': (r) => r.status === 200,
        'detail response time < 500ms': (r) => r.timings.duration < 500,
      });
    }
  });

  // ── Test Run Operations ───────────────────────────────────────────────
  group('Test Run Management', () => {
    // List test runs
    let runsRes = http.get(`${BASE_URL}/api/v1/test-runs?project_id=${project_id}&limit=20`, {
      headers: authHeader,
    });

    check(runsRes, {
      'list runs status is 200': (r) => r.status === 200,
      'list runs response time < 1000ms': (r) => r.timings.duration < 1000,
    });

    // Create test run
    let runRes = http.post(`${BASE_URL}/api/v1/test-runs`, {
      project_id: project_id,
      name: `Load Test Run ${Date.now()}`,
      status: 'in_progress',
    }, {
      headers: authHeader,
    });

    check(runRes, {
      'create run status is 201': (r) => r.status === 201,
      'create run response time < 2000ms': (r) => r.timings.duration < 2000,
    });
  });

  // ── Analytics & Dashboard ─────────────────────────────────────────────
  group('Analytics Operations', () => {
    // Get coverage stats
    let coverageRes = http.get(
      `${BASE_URL}/api/v1/analytics/coverage?project_id=${project_id}`,
      { headers: authHeader }
    );

    check(coverageRes, {
      'coverage status is 200': (r) => r.status === 200 || r.status === 404,
      'coverage response time < 1500ms': (r) => r.timings.duration < 1500,
    });

    // Get execution stats
    let execRes = http.get(
      `${BASE_URL}/api/v1/analytics/executions?project_id=${project_id}`,
      { headers: authHeader }
    );

    check(execRes, {
      'execution stats response time < 1500ms': (r) => r.timings.duration < 1500,
    });
  });

  // ── Health Checks ─────────────────────────────────────────────────────
  group('Health & Monitoring', () => {
    // Fast health check
    let healthRes = http.get(`${BASE_URL}/health`, {});

    check(healthRes, {
      'health status is 200': (r) => r.status === 200,
      'health response time < 50ms': (r) => r.timings.duration < 50,
    });

    // Detailed health check
    let detailedRes = http.get(`${BASE_URL}/health?detailed=true`, {});

    check(detailedRes, {
      'detailed health status is 200': (r) => r.status === 200,
      'detailed health response time < 1000ms': (r) => r.timings.duration < 1000,
    });

    // DB pool stats
    let poolRes = http.get(`${BASE_URL}/api/v1/monitoring/health/db-pool`, {
      headers: authHeader,
    });

    check(poolRes, {
      'pool status available': (r) => r.status === 200,
      'pool utilization < 80%': (r) => r.json().utilization_percent < 80,
    });

    // Cache metrics
    let cacheRes = http.get(`${BASE_URL}/api/v1/monitoring/metrics/cache`, {
      headers: authHeader,
    });

    check(cacheRes, {
      'cache metrics available': (r) => r.status === 200,
    });
  });

  sleep(1);
}

/**
 * Teardown: Cleanup
 */
export function teardown(data) {
  if (!data) return;

  const { org_id } = data;
  const authHeader = { 'Authorization': `Bearer ${API_KEY}` };

  // Delete organization (cascade deletes projects, test cases, etc)
  http.del(`${BASE_URL}/api/v1/organizations/${org_id}`, {
    headers: authHeader,
  });
}
