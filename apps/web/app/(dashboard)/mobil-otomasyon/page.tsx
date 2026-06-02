"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch, ApiError } from "@/lib/api";
import { DeviceFarmGrid } from "./components/DeviceFarmGrid";
import { SessionLogPanel } from "./components/SessionLogPanel";
import { LLMScenarioGenerator } from "./components/LLMScenarioGenerator";
import { ScenarioTemplateGallery } from "./components/ScenarioTemplateGallery";
import { DeviceScreenModal } from "./components/DeviceScreenModal";
import { ResearchReportPanel } from "./components/ResearchReportPanel";

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
        <ResearchReportPanel onClose={() => setShowReportPanel(false)} />
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
      <LLMScenarioGenerator
        prompt={prompt}
        onPromptChange={setPrompt}
        scenarioName={scenarioName}
        onScenarioNameChange={setScenarioName}
        targetPlatform={targetPlatform}
        onTargetPlatformChange={setTargetPlatform}
        parallel={parallel}
        onParallelChange={setParallel}
        passRate={passRate}
        onPassRateChange={setPassRate}
        healRate={healRate}
        onHealRateChange={setHealRate}
        generatedSteps={generatedSteps}
        onGenerate={handleGenerate}
        onRunSuite={handleRunSuite}
      />

      {/* ═══════════════════════════════════════════════ */}
      {/* Seed Senaryo Galerisi                           */}
      {/* ═══════════════════════════════════════════════ */}
      <ScenarioTemplateGallery
        seedScenarios={seedScenarios}
        seedFilter={seedFilter}
        onFilterChange={setSeedFilter}
        onSelectScenario={(s) => {
          setPrompt(s.prompt);
          setScenarioName(s.title);
          setGeneratedSteps(null);
          pushLog({ level: "info", message: `📚 Seed yüklendi: "${s.title}"` });
          document.querySelector('[data-testid="mobil-otomasyon-page"] textarea')
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
        }}
      />

      {/* ═══════════════════════════════════════════════ */}
      {/* Device Farm                                     */}
      {/* ═══════════════════════════════════════════════ */}
      <DeviceFarmGrid
        devices={devices}
        activeDeviceId={activeDeviceId}
        onSelectDevice={(id) => setActiveDeviceId(id)}
        onReboot={(id) => rebootDevice(id)}
        onOpenScreen={() => setShowDeviceScreen(true)}
        onScreenshot={() => {
          if (activeDevice) {
            pushLog({ level: "info", deviceId: activeDevice.id, message: `Screenshot alındı (mock)` });
          }
        }}
        onRunDevice={() => {
          if (!activeDevice) return;
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
      />

      {/* Mock Cihaz Ekranı Modal */}
      {showDeviceScreen && activeDevice && (
        <DeviceScreenModal device={activeDevice} onClose={() => setShowDeviceScreen(false)} />
      )}

      {/* ═══════════════════════════════════════════════ */}
      {/* Sessions + Live Logs (2 kolon)                  */}
      {/* ═══════════════════════════════════════════════ */}
      <SessionLogPanel
        sessions={sessions}
        logs={logs}
        devices={devices}
        onClearLogs={() => setLogs([])}
      />

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
