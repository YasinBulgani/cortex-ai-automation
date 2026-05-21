"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiError } from "@/lib/api";

/* ─────────────────────────────────────────────────────────────
 * MOBİL OTOMASYON — Neurex QA
 * ─────────────────────────────────────────────────────────────
 *  - 10 sanal cihaz (6 Android AVD + 4 iOS Simulator)
 *  - LLM destekli doğal dil → Appium adımları
 *  - Paralel koşu simülasyonu (session orchestrator, canlı loglar)
 *  - Fiziksel cihaz kayıt (onboarding modal)
 *  - Araştırma raporu özeti + tam rapora link
 *
 *  Not: Backend endpoint'leri (F1 fazında) şöyle olacak:
 *    GET  /api/v1/mobile/devices
 *    POST /api/v1/mobile/sessions
 *    POST /api/v1/mobile/generate-from-prompt
 *  Şu an prototip — mock state + client-side simülasyon.
 * ─────────────────────────────────────────────────────────── */

type Platform = "android" | "ios";
type DeviceKind = "emulator" | "simulator" | "physical";
type DeviceStatus = "idle" | "running" | "booting" | "offline" | "error";

type Device = {
  id: string;
  name: string;
  platform: Platform;
  osVersion: string;
  profile: string;
  kind: DeviceKind;
  status: DeviceStatus;
  battery: number;
  cpuPct: number;
  ramPct: number;
  appiumPort: number;
  currentStep?: string;
  stepsDone: number;
  stepsTotal: number;
  healStreak: number;
};

type AppiumAction = {
  action: "launch" | "find" | "tap" | "sendKeys" | "verifyVisible" | "wait" | "swipe";
  by?: "accessibilityId" | "xpath" | "predicate";
  value?: string;
  text?: string;
  timeout?: number;
  ms?: number;
  direction?: "up" | "down" | "left" | "right";
};

type Session = {
  id: string;
  deviceId: string;
  scenarioName: string;
  status: "queued" | "running" | "passed" | "failed";
  startedAt: number;
  finishedAt?: number;
  healed: number;
};

type LogEntry = {
  id: number;
  ts: number;
  level: "info" | "warn" | "error" | "llm" | "heal";
  deviceId?: string;
  sessionId?: string;
  message: string;
};

/* ─── Seed device farm (10 cihaz) ────────────────────────────── */
const INITIAL_DEVICES: Device[] = [
  { id: "and-01", name: "Pixel 8",             platform: "android", osVersion: "14", profile: "pixel_8",       kind: "emulator",  status: "idle",    battery: 92, cpuPct: 8,  ramPct: 34, appiumPort: 4723, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-02", name: "Pixel 8 Pro",         platform: "android", osVersion: "14", profile: "pixel_8_pro",   kind: "emulator",  status: "idle",    battery: 88, cpuPct: 6,  ramPct: 38, appiumPort: 4724, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-03", name: "Galaxy S23 (OneUI)",  platform: "android", osVersion: "13", profile: "galaxy_s23",    kind: "emulator",  status: "idle",    battery: 74, cpuPct: 12, ramPct: 42, appiumPort: 4725, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-04", name: "Pixel 6",             platform: "android", osVersion: "12", profile: "pixel_6",       kind: "emulator",  status: "idle",    battery: 100,cpuPct: 4,  ramPct: 30, appiumPort: 4726, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-05", name: "Pixel 5 (legacy)",    platform: "android", osVersion: "11", profile: "pixel_5",       kind: "emulator",  status: "idle",    battery: 67, cpuPct: 9,  ramPct: 40, appiumPort: 4727, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "and-06", name: "Nexus 5X (legacy)",   platform: "android", osVersion: "9",  profile: "nexus_5x",      kind: "emulator",  status: "offline", battery: 0,  cpuPct: 0,  ramPct: 0,  appiumPort: 4728, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-01", name: "iPhone 15 Pro",       platform: "ios",     osVersion: "17", profile: "iphone_15_pro", kind: "simulator", status: "idle",    battery: 95, cpuPct: 5,  ramPct: 28, appiumPort: 4730, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-02", name: "iPhone 15",           platform: "ios",     osVersion: "17", profile: "iphone_15",     kind: "simulator", status: "idle",    battery: 84, cpuPct: 7,  ramPct: 31, appiumPort: 4731, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-03", name: "iPhone 14",           platform: "ios",     osVersion: "16", profile: "iphone_14",     kind: "simulator", status: "idle",    battery: 62, cpuPct: 11, ramPct: 36, appiumPort: 4732, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
  { id: "ios-04", name: "iPhone SE (3rd)",     platform: "ios",     osVersion: "15", profile: "iphone_se_3",   kind: "simulator", status: "idle",    battery: 77, cpuPct: 6,  ramPct: 29, appiumPort: 4733, stepsDone: 0, stepsTotal: 0, healStreak: 0 },
];

/* ─── Örnek senaryolar ──────────────────────────────────────── */
const SAMPLE_PROMPTS = [
  "Uygulamayı aç, Giriş yap butonuna bas, email alanına test@bgts.ai yaz, şifre alanına Test123! yaz, Devam'a bas, ana sayfanın yüklendiğini doğrula.",
  "Onboarding ekranlarını geç, bildirim izinlerini reddet, dil olarak Türkçe seç, hesap oluştur sayfasının açıldığını doğrula.",
  "Ürün arama kutusuna 'kahve' yaz, filtreyi 'fiyat artan' yap, ilk ürünü sepete ekle, sepet sayacının 1 olduğunu doğrula.",
  "Profil sayfasına git, 'Çıkış Yap' butonuna bas, onay dialog'unda 'Evet' seç, login sayfasına döndüğünü doğrula.",
];

/* ─── LLM adım dönüştürme — istemci tarafı mock ─────────────── */
function mockLLMStepper(prompt: string, platform: Platform): AppiumAction[] {
  const steps: AppiumAction[] = [{ action: "launch" }];
  const lower = prompt.toLowerCase();
  // Basit kural tabanlı mock — gerçek LLM çağrısına ikame
  if (lower.includes("giriş yap") || lower.includes("login")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "login_button", timeout: 5000 },
      { action: "tap" },
    );
  }
  if (lower.includes("email")) {
    const m = prompt.match(/[\w.+-]+@[\w-]+\.[\w.-]+/);
    steps.push(
      { action: "find", by: "accessibilityId", value: "email_input" },
      { action: "sendKeys", text: m?.[0] ?? "test@example.com" },
    );
  }
  if (lower.includes("şifre") || lower.includes("password")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "password_input" },
      { action: "sendKeys", text: "Test123!" },
    );
  }
  if (lower.includes("devam") || lower.includes("gönder") || lower.includes("submit")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "submit_button" },
      { action: "tap" },
    );
  }
  if (lower.includes("onboarding") || lower.includes("dil")) {
    steps.push(
      { action: "find", by: platform === "ios" ? "predicate" : "accessibilityId", value: "onboarding_skip" },
      { action: "tap" },
      { action: "wait", ms: 500 },
      { action: "find", by: "accessibilityId", value: "lang_tr" },
      { action: "tap" },
    );
  }
  if (lower.includes("ara") || lower.includes("arama") || lower.includes("search")) {
    const q = prompt.match(/'([^']+)'/)?.[1] ?? "kahve";
    steps.push(
      { action: "find", by: "accessibilityId", value: "search_input" },
      { action: "sendKeys", text: q },
    );
  }
  if (lower.includes("sepet")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "add_to_cart" },
      { action: "tap" },
      { action: "verifyVisible", by: "accessibilityId", value: "cart_badge_1", timeout: 3000 },
    );
  }
  if (lower.includes("çıkış")) {
    steps.push(
      { action: "find", by: "accessibilityId", value: "profile_tab" },
      { action: "tap" },
      { action: "find", by: "accessibilityId", value: "logout_button" },
      { action: "tap" },
      { action: "find", by: "accessibilityId", value: "confirm_yes" },
      { action: "tap" },
      { action: "verifyVisible", by: "accessibilityId", value: "login_screen", timeout: 5000 },
    );
  }
  if (lower.includes("ana sayfa") || lower.includes("doğrula")) {
    steps.push({ action: "verifyVisible", by: "accessibilityId", value: "home_screen", timeout: 8000 });
  }
  // Eğer kurallar hiç eşleşmediyse, makul bir fallback
  if (steps.length === 1) {
    steps.push(
      { action: "wait", ms: 1000 },
      { action: "verifyVisible", by: "accessibilityId", value: "app_root", timeout: 5000 },
    );
  }
  return steps;
}

/* ─── Yardımcılar ───────────────────────────────────────────── */
const rnd = (min: number, max: number) => Math.random() * (max - min) + min;
const rndInt = (min: number, max: number) => Math.floor(rnd(min, max));
const fmtMs = (ms: number) => (ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`);

function statusPill(s: DeviceStatus) {
  const map: Record<DeviceStatus, string> = {
    idle:    "bg-slate-500/15 text-slate-300 border-slate-500/30",
    running: "bg-blue-500/15 text-blue-300 border-blue-500/30 animate-pulse",
    booting: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    offline: "bg-slate-700/40 text-slate-500 border-slate-600/40",
    error:   "bg-red-500/15 text-red-300 border-red-500/30",
  };
  const label: Record<DeviceStatus, string> = {
    idle: "hazır", running: "çalışıyor", booting: "açılıyor", offline: "kapalı", error: "hata",
  };
  return <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${map[s]}`}>{label[s]}</span>;
}

function platformBadge(p: Platform, os: string, kind: DeviceKind) {
  const color = p === "ios" ? "text-slate-200" : "text-emerald-300";
  const icon  = p === "ios" ? "" : "🤖";
  const kindLabel = kind === "emulator" ? "emu" : kind === "simulator" ? "sim" : "fiz";
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] ${color}`}>
      <span className="text-sm leading-none">{icon}</span>
      <span className="font-medium">{p === "ios" ? "iOS" : "Android"} {os}</span>
      <span className="rounded bg-slate-800 px-1 text-[9px] uppercase tracking-wide text-slate-400">{kindLabel}</span>
    </span>
  );
}

/* ─── Backend ↔ UI tip adaptörü ────────────────────────────── */
type BackendDevice = {
  id: string;
  name: string;
  platform: Platform;
  os_version: string;
  profile: string;
  kind: DeviceKind;
  status: DeviceStatus;
  battery: number;
  cpu_pct: number;
  ram_pct: number;
  current_step?: string | null;
  steps_done: number;
  steps_total: number;
  heal_streak: number;
  appium_url: string;
};

function fromBackendDevice(d: BackendDevice): Device {
  const portMatch = d.appium_url?.match(/:(\d+)/);
  return {
    id: d.id,
    name: d.name,
    platform: d.platform,
    osVersion: d.os_version,
    profile: d.profile,
    kind: d.kind,
    status: d.status,
    battery: d.battery,
    cpuPct: d.cpu_pct,
    ramPct: d.ram_pct,
    appiumPort: portMatch ? Number(portMatch[1]) : 4723,
    currentStep: d.current_step ?? undefined,
    stepsDone: d.steps_done,
    stepsTotal: d.steps_total,
    healStreak: d.heal_streak,
  };
}

type BackendStepResp = {
  steps: AppiumAction[];
  model: string;
  fallback_used: boolean;
};

type SeedScenario = {
  id: string;
  title: string;
  category: string;
  difficulty: "kolay" | "orta" | "zor";
  platforms: string[];
  description: string;
  prompt: string;
  expected_steps: number;
  tags: string[];
};

/* ═══════════════════════════════════════════════════════════════ */
export default function MobilOtomasyonPage() {
  const [devices, setDevices] = useState<Device[]>(INITIAL_DEVICES);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logSeq = useRef(1);

  /* Backend sağlık durumu: 'probing' | 'connected' | 'mock' */
  const [backendMode, setBackendMode] = useState<"probing" | "connected" | "mock">("probing");
  const [llmModel, setLlmModel] = useState<string>("heuristic-tr");

  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0]);
  const [scenarioName, setScenarioName] = useState("Örnek Senaryo");
  const [targetPlatform, setTargetPlatform] = useState<"both" | Platform>("both");
  const [parallel, setParallel] = useState(4);
  const [passRate, setPassRate] = useState(82);
  const [healRate, setHealRate] = useState(35);
  const [generatedSteps, setGeneratedSteps] = useState<AppiumAction[] | null>(null);
  const [showPhysicalModal, setShowPhysicalModal] = useState(false);
  const [showReportPanel, setShowReportPanel] = useState(false);
  const [activeDeviceId, setActiveDeviceId] = useState<string | null>(null);
  const [showDeviceScreen, setShowDeviceScreen] = useState(false);

  /* Seed senaryo galerisi */
  const [seedScenarios, setSeedScenarios] = useState<SeedScenario[]>([]);
  const [seedFilter, setSeedFilter] = useState<string>("all");

  /* ─── Canlı metrik drift — sadece idle olmayan cihazlarda ── */
  useEffect(() => {
    const t = setInterval(() => {
      setDevices((prev) =>
        prev.map((d) => {
          if (d.status === "offline") return d;
          const cpu = Math.max(2, Math.min(98, d.cpuPct + rndInt(-3, 4)));
          const ram = Math.max(18, Math.min(92, d.ramPct + rndInt(-2, 3)));
          const battery = d.status === "running" ? Math.max(5, d.battery - (Math.random() < 0.15 ? 1 : 0)) : d.battery;
          return { ...d, cpuPct: cpu, ramPct: ram, battery };
        })
      );
    }, 1500);
    return () => clearInterval(t);
  }, []);

  const pushLog = useCallback((entry: Omit<LogEntry, "id" | "ts">) => {
    setLogs((p) => [
      { id: logSeq.current++, ts: Date.now(), ...entry },
      ...p.slice(0, 199),
    ]);
  }, []);

  /* ─── Backend probe: mount'ta cihaz + seed senaryoları çek ─── */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await apiFetch<BackendDevice[]>("/api/v1/mobile/devices");
        if (cancelled) return;
        if (Array.isArray(list) && list.length > 0) {
          setDevices(list.map(fromBackendDevice));
          setBackendMode("connected");
          pushLog({ level: "info", message: `✓ Backend bağlantısı kuruldu — ${list.length} cihaz yüklendi (/api/v1/mobile)` });
          // Seed senaryoları da çek
          try {
            const seeds = await apiFetch<SeedScenario[]>("/api/v1/mobile/scenarios/seed");
            if (!cancelled && Array.isArray(seeds)) {
              setSeedScenarios(seeds);
              pushLog({ level: "info", message: `✓ ${seeds.length} seed senaryo yüklendi` });
            }
          } catch (err) { console.warn("[mobil-otomasyon]:", err); }
        } else {
          setBackendMode("mock");
          pushLog({ level: "warn", message: "Backend boş liste döndü — mock mod devrede" });
        }
      } catch (err) {
        if (cancelled) return;
        setBackendMode("mock");
        const msg = err instanceof ApiError ? `HTTP ${err.status}` : "erişilemez";
        pushLog({ level: "warn", message: `Backend ${msg} — client-side mock mod kullanılıyor` });
      }
    })();
    return () => { cancelled = true; };
  }, [pushLog]);

  /* ─── Cihaz listesini periyodik tazele (backend modda) ────── */
  useEffect(() => {
    if (backendMode !== "connected") return;
    const t = setInterval(async () => {
      try {
        const list = await apiFetch<BackendDevice[]>("/api/v1/mobile/devices");
        if (Array.isArray(list)) setDevices(list.map(fromBackendDevice));
      } catch (err) { console.warn("[mobil-otomasyon]:", err); }
    }, 3000);
    return () => clearInterval(t);
  }, [backendMode]);

  /* ─── LLM adım üretimi — backend→fallback mock ────────────── */
  async function handleGenerate() {
    if (!prompt.trim()) return;
    pushLog({ level: "llm", message: `LLM senaryo üretimi başlatıldı (${prompt.length} karakter)` });
    const plat: Platform = targetPlatform === "ios" ? "ios" : "android";

    if (backendMode === "connected") {
      try {
        const res = await apiFetch<BackendStepResp>("/api/v1/mobile/generate-from-prompt", {
          method: "POST",
          json: { prompt, platform: plat },
        });
        setGeneratedSteps(res.steps);
        setLlmModel(res.model);
        pushLog({
          level: "llm",
          message: `✓ ${res.steps.length} adım üretildi — model: ${res.model}${res.fallback_used ? " (fallback)" : ""}`,
        });
        return;
      } catch (err) {
        pushLog({ level: "warn", message: `Backend stepper hata — client-side fallback` });
      }
    }
    await new Promise((r) => setTimeout(r, 400));
    const steps = mockLLMStepper(prompt, plat);
    setGeneratedSteps(steps);
    setLlmModel("heuristic-client");
    pushLog({ level: "llm", message: `✓ ${steps.length} adım üretildi (client-side heuristic)` });
  }

  /* ─── Paralel koşu — önce backend, olmazsa client simülasyon ─ */
  async function handleRunSuite() {
    const steps = generatedSteps ?? mockLLMStepper(prompt, "android");
    if (!steps.length) { pushLog({ level: "error", message: "Adım yok — önce senaryo üretin" }); return; }

    if (backendMode === "connected") {
      try {
        type BackendSession = { id: string; device_id: string; scenario_name: string; status: string };
        const started = await apiFetch<BackendSession[]>("/api/v1/mobile/sessions", {
          method: "POST",
          json: {
            scenario_name: scenarioName,
            prompt,
            platform: targetPlatform,
            parallel,
            pass_rate: passRate,
            heal_rate: healRate,
          },
        });
        pushLog({ level: "info", message: `🚀 Backend'de ${started.length} session başlatıldı — canlı stream'ler açılıyor` });
        // Her session için SSE aç
        started.forEach((s) => {
          subscribeToSession(s.id, s.device_id, s.scenario_name, steps.length);
          setSessions((p) => [
            { id: s.id, deviceId: s.device_id, scenarioName: s.scenario_name, status: "running", startedAt: Date.now(), healed: 0 },
            ...p,
          ]);
        });
        return;
      } catch (err) {
        pushLog({ level: "warn", message: `Backend session start hata — client-side simülasyona dönülüyor` });
      }
    }

    // Client-side simülasyon (fallback)
    const pool = devices.filter((d) => {
      if (d.status === "offline") return false;
      if (targetPlatform === "both") return true;
      return d.platform === targetPlatform;
    });
    const selected = pool.slice(0, parallel);
    if (!selected.length) { pushLog({ level: "error", message: "Uygun cihaz yok" }); return; }

    pushLog({ level: "info", message: `🚀 "${scenarioName}" — ${selected.length} cihazda paralel başlıyor` });

    for (const d of selected) {
      const sessionId = `s_${Date.now()}_${d.id}`;
      const newSession: Session = {
        id: sessionId, deviceId: d.id, scenarioName,
        status: "running", startedAt: Date.now(), healed: 0,
      };
      setSessions((p) => [newSession, ...p]);
      setDevices((p) => p.map((x) => x.id === d.id
        ? { ...x, status: "running", stepsDone: 0, stepsTotal: steps.length, currentStep: steps[0].action }
        : x));
      pushLog({ level: "info", deviceId: d.id, sessionId, message: `[${d.name}] session başladı — ${steps.length} adım` });

      // adım adım ilerle — async
      void runSession(d, steps, sessionId);
    }
  }

  async function runSession(device: Device, steps: AppiumAction[], sessionId: string) {
    let healed = 0;
    let failedAt: number | null = null;
    for (let i = 0; i < steps.length; i++) {
      await new Promise((r) => setTimeout(r, rndInt(400, 1100)));
      const step = steps[i];
      // Rastgele self-heal olayı
      const stepShouldHeal = Math.random() * 100 < healRate / steps.length;
      if (stepShouldHeal && step.action === "find") {
        healed++;
        pushLog({
          level: "heal",
          deviceId: device.id,
          sessionId,
          message: `[${device.name}] locator '${step.value}' bulunamadı → LLM önerisi: xpath fallback uygulandı`,
        });
        await new Promise((r) => setTimeout(r, 600));
      }

      setDevices((p) => p.map((x) => x.id === device.id
        ? { ...x, stepsDone: i + 1, currentStep: step.action, healStreak: healed }
        : x));

      if (Math.random() > 0.995 && step.action !== "launch") {
        pushLog({ level: "warn", deviceId: device.id, sessionId, message: `[${device.name}] ağ gecikmesi — yeniden deneme` });
      }
    }
    // Bitiş kararı — passRate ile kumar
    const passed = Math.random() * 100 < passRate;
    if (!passed) failedAt = rndInt(Math.max(0, steps.length - 3), steps.length);

    setSessions((p) => p.map((s) => s.id === sessionId
      ? { ...s, status: passed ? "passed" : "failed", finishedAt: Date.now(), healed }
      : s));
    setDevices((p) => p.map((x) => x.id === device.id
      ? { ...x, status: "idle", currentStep: undefined, stepsDone: 0, stepsTotal: 0 }
      : x));
    pushLog({
      level: passed ? "info" : "error",
      deviceId: device.id,
      sessionId,
      message: passed
        ? `✅ [${device.name}] PASSED — ${steps.length} adım, ${healed} self-heal`
        : `❌ [${device.name}] FAILED adım #${failedAt} (${steps[failedAt ?? 0]?.action})`,
    });
  }

  /* ─── SSE: backend session'a abone ol ──────────────────────── */
  function subscribeToSession(sessionId: string, deviceId: string, name: string, totalSteps: number) {
    // EventSource ile canlı adım event'leri
    const base = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");
    const url = `${base}/api/v1/mobile/sessions/${sessionId}/stream`;
    let es: EventSource | null = null;
    try {
      es = new EventSource(url, { withCredentials: false });
    } catch {
      pushLog({ level: "warn", sessionId, deviceId, message: `SSE desteklenmiyor — session bitince refresh yapılacak` });
      return;
    }

    const onStep = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        const { seq, action, done, total } = data.payload || {};
        setDevices((p) => p.map((d) => d.id === deviceId
          ? { ...d, stepsDone: done ?? d.stepsDone, stepsTotal: total ?? d.stepsTotal, currentStep: action, status: "running" }
          : d));
      } catch { /* ignore */ }
    };
    const onHeal = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        pushLog({
          level: "heal", sessionId, deviceId,
          message: `[${name}] 🔧 heal #${data.payload?.seq} → ${data.payload?.decision}: ${data.payload?.reason ?? ""}`,
        });
        setDevices((p) => p.map((d) => d.id === deviceId ? { ...d, healStreak: d.healStreak + 1 } : d));
      } catch { /* ignore */ }
    };
    const onDone = (ev: MessageEvent) => {
      try {
        const data = JSON.parse(ev.data);
        const passed = data.payload?.status === "passed";
        setSessions((p) => p.map((s) => s.id === sessionId
          ? { ...s, status: passed ? "passed" : "failed", finishedAt: Date.now(), healed: data.payload?.healed ?? s.healed }
          : s));
        setDevices((p) => p.map((d) => d.id === deviceId
          ? { ...d, status: "idle", stepsDone: 0, stepsTotal: 0, currentStep: undefined }
          : d));
        pushLog({
          level: passed ? "info" : "error", sessionId, deviceId,
          message: passed
            ? `✅ [${name}] PASSED — ${data.payload?.healed ?? 0} self-heal`
            : `❌ [${name}] FAILED adım #${data.payload?.failed_at ?? "?"}`,
        });
      } catch { /* ignore */ }
      es?.close();
    };

    es.addEventListener("step", onStep);
    es.addEventListener("heal", onHeal);
    es.addEventListener("done", onDone);
    es.onerror = () => {
      pushLog({ level: "warn", sessionId, deviceId, message: `SSE bağlantısı koptu — ${totalSteps} adım bitişi bekleniyor` });
      es?.close();
    };
  }

  /* ─── Cihaz aksiyonları ───────────────────────────────────── */
  function rebootDevice(id: string) {
    if (backendMode === "connected") {
      apiFetch(`/api/v1/mobile/devices/${id}/reboot`, { method: "POST" })
        .then(() => pushLog({ level: "info", deviceId: id, message: `Backend reboot tetiklendi` }))
        .catch(() => pushLog({ level: "warn", deviceId: id, message: `Backend reboot başarısız — client-side mock` }));
    }
    setDevices((p) => p.map((d) => d.id === id ? { ...d, status: "booting", battery: Math.max(d.battery, 80), cpuPct: 5, ramPct: 22 } : d));
    pushLog({ level: "info", deviceId: id, message: `Cihaz yeniden başlatılıyor…` });
    setTimeout(() => {
      setDevices((p) => p.map((d) => d.id === id ? { ...d, status: "idle" } : d));
      pushLog({ level: "info", deviceId: id, message: `✓ Cihaz hazır` });
    }, 2200);
  }

  /* ─── Metrikler ───────────────────────────────────────────── */
  const stats = useMemo(() => {
    const total = devices.length;
    const online = devices.filter((d) => d.status !== "offline").length;
    const running = devices.filter((d) => d.status === "running").length;
    const recent = sessions.slice(0, 40);
    const passed = recent.filter((s) => s.status === "passed").length;
    const failed = recent.filter((s) => s.status === "failed").length;
    const heals = recent.reduce((acc, s) => acc + s.healed, 0);
    return { total, online, running, passed, failed, heals };
  }, [devices, sessions]);

  const activeDevice = devices.find((d) => d.id === activeDeviceId);

  /* ─── Render ──────────────────────────────────────────────── */
  return (
    <div className="mx-auto max-w-7xl space-y-6" data-testid="mobil-otomasyon-page">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-semibold tracking-tight">📱 Mobil Otomasyon</h1>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium
                ${backendMode === "connected"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : backendMode === "probing"
                    ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                    : "border-slate-700 bg-slate-800/40 text-slate-400"}`}
              title={
                backendMode === "connected"
                  ? "Backend /api/v1/mobile erişilebilir — canlı veri"
                  : backendMode === "mock"
                    ? "Backend erişilemez — tarayıcı içinde simülasyon"
                    : "Backend yokluyor…"
              }
            >
              <span className={`h-1.5 w-1.5 rounded-full ${
                backendMode === "connected" ? "bg-emerald-400 animate-pulse"
                : backendMode === "probing" ? "bg-amber-400 animate-pulse"
                : "bg-slate-500"
              }`} />
              {backendMode === "connected" ? "Backend bağlı" : backendMode === "probing" ? "Bağlanıyor…" : "Mock mod"}
            </span>
            {llmModel && backendMode === "connected" && (
              <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-0.5 text-[11px] text-violet-300">
                🧠 {llmModel}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            LLM destekli Appium grid — şu an 10 sanal cihaz, fiziksel cihazlar için hazır altyapı
          </p>
          <div className="mt-3 inline-flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[12px] text-amber-200">
            <span className="text-base leading-none">⚠️</span>
            <div>
              <p className="font-semibold">DEV / DEMO Modu</p>
              <p className="mt-0.5 text-amber-200/80">
                Bu sayfa tamamen <strong>mock veri</strong> ile çalışır. Gerçek Appium grid ya da fiziksel cihaz bağlantısı yoktur.
                Production kullanım için <code className="rounded bg-amber-500/10 px-1">Visium Mobile</code> ürününü kullanın.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button type="button" variant="secondary" onClick={() => setShowReportPanel((v) => !v)}>
            📄 Araştırma Raporu
          </Button>
          <Button type="button" onClick={() => setShowPhysicalModal(true)}>
            ➕ Fiziksel Cihaz Kaydet
          </Button>
        </div>
      </div>

      {/* Rapor paneli (in-UI özet) */}
      {showReportPanel && (
        <section className="rounded-lg border border-blue-500/30 bg-blue-500/5 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-blue-300">Araştırma Raporu — Özet</h2>
            <button type="button" onClick={() => setShowReportPanel(false)} className="text-xs text-slate-400 hover:text-white">✕ Kapat</button>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Neurex QA için <b>Appium 2.x + LLM</b> üçlü katmanlı mimari önerilir: (1) NL→Appium stepper, (2) self-healing
            locator, (3) multimodal görsel doğrulayıcı. Şu an 10 sanal cihaz (6 Android AVD, 4 iOS Sim);
            fiziksel geçiş için Mac Mini M2 + USB-Hub15 + 10 telefon (~464K ₺ CAPEX).
            Rakiplerden (BrowserStack, Kobiton, Sofy) farkınız: <b>on-prem + KVKK + Türkçe + sentetik veri entegre</b>.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {[
              ["Mimari", "Appium 2 + Device Broker + LLM Gateway"],
              ["LLM 1", "Senaryo Yazıcı (NL→Gherkin→Appium)"],
              ["LLM 2", "Self-Healing Locator"],
              ["LLM 3", "Görsel Doğrulayıcı (GPT-4o/Gemini)"],
              ["Faz 1", "4 hafta — 10 sanal cihaz MVP"],
              ["Faz 3", "6 hafta — 10 fiziksel cihaz"],
              ["Maliyet/1K test", "~$10 (Gemini Flash)"],
            ].map(([k, v]) => (
              <div key={k} className="rounded border border-slate-800 bg-slate-950/40 px-3 py-1.5">
                <span className="block text-[10px] uppercase tracking-wide text-slate-500">{k}</span>
                <span className="block text-[11px] text-slate-200">{v}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-4 pt-2 border-t border-slate-800/50">
            <a
              href="/docs/mobil-otomasyon-rapor"
              className="text-xs text-blue-400 hover:underline"
              onClick={(e) => {
                e.preventDefault();
                window.open("/docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md", "_blank");
              }}
            >
              📖 Tam Raporu Aç (18 bölüm, ~9K kelime)
            </a>
            <span className="text-[11px] text-slate-500">
              • Dosya: <code className="font-mono">docs/MOBIL_OTOMASYON_ARASTIRMA_RAPORU.md</code>
            </span>
          </div>
        </section>
      )}

      {/* ── Stats row ── */}
      <div className="grid gap-3 grid-cols-2 md:grid-cols-6">
        {[
          { label: "Toplam Cihaz", value: stats.total,   color: "text-slate-200" },
          { label: "Online",       value: stats.online,  color: "text-emerald-300" },
          { label: "Çalışan",      value: stats.running, color: "text-blue-300" },
          { label: "Son Pass",     value: stats.passed,  color: "text-emerald-400" },
          { label: "Son Fail",     value: stats.failed,  color: "text-red-400" },
          { label: "Self-Heal",    value: stats.heals,   color: "text-amber-300" },
        ].map((s) => (
          <div key={s.label} className="rounded-lg border border-slate-800 bg-slate-900/30 px-3 py-2.5">
            <p className="text-[10px] uppercase tracking-wide text-slate-500">{s.label}</p>
            <p className={`mt-0.5 text-xl font-semibold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════ */}
      {/* LLM senaryo üretici                             */}
      {/* ═══════════════════════════════════════════════ */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold">🧠 LLM Senaryo Üretici</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Doğal dil → Gherkin → Appium aksiyonları. AI Gateway üzerinden GPT-4o / Gemini Flash.
            </p>
          </div>
          <div className="flex items-center gap-1">
            {(["both", "android", "ios"] as const).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setTargetPlatform(p)}
                className={`rounded px-2.5 py-1 text-[11px] font-medium border transition-colors
                  ${targetPlatform === p
                    ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                    : "border-slate-800 text-slate-400 hover:border-slate-600"}`}
              >
                {p === "both" ? "Tümü" : p === "ios" ? "iOS" : "Android"}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 grid gap-4 lg:grid-cols-[1fr_360px]">
          {/* Prompt alanı */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <label className="text-xs text-slate-400">Senaryo Adı</label>
              <div className="flex gap-1.5 flex-wrap">
                {SAMPLE_PROMPTS.map((s, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => { setPrompt(s); setScenarioName(["Login", "Onboarding", "Arama+Sepet", "Çıkış"][i]); }}
                    className="rounded border border-slate-800 px-2 py-0.5 text-[10px] text-slate-400 hover:border-blue-500/40 hover:text-blue-300"
                  >
                    örnek {i + 1}
                  </button>
                ))}
              </div>
            </div>
            <Input value={scenarioName} onChange={(e) => setScenarioName(e.target.value)} placeholder="Senaryo adı" />
            <textarea
              rows={5}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Örn: Uygulamayı aç, giriş yap butonuna bas, email alanına test@bgts.ai yaz…"
              className="w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Paralel:</span>
                <input
                  type="number" min={1} max={10} value={parallel}
                  onChange={(e) => setParallel(Math.max(1, Math.min(10, Number(e.target.value))))}
                  className="h-8 w-16 rounded border border-slate-800 bg-slate-900 px-2 text-xs"
                />
              </div>
              <div className="flex items-center gap-2 min-w-[180px]">
                <span className="text-xs text-slate-400">Başarı %{passRate}</span>
                <input type="range" min={30} max={100} value={passRate} onChange={(e) => setPassRate(Number(e.target.value))} className="flex-1 accent-blue-500" />
              </div>
              <div className="flex items-center gap-2 min-w-[180px]">
                <span className="text-xs text-slate-400">Heal %{healRate}</span>
                <input type="range" min={0} max={80} value={healRate} onChange={(e) => setHealRate(Number(e.target.value))} className="flex-1 accent-amber-500" />
              </div>
              <div className="flex gap-2 ml-auto">
                <Button type="button" variant="secondary" onClick={handleGenerate}>✨ Adımları Üret</Button>
                <Button type="button" onClick={handleRunSuite}>🚀 Paralel Koş</Button>
              </div>
            </div>
          </div>

          {/* Üretilen adımlar */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 max-h-[340px] overflow-y-auto">
            <p className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">Üretilen Appium Adımları</p>
            {!generatedSteps ? (
              <p className="text-xs text-slate-500 italic">Henüz üretilmedi — "Adımları Üret"e basın.</p>
            ) : (
              <ol className="space-y-1">
                {generatedSteps.map((s, i) => (
                  <li key={i} className="text-[11px] font-mono flex gap-2">
                    <span className="text-slate-600">{String(i + 1).padStart(2, "0")}</span>
                    <span className="text-blue-300">{s.action}</span>
                    {s.by && <span className="text-slate-500">by={s.by}</span>}
                    {s.value && <span className="text-emerald-300 truncate">"{s.value}"</span>}
                    {s.text && <span className="text-amber-300 truncate">"{s.text}"</span>}
                    {s.ms && <span className="text-slate-500">{s.ms}ms</span>}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════ */}
      {/* Seed Senaryo Galerisi                           */}
      {/* ═══════════════════════════════════════════════ */}
      {seedScenarios.length > 0 && (
        <section className="rounded-lg border border-slate-800 overflow-hidden">
          <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
            <div>
              <h2 className="text-sm font-semibold">📚 Senaryo Galerisi</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Production-benzeri {seedScenarios.length} hazır senaryo — tıkla, prompt otomatik dolsun
              </p>
            </div>
            <div className="flex gap-1 flex-wrap">
              {["all", ...Array.from(new Set(seedScenarios.map((s) => s.category)))].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSeedFilter(cat)}
                  className={`rounded-full border px-2.5 py-0.5 text-[10px] font-medium transition-colors
                    ${seedFilter === cat
                      ? "border-blue-500/60 bg-blue-500/10 text-blue-300"
                      : "border-slate-800 text-slate-400 hover:border-slate-600"}`}
                >
                  {cat === "all" ? "Tümü" : cat}
                </button>
              ))}
            </div>
          </div>
          <div className="p-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {seedScenarios
              .filter((s) => seedFilter === "all" || s.category === seedFilter)
              .map((s) => {
                const diffColor = s.difficulty === "kolay"
                  ? "text-emerald-300 border-emerald-500/30 bg-emerald-500/5"
                  : s.difficulty === "orta"
                    ? "text-amber-300 border-amber-500/30 bg-amber-500/5"
                    : "text-red-300 border-red-500/30 bg-red-500/5";
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setPrompt(s.prompt);
                      setScenarioName(s.title);
                      setGeneratedSteps(null);
                      pushLog({ level: "info", message: `📚 Seed yüklendi: "${s.title}"` });
                      document.querySelector('[data-testid="mobil-otomasyon-page"] textarea')
                        ?.scrollIntoView({ behavior: "smooth", block: "center" });
                    }}
                    className="group rounded-lg border border-slate-800 bg-slate-900/20 hover:border-blue-500/40 hover:bg-blue-500/5 p-3 text-left transition-colors space-y-1.5"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <p className="text-[12px] font-semibold truncate group-hover:text-blue-300">{s.title}</p>
                      <span className={`shrink-0 rounded border px-1.5 text-[9px] font-medium ${diffColor}`}>
                        {s.difficulty}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400 leading-snug line-clamp-2">{s.description}</p>
                    <div className="flex items-center gap-1 flex-wrap pt-1">
                      <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[9px] text-slate-400">{s.category}</span>
                      {s.platforms.map((p) => (
                        <span key={p} className="text-[10px]">{p === "ios" ? "" : "🤖"}</span>
                      ))}
                      <span className="ml-auto text-[9px] text-slate-500">~{s.expected_steps} adım</span>
                    </div>
                  </button>
                );
              })}
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════ */}
      {/* Device Farm                                     */}
      {/* ═══════════════════════════════════════════════ */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
          <h2 className="text-sm font-semibold">🖥️ Cihaz Farm'ı (10 sanal)</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Appium port eşlemesi 4723–4728 (Android), 4730–4733 (iOS). Canlı CPU/RAM metriği her 1.5 sn güncellenir.
          </p>
        </div>
        <div className="p-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {devices.map((d) => {
            const progress = d.stepsTotal ? Math.round((d.stepsDone / d.stepsTotal) * 100) : 0;
            return (
              <div
                key={d.id}
                onClick={() => setActiveDeviceId(d.id === activeDeviceId ? null : d.id)}
                className={`cursor-pointer rounded-lg border p-3 space-y-2 transition-colors
                  ${activeDeviceId === d.id
                    ? "border-blue-500/60 bg-blue-500/5"
                    : "border-slate-800 bg-slate-900/20 hover:border-slate-700"}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold truncate">{d.name}</p>
                    {platformBadge(d.platform, d.osVersion, d.kind)}
                  </div>
                  {statusPill(d.status)}
                </div>

                {/* Mini "phone frame" */}
                <div className={`relative mx-auto aspect-[9/19] w-[70px] rounded-[10px] border border-slate-700
                                  ${d.status === "offline" ? "bg-slate-900" : "bg-gradient-to-b from-slate-800 to-slate-950"}
                                  flex items-center justify-center overflow-hidden`}>
                  <div className="absolute left-1/2 top-0.5 h-1 w-5 -translate-x-1/2 rounded-full bg-slate-700" />
                  {d.status === "running" && (
                    <div className="absolute inset-0 flex items-end justify-center pb-2">
                      <div className="h-0.5 w-[80%] bg-slate-800 rounded overflow-hidden">
                        <div className="h-full bg-blue-500 transition-all" style={{ width: `${progress}%` }} />
                      </div>
                    </div>
                  )}
                  {d.status === "booting" && (
                    <div className="text-[8px] text-amber-400 animate-pulse">boot…</div>
                  )}
                  {d.status === "error" && <div className="text-[8px] text-red-400">err</div>}
                  {d.status === "offline" && <div className="text-[8px] text-slate-600">off</div>}
                  {d.status === "idle" && <div className="text-[8px] text-slate-500">idle</div>}
                </div>

                {/* Metrikler */}
                <div className="grid grid-cols-3 gap-1 text-[10px]">
                  <div className="rounded bg-slate-950/60 px-1.5 py-1 text-center">
                    <p className="text-slate-500">CPU</p>
                    <p className="font-mono text-slate-300">{d.cpuPct}%</p>
                  </div>
                  <div className="rounded bg-slate-950/60 px-1.5 py-1 text-center">
                    <p className="text-slate-500">RAM</p>
                    <p className="font-mono text-slate-300">{d.ramPct}%</p>
                  </div>
                  <div className="rounded bg-slate-950/60 px-1.5 py-1 text-center">
                    <p className="text-slate-500">🔋</p>
                    <p className="font-mono text-slate-300">{d.battery}%</p>
                  </div>
                </div>

                {/* Durum satırı */}
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-slate-500">:{d.appiumPort}</span>
                  {d.status === "running" ? (
                    <span className="text-blue-300 truncate">{d.stepsDone}/{d.stepsTotal} · {d.currentStep}</span>
                  ) : d.healStreak > 0 ? (
                    <span className="text-amber-300">🔧 {d.healStreak} heal</span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Seçili cihaz detay paneli */}
        {activeDevice && (
          <div className="border-t border-slate-800 bg-slate-950/40 p-4 grid gap-4 md:grid-cols-[1fr_auto]">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <p className="text-sm font-semibold">{activeDevice.name}</p>
                {statusPill(activeDevice.status)}
                {platformBadge(activeDevice.platform, activeDevice.osVersion, activeDevice.kind)}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-500">Profile:</span>{" "}
                  <span className="font-mono text-slate-300">{activeDevice.profile}</span>
                </div>
                <div>
                  <span className="text-slate-500">Kind:</span>{" "}
                  <span className="font-mono text-slate-300">{activeDevice.kind}</span>
                </div>
                <div>
                  <span className="text-slate-500">Appium URL:</span>{" "}
                  <span className="font-mono text-slate-300">http://127.0.0.1:{activeDevice.appiumPort}</span>
                </div>
                <div>
                  <span className="text-slate-500">ID:</span>{" "}
                  <span className="font-mono text-slate-300">{activeDevice.id}</span>
                </div>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button type="button" variant="secondary" onClick={() => setShowDeviceScreen(true)}>
                📱 Ekranı Aç
              </Button>
              <Button type="button" variant="secondary" onClick={() => rebootDevice(activeDevice.id)}>
                🔄 Reboot
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  pushLog({ level: "info", deviceId: activeDevice.id, message: `Screenshot alındı (mock)` });
                }}
              >
                📸 Screenshot
              </Button>
              <Button
                type="button"
                onClick={() => {
                  const steps = generatedSteps ?? mockLLMStepper(prompt, activeDevice.platform);
                  const sessionId = `s_${Date.now()}_${activeDevice.id}`;
                  setSessions((p) => [
                    { id: sessionId, deviceId: activeDevice.id, scenarioName, status: "running", startedAt: Date.now(), healed: 0 },
                    ...p,
                  ]);
                  setDevices((p) => p.map((x) => x.id === activeDevice.id
                    ? { ...x, status: "running", stepsDone: 0, stepsTotal: steps.length, currentStep: steps[0].action }
                    : x));
                  pushLog({ level: "info", deviceId: activeDevice.id, sessionId, message: `[${activeDevice.name}] tek cihaz koşusu başladı` });
                  void runSession(activeDevice, steps, sessionId);
                }}
              >
                ▶️ Bu cihazda koş
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* Mock Cihaz Ekranı Modal */}
      {showDeviceScreen && activeDevice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4" onClick={() => setShowDeviceScreen(false)}>
          <div className="flex max-h-full max-w-md flex-col overflow-hidden rounded-3xl border border-slate-700 bg-slate-950 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <div>
                <p className="text-sm font-semibold text-white">{activeDevice.name}</p>
                <p className="text-[10px] text-slate-500">
                  {activeDevice.platform === "ios" ? "iOS" : "Android"} {activeDevice.osVersion} · {activeDevice.profile} · :{activeDevice.appiumPort}
                </p>
              </div>
              <button type="button" onClick={() => setShowDeviceScreen(false)} className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800">
                ✕ Kapat
              </button>
            </div>

            {/* Device Frame */}
            <div className="flex-1 overflow-auto bg-slate-900/40 p-6">
              <div className="relative mx-auto w-[280px]">
                {/* Phone bezel */}
                <div className="rounded-[40px] border-4 border-slate-800 bg-slate-950 p-2 shadow-[0_0_60px_rgba(124,58,237,0.15)]">
                  {/* Notch */}
                  <div className="relative mx-auto h-5 w-24 -translate-y-0.5 rounded-b-2xl bg-slate-950 z-10" />
                  {/* Screen */}
                  <div className="relative aspect-[9/19.5] overflow-hidden rounded-[28px] bg-gradient-to-b from-slate-900 to-slate-950">
                    {/* Status bar */}
                    <div className="flex items-center justify-between bg-slate-900/80 px-4 py-2 text-[10px] text-slate-300">
                      <span>{new Date().toTimeString().slice(0, 5)}</span>
                      <span className="flex items-center gap-1">📶 📶 🔋{activeDevice.battery}%</span>
                    </div>
                    {/* Mock App Content */}
                    <div className="flex h-full flex-col items-center justify-center px-4 text-center text-white">
                      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-500/20 text-3xl">
                        📱
                      </div>
                      <p className="text-sm font-semibold">{activeDevice.status === "running" ? "Test Koşuyor" : "Cihaz Hazır"}</p>
                      <p className="mt-1 text-[10px] text-slate-400">
                        {activeDevice.status === "running"
                          ? `${activeDevice.stepsDone}/${activeDevice.stepsTotal} adım`
                          : "Otomasyon başlatın"}
                      </p>
                      {activeDevice.status === "running" && activeDevice.currentStep && (
                        <p className="mt-3 rounded-lg bg-slate-800/60 px-3 py-1.5 text-[10px] font-mono text-violet-200">
                          {activeDevice.currentStep}
                        </p>
                      )}
                      <div className="mt-6 grid grid-cols-3 gap-2 w-full max-w-[200px]">
                        {["💬", "📷", "🎮", "🛒", "📧", "⚙️"].map((emoji, i) => (
                          <div key={i} className="aspect-square flex items-center justify-center rounded-xl bg-slate-800/50 text-2xl">
                            {emoji}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Home indicator */}
                <div className="mx-auto mt-3 h-1 w-24 rounded-full bg-slate-700" />
              </div>
            </div>

            {/* Footer info */}
            <div className="border-t border-slate-800 bg-slate-900/40 px-4 py-3">
              <p className="text-[11px] text-amber-200/80">
                ⚠️ Bu mock bir görünümdür. Gerçek ekran mirroring için Appium Inspector veya scrcpy kullanın.
              </p>
              <p className="mt-1 text-[10px] text-slate-500 font-mono">
                Appium: http://127.0.0.1:{activeDevice.appiumPort}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════ */}
      {/* Sessions + Live Logs (2 kolon)                  */}
      {/* ═══════════════════════════════════════════════ */}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-slate-800 overflow-hidden">
          <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
            <h2 className="text-sm font-semibold">📊 Koşular</h2>
            <p className="text-xs text-slate-400 mt-0.5">Son {sessions.length} session</p>
          </div>
          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-800/60">
            {sessions.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500">Henüz koşu yok</div>
            ) : sessions.map((s) => {
              const d = devices.find((x) => x.id === s.deviceId);
              const dur = s.finishedAt ? s.finishedAt - s.startedAt : Date.now() - s.startedAt;
              const color = s.status === "passed" ? "text-emerald-400"
                         : s.status === "failed" ? "text-red-400"
                         : "text-blue-400";
              return (
                <div key={s.id} className="flex items-center gap-3 px-4 py-2 text-xs">
                  <span className={`w-14 font-semibold uppercase ${color}`}>{s.status}</span>
                  <span className="flex-1 truncate">
                    <span className="font-medium">{s.scenarioName}</span>
                    {" · "}
                    <span className="text-slate-400">{d?.name ?? s.deviceId}</span>
                  </span>
                  {s.healed > 0 && <span className="text-amber-400">🔧{s.healed}</span>}
                  <span className="text-slate-500 font-mono">{fmtMs(dur)}</span>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-lg border border-slate-800 overflow-hidden">
          <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">📜 Canlı Loglar</h2>
              <p className="text-xs text-slate-400 mt-0.5">Son {logs.length} olay</p>
            </div>
            <button
              type="button"
              onClick={() => setLogs([])}
              className="text-[11px] text-slate-400 hover:text-white"
            >
              Temizle
            </button>
          </div>
          <div className="max-h-[380px] overflow-y-auto bg-slate-950/60">
            {logs.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-500">Henüz log yok</div>
            ) : (
              <ul className="divide-y divide-slate-800/40">
                {logs.map((l) => {
                  const color = l.level === "error" ? "text-red-400"
                              : l.level === "warn"  ? "text-amber-400"
                              : l.level === "llm"   ? "text-violet-300"
                              : l.level === "heal"  ? "text-amber-300"
                              : "text-slate-300";
                  const icon  = l.level === "error" ? "✕"
                              : l.level === "warn"  ? "⚠"
                              : l.level === "llm"   ? "🧠"
                              : l.level === "heal"  ? "🔧"
                              : "›";
                  return (
                    <li key={l.id} className="flex gap-2 px-3 py-1.5 text-[11px] font-mono">
                      <span className="text-slate-600 shrink-0">{new Date(l.ts).toLocaleTimeString("tr-TR")}</span>
                      <span className={`${color} shrink-0 w-3`}>{icon}</span>
                      <span className={`${color} truncate`}>{l.message}</span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>
      </div>

      {/* ═══════════════════════════════════════════════ */}
      {/* Mimari (görsel)                                 */}
      {/* ═══════════════════════════════════════════════ */}
      <section className="rounded-lg border border-slate-800 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
          <h2 className="text-sm font-semibold">🏗️ Mimari Özet</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Neurex QA Web → FastAPI Orchestrator → AI Gateway + Device Broker → Appium N → Cihaz N
          </p>
        </div>
        <div className="p-4">
          <pre className="text-[10px] sm:text-[11px] leading-tight font-mono text-slate-300 overflow-x-auto">
{`      ┌──────────────────────────────────────────────────────────┐
      │  Neurex QA Web UI  (/mobil-otomasyon)  ← buradasınız           │
      └─────────────────────────────┬────────────────────────────┘
                                    │ REST + SSE
      ┌─────────────────────────────▼────────────────────────────┐
      │  FastAPI  backend/app/domains/mobile/                     │
      │   · SessionOrchestrator                                   │
      │   · LLMStepper  (NL → Gherkin → Appium)                   │
      │   · SelfHealing (locator rewrite)                         │
      │   · VisualVerifier (screenshot assertion)                 │
      │   · ArtifactStore (MinIO)                                 │
      └───┬──────────────────┬──────────────────────┬─────────────┘
          │                  │                      │
   ┌──────▼───────┐  ┌───────▼────────┐    ┌────────▼──────────┐
   │ AI Gateway   │  │ Device Broker  │    │ Artifact / MinIO  │
   │ GPT-4o /     │  │ AVD lifecycle  │    │ screenshots/video │
   │ Gemini Flash │  │ Appium pool    │    │                   │
   └──────────────┘  └────┬───────────┘    └───────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │ Appium  │  ...  │ Appium  │       │ Appium  │
   │ :4723   │       │ :4728   │       │ :4733   │
   └────┬────┘       └────┬────┘       └────┬────┘
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
   │Pixel 8  │       │Nexus 5X │       │iPhone SE│
   │  AVD    │       │  AVD    │       │   Sim   │
   └─────────┘       └─────────┘       └─────────┘`}
          </pre>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════ */}
      {/* Fiziksel Cihaz Modal                            */}
      {/* ═══════════════════════════════════════════════ */}
      {showPhysicalModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setShowPhysicalModal(false)}
        >
          <div
            className="w-full max-w-2xl rounded-lg border border-slate-800 bg-slate-950 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
              <h3 className="text-sm font-semibold">➕ Fiziksel Cihaz Kaydet</h3>
              <button type="button" onClick={() => setShowPhysicalModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="p-5 space-y-4">
              <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-200">
                <b>Ön koşullar</b> — Android: USB debugging açık, ADB'de <code className="font-mono">authorized</code> olarak görünür.
                iOS: Apple Developer sertifikası, WebDriverAgent imzalı, UDID kayıtlı.
              </div>

              <PhysicalEnrollForm
                onSubmitted={(deviceName) => {
                  pushLog({ level: "info", message: `✓ Fiziksel cihaz kaydı: ${deviceName}` });
                  setShowPhysicalModal(false);
                  // Backend modda cihaz listesini tazele
                  if (backendMode === "connected") {
                    apiFetch<BackendDevice[]>("/api/v1/mobile/devices").then((list) => {
                      setDevices(list.map(fromBackendDevice));
                    }).catch((err) => console.warn("[mobil-otomasyon]:", err));
                  }
                }}
                backendMode={backendMode}
              />

            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
 * PhysicalEnrollForm
 * ─────────────────────────────────────────────────────────────── */
function PhysicalEnrollForm({
  onSubmitted,
  backendMode,
}: {
  onSubmitted: (name: string) => void;
  backendMode: "probing" | "connected" | "mock";
}) {
  const [name, setName] = useState("");
  const [platform, setPlatform] = useState<Platform>("android");
  const [udid, setUdid] = useState("");
  const [osVersion, setOsVersion] = useState("14");
  const [appiumUrl, setAppiumUrl] = useState("http://lab-node-1.bgts.internal:4750");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!name.trim() || !udid.trim()) {
      setErr("Cihaz adı ve UDID/Serial zorunlu");
      return;
    }
    setErr(null);
    setSubmitting(true);
    try {
      if (backendMode === "connected") {
        await apiFetch("/api/v1/mobile/enroll-physical", {
          method: "POST",
          json: {
            name: name.trim(),
            platform,
            os_version: osVersion.trim(),
            udid: udid.trim(),
            appium_url: appiumUrl.trim(),
            profile: name.toLowerCase().replace(/\s+/g, "_"),
          },
        });
      } else {
        // Mock mod — 600ms bekle
        await new Promise((r) => setTimeout(r, 600));
      }
      onSubmitted(name);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Kayıt başarısız");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">Cihaz Adı</label>
          <Input placeholder="Samsung S24 - Lab-01" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">Platform</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value as Platform)}
            className="h-10 w-full rounded border border-slate-800 bg-slate-900 px-3 text-sm"
          >
            <option value="android">Android</option>
            <option value="ios">iOS</option>
          </select>
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">UDID / Serial</label>
          <Input placeholder="R58M3..." value={udid} onChange={(e) => setUdid(e.target.value)} />
        </div>
        <div>
          <label className="block text-[11px] text-slate-400 mb-1">OS Version</label>
          <Input placeholder="14" value={osVersion} onChange={(e) => setOsVersion(e.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-[11px] text-slate-400 mb-1">Appium Server URL</label>
          <Input placeholder="http://lab-node-1.bgts.internal:4750" value={appiumUrl} onChange={(e) => setAppiumUrl(e.target.value)} />
        </div>
      </div>

      <div className="rounded-md border border-slate-800 bg-slate-900/40 p-3 space-y-1.5">
        <p className="text-[11px] font-semibold text-slate-300">Bir sonraki adımlar</p>
        <ol className="list-decimal list-inside text-[11px] text-slate-400 space-y-0.5">
          <li>Cihaz USB hub&apos;a takılı ve powered mı? (Cambrionix PowerPad veya muadili)</li>
          <li>ADB/WDA handshake testi otomatik çalışacak.</li>
          <li>MDM profili yüklenecek (Jamf iOS / Headwind Android).</li>
          <li>Kiosk mode etkinleştirilecek — cihaz yalnız test için.</li>
        </ol>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}

      <div className="flex items-center justify-end gap-2 pt-1">
        <span className="text-[10px] text-slate-500 mr-auto">
          {backendMode === "connected" ? "→ POST /api/v1/mobile/enroll-physical" : "Mock mod: yalnız UI'ya eklenir"}
        </span>
        <Button type="button" variant="secondary" onClick={() => onSubmitted("")} disabled={submitting}>
          Vazgeç
        </Button>
        <Button type="button" onClick={submit} disabled={submitting}>
          {submitting ? "Kaydediliyor…" : "Kaydet & Handshake Yap"}
        </Button>
      </div>
    </>
  );
}
