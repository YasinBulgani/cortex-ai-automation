/**
 * Nexus QA — k6 Yük Testi
 * ========================
 * Backend (FastAPI :8000) ve Engine (Flask :5001) API uç noktaları için
 * smoke / load / stress / spike senaryoları.
 *
 * Kullanım:
 *   k6 run tests/load/api-load.js                          # smoke (varsayılan)
 *   k6 run --env SCENARIO=load    tests/load/api-load.js   # yük testi
 *   k6 run --env SCENARIO=stress  tests/load/api-load.js   # stres testi
 *   k6 run --env SCENARIO=spike   tests/load/api-load.js   # ani yük testi
 *
 * Ortam değişkenleri (isteğe bağlı):
 *   BASE_URL      → varsayılan http://localhost:8000
 *   ENGINE_URL    → varsayılan http://localhost:5001
 *   TEST_EMAIL    → varsayılan admin@bgtest.dev
 *   TEST_PASSWORD → varsayılan admin123
 *   SCENARIO      → smoke | load | stress | spike  (varsayılan: smoke)
 *
 * Kurulum:
 *   https://k6.io/docs/get-started/installation/
 *   brew install k6   # macOS
 */

import http   from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ── Özel metrikler ─────────────────────────────────────────────────────────────
const errRate          = new Rate('error_rate');
const loginDur         = new Trend('login_duration_ms',        true);
const projectsDur      = new Trend('projects_list_ms',         true);
const scenariosDur     = new Trend('scenarios_list_ms',        true);
const execDur          = new Trend('executions_list_ms',       true);
const execFilteredDur  = new Trend('executions_filtered_ms',   true);
const mobileDevDur     = new Trend('mobile_devices_ms',        true);
const farmStatusDur    = new Trend('farm_status_ms',           true);
const requestCount     = new Counter('total_requests');

// ── Senaryo tanımları ─────────────────────────────────────────────────────────
const SCENARIOS = {
  /**
   * Smoke: 1 VU × 1 dk — temel sağlık doğrulaması.
   * Her PR/deploy sonrası CI'da çalıştırılması önerilir.
   */
  smoke: {
    executor: 'constant-vus',
    vus: 1,
    duration: '1m',
    gracefulStop: '10s',
  },

  /**
   * Load: 0 → 20 VU × 3 dk → 0 — normal üretim yükü.
   * Haftalık zamanlı testte kullanılır.
   */
  load: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 20 },
      { duration: '3m', target: 20 },
      { duration: '1m', target: 0  },
    ],
    gracefulRampDown: '30s',
  },

  /**
   * Stress: 0 → 50 VU × 2 dk → 0 — sistem limitlerini ölçer.
   * Yeni özellik / refactor sonrası çalıştırılır.
   */
  stress: {
    executor: 'ramping-vus',
    startVUs: 0,
    stages: [
      { duration: '2m', target: 50 },
      { duration: '2m', target: 50 },
      { duration: '1m', target: 0  },
    ],
    gracefulRampDown: '30s',
  },

  /**
   * Spike: ani 0 → 100 VU × 30 sn → 0 — DDoS benzeri ani yüklenme.
   * Aylık kapasite testinde çalıştırılır.
   */
  spike: {
    executor: 'ramping-arrival-rate',
    preAllocatedVUs: 100,
    maxVUs: 200,
    timeUnit: '1s',
    stages: [
      { duration: '10s', target: 5   },
      { duration: '30s', target: 100 },
      { duration: '10s', target: 0   },
    ],
  },
};

// ── Aktif senaryo seçimi ──────────────────────────────────────────────────────
const SCENARIO_NAME = __ENV.SCENARIO || 'smoke';
if (!SCENARIOS[SCENARIO_NAME]) {
  throw new Error(`Geçersiz SCENARIO: "${SCENARIO_NAME}". Geçerli değerler: ${Object.keys(SCENARIOS).join(', ')}`);
}

export const options = {
  scenarios: {
    [SCENARIO_NAME]: {
      ...SCENARIOS[SCENARIO_NAME],
      exec: 'mainFlow',
    },
  },
  thresholds: {
    // Genel HTTP
    'http_req_duration':    ['p(95)<500', 'p(99)<1500'],
    'http_req_failed':      ['rate<0.05'],
    // Özel metrikler
    'error_rate':           ['rate<0.05'],
    'login_duration_ms':    ['p(95)<400'],
    'projects_list_ms':     ['p(95)<200'],
    'scenarios_list_ms':    ['p(95)<200'],
    'executions_list_ms':   ['p(95)<300'],
    'executions_filtered_ms': ['p(95)<300'],
    'mobile_devices_ms':    ['p(95)<100'],
    'farm_status_ms':       ['p(95)<100'],
  },
};

// ── Yapılandırma ──────────────────────────────────────────────────────────────
const BASE_URL      = __ENV.BASE_URL       || 'http://localhost:8000';
const ENGINE_URL    = __ENV.ENGINE_URL     || 'http://localhost:5001';
const TEST_EMAIL    = __ENV.TEST_EMAIL     || 'admin@bgtest.dev';
const TEST_PASSWORD = __ENV.TEST_PASSWORD  || 'admin123';

// ── Kurulum — token + ilk proje ID'si al ─────────────────────────────────────
export function setup() {
  // 1. Login
  const loginStart = Date.now();
  const loginRes = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  loginDur.add(Date.now() - loginStart);
  requestCount.add(1);

  const loginOk = check(loginRes, {
    'setup: login 200':       (r) => r.status === 200,
    'setup: access_token var': (r) => {
      try { return !!JSON.parse(r.body).access_token; } catch { return false; }
    },
  });

  if (!loginOk || loginRes.status !== 200) {
    console.error(`[setup] Login başarısız: ${loginRes.status} — ${loginRes.body}`);
    return { token: null, projectId: null };
  }

  const token = JSON.parse(loginRes.body).access_token;

  // 2. İlk proje ID'sini al
  const projRes = http.get(`${BASE_URL}/api/v1/projects`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  requestCount.add(1);
  let projectId = null;
  if (projRes.status === 200) {
    try {
      const projects = JSON.parse(projRes.body);
      if (Array.isArray(projects) && projects.length > 0) {
        projectId = projects[0].id;
      }
    } catch (_) {}
  }

  console.log(`[setup] token alındı. projectId=${projectId || 'YOK — bazı testler atlanacak'}`);
  return { token, projectId };
}

// ── Ana test akışı ─────────────────────────────────────────────────────────────
export function mainFlow(data) {
  if (!data.token) {
    // Login başarısız olmuşsa bu VU'yu atla
    sleep(1);
    return;
  }

  const h = {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${data.token}`,
    },
  };

  // ── 1. Sağlık kontrolleri ────────────────────────────────────────────────
  group('01_health', function () {
    const r = http.get(`${BASE_URL}/health`);
    requestCount.add(1);
    const ok = check(r, { 'backend healthy': (r) => r.status === 200 });
    errRate.add(!ok);
  });

  // ── 2. Kimlik doğrulama — token yenileme simülasyonu ─────────────────────
  group('02_auth_refresh', function () {
    // Gerçek bir token refresh endpoint'i varsa burası güncellenir.
    // Şimdilik profile/me endpoint'i simüle eder.
    const r = http.get(`${BASE_URL}/api/v1/auth/me`, h);
    requestCount.add(1);
    const ok = check(r, { 'auth/me 200 ya da 404': (r) => r.status === 200 || r.status === 404 });
    // 404 kabul edilebilir (endpoint yoksa)
    errRate.add(r.status >= 500);
  });

  // ── 3. Proje listesi ─────────────────────────────────────────────────────
  group('03_projects', function () {
    const t0 = Date.now();
    const r = http.get(`${BASE_URL}/api/v1/projects`, h);
    projectsDur.add(Date.now() - t0);
    requestCount.add(1);
    const ok = check(r, {
      'projects 200':     (r) => r.status === 200,
      'projects is list': (r) => { try { return Array.isArray(JSON.parse(r.body)); } catch { return false; } },
    });
    errRate.add(!ok);
  });

  // Kalan gruplar proje ID'si gerektiriyor
  if (!data.projectId) {
    sleep(1);
    return;
  }
  const pid = data.projectId;

  // ── 4. Senaryo listesi ───────────────────────────────────────────────────
  group('04_scenarios', function () {
    const t0 = Date.now();
    const r = http.get(`${BASE_URL}/api/v1/projects/${pid}/scenarios`, h);
    scenariosDur.add(Date.now() - t0);
    requestCount.add(1);
    const ok = check(r, { 'scenarios 200': (r) => r.status === 200 });
    errRate.add(!ok);
  });

  // ── 5. İcra listesi (tümü + platform filtreleri) ─────────────────────────
  group('05_executions', function () {
    // Tümü
    const t0 = Date.now();
    const all = http.get(`${BASE_URL}/api/v1/projects/${pid}/executions`, h);
    execDur.add(Date.now() - t0);
    requestCount.add(1);
    check(all, { 'executions 200': (r) => r.status === 200 });
    errRate.add(all.status !== 200);

    // iOS filtresi
    const t1 = Date.now();
    const ios = http.get(`${BASE_URL}/api/v1/projects/${pid}/executions?platform=ios`, h);
    execFilteredDur.add(Date.now() - t1);
    requestCount.add(1);
    check(ios, { 'executions?platform=ios 200': (r) => r.status === 200 });

    // Android filtresi
    const t2 = Date.now();
    const android = http.get(`${BASE_URL}/api/v1/projects/${pid}/executions?platform=android`, h);
    execFilteredDur.add(Date.now() - t2);
    requestCount.add(1);
    check(android, { 'executions?platform=android 200': (r) => r.status === 200 });

    // Desktop filtresi
    const t3 = Date.now();
    const desktop = http.get(`${BASE_URL}/api/v1/projects/${pid}/executions?platform=desktop`, h);
    execFilteredDur.add(Date.now() - t3);
    requestCount.add(1);
    check(desktop, { 'executions?platform=desktop 200': (r) => r.status === 200 });
  });

  // ── 6. Zamanlama listesi (schedules) ────────────────────────────────────
  group('06_schedules', function () {
    const r = http.get(`${BASE_URL}/api/v1/projects/${pid}/schedules`, h);
    requestCount.add(1);
    check(r, { 'schedules 200 ya da 404': (r) => r.status === 200 || r.status === 404 });
    errRate.add(r.status >= 500);
  });

  // ── 7. Bildirimler ───────────────────────────────────────────────────────
  group('07_notifications', function () {
    const r = http.get(`${BASE_URL}/api/v1/notifications`, h);
    requestCount.add(1);
    check(r, { 'notifications 200 ya da 404': (r) => r.status === 200 || r.status === 404 });
    errRate.add(r.status >= 500);
  });

  // ── 8. Visium Farm — Engine API ──────────────────────────────────────────
  group('08_visium_farm', function () {
    // Cihaz listesi
    const t0 = Date.now();
    const devRes = http.get(`${ENGINE_URL}/api/mobile/devices`);
    mobileDevDur.add(Date.now() - t0);
    requestCount.add(1);
    check(devRes, {
      'devices 200':        (r) => r.status === 200,
      'devices array':      (r) => { try { return Array.isArray(JSON.parse(r.body)); } catch { return false; } },
      'devices count >= 1': (r) => { try { return JSON.parse(r.body).length >= 1; } catch { return false; } },
    });
    errRate.add(devRes.status !== 200);

    // Farm durumu
    const t1 = Date.now();
    const fs = http.get(`${ENGINE_URL}/api/mobile/farm-status`);
    farmStatusDur.add(Date.now() - t1);
    requestCount.add(1);
    check(fs, {
      'farm-status 200':        (r) => r.status === 200,
      'farm-status has field':   (r) => { try { return !!JSON.parse(r.body).active_farm; } catch { return false; } },
    });
    errRate.add(fs.status !== 200);
  });

  // ── 9. AI — Varlık doğrulaması ───────────────────────────────────────────
  group('09_ai_health', function () {
    // /api/v1/ai/health varsa kontrol et; yoksa 404 kabul edilebilir
    const r = http.get(`${BASE_URL}/api/v1/ai/health`, h);
    requestCount.add(1);
    check(r, { 'ai health 200 ya da 404': (r) => r.status === 200 || r.status === 404 });
    errRate.add(r.status >= 500);
  });

  // Gerçekçi kullanıcı gecikmesi: 0.5 – 2 saniye arası
  sleep(Math.random() * 1.5 + 0.5);
}

// ── Temizlik ──────────────────────────────────────────────────────────────────
export function teardown(data) {
  console.log(
    `\n✅ Yük testi tamamlandı`
    + `\n   Senaryo:    ${SCENARIO_NAME}`
    + `\n   Proje ID:   ${data.projectId || 'N/A'}`
    + `\n   BASE_URL:   ${BASE_URL}`
    + `\n   ENGINE_URL: ${ENGINE_URL}`,
  );
}
