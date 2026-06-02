"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { aiComplete, aiStream } from "@/lib/ai-gateway";
import { getToken, ensureValidToken } from "@/lib/api-client";
import { MonkeyConfigPanel } from "./components/MonkeyConfigPanel";
import { MonkeySessionList } from "./components/MonkeySessionList";
import { BugReportPanel } from "./components/BugReportPanel";
import { MonkeyLivePreview } from "./components/MonkeyLivePreview";
import { AiPipelinePanel } from "./components/AiPipelinePanel";
import {
  buildDetailedAnalysisPrompt,
  buildScenariosPromptFromEngine,
  buildKaratePrompt,
} from "./prompts";

// ── Types ────────────────────────────────────────────────────────────────────

type ActionType =
  | "click"
  | "input"
  | "scroll"
  | "navigate"
  | "resize"
  | "keypress";

type SessionConfig = {
  targetUrl: string;
  actionCount: number;
  seed: string;
  actionTypes: ActionType[];
};

type AiPhase = "idle" | "scenarios" | "karate" | "done" | "error";

type EngineAction = {
  step: number;
  type: string;
  url: string;
  timestamp: string;
  target?: string;
  value?: string;
  result?: string;
  triggered_error?: boolean;
  load_time_ms?: number;
  direction?: string;
  key?: string;
  viewport?: string;
};

type EngineConsoleError = {
  type: string;
  text: string;
  url: string;
  timestamp: string;
  category: string;
};

type EngineNetworkError = {
  url: string;
  status: number;
  page_url: string;
  timestamp: string;
  category: string;
};

type EngineBug = {
  category: string;
  severity: "critical" | "warning" | string;
  count: number;
  sample: string;
  affected_pages: string[];
};

type EngineScenario = {
  title: string;
  type: string;
  description: string;
  steps: { action: string; expected: string }[];
  priority: string;
};

type EngineRecommendation = { priority: string; text: string };

type EngineAnalysis = {
  scenarios: EngineScenario[];
  bugs: EngineBug[];
  recommendations: EngineRecommendation[];
  risk_level: string;
  summary: {
    total_bugs: number;
    critical_bugs: number;
    warning_bugs: number;
    scenarios_generated: number;
    pages_with_errors: number;
    error_categories: string[];
    network_categories: string[];
  };
};

type EngineResult = {
  run_id?: string;
  status: string;
  test_url: string;
  actions_performed: number;
  actions_log: EngineAction[];
  action_stats: Record<string, { total: number; success: number; error: number }>;
  console_errors: EngineConsoleError[];
  network_errors: EngineNetworkError[];
  error_count: number;
  stability_score: number;
  pages_visited: string[];
  pages_visited_count: number;
  performance_metrics: { url: string; load_time_ms: number; timestamp: string }[];
  screenshots: { final?: string };
  total_time_seconds: number;
  analysis: EngineAnalysis;
  started_at: string;
  video_url?: string | null;
};

type AuthConfig = {
  login_url: string;
  username_selector: string;
  password_selector: string;
  submit_selector: string;
  username: string;
  password: string;
};

type LiveFrame = { step: number | "final"; screenshot: string; url: string };

type HistoryEntry = {
  id: string;
  timestamp: string;
  url: string;
  actions: number;
  errors: number;
  stability: number;
  scenarios: number;
  videoUrl?: string | null;
  data: EngineResult;
};

// ── Constants ────────────────────────────────────────────────────────────────

const DEFAULT_ACTIONS: ActionType[] = [
  "click",
  "input",
  "scroll",
  "navigate",
  "keypress",
];

const ACTION_LABELS: Record<ActionType, string> = {
  click: "Rastgele Tıklama",
  input: "Rastgele Yazma",
  scroll: "Kaydırma",
  navigate: "Geri/İleri Gezinme",
  resize: "Pencere Boyutu Değiştirme",
  keypress: "Rastgele Tuş Basma",
};

const FRONTEND_TO_ENGINE_ACTIONS: Record<ActionType, string[]> = {
  click: ["click"],
  input: ["fill"],
  scroll: ["scroll"],
  navigate: ["navigate", "back_forward"],
  resize: ["resize_viewport"],
  keypress: ["keyboard", "tab_navigation"],
};

const HISTORY_KEY = "bgts_monkey_history_v1";
const HISTORY_MAX = 20;

// ── Helpers ──────────────────────────────────────────────────────────────────

function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function download(content: string, filename: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const el = document.createElement("a");
  el.href = url;
  el.download = filename;
  el.click();
  URL.revokeObjectURL(url);
}

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as HistoryEntry[];
  } catch {
    return [];
  }
}

function saveHistory(items: HistoryEntry[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, HISTORY_MAX)));
  } catch {
    // sessiz geç (quota dolmuş olabilir)
  }
}

// ── Component ────────────────────────────────────────────────────────────────

export default function MonkeyTestingPage() {
  const projectId = useRouteParam("projectId");

  const [config, setConfig] = useState<SessionConfig>({
    targetUrl: "https://cortex-test.bgtsai.com",
    actionCount: 50,
    seed: "bgts-monkey-1",
    actionTypes: DEFAULT_ACTIONS,
  });

  const [authOpen, setAuthOpen] = useState(false);
  const [auth, setAuth] = useState<AuthConfig>({
    login_url: "",
    username_selector: "",
    password_selector: "",
    submit_selector: "",
    username: "",
    password: "",
  });
  const [recordVideo, setRecordVideo] = useState(false);

  const [liveRunning, setLiveRunning] = useState(false);
  const [liveProgress, setLiveProgress] = useState(0);
  const [liveActions, setLiveActions] = useState<EngineAction[]>([]);
  const [liveFrame, setLiveFrame] = useState<LiveFrame | null>(null);
  const [liveConsoleErrors, setLiveConsoleErrors] = useState<EngineConsoleError[]>([]);
  const [liveNetworkErrors, setLiveNetworkErrors] = useState<EngineNetworkError[]>([]);
  const [liveResult, setLiveResult] = useState<EngineResult | null>(null);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [liveStatus, setLiveStatus] = useState<string>("");
  const abortRef = useRef<AbortController | null>(null);

  const [drawerAction, setDrawerAction] = useState<EngineAction | null>(null);

  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  const [aiPhase, setAiPhase] = useState<AiPhase>("idle");
  const [scenariosText, setScenariosText] = useState<string | null>(null);
  const [karateText, setKarateText] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  // ── Akıllı Senaryo Analizi (streaming LLM) ────────────────────────
  const [analysisStreaming, setAnalysisStreaming] = useState(false);
  const [analysisText, setAnalysisText] = useState<string>("");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisDone, setAnalysisDone] = useState(false);
  const analysisAbortRef = useRef<AbortController | null>(null);

  // ── Pre-flight URL probe ──────────────────────────────────────────────────
  type ProbeResult = {
    ok: boolean;
    skipped?: boolean;
    status?: number;
    final_url?: string;
    elapsed_ms?: number;
    body_size?: number;
    redirected?: boolean;
    error?: string;
    reason?: string;
  };
  type ProbeResponse = { target: ProbeResult; login: ProbeResult };

  const [probing, setProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<ProbeResponse | null>(null);

  const handleProbe = useCallback(async () => {
    if (!config.targetUrl || probing) return;
    setProbing(true);
    setProbeResult(null);
    try {
      const token = getToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(
        `/api/v1/tspm/projects/${projectId}/monkey-testing/probe`,
        {
          method: "POST",
          credentials: "include",
          headers,
          body: JSON.stringify({
            url: config.targetUrl,
            login_url: auth.login_url || "",
          }),
        },
      );
      if (!res.ok) {
        setProbeResult({
          target: { ok: false, error: "http", reason: `Probe başarısız: ${res.status}` },
          login:  { ok: false, skipped: true, reason: "" },
        });
        return;
      }
      setProbeResult(await res.json() as ProbeResponse);
    } catch (err) {
      setProbeResult({
        target: { ok: false, error: "network", reason: err instanceof Error ? err.message : "Bilinmeyen hata" },
        login:  { ok: false, skipped: true, reason: "" },
      });
    } finally {
      setProbing(false);
    }
  }, [config.targetUrl, auth.login_url, projectId, probing]);

  // ── Live SSE runner ────────────────────────────────────────────────────────
  const handleRunLive = useCallback(async () => {
    setLiveProgress(0);
    setLiveActions([]);
    setLiveFrame(null);
    setLiveConsoleErrors([]);
    setLiveNetworkErrors([]);
    setLiveResult(null);
    setLiveError(null);
    setScenariosText(null);
    setKarateText(null);
    setAiPhase("idle");

    // Pre-flight: projectId UUID formatında mı?
    const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!projectId) {
      setLiveError("Proje ID eksik. Portfolio'dan bir proje seçin.");
      return;
    }
    if (!UUID_RE.test(projectId)) {
      setLiveError(
        `Geçersiz proje ID formatı: "${projectId}". ` +
        `Beklenen UUID formatı (örn: 0f8fad5b-d9cb-469f-a165-70867728950e). ` +
        `URL'i kontrol edin veya Portfolio'dan tekrar seçin.`,
      );
      return;
    }

    setLiveRunning(true);
    setLiveStatus("Başlatılıyor…");

    // ── Oturum tazeliği kontrolü ──────────────────────────────────────
    // SSE stream başlamadan önce token/cookie'nin geçerli olduğundan emin ol.
    // Expire olmuşsa refresh endpoint'i ile yenilenir; başarısız olursa
    // kullanıcıya anlamlı hata gösterilir.
    setLiveStatus("Oturum kontrol ediliyor…");
    const sessionOk = await ensureValidToken();
    if (!sessionOk) {
      // Refresh başarısız — kullanıcı yeniden giriş yapmalı
      setLiveError("Oturumunuz sona erdi. Lütfen sayfayı yenileyip tekrar deneyin.");
      setLiveRunning(false);
      setLiveStatus("");
      return;
    }

    setLiveStatus("Başlatılıyor…");

    const enabledEngineActions = Array.from(
      new Set(
        config.actionTypes.flatMap(
          (t) => FRONTEND_TO_ENGINE_ACTIONS[t] ?? []
        )
      )
    );

    const credentials = auth.login_url
      ? {
          login_url: auth.login_url,
          username_selector: auth.username_selector,
          password_selector: auth.password_selector,
          submit_selector: auth.submit_selector,
          username: auth.username,
          password: auth.password,
        }
      : undefined;

    const body = {
      url: config.targetUrl,
      max_actions: config.actionCount,
      record_video: recordVideo,
      frame_every: 3,
      credentials,
      config: { enabled_actions: enabledEngineActions },
    };

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const token = getToken();
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const streamUrl = `/api/v1/tspm/projects/${projectId}/monkey-testing/run/stream`;
      const fetchOpts: RequestInit = {
        method: "POST",
        credentials: "include",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      };

      let res = await fetch(streamUrl, fetchOpts);

      // 401 → token yenilemeyi dene ve bir kez daha çağır
      if (res.status === 401) {
        setLiveStatus("Oturum yenileniyor…");
        const refreshed = await ensureValidToken();
        if (refreshed) {
          res = await fetch(streamUrl, { ...fetchOpts, signal: controller.signal });
        }
      }

      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => "");
        // Status'a göre kullanıcı dostu mesaj
        let friendly: string;
        switch (res.status) {
          case 401:
            friendly = "Oturum süresi dolmuş. Sayfayı yenileyip tekrar deneyin (F5).";
            break;
          case 403:
            friendly = "Bu projeye erişim yetkiniz yok. Yöneticiden üye eklenmesini isteyin.";
            break;
          case 404:
            friendly =
              `Proje bulunamadı (ID: ${projectId.slice(0, 8)}…). ` +
              `Bu proje silinmiş olabilir veya başka bir hesapta tanımlı. ` +
              `Portfolio'dan geçerli bir proje seçin.`;
            break;
          case 503:
            friendly = "Engine bağlantı hatası. Port 5001'in açık olduğundan emin olun.";
            break;
          case 502:
          case 504:
            friendly = "Backend gecikti veya kapalı. Birkaç saniye sonra tekrar deneyin.";
            break;
          default:
            friendly = `Sunucu yanıtı: ${res.status} ${text.slice(0, 200)}`;
        }
        throw new Error(friendly);
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
          // Each SSE record is multiple lines: `event: <name>\ndata: <json>`.
          // Engine puts the type on the `event:` line and only the payload in
          // `data:`. The previous parser only read `data:` and read evt.type
          // from the JSON, which silently dropped every event.
          let eventName = "";
          let dataLine = "";
          for (const ln of raw.split("\n")) {
            const t = ln.trim();
            if (t.startsWith("event:")) eventName = t.slice(6).trim();
            else if (t.startsWith("data:")) dataLine = t.slice(5).trim();
          }
          if (!dataLine) continue;

          let payload: { [k: string]: unknown };
          try {
            payload = JSON.parse(dataLine);
          } catch {
            continue;
          }

          // Engine sends `image` for screenshots; UI uses `screenshot`.
          // Normalize both names to `screenshot` so the UI works regardless.
          if (payload.image !== undefined && payload.screenshot === undefined) {
            payload.screenshot = payload.image;
          }

          // Allow legacy events that include a type field; otherwise rely on
          // the SSE event line.
          const evt: { type: string; [k: string]: unknown } = {
            ...payload,
            type: (typeof payload.type === "string" && payload.type) || eventName,
          };

          switch (evt.type) {
            case "start":
              setLiveStatus(`Tarayıcı açıldı — ${evt.max_actions ?? config.actionCount} eylem hazırlanıyor`);
              break;
            case "login":
              setLiveStatus(
                evt.status === "completed"
                  ? "Giriş yapıldı, teste başlanıyor"
                  : `Giriş başarısız: ${(evt.error as string) ?? "?"}`
              );
              break;
            case "nav":
              setLiveStatus(`Sayfa yüklendi (${evt.load_time_ms}ms) — eylemler başlıyor`);
              break;
            case "action": {
              const a = evt as unknown as EngineAction;
              setLiveActions((prev) => [...prev, a]);
              setLiveProgress(
                Math.round(((a.step ?? 0) / Math.max(1, config.actionCount)) * 100)
              );
              setLiveStatus(`Eylem ${a.step}/${config.actionCount}: ${a.type}`);
              break;
            }
            case "frame": {
              setLiveFrame({
                step: (evt.step as number) ?? 0,
                screenshot: evt.screenshot as string,
                url: (evt.url as string) ?? "",
              });
              break;
            }
            case "error_shot": {
              if (evt.screenshot) {
                setLiveFrame((prev) => ({
                  step: (evt.step as number) ?? 0,
                  screenshot: evt.screenshot as string,
                  url: prev?.url ?? "",
                }));
              }
              break;
            }
            case "console_error":
              setLiveConsoleErrors((prev) => [
                ...prev,
                evt as unknown as EngineConsoleError,
              ]);
              break;
            case "network_error":
              setLiveNetworkErrors((prev) => [
                ...prev,
                evt as unknown as EngineNetworkError,
              ]);
              break;
            case "done": {
              const result = evt as unknown as EngineResult;
              setLiveResult(result);
              setLiveProgress(100);
              setLiveStatus(
                `Tamamlandı — Stabilite %${result.stability_score}, ${result.error_count} hata`
              );
              const entry: HistoryEntry = {
                id: result.run_id ?? `run-${Date.now()}`,
                timestamp: result.started_at ?? new Date().toISOString(),
                url: result.test_url,
                actions: result.actions_performed,
                errors: result.error_count,
                stability: result.stability_score,
                scenarios: result.analysis?.scenarios?.length ?? 0,
                videoUrl: result.video_url ?? null,
                data: result,
              };
              setHistory((prev) => {
                const next = [entry, ...prev].slice(0, HISTORY_MAX);
                saveHistory(next);
                return next;
              });
              break;
            }
            case "fail":
              setLiveError(String(evt.error ?? "Bilinmeyen hata"));
              setLiveStatus("Başarısız");
              break;
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setLiveStatus("İptal edildi");
      } else {
        setLiveError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setLiveRunning(false);
      abortRef.current = null;
    }
  }, [config, auth, recordVideo, projectId]);

  const handleAbort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // ── AI Pipeline ────────────────────────────────────────────────────────────
  const handleExtractScenarios = useCallback(async () => {
    if (!liveResult) return;
    setAiPhase("scenarios");
    setAiError(null);
    setScenariosText(null);
    setKarateText(null);
    try {
      const prompt = buildScenariosPromptFromEngine(liveResult);
      const res = await aiComplete({
        task_type: "chat",
        messages: [{ role: "user", content: prompt }],
        temperature: 0.4,
        max_tokens: 2000,
      });
      setScenariosText(res.content);
      setAiPhase("done");
    } catch (err) {
      setAiError(err instanceof Error ? err.message : String(err));
      setAiPhase("error");
    }
  }, [liveResult]);

  const handleGenerateKarate = useCallback(async () => {
    if (!scenariosText) return;
    setAiPhase("karate");
    setAiError(null);
    setKarateText(null);
    try {
      const prompt = buildKaratePrompt(scenariosText, config.targetUrl);
      const res = await aiComplete({
        task_type: "chat",
        messages: [{ role: "user", content: prompt }],
        temperature: 0.3,
        max_tokens: 5000,
      });
      setKarateText(res.content);
      setAiPhase("done");
    } catch (err) {
      setAiError(err instanceof Error ? err.message : String(err));
      setAiPhase("error");
    }
  }, [scenariosText, config.targetUrl]);

  // ── Akıllı Senaryo Analizi ─────────────────────────────────────────────────
  const handleStartAnalysis = useCallback(async () => {
    if (!liveResult || analysisStreaming) return;
    setAnalysisStreaming(true);
    setAnalysisText("");
    setAnalysisError(null);
    setAnalysisDone(false);

    const controller = new AbortController();
    analysisAbortRef.current = controller;

    try {
      const prompt = buildDetailedAnalysisPrompt(liveResult);
      await aiStream(
        {
          task_type: "chat",
          messages: [{ role: "user", content: prompt }],
          temperature: 0.45,
          max_tokens: 7000,
        },
        (token, done) => {
          if (done) {
            setAnalysisDone(true);
            setAnalysisStreaming(false);
          } else {
            setAnalysisText(prev => prev + token);
          }
        },
        controller.signal,
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setAnalysisError(err instanceof Error ? err.message : String(err));
      }
      setAnalysisStreaming(false);
    } finally {
      analysisAbortRef.current = null;
    }
  }, [liveResult, analysisStreaming]);

  const handleAbortAnalysis = useCallback(() => {
    analysisAbortRef.current?.abort();
    setAnalysisStreaming(false);
  }, []);

  const handleExportAnalysis = useCallback(() => {
    if (!analysisText || !liveResult) return;
    const header = [
      `# Akıllı Monkey Test Senaryo Analizi`,
      `Hedef: ${liveResult.test_url}`,
      `Tarih: ${new Date(liveResult.started_at).toLocaleString("tr-TR")}`,
      `Eylem: ${liveResult.actions_performed} | Stabilite: %${liveResult.stability_score}`,
      "",
      "---",
      "",
    ].join("\n");
    download(header + analysisText, `monkey_analysis_${today()}.md`, "text/markdown");
  }, [analysisText, liveResult]);

  // ── Export ─────────────────────────────────────────────────────────────────
  const handleExportReport = useCallback(() => {
    if (!liveResult) return;
    const lines: string[] = [
      `# Canlı Monkey Test Raporu`,
      `Hedef URL: ${liveResult.test_url}`,
      `Tarih: ${new Date(liveResult.started_at).toLocaleString("tr-TR")}`,
      `Run ID: ${liveResult.run_id ?? "-"}`,
      `Stabilite: %${liveResult.stability_score} | Risk: ${liveResult.analysis.risk_level}`,
      `Süre: ${liveResult.total_time_seconds}s | Eylem: ${liveResult.actions_performed} | Hata: ${liveResult.error_count}`,
      "",
      "## Bug'lar",
      ...liveResult.analysis.bugs.map(
        (b) => `- **[${b.severity}]** ${b.category} (${b.count}x): ${b.sample}`
      ),
      "",
      "## Console Hataları",
      ...liveResult.console_errors.map(
        (c) => `- ${c.category} — ${c.text} (${c.url})`
      ),
      "",
      "## Network Hataları",
      ...liveResult.network_errors.map(
        (n) => `- ${n.status} ${n.category} — ${n.url}`
      ),
      "",
      "## Öneriler",
      ...liveResult.analysis.recommendations.map(
        (r) => `- [${r.priority}] ${r.text}`
      ),
    ];
    download(
      lines.join("\n"),
      `monkey_live_${liveResult.run_id ?? today()}.md`,
      "text/markdown"
    );
  }, [liveResult]);

  const handleExportScenarios = useCallback(() => {
    if (!scenariosText) return;
    download(scenariosText, `monkey_scenarios_${config.seed}_${today()}.md`, "text/markdown");
  }, [scenariosText, config.seed]);

  const handleExportKarate = useCallback(() => {
    if (!karateText) return;
    download(karateText, `monkey_test_${config.seed}_${today()}.feature`, "text/plain");
  }, [karateText, config.seed]);

  // ── History ────────────────────────────────────────────────────────────────
  const handleLoadHistory = useCallback((entry: HistoryEntry) => {
    setLiveResult(entry.data);
    setLiveActions(entry.data.actions_log);
    setLiveConsoleErrors(entry.data.console_errors);
    setLiveNetworkErrors(entry.data.network_errors);
    setLiveFrame(
      entry.data.screenshots?.final
        ? { step: "final", screenshot: entry.data.screenshots.final, url: entry.data.test_url }
        : null
    );
    setLiveProgress(100);
    setLiveStatus(`Geçmiş: ${entry.url}`);
    setShowHistory(false);
  }, []);

  const handleClearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
  }, []);

  // ── Derived ────────────────────────────────────────────────────────────────
  const toggleActionType = (type: ActionType) => {
    setConfig((c) => ({
      ...c,
      actionTypes: c.actionTypes.includes(type)
        ? c.actionTypes.filter((t) => t !== type)
        : [...c.actionTypes, type],
    }));
  };

  const liveFinished = !liveRunning && liveResult !== null;
  const actionErrors = liveActions.filter((a) =>
    (a.result ?? "").includes("error") || a.triggered_error
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4">
      {/* Banner */}
      <div className="rounded-lg border border-orange-400/20 bg-orange-500/5 px-4 py-2.5 text-xs text-orange-200/80">
        🐒 Monkey Testing — Headless Chromium ile gerçek tarayıcıda rastgele eylemler yapar, console+network hatalarını yakalar, AI ile test senaryosu ve Karate DSL üretir.
      </div>

      {/* History toggle */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setShowHistory((v) => !v)}
          className="flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800/40 px-2.5 py-1 text-[11px] text-slate-300 hover:border-slate-500"
        >
          📜 Geçmiş ({history.length})
        </button>
      </div>

      {showHistory && (
        <MonkeySessionList
          history={history}
          onLoadEntry={handleLoadHistory}
          onClearHistory={handleClearHistory}
        />
      )}

      {/* Config + Action buttons + Status */}
      <MonkeyConfigPanel
        config={config}
        onConfigChange={setConfig}
        auth={auth}
        onAuthChange={setAuth}
        authOpen={authOpen}
        onAuthOpenToggle={() => setAuthOpen((v) => !v)}
        recordVideo={recordVideo}
        onRecordVideoChange={setRecordVideo}
        liveRunning={liveRunning}
        liveProgress={liveProgress}
        liveFinished={liveFinished}
        probing={probing}
        liveError={liveError}
        liveStatus={liveStatus}
        onRunLive={handleRunLive}
        onProbe={handleProbe}
        onAbort={handleAbort}
        onExportReport={handleExportReport}
      />

      {/* Live error */}
      {liveError && (
        <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200 flex items-center justify-between gap-3 flex-wrap">
          <span>❌ {liveError}</span>
          {(liveError.includes("Proje bulunamadı") || liveError.includes("Geçersiz proje")) && (
            <Link
              href="/portfolio"
              className="px-2.5 py-1 rounded-md bg-red-500/20 text-red-100 hover:bg-red-500/30 border border-red-400/40 font-semibold whitespace-nowrap"
            >
              → Portfolio'ya Git
            </Link>
          )}
        </div>
      )}

      {/* Pre-flight probe result */}
      {probeResult && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-300">🔍 URL Hazırlık Kontrolü</span>
            <button
              onClick={() => setProbeResult(null)}
              className="text-slate-500 hover:text-slate-300 text-base leading-none"
            >×</button>
          </div>

          {/* Target URL row */}
          <div className={cn(
            "rounded-md px-3 py-2 flex items-start gap-2",
            probeResult.target.ok
              ? "bg-emerald-500/10 border border-emerald-400/25"
              : "bg-red-500/10 border border-red-400/25"
          )}>
            <span className="text-base">{probeResult.target.ok ? "✅" : "❌"}</span>
            <div className="flex-1 min-w-0">
              <div className="font-mono text-[11px] text-slate-300 truncate">{config.targetUrl}</div>
              {probeResult.target.ok ? (
                <div className="text-[11px] text-emerald-300 mt-0.5">
                  HTTP {probeResult.target.status} · {probeResult.target.elapsed_ms}ms · {Math.round((probeResult.target.body_size ?? 0) / 1024)}KB
                  {probeResult.target.redirected && (
                    <span className="ml-2 text-amber-300">
                      ↪ {probeResult.target.final_url}
                    </span>
                  )}
                </div>
              ) : (
                <div className="text-[11px] text-red-300 mt-0.5">
                  {probeResult.target.reason ?? `${probeResult.target.error}: ${probeResult.target.status ?? ""}`}
                </div>
              )}
            </div>
          </div>

          {/* Login URL row (if provided) */}
          {!probeResult.login.skipped && (
            <div className={cn(
              "rounded-md px-3 py-2 flex items-start gap-2",
              probeResult.login.ok
                ? "bg-emerald-500/10 border border-emerald-400/25"
                : "bg-red-500/10 border border-red-400/25"
            )}>
              <span className="text-base">{probeResult.login.ok ? "🔐" : "❌"}</span>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-[11px] text-slate-300 truncate">
                  Login: {auth.login_url}
                </div>
                {probeResult.login.ok ? (
                  <div className="text-[11px] text-emerald-300 mt-0.5">
                    HTTP {probeResult.login.status} · {probeResult.login.elapsed_ms}ms
                  </div>
                ) : (
                  <div className="text-[11px] text-red-300 mt-0.5">
                    {probeResult.login.reason ?? probeResult.login.error}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recommendation */}
          {!probeResult.target.ok && (
            <div className="text-[11px] text-amber-200 bg-amber-500/10 border border-amber-400/25 rounded-md px-3 py-2">
              💡 Bu durumda monkey testi de takılır. URL'i düzelt veya site'i ayağa kaldır, sonra başlat.
            </div>
          )}
          {probeResult.target.ok && !probeResult.login.skipped && !probeResult.login.ok && (
            <div className="text-[11px] text-amber-200 bg-amber-500/10 border border-amber-400/25 rounded-md px-3 py-2">
              💡 Login URL erişilemez ama hedef URL çalışıyor. Login adımını atlayıp test başlatabilirsin (Login bölümünü temizle).
            </div>
          )}
          {probeResult.target.ok && (probeResult.login.skipped || probeResult.login.ok) && (
            <div className="text-[11px] text-emerald-200 bg-emerald-500/10 border border-emerald-400/25 rounded-md px-3 py-2">
              ✓ Her şey hazır. "Canlı Tarayıcı Testi Başlat" tıkla.
            </div>
          )}
        </div>
      )}

      {/* Live preview + stats */}
      {(liveRunning || liveResult) && (
        <MonkeyLivePreview
          liveRunning={liveRunning}
          liveFrame={liveFrame}
          liveResult={liveResult}
        />
      )}

      {/* Action log (canlı) */}
      {liveActions.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-700">
          <div className="border-b border-slate-800 bg-slate-900/60 px-3 py-1.5 text-[11px] font-semibold text-slate-300 flex items-center justify-between">
            <span>📋 Eylemler ({liveActions.length})</span>
            <span className="text-slate-500">
              <span className="text-red-400">{actionErrors.length}</span> hata tetiklendi
            </span>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {liveActions.slice(-200).map((a) => {
              const hasError = (a.result ?? "").includes("error") || a.triggered_error;
              return (
                <button
                  key={`${a.step}-${a.timestamp}`}
                  type="button"
                  onClick={() => setDrawerAction(a)}
                  className={cn(
                    "w-full text-left flex items-start gap-3 border-b border-slate-800/60 px-3 py-1.5 text-xs hover:bg-slate-800/40 transition-colors",
                    hasError && "bg-red-500/5"
                  )}
                >
                  <span className="w-8 shrink-0 text-right font-mono text-[10px] text-slate-600">
                    {a.step}
                  </span>
                  <span className={cn(
                    "mt-0.5 h-2 w-2 shrink-0 rounded-full",
                    hasError ? "bg-red-400" : "bg-emerald-400"
                  )} />
                  <span className="w-24 shrink-0 font-medium text-orange-300">{a.type}</span>
                  <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-slate-400">
                    {a.target ?? a.value ?? a.key ?? a.direction ?? a.viewport ?? "—"}
                  </span>
                  <span className={cn(
                    "max-w-[260px] truncate text-[10px]",
                    hasError ? "text-red-400" : "text-slate-500"
                  )}>
                    {a.result}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Bug & error tabs */}
      {liveResult && (
        <BugReportPanel
          bugs={liveResult.analysis.bugs}
          consoleErrors={liveResult.console_errors}
          networkErrors={liveResult.network_errors}
          recommendations={liveResult.analysis.recommendations}
        />
      )}

      {/* ── AI Pipeline + Akıllı Senaryo Analizi ───────────────────────────── */}
      {liveFinished && (
        <AiPipelinePanel
          aiPhase={aiPhase}
          aiError={aiError}
          scenariosText={scenariosText}
          karateText={karateText}
          onExtractScenarios={handleExtractScenarios}
          onGenerateKarate={handleGenerateKarate}
          onExportScenarios={handleExportScenarios}
          onExportKarate={handleExportKarate}
          analysisStreaming={analysisStreaming}
          analysisText={analysisText}
          analysisDone={analysisDone}
          analysisError={analysisError}
          onStartAnalysis={handleStartAnalysis}
          onAbortAnalysis={handleAbortAnalysis}
          onExportAnalysis={handleExportAnalysis}
          actionsPerformed={liveResult.actions_performed}
          pagesVisitedCount={liveResult.pages_visited_count}
          errorCount={liveResult.error_count}
        />
      )}


      {/* Boş durum */}
      {!liveRunning && !liveResult && !liveError && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16 text-center">
          <p className="text-4xl mb-3">🐒</p>
          <p className="text-sm font-semibold text-slate-300">Monkey test hazır</p>
          <p className="text-xs text-slate-500 mt-1">
            URL girin, eylem türlerini seçin ve &quot;Canlı Tarayıcı Testi Başlat&quot; butonuna tıklayın
          </p>
        </div>
      )}

      {/* Error drawer */}
      {drawerAction && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-3"
          onClick={() => setDrawerAction(null)}
        >
          <div
            className="w-full max-w-2xl rounded-xl border border-slate-700 bg-slate-900 p-4 flex flex-col gap-2"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">
                Eylem #{drawerAction.step} — {drawerAction.type}
              </h3>
              <button
                type="button"
                onClick={() => setDrawerAction(null)}
                className="text-slate-500 hover:text-slate-200 text-lg leading-none"
              >
                ×
              </button>
            </div>
            <dl className="grid grid-cols-3 gap-y-1.5 gap-x-3 text-[11px]">
              {Object.entries(drawerAction).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="col-span-2 font-mono text-slate-300 break-all">
                    {String(v ?? "—")}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </div>
  );
}

