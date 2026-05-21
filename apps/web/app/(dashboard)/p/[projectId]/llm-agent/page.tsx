"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { ensureValidToken } from "@/lib/api-client";

// ─── Types ────────────────────────────────────────────────────────────────────

type AgentPhase = "idle" | "starting" | "planning" | "running" | "summarizing" | "done" | "error";

type Finding = {
  id: string;
  step: number;
  text: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  url: string;
  timestamp: string;
  wave?: number;
  // Enriched metadata from backend classify call (#66)
  title?: string;
  category?: string;
  hypothesis_id?: string;
  impact?: string;
  steps_to_reproduce?: string[];
};

type ActionRecord = {
  step: number;
  type: string;
  selector?: string;
  value?: string;
  description: string;
  success: boolean;
  url: string;
  timestamp: string;
  wave?: number;
};

type HypothesisStatus = "pending" | "testing" | "verified" | "rejected" | "partial" | "skipped";

type Hypothesis = {
  id: string;
  claim: string;
  area: string;
  priority: "critical" | "high" | "medium" | "low";
  status: HypothesisStatus;
  confidence?: number;
  evidence?: string;
  wave?: number;
  test_type?: string;
};

type PageDiscovery = {
  page_type: string;
  buttons_count: number;
  inputs_count: number;
  links_count: number;
  forms_count: number;
  alerts: Array<{ text: string; type: string }>;
  headings: Array<{ level: number; text: string }>;
};

// New advanced types
type ApiCall = {
  url: string;
  method: string;
  status: number;
  duration_ms: number;
  is_error: boolean;
  timestamp: string;
};

type ConsoleMsg = {
  type: "error" | "warning" | "info";
  text: string;
  url?: string;
  timestamp: string;
};

type TechItem = { name: string; category: string; version?: string };

type CoverageData = {
  coverage_pct: number;
  tested_areas: string[];
  wave1_count: number;
  wave2_count: number;
  findings_by_severity: Record<string, number>;
};

type AgentConfig = {
  targetUrl: string;
  maxSteps: number;
  loginUrl: string;
  username: string;
  password: string;
  usernameSelector: string;
  passwordSelector: string;
  submitSelector: string;
  testFocus: string;
  dryRun: boolean;
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cn(...cls: (string | false | null | undefined)[]) {
  return cls.filter(Boolean).join(" ");
}

function severityColor(s: string) {
  if (s === "critical") return { bg: "bg-red-500/15 border-red-500/30", text: "text-red-300", badge: "bg-red-500/25 text-red-200" };
  if (s === "high")     return { bg: "bg-orange-500/10 border-orange-500/25", text: "text-orange-300", badge: "bg-orange-500/20 text-orange-200" };
  if (s === "medium")   return { bg: "bg-yellow-500/10 border-yellow-500/25", text: "text-yellow-300", badge: "bg-yellow-500/20 text-yellow-200" };
  if (s === "low")      return { bg: "bg-blue-500/10 border-blue-500/25", text: "text-blue-300", badge: "bg-blue-500/20 text-blue-200" };
  return { bg: "bg-slate-800/60 border-slate-700", text: "text-slate-300", badge: "bg-slate-700 text-slate-300" };
}

function statusColor(status: number) {
  if (status < 300) return "text-emerald-400";
  if (status < 400) return "text-sky-400";
  if (status < 500) return "text-yellow-400";
  return "text-red-400";
}

function techCategoryIcon(category: string) {
  if (category === "framework") return "⚛️";
  if (category === "library") return "📦";
  if (category === "cms") return "📰";
  return "🔧";
}

function areaIcon(area: string) {
  const m: Record<string, string> = {
    security: "🔐", auth: "🔑", form: "📝", navigation: "🧭",
    api: "📡", performance: "⚡", accessibility: "♿", ux: "🎨",
    genel: "🌐", other: "🔍",
  };
  return m[area] ?? "🔍";
}

function actionIcon(type: string) {
  const icons: Record<string, string> = {
    click: "👆", fill: "⌨️", navigate: "🔗", scroll: "📜",
    hover: "🖱️", press_key: "⌨️", done: "✅",
    type_text: "⌨️", clear_and_fill: "🔄", scroll_to_top: "⬆️",
    select_option: "📋", assert_visible: "👁️",
    wait_for_text: "⏳", wait_for_selector: "⏳",
  };
  return icons[type] ?? "⚡";
}

const FOCUS_OPTIONS = [
  { value: "", label: "Genel keşif" },
  { value: "login_auth", label: "Login & Kimlik doğrulama" },
  { value: "forms", label: "Form validasyonları" },
  { value: "navigation", label: "Navigasyon & Routing" },
  { value: "errors", label: "Hata senaryoları" },
  { value: "accessibility", label: "Erişilebilirlik" },
  { value: "performance", label: "Performans" },
];

// ─── Typewriter cursor ────────────────────────────────────────────────────────

function Cursor() {
  return <span className="inline-block w-1.5 h-3.5 bg-violet-400 animate-pulse ml-0.5 align-middle rounded-sm" />;
}

// ─── Phase badge ─────────────────────────────────────────────────────────────

function PhaseBadge({ phase }: { phase: AgentPhase }) {
  const cfg: Record<AgentPhase, { label: string; color: string; pulse: boolean }> = {
    idle:       { label: "Hazır",       color: "border-slate-600 text-slate-400", pulse: false },
    starting:   { label: "Başlatılıyor", color: "border-sky-500/40 text-sky-400", pulse: true },
    planning:   { label: "Planlıyor",   color: "border-violet-500/40 text-violet-300", pulse: true },
    running:    { label: "Çalışıyor",   color: "border-emerald-500/40 text-emerald-400", pulse: true },
    summarizing:{ label: "Özetliyor",   color: "border-amber-500/40 text-amber-300", pulse: true },
    done:       { label: "Tamamlandı",  color: "border-emerald-500/40 text-emerald-400", pulse: false },
    error:      { label: "Hata",        color: "border-red-500/40 text-red-400", pulse: false },
  };
  const { label, color, pulse } = cfg[phase];
  return (
    <span className={cn("flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold", color)}>
      {pulse && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
      {label}
    </span>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function LlmAgentPage() {
  const projectId = useRouteParam("projectId");

  const [config, setConfig] = useState<AgentConfig>({
    targetUrl: "https://cortex-test.bgtsai.com",
    maxSteps: 10,
    loginUrl: "",
    username: "",
    password: "",
    usernameSelector: "",
    passwordSelector: "",
    submitSelector: "",
    testFocus: "",
    dryRun: false,
  });
  const [advOpen, setAdvOpen] = useState(false);

  // Agent state
  const [phase, setPhase]         = useState<AgentPhase>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [currentUrl, setCurrentUrl]   = useState("");
  const [screenshot, setScreenshot]   = useState<string>("");
  const [planText, setPlanText]       = useState("");
  const [brainText, setBrainText]     = useState("");   // streaming düşünce
  const [brainMode, setBrainMode]     = useState<"thinking" | "observing" | "summarizing" | "">("");
  const [summaryText, setSummaryText] = useState("");
  const [actions, setActions]         = useState<ActionRecord[]>([]);
  const [findings, setFindings]       = useState<Finding[]>([]);
  const [errorMsg, setErrorMsg]       = useState<string>("");
  const [duration, setDuration]       = useState(0);
  const [startedAt, setStartedAt]     = useState<number>(0);
  // Yeni gelişmiş state
  const [hypotheses, setHypotheses]       = useState<Hypothesis[]>([]);
  const [activeHypId, setActiveHypId]     = useState<string>("");
  const [discovery, setDiscovery]         = useState<PageDiscovery | null>(null);
  const [comprehensionText, setComprehensionText] = useState<string>("");
  // Working memory & sequence plan
  const [learnedFacts, setLearnedFacts]   = useState<string[]>([]);
  const [sequencePlan, setSequencePlan]   = useState<{ strategy: string; actions: Array<{ type: string; description: string; critical?: boolean }> } | null>(null);
  const [subStep, setSubStep]             = useState(0);
  const [subTotal, setSubTotal]           = useState(0);
  const [memoryOpen, setMemoryOpen]       = useState(true);
  // Advanced monitoring
  const [apiCalls, setApiCalls]           = useState<ApiCall[]>([]);
  const [consoleErrors, setConsoleErrors] = useState<ConsoleMsg[]>([]);
  const [techStack, setTechStack]         = useState<TechItem[]>([]);
  const [wave, setWave]                   = useState(1);
  const [waveReason, setWaveReason]       = useState("");
  const [coverage, setCoverage]           = useState<CoverageData | null>(null);
  const [sensitiveKeys, setSensitiveKeys] = useState<string[]>([]);
  const [rightTab, setRightTab]           = useState<"hypotheses" | "network" | "console" | "findings">("hypotheses");

  // Session yeniden kullanımı: son tamamlanan çalışmanın session_id'si tutulur.
  // Bir sonraki çalıştırmada backend'e reuse_session_id olarak gönderilir → ~1-3s tasarruf.
  const lastSessionIdRef = useRef<string | null>(null);

  const abortRef     = useRef<AbortController | null>(null);
  const brainScrollRef = useRef<HTMLDivElement>(null);
  const timerRef     = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-scroll brain panel
  useEffect(() => {
    if (brainScrollRef.current) {
      brainScrollRef.current.scrollTop = brainScrollRef.current.scrollHeight;
    }
  }, [brainText, summaryText]);

  // Duration timer. Background-tab fix: tarayıcılar gizli sekmelerde
  // setInterval'i ~1dk'ya düşürür. Bu yüzden visibilitychange tetiğinde
  // de tetikle ki kullanıcı sekmeye döndüğünde timer hemen güncellensin.
  useEffect(() => {
    if (!(phase === "running" || phase === "planning" || phase === "starting" || phase === "summarizing")) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    const tick = () => setDuration(Math.floor((Date.now() - startedAt) / 1000));
    tick();
    timerRef.current = setInterval(tick, 1000);
    const onVisibility = () => { if (!document.hidden) tick(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [phase, startedAt]);

  const handleStart = useCallback(async () => {
    if (!config.targetUrl || phase !== "idle") return;

    const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!UUID_RE.test(projectId ?? "")) {
      setErrorMsg("Geçersiz proje ID. Portfolio'dan bir proje seçin.");
      setPhase("error");
      return;
    }

    // Reset — hypotheses ve süre dahil tüm çalışma state'i temizlenir
    setPlanText(""); setBrainText(""); setSummaryText(""); setScreenshot("");
    setActions([]); setFindings([]); setErrorMsg(""); setCurrentStep(0); setDuration(0);
    setCurrentUrl(config.targetUrl); setBrainMode("");
    setHypotheses([]); setActiveHypId(""); setDiscovery(null); setComprehensionText("");
    setLearnedFacts([]); setSequencePlan(null); setSubStep(0); setSubTotal(0);
    setApiCalls([]); setConsoleErrors([]); setTechStack([]); setWave(1); setWaveReason("");
    setCoverage(null); setSensitiveKeys([]);

    // Stale closure fix: capture start time in a local variable so agent_done
    // handler can compute correct elapsed duration regardless of React batching.
    const _runStartedAt = Date.now();
    setPhase("starting");
    setStartedAt(_runStartedAt);

    const sessionOk = await ensureValidToken();
    if (!sessionOk) {
      setErrorMsg("Oturum sona erdi. Sayfayı yenileyip tekrar deneyin.");
      setPhase("error");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const credentials = config.loginUrl ? {
        login_url: config.loginUrl,
        username: config.username,
        password: config.password,
        username_selector: config.usernameSelector,
        password_selector: config.passwordSelector,
        submit_selector: config.submitSelector,
      } : undefined;

      const res = await fetch(
        `/api/v1/tspm/projects/${projectId}/llm-agent/run/stream`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
          body: JSON.stringify({
            url: config.targetUrl,
            max_steps: config.maxSteps,
            credentials,
            test_focus: config.testFocus || undefined,
            dry_run: config.dryRun || undefined,
            // Aynı sayfa tekrar test ediliyorsa önceki session'ı gönder → browser reuse (~1-3s hız)
            reuse_session_id: lastSessionIdRef.current || undefined,
          }),
          signal: controller.signal,
        },
      );

      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => "");
        throw new Error(`Sunucu hatası ${res.status}: ${text.slice(0, 200)}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const raw of parts) {
          let eventName = "";
          let dataLine = "";
          for (const ln of raw.split("\n")) {
            const t = ln.trim();
            if (t.startsWith("event:")) eventName = t.slice(6).trim();
            else if (t.startsWith("data:")) dataLine = t.slice(5).trim();
          }
          if (!dataLine) continue;

          let payload: Record<string, unknown>;
          try { payload = JSON.parse(dataLine); } catch { continue; }

          const evt = eventName || String(payload.type ?? "");

          switch (evt) {
            case "agent_start":
              setPhase("planning");
              setScreenshot(String(payload.screenshot_b64 ?? payload.screenshot ?? ""));
              setCurrentUrl(String(payload.url ?? config.targetUrl));
              // Session yeniden kullanıldıysa brain paneline not düş
              if (payload.reused) {
                setBrainText(prev =>
                  (prev ? prev + "\n\n" : "") +
                  "♻️ Mevcut browser oturumu yeniden kullanılıyor (yeni kontekst açılmadı).\n"
                );
              }
              break;

            case "agent_discovery": {
              const d = payload as unknown as PageDiscovery;
              setDiscovery({
                page_type: String(d.page_type ?? "generic"),
                buttons_count: Number(d.buttons_count ?? 0),
                inputs_count: Number(d.inputs_count ?? 0),
                links_count: Number(d.links_count ?? 0),
                forms_count: Number(d.forms_count ?? 0),
                alerts: (d.alerts ?? []) as PageDiscovery["alerts"],
                headings: (d.headings ?? []) as PageDiscovery["headings"],
              });
              break;
            }

            case "agent_comprehension_token":
              setBrainMode("thinking");
              setComprehensionText(prev => prev + String(payload.token ?? ""));
              setBrainText(prev => prev + String(payload.token ?? ""));
              break;

            case "agent_comprehension":
              // comprehension tamamlandı — planlamaya geç
              setBrainText(prev => prev + "\n\n");
              break;

            case "agent_plan":
              if (!payload.wave) {
                // Wave 1: set plan and replace hypotheses
                setPlanText(String(payload.plan ?? ""));
                setPhase("running");
              }
              if (Array.isArray(payload.hypotheses)) {
                const newHyps = (payload.hypotheses as Hypothesis[]).map(h => ({
                  ...h,
                  status: "pending" as HypothesisStatus,
                  wave: Number(payload.wave ?? 1),
                }));
                if (payload.wave && Number(payload.wave) > 1) {
                  // Wave 2+: append hypotheses
                  setHypotheses(prev => [...prev, ...newHyps]);
                } else {
                  setHypotheses(newHyps);
                }
              }
              break;

            case "agent_plan_token":
              setPlanText(prev => prev + String(payload.token ?? ""));
              break;

            case "agent_hypothesis_start": {
              const hyp = payload.hypothesis as Hypothesis | undefined;
              if (hyp) {
                const idx = Number(payload.index ?? 0);
                const total = Number(payload.total ?? 0);
                const progress = total > 0 ? ` (${idx + 1}/${total})` : "";
                setActiveHypId(hyp.id);
                setHypotheses(prev => prev.map(h =>
                  h.id === hyp.id ? { ...h, status: "testing" } : h
                ));
                setBrainText(prev => prev + `\n\n${"─".repeat(40)}\n🔬 [${hyp.id}]${progress} ${hyp.claim}\n   Alan: ${hyp.area || "?"} | Öncelik: ${hyp.priority || "?"}\n`);
              }
              break;
            }

            case "agent_thinking":
              setBrainMode("thinking");
              setBrainText(prev => prev + String(payload.thinking ?? payload.token ?? payload.text ?? ""));
              break;

            case "agent_sequence_plan": {
              const sp = payload;
              // Backend may send objects or strings; normalise both
              const rawActions = Array.isArray(sp.actions) ? sp.actions : [];
              const spActions: Array<{ type: string; description: string; critical?: boolean }> = rawActions.map(a =>
                typeof a === "string"
                  ? { type: "action", description: a }
                  : { type: String((a as Record<string,unknown>).type ?? ""), description: String((a as Record<string,unknown>).description ?? ""), critical: Boolean((a as Record<string,unknown>).critical) }
              );
              setSequencePlan({ strategy: String(sp.strategy ?? ""), actions: spActions });
              setSubStep(0);
              setSubTotal(spActions.length);
              const _actList = spActions.map((a, i) => `  ${i+1}. [${a.type}]${a.critical ? " ⚠️" : ""} ${a.description.slice(0,50)}`).join("\n");
              setBrainText(prev => prev + `\n📋 Strateji: ${String(sp.strategy ?? "")}\n${_actList}\n`);
              break;
            }

            case "agent_memory_update": {
              const fact = String(payload.fact ?? "");
              if (fact) setLearnedFacts(prev => [...prev, fact]);
              const nextSugg = String(payload.next_suggestion ?? "");
              if (nextSugg) setBrainText(prev => prev + `\n💡 Sonraki ipucu: ${nextSugg}\n`);
              break;
            }

            case "agent_tech_detected": {
              const ts = (payload.tech_stack as TechItem[] | undefined) ?? [];
              if (ts.length > 0) setTechStack(ts);
              const sens = (payload.sensitive_storage_keys as string[] | undefined) ?? [];
              if (sens.length > 0) setSensitiveKeys(sens);
              if (ts.length > 0) {
                setBrainText(prev => prev + `\n🔧 Teknoloji: ${ts.map(t => t.name).join(", ")}\n`);
              }
              if (sens.length > 0) {
                setBrainText(prev => prev + `⚠️ Hassas storage anahtarı tespit edildi: ${sens.join(", ")}\n`);
              }
              break;
            }

            case "agent_network_activity": {
              const newErrs = (payload.new_errors as ApiCall[] | undefined) ?? [];
              if (newErrs.length > 0) {
                setApiCalls(prev => [...prev, ...newErrs].slice(-100));
                setRightTab("network");
                setBrainText(prev => prev + `\n📡 ${newErrs.length} yeni API hatası: ${newErrs.map(e => `${e.status} ${e.url.slice(-40)}`).join(", ")}\n`);
              }
              break;
            }

            case "agent_wave_start": {
              const w = Number(payload.wave ?? 2);
              const reason = String(payload.reason ?? "");
              setWave(w);
              setWaveReason(reason);
              setBrainText(prev => prev + `\n\n🌊 DALGA ${w} BAŞLIYOR\n${reason}\n${"─".repeat(40)}\n`);
              // Reset sub-step for new wave
              setSubStep(0); setSubTotal(0); setSequencePlan(null);
              break;
            }

            case "agent_wave_skipped": {
              // Backend tüm öncelikli alanları kapsadığını bildirdi → wave 2 atlandı
              const reason = String(payload.reason ?? "");
              const tested = (payload.tested_areas as string[] | undefined) ?? [];
              setBrainText(prev => prev + `\n\n⏭️ DALGA 2 ATLANDI\n${reason}\nTest edilen: ${tested.join(", ")}\n${"─".repeat(40)}\n`);
              break;
            }

            case "agent_coverage_update": {
              setCoverage({
                coverage_pct: Number(payload.coverage_pct ?? 0),
                tested_areas: (payload.tested_areas as string[] | undefined) ?? [],
                wave1_count: Number(payload.wave1_count ?? 0),
                wave2_count: Number(payload.wave2_count ?? 0),
                findings_by_severity: (payload.findings_by_severity as Record<string,number> | undefined) ?? {},
              });
              break;
            }

            case "agent_live_coverage": {
              // Her hipotez sonunda canlı kapsam güncellemesi — coverage bar anlık yansır
              setCoverage(prev => ({
                coverage_pct: Number(payload.coverage_pct ?? prev?.coverage_pct ?? 0),
                tested_areas: (payload.tested_areas as string[] | undefined) ?? prev?.tested_areas ?? [],
                wave1_count: prev?.wave1_count ?? 0,
                wave2_count: prev?.wave2_count ?? 0,
                findings_by_severity: prev?.findings_by_severity ?? {},
              }));
              break;
            }

            case "agent_action": {
              const step = Number(payload.step ?? currentStep);
              setCurrentStep(step);
              const ss = Number(payload.sub_step ?? 0);
              const st = Number(payload.sub_total ?? 0);
              if (ss > 0) setSubStep(ss);
              if (st > 0) setSubTotal(st);
              // Backend: {step, sub_step, sub_total, action: {type, selector, value, description}}
              const act = (payload.action as Record<string, unknown> | undefined) ?? {};
              const actType = String(act.type ?? payload.action_type ?? payload.type ?? "");
              const actDesc = String(act.description ?? payload.description ?? "");
              const subLabel = ss > 0 && st > 0 ? ` [${ss}/${st}]` : "";
              setActions(prev => [...prev, {
                step,
                type: actType,
                selector: (act.selector ?? payload.selector) as string | undefined,
                value: (act.value ?? payload.value) as string | undefined,
                description: actDesc,
                success: true,
                url: currentUrl,
                timestamp: new Date().toISOString(),
              }]);
              setBrainText(prev => prev + `\n\n▶ Adım ${step}${subLabel}: ${actDesc}\n`);
              break;
            }

            case "agent_screenshot": {
              setScreenshot(String(payload.screenshot_b64 ?? payload.screenshot ?? ""));
              setCurrentUrl(String(payload.url ?? currentUrl));
              if (payload.sub_step) setSubStep(Number(payload.sub_step));
              // Update last action success state based on actual result
              const actSuccess = payload.success !== false;  // undefined = assume success
              const actError = String(payload.error ?? "");
              if (!actSuccess && actError) {
                setActions(prev => {
                  if (prev.length === 0) return prev;
                  const updated = [...prev];
                  updated[updated.length - 1] = { ...updated[updated.length - 1], success: false };
                  return updated;
                });
                setBrainText(prev => prev + `  ❗ Hata: ${actError.slice(0, 80)}\n`);
              }
              break;
            }

            case "agent_navigate":
              setCurrentUrl(String(payload.to_url ?? payload.url ?? currentUrl));
              setBrainText(prev => prev + `🔗 Yeni sayfa: ${String(payload.to_url ?? payload.url ?? "")}\n`);
              break;

            case "agent_observation":
              setBrainMode("observing");
              // Supports both token-by-token streaming (payload.token) and full text (payload.observation)
              setBrainText(prev => prev + String(payload.token ?? payload.observation ?? payload.text ?? ""));
              break;

            case "agent_hypothesis_result": {
              const hypId = String(payload.hypothesis_id ?? "");
              const verdict = String(payload.verdict ?? "partial") as HypothesisStatus;
              const conf = Number(payload.confidence ?? 0);
              const evidence = String(payload.evidence ?? "");
              setHypotheses(prev => prev.map(h =>
                h.id === hypId ? { ...h, status: verdict, confidence: conf, evidence } : h
              ));
              setActiveHypId("");
              const icon = verdict === "verified" ? "✅" : verdict === "rejected" ? "❌" : "⚠️";
              setBrainText(prev => prev + `\n${icon} [${hypId}] ${verdict} (güven: ${Math.round(conf * 100)}%)\n`);
              break;
            }

            case "agent_finding": {
              const sev = String(payload.severity ?? "info") as Finding["severity"];
              const findingTitle = String(payload.title ?? "");
              setFindings(prev => [...prev, {
                id: String(payload.id ?? `f-${Date.now()}-${Math.random()}`),
                step: Number(payload.step ?? currentStep),
                text: String(payload.description ?? payload.finding ?? payload.text ?? ""),
                severity: sev,
                url: String(payload.url ?? currentUrl),
                timestamp: new Date().toISOString(),
                title: findingTitle || undefined,
                category: String(payload.category ?? "") || undefined,
                hypothesis_id: String(payload.hypothesis_id ?? "") || undefined,
                impact: String(payload.impact ?? "") || undefined,
                steps_to_reproduce: Array.isArray(payload.steps_to_reproduce) ? payload.steps_to_reproduce as string[] : undefined,
                wave: payload.wave ? Number(payload.wave) : undefined,
              }]);
              // Show title in brain log if available
              if (findingTitle) {
                setBrainText(prev => prev + `\n🐛 BULGU: [${sev.toUpperCase()}] ${findingTitle}\n`);
              }
              break;
            }

            case "agent_finding_skipped": {
              // Tekrar eden bulgu — sadece brain log'una not düş
              const skipTitle = String(payload.title ?? "");
              setBrainText(prev => prev + `\n⏭️ Tekrar bulgu atlandı: ${skipTitle}\n`);
              break;
            }

            case "agent_summarizing":
              setPhase("summarizing");
              setBrainMode("summarizing");
              break;

            case "agent_summary_token":
              setSummaryText(prev => prev + String(payload.token ?? ""));
              break;

            case "agent_summary":
              if (payload.summary) setSummaryText(String(payload.summary));
              setPhase("summarizing");
              setBrainMode("summarizing");
              break;

            case "agent_error":
              setErrorMsg(String(payload.error ?? payload.message ?? "Beklenmeyen hata"));
              setPhase("error");
              break;

            case "agent_done":
              setPhase("done");
              setDuration(Math.floor((Date.now() - _runStartedAt) / 1000));
              setBrainMode("");
              setSubStep(0); setSubTotal(0); setSequencePlan(null);
              // Session ID'yi sakla — bir sonraki çalıştırmada browser reuse için kullanılır
              if (payload.session_id) lastSessionIdRef.current = payload.session_id as string;
              if (payload.dry_run) {
                // Dry-run tamamlandı: özet olmadan sadece plan göster
                setSummaryText(
                  `🔍 Dry-run tamamlandı — ${payload.hypothesis_count ?? 0} hipotez üretildi.\n` +
                  `Tarayıcı aksiyonu çalıştırılmadı. Tam test için "Dry Run" seçeneğini kapatın.`
                );
              }
              break;
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setPhase("idle");
      } else {
        setErrorMsg(err instanceof Error ? err.message : String(err));
        setPhase("error");
      }
    } finally {
      abortRef.current = null;
    }
  }, [config, projectId, phase, currentStep, currentUrl, startedAt]);

  const handleAbort = useCallback(() => {
    abortRef.current?.abort();
    setPhase("idle");
  }, []);

  const handleReset = useCallback(() => {
    setPhase("idle");
    setPlanText(""); setBrainText(""); setSummaryText(""); setScreenshot("");
    setActions([]); setFindings([]); setErrorMsg(""); setCurrentStep(0);
    setDuration(0); setCurrentUrl(""); setBrainMode("");
    setHypotheses([]); setActiveHypId(""); setDiscovery(null); setComprehensionText("");
    setLearnedFacts([]); setSequencePlan(null); setSubStep(0); setSubTotal(0);
    setApiCalls([]); setConsoleErrors([]); setTechStack([]); setWave(1); setWaveReason("");
    setCoverage(null); setSensitiveKeys([]);
  }, []);

  const isRunning = phase === "starting" || phase === "planning" || phase === "running" || phase === "summarizing";
  const isDone    = phase === "done";

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">

      {/* ── Top bar ── */}
      <header className="flex items-center justify-between gap-4 border-b border-slate-800 px-5 py-3">
        <div className="flex items-center gap-3">
          <Link href="../scenarios" className="text-slate-500 hover:text-slate-300 text-lg leading-none">←</Link>
          <div>
            <h1 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="text-base">🤖</span> LLM Ajan Testi
            </h1>
            <p className="text-[11px] text-slate-500">Yapay zeka sayfayı planlı olarak keşfeder ve belgeler</p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          {isRunning && (
            <span className="font-mono text-xs text-slate-400 tabular-nums">
              {Math.floor(duration / 60)}:{String(duration % 60).padStart(2, "0")}
            </span>
          )}
          <PhaseBadge phase={phase} />
          {isRunning && (
            <button onClick={handleAbort}
              className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-500/20">
              ⏹ Durdur
            </button>
          )}
          {(isDone || phase === "error") && (
            <button onClick={handleReset}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700">
              ↺ Yeniden Başlat
            </button>
          )}
        </div>
      </header>

      {/* ── Config bar (only when idle/error) ── */}
      {(phase === "idle" || phase === "error") && (
        <div className="border-b border-slate-800 bg-slate-900/60 px-5 py-4">
          <div className="flex flex-wrap items-end gap-3 max-w-5xl">
            <div className="flex-1 min-w-[260px]">
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-slate-400">Hedef URL</label>
              <input
                value={config.targetUrl}
                onChange={e => setConfig(c => ({ ...c, targetUrl: e.target.value }))}
                placeholder="https://example.com"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-mono text-slate-200 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/25"
              />
            </div>
            <div className="w-36">
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-slate-400">Max Adım</label>
              <input type="number" min={3} max={20} value={config.maxSteps}
                onChange={e => setConfig(c => ({ ...c, maxSteps: parseInt(e.target.value) || 10 }))}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-violet-500/50 focus:outline-none"
              />
            </div>
            <div className="w-52">
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-slate-400">Test Odağı</label>
              <select value={config.testFocus}
                onChange={e => setConfig(c => ({ ...c, testFocus: e.target.value }))}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-violet-500/50 focus:outline-none">
                {FOCUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            {/* Dry-run toggle */}
            <div className="flex items-center gap-2">
              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  type="checkbox"
                  checked={config.dryRun}
                  onChange={e => setConfig(c => ({ ...c, dryRun: e.target.checked }))}
                  className="peer sr-only"
                />
                <div className="h-5 w-9 rounded-full bg-slate-700 peer-checked:bg-violet-600 transition-colors after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-transform peer-checked:after:translate-x-4" />
              </label>
              <span className="text-[11px] text-slate-400" title="Tarayıcı aksiyonu olmadan sadece hipotez planı üretir">
                Dry Run (önizleme)
              </span>
            </div>
            <button
              onClick={handleStart}
              disabled={!config.targetUrl}
              className={cn(
                "flex items-center gap-2 rounded-lg border px-5 py-2 text-sm font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed",
                config.dryRun
                  ? "border-amber-500/40 bg-amber-500/20 text-amber-100 hover:bg-amber-500/30"
                  : "border-violet-500/40 bg-violet-500/20 text-violet-100 hover:bg-violet-500/30"
              )}
            >
              <span className="text-base">{config.dryRun ? "🔍" : "🤖"}</span>
              {config.dryRun ? "Plan Önizle" : "Ajanı Başlat"}
            </button>
          </div>

          {/* Advanced */}
          <div className="mt-3 max-w-5xl">
            <button onClick={() => setAdvOpen(v => !v)}
              className="text-[11px] text-slate-500 hover:text-slate-300">
              🔑 Login ayarları {advOpen ? "▲" : "▼"}
            </button>
            {advOpen && (
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  { key: "loginUrl", ph: "Login URL" },
                  { key: "usernameSelector", ph: 'Username selector (input[name="email"])' },
                  { key: "passwordSelector", ph: 'Password selector (input[type="password"])' },
                  { key: "submitSelector", ph: 'Submit selector (button[type="submit"])' },
                  { key: "username", ph: "Kullanıcı adı" },
                  { key: "password", ph: "Şifre" },
                ].map(({ key, ph }) => (
                  <input key={key}
                    type={key === "password" ? "password" : "text"}
                    placeholder={ph}
                    value={(config as unknown as Record<string, string>)[key]}
                    onChange={e => setConfig(c => ({ ...c, [key]: e.target.value }))}
                    className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-[11px] font-mono text-slate-300 focus:border-violet-500/40 focus:outline-none"
                  />
                ))}
              </div>
            )}
          </div>

          {phase === "error" && (
            <p className="mt-3 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              ❌ {errorMsg}
            </p>
          )}
        </div>
      )}

      {/* ── Main 3-panel layout ── */}
      {(isRunning || isDone) && (
        <div className="flex flex-1 overflow-hidden" style={{ height: "calc(100vh - 120px)" }}>

          {/* ── LEFT: Browser preview ── */}
          <div className="flex w-[40%] flex-col border-r border-slate-800">
            {/* URL bar */}
            <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/80 px-3 py-2">
              <div className="flex gap-1">
                <span className="h-2.5 w-2.5 rounded-full bg-red-500/60" />
                <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/60" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/60" />
              </div>
              <div className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-0.5 text-[11px] font-mono text-slate-400 truncate">
                {currentUrl || config.targetUrl}
              </div>
              {isRunning && (
                <div className="h-2 w-2 rounded-full bg-violet-400 animate-pulse shrink-0" title="Tarayıcı aktif" />
              )}
            </div>

            {/* Screenshot */}
            <div className="flex-1 overflow-hidden bg-slate-950 flex items-center justify-center">
              {screenshot ? (
                <img
                  src={`data:image/jpeg;base64,${screenshot}`}
                  alt="agent-view"
                  className="h-full w-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center gap-3 text-slate-600">
                  {isRunning ? (
                    <>
                      <div className="h-8 w-8 rounded-full border-2 border-violet-500/40 border-t-violet-400 animate-spin" />
                      <span className="text-xs">
                        {phase === "starting" && "Tarayıcı başlatılıyor…"}
                        {phase === "planning" && "Hipotezler üretiliyor…"}
                        {phase === "running" && "Test yürütülüyor…"}
                        {phase === "summarizing" && "Özet hazırlanıyor…"}
                        {!["starting","planning","running","summarizing"].includes(phase) && "İşleniyor…"}
                      </span>
                      {duration > 0 && (
                        <span className="text-[10px] text-slate-700 font-mono">
                          {Math.floor(duration / 60)}:{String(duration % 60).padStart(2, "0")}
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="text-sm">Ekran görüntüsü yok</span>
                  )}
                </div>
              )}
            </div>

            {/* Action log */}
            <div className="border-t border-slate-800 bg-slate-900/60" style={{ maxHeight: "220px" }}>
              <div className="flex items-center justify-between border-b border-slate-800 px-3 py-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Eylem Geçmişi</span>
                <span className="text-[10px] text-slate-600">{actions.length} eylem</span>
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: "180px" }}>
                {actions.length === 0 && (
                  <div className="px-3 py-4 text-center text-[11px] text-slate-600">Henüz eylem yok</div>
                )}
                {[...actions].reverse().map((a) => (
                  <div key={`${a.step}-${a.timestamp}`}
                    className={cn(
                      "flex items-start gap-2 border-b border-slate-800/60 px-3 py-2 text-[11px]",
                      a.success === false ? "bg-red-500/5 border-red-500/20" : ""
                    )}>
                    <span className="mt-0.5 shrink-0 text-sm">{actionIcon(a.type)}</span>
                    <div className="min-w-0 flex-1">
                      <p className={cn("font-medium truncate", a.success === false ? "text-red-300" : "text-slate-300")}>
                        {a.description}
                      </p>
                      <p className="text-slate-600 truncate font-mono">{a.selector ?? a.value ?? ""}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {a.success === false && <span className="text-[9px] text-red-400">✗</span>}
                      <span className="rounded px-1 py-0.5 text-[9px] font-bold uppercase bg-slate-800 text-slate-400">
                        #{a.step}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── CENTER: Agent Brain ── */}
          <div className="flex w-[37%] flex-col border-r border-slate-800">
            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/80 px-4 py-2">
              <div className="flex items-center gap-2">
                <span className="text-sm">🧠</span>
                <span className="text-xs font-semibold text-slate-300">Ajan Zihni</span>
                {/* Wave badge */}
                <span className={cn(
                  "rounded-full px-2 py-0.5 text-[9px] font-bold uppercase",
                  wave === 1 ? "bg-violet-500/20 text-violet-300" : "bg-amber-500/20 text-amber-300"
                )}>
                  🌊 Dalga {wave}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {brainMode === "thinking" && (
                  <span className="flex items-center gap-1 text-[10px] text-violet-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse" />
                    {activeHypId ? `[${activeHypId}]` : "Düşünüyor"}
                  </span>
                )}
                {brainMode === "observing" && (
                  <span className="flex items-center gap-1 text-[10px] text-sky-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-400 animate-pulse" /> Gözlemliyor
                  </span>
                )}
                {brainMode === "summarizing" && (
                  <span className="flex items-center gap-1 text-[10px] text-amber-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" /> Özetliyor
                  </span>
                )}
                {subTotal > 0 && isRunning && (
                  <span className="text-[10px] font-mono text-violet-500/80 tabular-nums">
                    {subStep}/{subTotal}
                  </span>
                )}
                <span className="text-[10px] font-mono text-slate-600 tabular-nums">
                  adım {currentStep}/{config.maxSteps}
                </span>
              </div>
            </div>
            {/* Coverage meter */}
            {coverage && (
              <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-1.5 flex items-center gap-3">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-[9px] text-slate-500 uppercase tracking-widest">Kapsam</span>
                    <span className="text-[10px] font-bold text-slate-300">%{coverage.coverage_pct}</span>
                  </div>
                  <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-violet-500 to-emerald-500 rounded-full transition-all duration-700"
                      style={{ width: `${coverage.coverage_pct}%` }}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-1.5 text-[9px]">
                  {coverage.wave2_count > 0 && (
                    <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-amber-300 font-bold">W2: {coverage.wave2_count}</span>
                  )}
                  <span className="text-red-300 font-bold">{coverage.findings_by_severity?.critical ?? 0}🔴</span>
                  <span className="text-orange-300 font-bold">{coverage.findings_by_severity?.high ?? 0}🟠</span>
                </div>
              </div>
            )}

            {/* Step progress bar */}
            <div className="h-0.5 w-full bg-slate-800">
              <div
                className="h-full bg-gradient-to-r from-violet-600 to-sky-500 transition-all duration-500"
                style={{ width: `${Math.min(100, (currentStep / config.maxSteps) * 100)}%` }}
              />
            </div>
            {/* Sub-step progress bar (within hypothesis) */}
            {subTotal > 0 && isRunning && (
              <div className="h-0.5 w-full bg-slate-800/60">
                <div
                  className="h-full bg-violet-400/50 transition-all duration-300"
                  style={{ width: `${Math.min(100, (subStep / subTotal) * 100)}%` }}
                />
              </div>
            )}

            {/* Discovery + tech strip */}
            {discovery && (
              <div className="border-b border-slate-800 bg-slate-900/60 px-4 py-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="flex items-center gap-1 rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-[10px] font-bold text-violet-300">
                    {discovery.page_type === "auth" ? "🔑" :
                     discovery.page_type === "dashboard" ? "📊" :
                     discovery.page_type === "form" ? "📝" :
                     discovery.page_type === "list_table" ? "📋" : "🌐"}
                    {" "}{discovery.page_type}
                  </span>
                  {/* Tech stack */}
                  {techStack.map(t => (
                    <span key={t.name} className="flex items-center gap-0.5 rounded-full border border-sky-500/20 bg-sky-500/10 px-2 py-0.5 text-[10px] text-sky-300">
                      {techCategoryIcon(t.category)} {t.name}
                    </span>
                  ))}
                  {discovery.buttons_count > 0 && <span className="text-[10px] text-slate-500">👆{discovery.buttons_count}</span>}
                  {discovery.inputs_count > 0 && <span className="text-[10px] text-slate-500">⌨️{discovery.inputs_count}</span>}
                  {discovery.forms_count > 0 && <span className="text-[10px] text-slate-500">📋{discovery.forms_count}</span>}
                  {discovery.alerts.length > 0 && <span className="text-[10px] text-yellow-400">⚠️{discovery.alerts.length}</span>}
                  {sensitiveKeys.length > 0 && (
                    <span className="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold text-red-300">
                      🚨 {sensitiveKeys.length} hassas key
                    </span>
                  )}
                </div>
                {discovery.headings.length > 0 && (
                  <p className="mt-0.5 text-[10px] text-slate-600 truncate">
                    {discovery.headings.slice(0, 3).map(h => h.text).join(" › ")}
                  </p>
                )}
              </div>
            )}

            {/* Plan section */}
            {planText && (
              <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-3">
                <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-violet-400">📋 Hipotez Planı</p>
                {hypotheses.length > 0 ? (
                  <div className="space-y-1">
                    {hypotheses.map(h => {
                      const sc = h.status === "verified" ? "text-emerald-400" :
                                 h.status === "rejected" ? "text-red-400" :
                                 h.status === "testing"  ? "text-violet-400 animate-pulse" :
                                 h.status === "partial"  ? "text-yellow-400" : "text-slate-500";
                      const icon = h.status === "verified" ? "✅" : h.status === "rejected" ? "❌" :
                                   h.status === "testing" ? "⚡" : h.status === "partial" ? "⚠️" : "○";
                      return (
                        <div key={h.id}
                          className={cn(
                            "flex items-start gap-2 rounded-md px-2 py-1 text-[11px] transition-all",
                            activeHypId === h.id ? "bg-violet-500/10 border border-violet-500/20" : "hover:bg-slate-800/40"
                          )}>
                          <span className={cn("shrink-0 text-xs mt-0.5", sc)}>{icon}</span>
                          <div className="min-w-0">
                            <span className="font-mono text-slate-600 text-[10px]">{h.id}</span>
                            <span className="ml-1 text-slate-300">{h.claim}</span>
                            {h.confidence !== undefined && h.status !== "pending" && (
                              <span className="ml-1 text-[10px] text-slate-600">
                                {Math.round(h.confidence * 100)}%
                              </span>
                            )}
                          </div>
                          <span className={cn(
                            "shrink-0 text-[9px] font-bold uppercase rounded px-1 py-0.5",
                            h.priority === "critical" ? "bg-red-500/20 text-red-300" :
                            h.priority === "high" ? "bg-orange-500/15 text-orange-300" :
                            h.priority === "medium" ? "bg-yellow-500/15 text-yellow-300" : "bg-slate-700 text-slate-400"
                          )}>{h.priority}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <pre className="whitespace-pre-wrap text-[11px] leading-5 text-slate-300 font-sans">
                    {planText.slice(0, 600)}{planText.length > 600 ? "…" : ""}
                  </pre>
                )}
              </div>
            )}

            {/* Sequence plan widget — shows current hypothesis action checklist */}
            {sequencePlan && isRunning && (
              <div className="border-b border-slate-800 bg-slate-900/40 px-4 py-2 flex-shrink-0">
                <p className="text-[10px] font-bold uppercase tracking-widest text-violet-400 mb-1">⚡ Eylem Dizisi</p>
                <p className="text-[10px] text-slate-500 mb-1.5 leading-relaxed">{sequencePlan.strategy.slice(0, 90)}{sequencePlan.strategy.length > 90 ? "…" : ""}</p>
                <div className="space-y-0.5">
                  {sequencePlan.actions.map((a, i) => {
                    const done = i + 1 < subStep;
                    const active = i + 1 === subStep;
                    return (
                      <div key={i} className={cn(
                        "flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px] transition-colors",
                        active ? "bg-violet-500/15 text-violet-300" :
                        done   ? "text-slate-600" : "text-slate-400"
                      )}>
                        <span className="shrink-0 font-mono">
                          {done ? "✓" : active ? "▶" : `${i + 1}.`}
                        </span>
                        <span className="truncate">{a.description || a.type}</span>
                        {a.critical && (
                          <span className="shrink-0 rounded bg-red-500/20 px-1 py-px text-[8px] font-bold text-red-400">CRITICAL</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Brain stream */}
            <div
              ref={brainScrollRef}
              className="flex-1 overflow-y-auto px-4 py-3"
            >
              {!brainText && !summaryText && (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-600">
                  <div className="text-3xl">🧠</div>
                  <p className="text-xs text-center">Ajan düşünceleri burada akacak…</p>
                </div>
              )}

              {brainText && (
                <pre className="whitespace-pre-wrap text-[11px] leading-[1.7] text-slate-300 font-sans">
                  {brainText}
                  {isRunning && brainMode !== "" && <Cursor />}
                </pre>
              )}

              {summaryText && (
                <div className="mt-4 rounded-xl border border-amber-500/25 bg-amber-500/5 p-4">
                  <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-amber-400">📊 Özet Rapor</p>
                  <pre className="whitespace-pre-wrap text-[11px] leading-[1.7] text-slate-300 font-sans">
                    {summaryText}
                    {phase === "summarizing" && <Cursor />}
                  </pre>
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: Tabbed panel ── */}
          <div className="flex w-[23%] flex-col">

            {/* Tab bar */}
            <div className="flex items-center border-b border-slate-800 bg-slate-900/80 flex-shrink-0">
              {(["hypotheses", "network", "console", "findings"] as const).map(tab => {
                const labels: Record<string, string> = {
                  hypotheses: `🧪 ${hypotheses.length}`,
                  network: `📡 ${apiCalls.length}`,
                  console: `⚠️ ${consoleErrors.length}`,
                  findings: `🔍 ${findings.length}`,
                };
                const hasAlert = (tab === "network" && apiCalls.some(c => c.is_error)) ||
                                 (tab === "console" && consoleErrors.some(c => c.type === "error")) ||
                                 (tab === "findings" && findings.some(f => ["critical","high"].includes(f.severity)));
                return (
                  <button key={tab} onClick={() => setRightTab(tab)}
                    className={cn(
                      "flex-1 py-1.5 text-[10px] font-semibold transition-colors relative",
                      rightTab === tab
                        ? "text-violet-300 border-b-2 border-violet-400 bg-slate-800/40"
                        : "text-slate-500 hover:text-slate-300"
                    )}>
                    {labels[tab]}
                    {hasAlert && rightTab !== tab && (
                      <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-red-400" />
                    )}
                  </button>
                );
              })}
            </div>

            {/* ── Tab: Hypotheses ── */}
            {rightTab === "hypotheses" && (
              <div className="flex flex-col flex-1 overflow-hidden">
                {/* Counters */}
                <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-900/40 px-3 py-1">
                  <div className="flex items-center gap-1.5 text-[9px] font-bold">
                    <span className="text-emerald-400">{hypotheses.filter(h => h.status === "verified").length}✅</span>
                    <span className="text-red-400">{hypotheses.filter(h => h.status === "rejected").length}❌</span>
                    <span className="text-yellow-400">{hypotheses.filter(h => h.status === "partial").length}⚠️</span>
                    <span className="text-slate-500">{hypotheses.filter(h => h.status === "pending" || h.status === "testing").length}○</span>
                  </div>
                  {wave > 1 && <span className="text-[9px] text-amber-300 font-bold">🌊 {wave} dalga</span>}
                </div>
                <div className="flex-1 overflow-y-auto">
                  {hypotheses.map(h => (
                    <div key={h.id} className={cn(
                      "flex items-start gap-1.5 border-b border-slate-800/50 px-3 py-1.5 text-[10px] transition-colors",
                      activeHypId === h.id ? "bg-violet-500/10" : "",
                      h.wave === 2 ? "border-l-2 border-l-amber-500/30" : ""
                    )}>
                      <span className={cn("shrink-0 text-xs mt-px",
                        h.status === "verified" ? "text-emerald-400" :
                        h.status === "rejected" ? "text-red-400" :
                        h.status === "testing"  ? "text-violet-400 animate-pulse" :
                        h.status === "partial"  ? "text-yellow-400" : "text-slate-600"
                      )}>
                        {h.status === "verified" ? "✅" : h.status === "rejected" ? "❌" :
                         h.status === "testing" ? "⚡" : h.status === "partial" ? "⚠️" : "○"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1 mb-px">
                          <span className="font-mono text-[9px] text-slate-600">{h.id}</span>
                          <span className="text-[9px] text-slate-600">{areaIcon(h.area)}</span>
                          {h.wave === 2 && <span className="text-[8px] text-amber-400 font-bold">W2</span>}
                        </div>
                        <span className="text-slate-400 leading-snug">{h.claim.slice(0, 60)}{h.claim.length > 60 ? "…" : ""}</span>
                        {h.confidence !== undefined && h.status !== "pending" && (
                          <div className="mt-0.5 h-0.5 w-full bg-slate-800 rounded-full overflow-hidden">
                            <div className={cn("h-full rounded-full", h.status === "verified" ? "bg-emerald-500" : h.status === "rejected" ? "bg-red-500" : "bg-yellow-500")}
                                 style={{ width: `${Math.round(h.confidence * 100)}%` }} />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {hypotheses.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-600 py-8">
                      <span className="text-2xl">🧪</span>
                      <p className="text-[11px] text-center px-3">Hipotezler oluşturulunca burada görünür</p>
                    </div>
                  )}
                </div>
                {/* Working memory */}
                {learnedFacts.length > 0 && (
                  <div className="border-t border-slate-800 flex-shrink-0">
                    <button onClick={() => setMemoryOpen(v => !v)}
                      className="flex items-center justify-between w-full px-3 py-1.5 hover:bg-slate-800/40 transition-colors">
                      <span className="text-[10px] text-slate-500">💾 Çalışma Belleği ({learnedFacts.length})</span>
                      <span className="text-[10px] text-slate-600">{memoryOpen ? "▲" : "▼"}</span>
                    </button>
                    {memoryOpen && (
                      <div className="overflow-y-auto border-t border-slate-800/40" style={{ maxHeight: "90px" }}>
                        {learnedFacts.map((fact, i) => (
                          <div key={i} className="border-b border-slate-800/30 px-3 py-1 text-[9px] text-slate-500 leading-relaxed">
                            <span className="text-slate-700 font-mono mr-1">#{i+1}</span>{fact.slice(0, 70)}{fact.length > 70 ? "…" : ""}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ── Tab: Network ── */}
            {rightTab === "network" && (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-900/40 px-3 py-1">
                  <span className="text-[10px] text-slate-400">{apiCalls.length} çağrı</span>
                  <span className="text-[10px] text-red-400">{apiCalls.filter(c => c.is_error).length} hata</span>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {apiCalls.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-600 py-8">
                      <span className="text-2xl">📡</span>
                      <p className="text-[11px] text-center px-3">API çağrıları burada izlenir</p>
                    </div>
                  )}
                  {[...apiCalls].reverse().map((call, i) => (
                    <div key={i} className={cn(
                      "flex items-center gap-2 border-b border-slate-800/40 px-3 py-1.5 text-[10px]",
                      call.is_error ? "bg-red-500/5" : ""
                    )}>
                      <span className={cn("shrink-0 text-[9px] font-bold font-mono w-8", statusColor(call.status))}>
                        {call.status}
                      </span>
                      <span className={cn("shrink-0 text-[9px] font-bold rounded px-1",
                        call.method === "GET" ? "text-sky-400" :
                        call.method === "POST" ? "text-violet-400" :
                        call.method === "DELETE" ? "text-red-400" : "text-slate-400"
                      )}>
                        {call.method}
                      </span>
                      <span className="flex-1 truncate text-slate-400 font-mono" title={call.url}>
                        {call.url.split("/").slice(-2).join("/")}
                      </span>
                      <span className="shrink-0 text-[9px] text-slate-600">{call.duration_ms}ms</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Tab: Console ── */}
            {rightTab === "console" && (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-900/40 px-3 py-1">
                  <span className="text-[10px] text-red-400">{consoleErrors.filter(c => c.type === "error").length} hata</span>
                  <span className="text-[10px] text-yellow-400">{consoleErrors.filter(c => c.type === "warning").length} uyarı</span>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {consoleErrors.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-600 py-8">
                      <span className="text-2xl">✅</span>
                      <p className="text-[11px] text-center px-3">Console hatası yok</p>
                    </div>
                  )}
                  {[...consoleErrors].reverse().map((msg, i) => (
                    <div key={i} className={cn(
                      "border-b border-slate-800/40 px-3 py-1.5 text-[10px]",
                      msg.type === "error" ? "bg-red-500/5" : "bg-yellow-500/5"
                    )}>
                      <span className={cn("font-bold text-[9px] uppercase mr-1",
                        msg.type === "error" ? "text-red-400" : "text-yellow-400"
                      )}>{msg.type}</span>
                      <span className="text-slate-400 leading-relaxed break-words">{msg.text.slice(0, 100)}{msg.text.length > 100 ? "…" : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Tab: Findings ── */}
            {rightTab === "findings" && (
              <div className="flex flex-col flex-1 overflow-hidden">
                {findings.length > 0 && (
                  <div className="grid grid-cols-2 gap-px border-b border-slate-800 bg-slate-800 flex-shrink-0">
                    {(["critical", "high", "medium", "low"] as const).map(sev => {
                      const count = findings.filter(f => f.severity === sev).length;
                      const col = severityColor(sev);
                      return (
                        <div key={sev} className={cn("px-2 py-1 bg-slate-900/80", count === 0 ? "opacity-30" : "")}>
                          <p className={cn("text-[9px] font-bold uppercase", col.text)}>{sev}</p>
                          <p className={cn("text-base font-bold leading-none", col.text)}>{count}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
                <div className="flex-1 overflow-y-auto">
                  {findings.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-600 py-8">
                      <span className="text-2xl">🔍</span>
                      <p className="text-[11px] text-center px-3">Bulgular ajan keşfettikçe görünür</p>
                    </div>
                  )}
                  {findings.map((f) => {
                    const col = severityColor(f.severity);
                    return (
                      <div key={f.id} className={cn("border-b border-slate-800 p-3", col.bg.split(" ")[0])}>
                        <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                          <span className={cn("rounded px-1.5 py-0.5 text-[9px] font-bold uppercase", col.badge)}>{f.severity}</span>
                          {f.category && (
                            <span className="rounded bg-slate-700/60 px-1.5 py-0.5 text-[9px] text-slate-400">
                              {f.category}
                            </span>
                          )}
                          {f.hypothesis_id && (
                            <span className="rounded bg-slate-800/80 px-1.5 py-0.5 text-[9px] text-slate-500">
                              {f.hypothesis_id}
                            </span>
                          )}
                          {f.wave === 2 && <span className="text-[9px] text-amber-300 font-bold">W2</span>}
                          <span className="text-[10px] text-slate-600 ml-auto">#{f.step}</span>
                        </div>
                        {f.title && (
                          <p className="text-[11px] font-semibold text-slate-200 mb-0.5">
                            {f.title.slice(0, 70)}
                          </p>
                        )}
                        <p className="text-[11px] text-slate-400 leading-relaxed">{f.text.slice(0, 110)}{f.text.length > 110 ? "…" : ""}</p>
                        <p className="mt-1 text-[9px] text-slate-600 truncate font-mono">{f.url}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Stats footer (done state) */}
            {isDone && (
              <div className="border-t border-slate-800 bg-slate-900/60 px-3 py-2 space-y-1 flex-shrink-0">
                <div className="grid grid-cols-3 gap-1 text-center mb-1">
                  <div><p className="text-[9px] text-slate-600">Eylem</p><p className="text-xs font-bold text-slate-300">{actions.length}</p></div>
                  <div><p className="text-[9px] text-slate-600">Bulgu</p><p className="text-xs font-bold text-slate-300">{findings.length}</p></div>
                  <div><p className="text-[9px] text-slate-600">Süre</p><p className="text-xs font-bold font-mono text-slate-300">{Math.floor(duration/60)}:{String(duration%60).padStart(2,"0")}</p></div>
                </div>
                <button
                  onClick={() => {
                    const techLine = techStack.length > 0 ? `Teknoloji: ${techStack.map(t => t.name).join(", ")}\n` : "";
                    const covLine = coverage ? `Kapsam: %${coverage.coverage_pct} (${coverage.tested_areas.join(", ")})\n` : "";
                    const findingsMd = findings.map(f => {
                      const impactLine = f.impact ? `\nEtki: ${f.impact}` : "";
                      const stepsLine = f.steps_to_reproduce?.length ? `\nAdımlar: ${f.steps_to_reproduce.join(" → ")}` : "";
                      return `### [${f.severity.toUpperCase()}${f.wave===2?" W2":""}] ${f.title || f.text.slice(0,60)}\n${f.text}${impactLine}${stepsLine}\nURL: ${f.url}`;
                    });
                    const md = [
                      "# LLM Ajan Test Raporu",
                      `URL: ${config.targetUrl} | Tarih: ${new Date().toLocaleString("tr-TR")}`,
                      techLine + covLine +
                      `Eylem: ${actions.length} | Bulgu: ${findings.length} | Süre: ${duration}s | Dalga: ${wave}`,
                      "", "## Test Planı", planText,
                      "", "## Bulgular", ...findingsMd,
                      "", "## Özet", summaryText,
                    ].join("\n");
                    const blob = new Blob([md], { type: "text/markdown;charset=utf-8;" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url; a.download = `llm_agent_${Date.now()}.md`; a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="w-full rounded-lg border border-emerald-500/25 bg-emerald-500/10 py-1.5 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-500/20"
                >
                  ↓ Rapor İndir (.md)
                </button>
                <button
                  type="button"
                  onClick={() => {
                    // Tam veri JSON — Jira/Slack/diğer sistemlere entegrasyon için
                    const payload = {
                      meta: {
                        url: config.targetUrl,
                        date_iso: new Date().toISOString(),
                        duration_sec: duration,
                        wave: wave,
                      },
                      summary: summaryText,
                      plan: planText,
                      coverage: coverage,
                      tech_stack: techStack,
                      hypotheses: hypotheses,
                      findings: findings,
                      actions: actions,
                      api_calls: apiCalls.slice(0, 50),
                      console_errors: consoleErrors.slice(0, 20),
                      sensitive_keys: sensitiveKeys,
                      learned_facts: learnedFacts,
                    };
                    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8;" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url; a.download = `llm_agent_${Date.now()}.json`; a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="mt-1.5 w-full rounded-lg border border-sky-500/25 bg-sky-500/10 py-1.5 text-[11px] font-semibold text-sky-300 hover:bg-sky-500/20"
                >
                  ↓ Tam Veri (.json)
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Live bottom bar ── */}
      {(isRunning || isDone) && (
        <div className="flex items-center gap-4 border-t border-slate-800 bg-slate-900/80 px-5 py-1.5 text-[10px] flex-shrink-0">
          <span className="text-slate-600">📡 {apiCalls.length} API</span>
          <span className={cn(apiCalls.filter(c => c.is_error).length > 0 ? "text-red-400" : "text-slate-600")}>
            {apiCalls.filter(c => c.is_error).length > 0 ? `⛔ ${apiCalls.filter(c => c.is_error).length} hata` : "✅ hata yok"}
          </span>
          <span className={cn(consoleErrors.filter(c => c.type === "error").length > 0 ? "text-yellow-400" : "text-slate-600")}>
            {consoleErrors.length > 0 ? `⚠️ ${consoleErrors.length} console` : "🟢 console temiz"}
          </span>
          {techStack.length > 0 && (
            <span className="text-sky-500">{techStack.map(t => t.name).join(" · ")}</span>
          )}
          {coverage && (
            <span className="text-emerald-400 font-bold ml-auto">%{coverage.coverage_pct} kapsam</span>
          )}
          {!coverage && isRunning && (
            <span className="text-slate-600 ml-auto">
              {hypotheses.filter(h => ["verified","rejected","partial"].includes(h.status)).length}/{hypotheses.length} hipotez
            </span>
          )}
        </div>
      )}

      {/* ── Idle empty state ── */}
      {phase === "idle" && (
        <div className="flex flex-1 items-center justify-center p-8">
          <div className="max-w-lg text-center">
            <div className="mb-4 text-5xl">🤖</div>
            <h2 className="text-lg font-bold text-white mb-2">Otonom LLM Test Ajanı</h2>
            <p className="text-sm text-slate-400 mb-6 leading-relaxed">
              Ajan bir web sayfasını açar, LLM ile ne test edeceğini planlar,
              adım adım tarayıcıyı yönetir, bulguları canlı olarak belgeler
              ve sonunda kapsamlı bir rapor üretir.
            </p>
            <div className="grid grid-cols-3 gap-3 text-left mb-6">
              {[
                { icon: "📋", title: "Akıllı Planlama", desc: "LLM sayfayı görür, ne test edeceğini stratejik olarak planlar" },
                { icon: "🧠", title: "ReAct Döngüsü", desc: "Düşün → Eylem yap → Gözlemle → Tekrar döngüsü" },
                { icon: "🔍", title: "Canlı Bulgular", desc: "Her adımdaki anormal davranış otomatik belgelenir" },
              ].map(({ icon, title, desc }) => (
                <div key={title} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                  <div className="text-xl mb-1">{icon}</div>
                  <p className="text-xs font-semibold text-white mb-1">{title}</p>
                  <p className="text-[11px] text-slate-500 leading-relaxed">{desc}</p>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-600">
              URL girin ve <strong className="text-slate-400">Ajanı Başlat</strong>'a tıklayın
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
