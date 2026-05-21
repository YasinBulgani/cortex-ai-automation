"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { aiComplete } from "@/lib/ai-gateway";
import { getToken } from "@/lib/api-client";

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

// ── AI prompt builders ───────────────────────────────────────────────────────

function buildScenariosPromptFromEngine(res: EngineResult): string {
  const bugLines = res.analysis.bugs
    .slice(0, 10)
    .map((b) => `- [${b.severity}] ${b.category} (${b.count}x): ${b.sample}`)
    .join("\n");

  const consoleLines = res.console_errors
    .slice(0, 6)
    .map((c) => `- ${c.category}: ${c.text}`)
    .join("\n");

  const netLines = res.network_errors
    .slice(0, 6)
    .map((n) => `- ${n.status} ${n.category}: ${n.url}`)
    .join("\n");

  return `Canlı Tarayıcı Monkey Test Sonuçları
Hedef: ${res.test_url}
Eylem: ${res.actions_performed} | Hata: ${res.error_count} | Stabilite: %${res.stability_score}
Sayfalar: ${res.pages_visited_count} | Süre: ${res.total_time_seconds}s

== BUG ÖZETİ ==
${bugLines || "Bug yok"}

== CONSOLE HATALARI ==
${consoleLines || "Yok"}

== NETWORK HATALARI ==
${netLines || "Yok"}

---
Yukarıdaki gerçek tarayıcı monkey test sonuçlarına dayanarak en az 5 kapsamlı test senaryosu üret.
Her bug için en az bir test senaryosu yaz; bug yoksa pozitif, negatif, sınır değer, edge case ve güvenlik senaryoları üret.

ÇIKTI KESİNLİKLE MARKDOWN TABLO FORMATINDA OLMALI. JSON, kod bloğu, açıklama YASAK.

Tam olarak şu format:

| Test ID | Alan | Açıklama | Ön Koşul | Adımlar | Beklenen Sonuç | Öncelik |
|---------|------|----------|----------|---------|----------------|---------|
| TC_MT_001 | Login | Geçerli kullanıcı girişi | Kullanıcı kayıtlı | 1. Login sayfası aç<br>2. Kullanıcı adı gir<br>3. Şifre gir<br>4. Gönder | Ana sayfaya yönlendirilir | high |

Türkçe yaz. Test ID: TC_MT_001..TC_MT_NNN. Önceliği: critical / high / medium / low.
SADECE TABLO YAZ, BAŞKA HİÇBİR ŞEY YAZMA.`;
}

function buildKaratePrompt(scenariosText: string, targetUrl: string): string {
  return `Aşağıdaki test senaryolarından Karate DSL feature dosyası üret.
Hedef URL: ${targetUrl || "https://cortex-test.bgtsai.com"}

Test Senaryoları:
${scenariosText}

---
ÇIKTI KESİNLİKLE GHERKIN BDD FORMATINDA KARATE DSL FEATURE DOSYASI OLMALI.
JSON, açıklama metin, markdown ek YASAK. Sadece .feature içeriği.

Yapı:

Feature: MonkeyTest - Otomatik Senaryolar

Background:
  * url '${targetUrl || "https://cortex-test.bgtsai.com"}'
  * configure driver = { type: 'chrome', headless: true }

Scenario: <senaryo başlığı>
  Given driver '${targetUrl || "https://cortex-test.bgtsai.com"}'
  When driver.click('<selector>')
  And input('<selector>', '<value>')
  Then match driver.title == '<expected>'

Kurallar:
- Her senaryo için ayrı Scenario bloğu (Scenario Outline yok)
- BDD: Given / When / Then / And anahtar kelimeleri zorunlu
- Sadece UI komutları: driver.get, driver.click, input, match driver.title, match driver.location
- Türkçe scenario başlıkları, İngilizce Karate komutları
- En az 3 Scenario yaz.

SADECE .feature içeriğini yaz, başka metin yok.`;
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

  // ── Live SSE runner ────────────────────────────────────────────────────────
  const handleRunLive = useCallback(async () => {
    setLiveRunning(true);
    setLiveProgress(0);
    setLiveActions([]);
    setLiveFrame(null);
    setLiveConsoleErrors([]);
    setLiveNetworkErrors([]);
    setLiveResult(null);
    setLiveError(null);
    setLiveStatus("Başlatılıyor…");
    setScenariosText(null);
    setKarateText(null);
    setAiPhase("idle");

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

      const res = await fetch(
        `/api/v1/tspm/projects/${projectId}/monkey-testing/run/stream`,
        {
          method: "POST",
          credentials: "include",
          headers,
          body: JSON.stringify(body),
          signal: controller.signal,
        }
      );

      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => "");
        throw new Error(`Sunucu yanıtı: ${res.status} ${text.slice(0, 200)}`);
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
          const line = raw.trim();
          if (!line.startsWith("data:")) continue;
          const jsonStr = line.slice(5).trim();
          if (!jsonStr) continue;

          let evt: { type: string; [k: string]: unknown };
          try {
            evt = JSON.parse(jsonStr);
          } catch {
            continue;
          }

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
      entry.data.screenshots.final
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
  const aiLoading = aiPhase === "scenarios" || aiPhase === "karate";
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
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-3">
          {history.length === 0 ? (
            <div className="text-center text-xs text-slate-500 py-4">
              Henüz çalıştırma kaydı yok.
            </div>
          ) : (
            <>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold text-slate-300">Son Çalıştırmalar</span>
                <button
                  type="button"
                  onClick={handleClearHistory}
                  className="text-[10px] text-red-400 hover:text-red-300"
                >
                  Tümünü temizle
                </button>
              </div>
              <div className="max-h-60 overflow-y-auto flex flex-col gap-1">
                {history.map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => handleLoadHistory(h)}
                    className="text-left flex items-center gap-3 rounded-md border border-slate-700 bg-slate-800/40 px-2 py-1.5 text-[11px] hover:border-slate-500"
                  >
                    <span className="font-mono text-slate-500 w-32 truncate">
                      {new Date(h.timestamp).toLocaleString("tr-TR")}
                    </span>
                    <span className="flex-1 truncate text-slate-300">{h.url}</span>
                    <span className="text-orange-300">{h.actions} eylem</span>
                    <span className={cn(
                      "font-semibold",
                      h.stability >= 80 ? "text-emerald-400" :
                      h.stability >= 50 ? "text-yellow-400" : "text-red-400"
                    )}>
                      %{h.stability}
                    </span>
                    <span className="text-red-400">{h.errors} hata</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Config */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 flex flex-col gap-4">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-400">Test Yapılandırması</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Hedef URL
            </label>
            <input
              value={config.targetUrl}
              onChange={(e) => setConfig((c) => ({ ...c, targetUrl: e.target.value }))}
              placeholder="https://cortex-test.bgtsai.com"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-xs font-mono text-slate-200 focus:border-orange-400/50 focus:outline-none focus:ring-1 focus:ring-orange-400/30"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Eylem Sayısı: {config.actionCount}
            </label>
            <input
              type="range"
              min={10}
              max={200}
              step={10}
              value={config.actionCount}
              onChange={(e) =>
                setConfig((c) => ({ ...c, actionCount: parseInt(e.target.value) }))
              }
              className="w-full accent-orange-400 mt-1"
            />
          </div>
        </div>

        {/* Action types */}
        <div>
          <label className="mb-2 block text-[11px] font-semibold uppercase tracking-widest text-slate-400">
            Eylem Türleri
          </label>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(ACTION_LABELS) as ActionType[]).map((type) => {
              const active = config.actionTypes.includes(type);
              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => toggleActionType(type)}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-[11px] font-medium transition-all",
                    active
                      ? "border-orange-400/40 bg-orange-500/15 text-orange-200"
                      : "border-slate-700 bg-slate-800/50 text-slate-500 hover:border-slate-600"
                  )}
                >
                  {ACTION_LABELS[type]}
                </button>
              );
            })}
          </div>
        </div>

        {/* Auth & Options */}
        <div className="rounded-lg border border-slate-700/80 bg-slate-900/40">
          <button
            type="button"
            onClick={() => setAuthOpen((v) => !v)}
            className="flex w-full items-center justify-between px-3 py-2 text-[11px] font-semibold uppercase tracking-widest text-slate-300 hover:bg-slate-800/30"
          >
            <span>🔑 Login & Gelişmiş Ayarlar {auth.login_url ? "(aktif)" : "(opsiyonel)"}</span>
            <span className="text-slate-500">{authOpen ? "−" : "+"}</span>
          </button>
          {authOpen && (
            <div className="border-t border-slate-700/80 p-3 flex flex-col gap-2 text-[11px]">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <input
                  value={auth.login_url}
                  onChange={(e) => setAuth((a) => ({ ...a, login_url: e.target.value }))}
                  placeholder="Login URL (örn: https://app.com/login)"
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.submit_selector}
                  onChange={(e) => setAuth((a) => ({ ...a, submit_selector: e.target.value }))}
                  placeholder='Submit selector (örn: button[type="submit"])'
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.username_selector}
                  onChange={(e) => setAuth((a) => ({ ...a, username_selector: e.target.value }))}
                  placeholder='Username selector (örn: input[name="email"])'
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.password_selector}
                  onChange={(e) => setAuth((a) => ({ ...a, password_selector: e.target.value }))}
                  placeholder='Password selector (örn: input[type="password"])'
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 font-mono text-slate-200"
                />
                <input
                  value={auth.username}
                  onChange={(e) => setAuth((a) => ({ ...a, username: e.target.value }))}
                  placeholder="Kullanıcı adı"
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 text-slate-200"
                />
                <input
                  type="password"
                  value={auth.password}
                  onChange={(e) => setAuth((a) => ({ ...a, password: e.target.value }))}
                  placeholder="Şifre"
                  className="rounded-md border border-slate-700 bg-slate-900/60 px-2 py-1.5 text-slate-200"
                />
              </div>
              <label className="flex items-center gap-2 mt-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={recordVideo}
                  onChange={(e) => setRecordVideo(e.target.checked)}
                  className="accent-orange-400"
                />
                <span className="text-slate-300">📹 Video kayıt (WebM)</span>
              </label>
              <p className="text-[10px] text-slate-500">
                Şifre, sunucudan diğer kullanıcılar tarafından erişilmez; sadece Playwright login formuna yazılır.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handleRunLive}
          disabled={liveRunning || !config.targetUrl || config.actionTypes.length === 0}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-all",
            liveRunning || !config.targetUrl || config.actionTypes.length === 0
              ? "cursor-not-allowed border-slate-700 bg-slate-900/40 text-slate-500"
              : "border-orange-300/40 bg-orange-500/20 text-orange-50 hover:bg-orange-500/30"
          )}
        >
          {liveRunning ? (
            <span>⏳ Tarayıcı testi çalışıyor… {liveProgress}%</span>
          ) : (
            <>
              <span>🌐</span>
              <span>Canlı Tarayıcı Testi Başlat</span>
            </>
          )}
        </button>

        {liveRunning && (
          <button
            type="button"
            onClick={handleAbort}
            className="rounded-lg border border-red-400/30 bg-red-500/15 px-3 py-2 text-xs font-semibold text-red-200 hover:bg-red-500/25"
          >
            ⏹ İptal
          </button>
        )}

        {liveFinished && (
          <button
            type="button"
            onClick={handleExportReport}
            className="flex items-center gap-1.5 rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/20"
          >
            ↓ Rapor (.md)
          </button>
        )}
      </div>

      {/* Status + Progress */}
      {(liveRunning || liveStatus) && (
        <div className="flex flex-col gap-1">
          <div className="text-xs text-slate-300">{liveStatus}</div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-300",
                liveError ? "bg-red-500" : "bg-orange-400"
              )}
              style={{ width: `${liveProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Live error */}
      {liveError && (
        <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200">
          ❌ {liveError}
        </div>
      )}

      {/* Live preview + stats */}
      {(liveRunning || liveResult) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Sol: canlı önizleme */}
          <div className="lg:col-span-2 rounded-xl border border-slate-700 bg-slate-900/60 p-2 flex flex-col gap-2">
            <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
              <span>📺 Canlı Önizleme {liveFrame?.step ? `(adım ${liveFrame.step})` : ""}</span>
              {liveFrame?.url && (
                <span className="font-mono truncate max-w-[60%]" title={liveFrame.url}>
                  {liveFrame.url}
                </span>
              )}
            </div>
            <div className="aspect-video w-full overflow-hidden rounded-md bg-slate-950 border border-slate-800 flex items-center justify-center">
              {liveFrame ? (
                <img
                  src={`data:image/jpeg;base64,${liveFrame.screenshot}`}
                  alt={`step-${liveFrame.step}`}
                  className="max-h-full max-w-full object-contain"
                />
              ) : (
                <div className="text-xs text-slate-600">
                  {liveRunning ? "İlk frame bekleniyor…" : "Henüz çalıştırılmadı"}
                </div>
              )}
            </div>

            {liveResult?.video_url && (
              <div className="mt-2">
                <div className="text-[11px] text-slate-400 mb-1 px-1">📹 Kayıt</div>
                <video
                  controls
                  className="w-full rounded-md bg-slate-950 border border-slate-800"
                  src={liveResult.video_url}
                />
              </div>
            )}
          </div>

          {/* Sağ: istatistikler */}
          <div className="flex flex-col gap-2">
            {liveResult && (
              <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 flex flex-col gap-2">
                <div className="text-[11px] uppercase tracking-widest text-slate-400">Özet</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <StatCard label="Stabilite" value={`%${liveResult.stability_score}`} accent={
                    liveResult.stability_score >= 80 ? "emerald" :
                    liveResult.stability_score >= 50 ? "yellow" : "red"
                  } />
                  <StatCard label="Risk" value={liveResult.analysis.risk_level} accent={
                    liveResult.analysis.risk_level === "low" ? "emerald" :
                    liveResult.analysis.risk_level === "medium" ? "yellow" : "red"
                  } />
                  <StatCard label="Eylem" value={`${liveResult.actions_performed}`} accent="slate" />
                  <StatCard label="Hata" value={`${liveResult.error_count}`} accent={liveResult.error_count === 0 ? "emerald" : "red"} />
                  <StatCard label="Sayfa" value={`${liveResult.pages_visited_count}`} accent="slate" />
                  <StatCard label="Süre" value={`${liveResult.total_time_seconds}s`} accent="slate" />
                </div>
              </div>
            )}

            {liveResult?.action_stats && (
              <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3">
                <div className="text-[11px] uppercase tracking-widest text-slate-400 mb-1.5">Eylem İstatistikleri</div>
                <div className="flex flex-col gap-0.5 text-[10px]">
                  {Object.entries(liveResult.action_stats).map(([t, s]) => (
                    <div key={t} className="flex justify-between text-slate-400">
                      <span>{t}</span>
                      <span>
                        <span className="text-emerald-400">{s.success}</span>
                        {" / "}
                        <span className="text-red-400">{s.error}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
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
        <div className="rounded-xl border border-slate-700">
          <div className="grid grid-cols-3 border-b border-slate-700 text-[11px] font-semibold">
            <ColHeader label={`🐛 Bug'lar (${liveResult.analysis.bugs.length})`} />
            <ColHeader label={`⚠️ Console (${liveResult.console_errors.length})`} />
            <ColHeader label={`🌐 Network (${liveResult.network_errors.length})`} />
          </div>
          <div className="grid grid-cols-3 gap-px bg-slate-700">
            <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
              {liveResult.analysis.bugs.length === 0 ? (
                <div className="text-[11px] text-slate-500 p-2">Bug yok 🎉</div>
              ) : (
                liveResult.analysis.bugs.map((b, i) => (
                  <div key={i} className="border-b border-slate-800 px-2 py-1.5 text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "rounded px-1 text-[9px] font-bold uppercase",
                        b.severity === "critical" ? "bg-red-500/30 text-red-200" : "bg-yellow-500/30 text-yellow-200"
                      )}>
                        {b.severity}
                      </span>
                      <span className="text-slate-300 truncate">{b.category}</span>
                      <span className="text-slate-500">×{b.count}</span>
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500 truncate">{b.sample}</div>
                  </div>
                ))
              )}
            </div>
            <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
              {liveResult.console_errors.length === 0 ? (
                <div className="text-[11px] text-slate-500 p-2">Console temiz</div>
              ) : (
                liveResult.console_errors.map((c, i) => (
                  <div key={i} className="border-b border-slate-800 px-2 py-1.5 text-[10px]">
                    <div className="text-slate-400">{c.category}</div>
                    <div className="text-red-300 line-clamp-2">{c.text}</div>
                    <div className="text-slate-600 truncate">{c.url}</div>
                  </div>
                ))
              )}
            </div>
            <div className="bg-slate-900/40 p-2 max-h-72 overflow-y-auto">
              {liveResult.network_errors.length === 0 ? (
                <div className="text-[11px] text-slate-500 p-2">Network temiz</div>
              ) : (
                liveResult.network_errors.map((n, i) => (
                  <div key={i} className="border-b border-slate-800 px-2 py-1.5 text-[10px]">
                    <div className="flex gap-2">
                      <span className={cn(
                        "rounded px-1 font-bold",
                        n.status >= 500 ? "bg-red-500/30 text-red-200" : "bg-yellow-500/30 text-yellow-200"
                      )}>
                        {n.status}
                      </span>
                      <span className="text-slate-400 truncate">{n.category}</span>
                    </div>
                    <div className="text-slate-500 truncate mt-0.5">{n.url}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          {liveResult.analysis.recommendations.length > 0 && (
            <div className="border-t border-slate-700 bg-slate-900/40 p-3">
              <div className="text-[11px] font-semibold text-violet-300 mb-1">💡 Öneriler</div>
              <ul className="text-[11px] text-slate-300 space-y-1">
                {liveResult.analysis.recommendations.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <span className={cn(
                      "shrink-0 rounded px-1 text-[9px] uppercase font-bold",
                      r.priority === "critical" ? "bg-red-500/30 text-red-200" :
                      r.priority === "high" ? "bg-orange-500/30 text-orange-200" :
                      r.priority === "info" ? "bg-blue-500/30 text-blue-200" : "bg-slate-700 text-slate-300"
                    )}>
                      {r.priority}
                    </span>
                    <span>{r.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── AI Pipeline ─────────────────────────────────────────────────────── */}
      {liveFinished && (
        <div className="mt-2 flex flex-col gap-4 rounded-xl border border-violet-400/20 bg-violet-500/5 p-4">
          <div className="flex items-center gap-2">
            <span className="text-base">🤖</span>
            <span className="text-sm font-semibold text-violet-200">AI Test Senaryosu &amp; Otomasyon</span>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={handleExtractScenarios}
                disabled={aiLoading}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-all",
                  aiLoading
                    ? "cursor-not-allowed border-slate-700 bg-slate-900/40 text-slate-500"
                    : "border-violet-400/30 bg-violet-500/15 text-violet-100 hover:bg-violet-500/25"
                )}
              >
                {aiPhase === "scenarios" ? (
                  <span>⏳ Senaryolar üretiliyor...</span>
                ) : (
                  <><span>✦</span><span>AI Senaryo Çıkar</span></>
                )}
              </button>

              {scenariosText && (
                <button
                  type="button"
                  onClick={handleExportScenarios}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-800/50 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700/50"
                >
                  ↓ Senaryolar (.md)
                </button>
              )}
            </div>

            {scenariosText && (
              <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900/60 p-3">
                <pre className="whitespace-pre-wrap text-[11px] leading-5 text-slate-300">
                  {scenariosText}
                </pre>
              </div>
            )}
          </div>

          {scenariosText && (
            <div className="flex flex-col gap-2 border-t border-slate-700/50 pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleGenerateKarate}
                  disabled={aiLoading}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-all",
                    aiLoading
                      ? "cursor-not-allowed border-slate-700 bg-slate-900/40 text-slate-500"
                      : "border-sky-400/30 bg-sky-500/15 text-sky-100 hover:bg-sky-500/25"
                  )}
                >
                  {aiPhase === "karate" ? (
                    <span>⏳ Karate DSL üretiliyor...</span>
                  ) : (
                    <><span>◈</span><span>Karate DSL Üret</span></>
                  )}
                </button>

                {karateText && (
                  <button
                    type="button"
                    onClick={handleExportKarate}
                    className="flex items-center gap-1.5 rounded-lg border border-emerald-400/25 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/20"
                  >
                    ↓ İndir (.feature)
                  </button>
                )}
              </div>

              {karateText && (
                <div className="max-h-96 overflow-y-auto rounded-lg border border-sky-400/20 bg-slate-950 p-3">
                  <pre className="whitespace-pre-wrap text-[11px] leading-5 text-sky-200">
                    {karateText}
                  </pre>
                </div>
              )}
            </div>
          )}

          {aiPhase === "error" && aiError && (
            <div className="rounded-lg border border-red-400/20 bg-red-500/5 px-3 py-2 text-xs text-red-300">
              AI Gateway hatası: {aiError}
            </div>
          )}
        </div>
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

// ── UI helpers ───────────────────────────────────────────────────────────────

function StatCard({
  label, value, accent,
}: {
  label: string;
  value: string;
  accent: "emerald" | "yellow" | "red" | "slate";
}) {
  const color =
    accent === "emerald" ? "text-emerald-400" :
    accent === "yellow" ? "text-yellow-400" :
    accent === "red" ? "text-red-400" : "text-slate-200";
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950/40 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-sm font-bold ${color}`}>{value}</div>
    </div>
  );
}

function ColHeader({ label }: { label: string }) {
  return (
    <div className="px-3 py-2 text-slate-300 bg-slate-900/60 text-center border-r last:border-r-0 border-slate-700">
      {label}
    </div>
  );
}
