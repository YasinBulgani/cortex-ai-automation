"use client";

/**
 * Cortex Scenario Author — modal with 3 authoring modes.
 *
 *   🎬 Recorder  — spawn Java recorder via Maven
 *   🤖 AI Üret   — prompt-based Gherkin scaffolding
 *   ✍️ Manuel    — enriched editor with locator inspector + builder + templates
 */

import { useEffect, useMemo, useRef, useState } from "react";

const DASHBOARD_URL = process.env.NEXT_PUBLIC_CORTEX_DASHBOARD_URL || "http://localhost:5001";

type Mode = "recorder" | "ai" | "manual";

interface Props {
  open: boolean;
  onClose: () => void;
}

interface StepPhrase  { phrase: string; kind: "Given" | "When" | "Then" }
interface LocatorEntry { type: string; value: string; source: string }
interface LocatorFile  { name: string; path: string; abs: string }
interface Template     { id: string; title: string; tag: string; description: string; content: string }

const LOCATOR_TYPES = ["css", "id", "name", "xpath", "linktext", "partiallinktext", "class", "tag"];

export function CortexScenarioAuthor({ open, onClose }: Props) {
  const [mode, setMode] = useState<Mode>("manual");
  const [expanded, setExpanded] = useState(false);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm grid place-items-center p-4" onClick={onClose}>
      <div
        className={`w-full overflow-y-auto rounded-2xl bg-slate-950 border border-fuchsia-500/30 shadow-2xl shadow-fuchsia-500/20 transition-all ${
          expanded ? "max-w-[95vw] max-h-[95vh]" : "max-w-6xl max-h-[92vh]"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 px-6 py-4 border-b border-slate-800 bg-slate-950/95 backdrop-blur flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">+ Yeni Cortex Senaryosu</h2>
            <p className="text-xs text-slate-400 mt-0.5">3 yöntem · sonuç projects/cortex/'a yazılır</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setExpanded((v) => !v)}
              className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors grid place-items-center"
              title={expanded ? "Küçült" : "Tam ekran"}
            >
              {expanded ? "🗗" : "⛶"}
            </button>
            <button onClick={onClose} className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors grid place-items-center">✕</button>
          </div>
        </div>

        <div className="px-6 pt-5">
          <div className="grid grid-cols-3 gap-2 p-1 bg-slate-900 rounded-xl border border-slate-800">
            {(["recorder", "ai", "manual"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  mode === m ? "bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white shadow-lg shadow-fuchsia-500/25" : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                {m === "recorder" ? "🎬 Recorder" : m === "ai" ? "🤖 AI Üret" : "✍️ Manuel"}
              </button>
            ))}
          </div>
        </div>

        <div className="p-6">
          {mode === "recorder" && <RecorderTab onClose={onClose} />}
          {mode === "ai" && <AiTab onClose={onClose} />}
          {mode === "manual" && <ManualTab onClose={onClose} />}
        </div>
      </div>
    </div>
  );
}

/* ============================================================== */
/*  1. Recorder tab                                                */
/* ============================================================== */

interface RecorderStatus { running: boolean; actions: number; port: number | null; pid: number | null }
interface RecordedAction { type: string; text?: string; key?: string; seconds?: number; element?: { tag?: string; text?: string } }

function RecorderTab({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState("https://cortex-test.bgtsai.com/");
  const [featureName, setFeatureName] = useState("");
  const [browser, setBrowser] = useState("chromium");
  // Recorder backend: "codegen" = Playwright official (daha sağlam, önerilen)
  const [backend, setBackend] = useState<"custom" | "codegen">("codegen");
  const [codegenJobId, setCodegenJobId] = useState<string | null>(null);

  // Lifecycle: idle → starting → running → stopping → idle
  const [phase, setPhase] = useState<"idle" | "starting" | "running" | "stopping">("idle");
  const [startInfo, setStartInfo] = useState<{ pid?: number; port?: number; warning?: string } | null>(null);
  const [status, setStatus] = useState<RecorderStatus | null>(null);
  const [actions, setActions] = useState<RecordedAction[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busyStop, setBusyStop] = useState(false);
  const [busyUndo, setBusyUndo] = useState(false);

  // 🪄 AI Polish — local Ollama post-processing of the most-recent .feature.
  // Triggered by the "AI Polish Son Kayıt" button in the idle view.
  type PolishState = {
    open: boolean;
    loading: boolean;
    saving?: boolean;
    error?: string | null;
    original?: string;
    enhanced?: string;
    streamingTokens?: string;
    path?: string;
    model: string;
  };
  const [polish, setPolish] = useState<PolishState>({
    open: false,
    loading: false,
    model: "qwen2.5:14b",
  });
  const polishAbortRef = React.useRef<AbortController | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState<number>(Date.now());
  useEffect(() => {
    if (phase !== "running") return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [phase]);
  const secondsSinceStart = startedAt ? Math.floor((now - startedAt) / 1000) : 0;
  const noEventsWarning =
    phase === "running" && startedAt && actions.length === 0 && secondsSinceStart >= 30;

  /* ── Live polling while running ──────────────────────────── */
  useEffect(() => {
    if (phase !== "running") return;
    let cancelled = false;
    const poll = async () => {
      try {
        const sr = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/status`);
        const st: RecorderStatus = await sr.json();
        if (cancelled) return;
        setStatus(st);
        if (!st.running) {
          // Recorder exited (e.g. user clicked in-browser Stop)
          setPhase("idle");
          return;
        }
        // Fetch the action list too, so we can show the live preview
        const ar = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/actions`);
        if (ar.ok) {
          const arr = await ar.json();
          if (Array.isArray(arr) && !cancelled) setActions(arr.slice(-12)); // last 12
        }
      } catch (e) {
        // Don't toast every transient poll error, but surface persistent ones
        // so the user sees them instead of staring at "0 aksiyon" forever.
        console.warn("[recorder] poll error", e);
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          setErr((prev) => prev ?? `Backend bağlantısı koptu: ${msg}`);
        }
      }
    };
    poll();
    const id = setInterval(poll, 1500);
    return () => { cancelled = true; clearInterval(id); };
  }, [phase]);

  /* ── Actions ─────────────────────────────────────────────── */

  const start = async () => {
    // Pre-launch: kill any orphan Chromium processes from previous runs.
    // This prevents "Chrome kalıyor" issues when the user starts a new
    // recording without cleanly stopping the previous one.
    try {
      await fetch(`${DASHBOARD_URL}/api/cortex/recorder/cleanup`, { method: "POST" });
    } catch (e) {
      // Best-effort, but log so we can debug "ghost Chromium" reports.
      console.warn("[recorder] pre-launch cleanup failed", e);
    }

    setPhase("starting"); setErr(null); setStartInfo(null); setActions([]); setStatus(null);
    setStartedAt(Date.now());
    try {
      if (backend === "codegen") {
        // Playwright official codegen
        const r = await fetch(`${DASHBOARD_URL}/api/cortex/codegen/start`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, target: "javascript", browser }),
        });
        const j = await r.json();
        if (!r.ok || !j.ok) {
          setErr(j.error || "Codegen başlatılamadı");
          setPhase("idle"); return;
        }
        setCodegenJobId(j.job.id);
        setStartInfo({ pid: j.job.pid, port: 0, warning: undefined });
        setPhase("running");
      } else {
        // Custom recorder.js + Java RecorderMain
        const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/start`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, feature_name: featureName || undefined, browser }),
        });
        const j = await r.json();
        if (!r.ok || !j.ok) {
          setErr(j.error || "Recorder başlatılamadı");
          setPhase("idle"); return;
        }
        setStartInfo({ pid: j.pid, port: j.port, warning: j.port_warning });
        setPhase("running");
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
      setPhase("idle");
    }
  };

  const stop = async () => {
    setBusyStop(true); setErr(null);
    try {
      if (backend === "codegen" && codegenJobId) {
        // Stop codegen then convert JS → Gherkin + save
        await fetch(`${DASHBOARD_URL}/api/cortex/codegen/stop/${codegenJobId}`, { method: "POST" });
        const convertR = await fetch(`${DASHBOARD_URL}/api/cortex/codegen/convert/${codegenJobId}`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            feature_name: featureName || `codegen-${codegenJobId}`,
            target_dir: "recordings",
          }),
        });
        const cj = await convertR.json();
        if (!convertR.ok || !cj.ok) {
          setErr(cj.error || "Codegen convert failed");
        }
        setPhase("stopping");
        setTimeout(() => { setPhase("idle"); setCodegenJobId(null); }, 1500);
      } else {
        const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/stop`, { method: "POST" });
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || "Stop failed");
        setPhase("stopping");
        setTimeout(() => setPhase("idle"), 3000);
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Stop failed");
    } finally { setBusyStop(false); }
  };

  const undo = async () => {
    setBusyUndo(true); setErr(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/undo`, { method: "POST" });
      if (!r.ok) throw new Error("Undo failed");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Undo failed");
    } finally { setBusyUndo(false); }
  };

  /* ── AI Polish ───────────────────────────────────────────────
   * Take the most-recently-saved .feature, hand it to local Ollama via SSE
   * streaming so the user sees tokens arrive in real-time.
   * Falls back to blocking /enhance if streaming fails.
   */
  const runPolish = async () => {
    const abort = new AbortController();
    polishAbortRef.current = abort;
    setPolish((p) => ({
      ...p,
      open: true,
      loading: true,
      error: null,
      original: undefined,
      enhanced: undefined,
      streamingTokens: "",
      path: undefined,
    }));
    try {
      const lr = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/last-feature`);
      const lj = await lr.json();
      if (!lr.ok || !lj.ok) throw new Error(lj.error || "Son .feature bulunamadı");

      // Use streaming endpoint for live token preview
      const er = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/enhance/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ featurePath: lj.path, featureContent: lj.content, model: polish.model }),
        signal: abort.signal,
      });
      if (!er.ok || !er.body) throw new Error("Streaming başlatılamadı");

      const reader = er.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const msg = JSON.parse(line.slice(6));
            if (msg.error) throw new Error(msg.error);
            if (msg.token) {
              setPolish((p) => ({ ...p, streamingTokens: (p.streamingTokens ?? "") + msg.token }));
            }
            if (msg.done) {
              setPolish((p) => ({
                ...p,
                loading: false,
                streamingTokens: undefined,
                original: msg.original ?? lj.content,
                enhanced: msg.enhanced,
                path: lj.path,
              }));
              return;
            }
          } catch (parseErr: unknown) {
            throw parseErr instanceof Error ? parseErr : new Error(String(parseErr));
          }
        }
      }
    } catch (e: unknown) {
      if ((e as Error).name === "AbortError") {
        setPolish((p) => ({ ...p, loading: false, streamingTokens: undefined, error: "İptal edildi." }));
        return;
      }
      setPolish((p) => ({
        ...p,
        loading: false,
        streamingTokens: undefined,
        error: e instanceof Error ? e.message : String(e),
      }));
    }
  };

  const cancelPolish = () => {
    polishAbortRef.current?.abort();
  };

  const acceptPolish = async () => {
    if (!polish.path || !polish.enhanced) return;
    setPolish((p) => ({ ...p, saving: true, error: null }));
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/files/write`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: polish.path, content: polish.enhanced }),
      });
      const j = await r.json().catch(() => ({} as Record<string, unknown>));
      if (!r.ok) throw new Error(((j as { error?: string }).error) || "Dosya yazılamadı");
      setPolish({ open: false, loading: false, model: polish.model });
    } catch (e: unknown) {
      setPolish((p) => ({
        ...p,
        saving: false,
        error: e instanceof Error ? e.message : String(e),
      }));
    }
  };

  const closePolish = () => setPolish((p) => ({ ...p, open: false }));

  /* ── Render ──────────────────────────────────────────────── */

  if (phase === "running" || phase === "stopping") {
    return (
      <div className="space-y-4">
        {/* Status banner */}
        <div className="rounded-xl bg-rose-500/10 border border-rose-500/30 p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              {phase === "running" && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${phase === "stopping" ? "bg-amber-400" : "bg-rose-500"}`} />
            </span>
            <div>
              <p className="text-sm font-bold text-white">
                {phase === "stopping" ? "Durduruluyor…" : "🔴 KAYIT YAPILIYOR"}
              </p>
              <p className="text-xs text-rose-200/80">
                {phase === "stopping"
                  ? "Aksiyonlar diske yazılıyor, JVM kapanıyor…"
                  : `Port :${status?.port ?? startInfo?.port ?? "?"} · PID ${status?.pid ?? startInfo?.pid ?? "?"}`}
              </p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-white tabular-nums leading-none">{status?.actions ?? 0}</div>
            <div className="text-[10px] text-rose-200/80 uppercase tracking-wide mt-0.5">aksiyon</div>
          </div>
        </div>

        {startInfo?.warning && (
          <div className="rounded-xl p-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">⚠ {startInfo.warning}</div>
        )}

        {/* Main grid: left = action list, right = quick-add panel */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-3">
          {/* LEFT — live actions */}
          <div className="rounded-xl bg-black/40 border border-slate-800 overflow-hidden flex flex-col">
            <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Son aksiyonlar</span>
              <span className="text-[10px] font-mono text-slate-600">son 12 · canlı</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-[11px] min-h-[200px] max-h-[320px]">
              {actions.length === 0 && !noEventsWarning && <div className="text-slate-600 italic p-2">Henüz aksiyon yok — Chromium'da gez veya sağdaki butonları kullan ({secondsSinceStart}s)</div>}
              {noEventsWarning && (
                <div className="m-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/40 text-amber-200 text-[11px] leading-relaxed">
                  <div className="font-bold text-amber-300 mb-1">⚠ {secondsSinceStart}s geçti, hiç aksiyon yakalanmadı</div>
                  Olası sebepler:
                  <ul className="list-disc list-inside mt-1 space-y-0.5">
                    <li><b>Yanlış tarayıcı:</b> Sadece <span className="font-mono bg-black/30 px-1 rounded">[REC]</span> başlıklı, üstte yeşil barı olan Chromium penceresinde işlem kayıt olur. Normal Chrome'da yaptığın hiçbir şey alınmaz.</li>
                    <li><b>Chromium arkada:</b> macOS Mission Control (F3) ile diğer Space'lere bak, ya da Dock'tan Chromium ikonuna tıkla (mavi-gri ikon, Chrome'dan farklı).</li>
                    <li><b>Script crash:</b> Chromium DevTools (F12) → Console → <span className="font-mono bg-black/30 px-1 rounded">__cortexDiag()</span> çalıştır. <span className="font-mono">last error</span> alanı dolu mu?</li>
                  </ul>
                </div>
              )}
              {actions.map((a, i) => <ActionRow key={i} a={a} />)}
            </div>
          </div>

          {/* RIGHT — quick-add panel */}
          <QuickAddPanel disabled={phase === "stopping"} onInjected={() => {/* status poll picks it up */}} />
        </div>

        {err && <div className="rounded-xl p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">✗ {err}</div>}

        {/* Control bar — STOP + UNDO + LOGS */}
        <div className="flex flex-wrap items-center gap-2 pt-1 sticky bottom-0 bg-slate-950 pb-1">
          <button
            onClick={undo}
            disabled={busyUndo || phase === "stopping" || (status?.actions ?? 0) === 0}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Son aksiyonu sil"
          >
            ↶ {busyUndo ? "…" : "Geri Al"}
          </button>
          <LogsButton />
          <CleanupButton />
          <a
            href="https://cortex-test.bgtsai.com/" target="_blank" rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium border border-slate-700"
          >
            ↗ Cortex sekmesini öne getir
          </a>
          <div className="flex-1" />
          <button
            onClick={stop}
            disabled={busyStop || phase === "stopping"}
            className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-rose-500 to-rose-600 hover:opacity-90 text-white text-sm font-bold shadow-lg shadow-rose-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busyStop ? "Gönderiliyor…" : phase === "stopping" ? "Kaydediliyor…" : "⏹ Durdur ve Kaydet"}
          </button>
        </div>
      </div>
    );
  }

  // phase === "idle" or "starting"
  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
        <p className="text-sm text-slate-300 leading-relaxed">
          <strong className="text-fuchsia-300">Tarayıcıdan kaydet.</strong> Chromium açılır, sağ-alt köşede 🔴 REC toolbar.
          Fareyle Cortex'i gez — aksiyonlar otomatik Gherkin'e çevrilir, locator JSON ile birlikte yazılır.
        </p>
      </div>

      {/* Backend selector — Custom Recorder vs Playwright Codegen */}
      <FormField label="Kayıt motoru">
        <div className="grid grid-cols-2 gap-2 p-1 bg-slate-900 rounded-lg border border-slate-700">
          {([
            { id: "codegen", label: "🤖 Playwright Codegen",  hint: "Microsoft official — önerilir" },
            { id: "custom",  label: "🎯 Custom Recorder",     hint: "Zengin UI, live action panel" },
          ] as const).map((b) => (
            <button
              key={b.id}
              onClick={() => setBackend(b.id as "custom" | "codegen")}
              className={`px-3 py-2 rounded text-xs font-medium text-left transition-all ${
                backend === b.id
                  ? "bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white shadow-md"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <div className="font-semibold">{b.label}</div>
              <div className={`text-[10px] mt-0.5 ${backend === b.id ? "text-white/80" : "text-slate-500"}`}>{b.hint}</div>
            </button>
          ))}
        </div>
        {/* Karşılaştırma kılavuzu */}
        <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-slate-500">
          <div className={`p-2 rounded border ${backend === "codegen" ? "border-fuchsia-500/40 text-slate-400" : "border-slate-800"}`}>
            <p className="font-semibold text-fuchsia-400 mb-1">🤖 Codegen — ne zaman?</p>
            <ul className="space-y-0.5 list-disc list-inside">
              <li>React / Next.js / SPA siteler</li>
              <li>Shadow DOM &amp; popup'lar</li>
              <li>İlk defa kayıt alırken</li>
              <li className="text-emerald-400 font-medium">← Genellikle bu seçin</li>
            </ul>
          </div>
          <div className={`p-2 rounded border ${backend === "custom" ? "border-fuchsia-500/40 text-slate-400" : "border-slate-800"}`}>
            <p className="font-semibold text-slate-400 mb-1">🎯 Custom — ne zaman?</p>
            <ul className="space-y-0.5 list-disc list-inside">
              <li>Live action panel lazımsa</li>
              <li>PICK mode kullanmak için</li>
              <li>Codegen'de sorun varsa</li>
            </ul>
          </div>
        </div>
      </FormField>

      <FormField label="Hedef URL">
        <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none" />
      </FormField>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Feature dosya adı (opsiyonel)">
          <input type="text" placeholder="recorded_login_v2" value={featureName} onChange={(e) => setFeatureName(e.target.value)} pattern="[A-Za-z0-9_-]+" className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none" />
        </FormField>
        <FormField label="Tarayıcı">
          <select value={browser} onChange={(e) => setBrowser(e.target.value)} className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none">
            <option value="chromium">Chromium — en sağlam (önerilir)</option>
            <option value="firefox">Firefox — SSO / OAuth testleri için</option>
            <option value="webkit">WebKit — Safari uyumluluk testi için</option>
          </select>
          {browser === "chromium" && (
            <p className="mt-1 text-[10px] text-amber-400/80">
              ⚠ Playwright'ın <strong>özel Chromium</strong>'u açılır — sisteminizin Chrome'u değil.
              Açılan penceredeki mavi-gri ikon doğru pencereyi gösterir; oradan kayıt yapın.
            </p>
          )}
        </FormField>
      </div>

      {err && (
        <div className="rounded-xl p-4 text-sm bg-rose-500/10 border border-rose-500/30 text-rose-300">
          ✗ {err}
          <div className="mt-1 text-xs text-slate-400">Konsol: <code className="text-fuchsia-300">make cortex-dashboard</code> ile dashboard çalışıyor mu?</div>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2 flex-wrap">
        <button onClick={onClose} className="px-4 py-2 rounded-lg text-slate-400 hover:text-white text-sm">İptal</button>
        <button
          onClick={runPolish}
          disabled={polish.loading}
          className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-fuchsia-300 text-sm font-medium border border-fuchsia-500/30 disabled:opacity-50"
          title="Son kaydedilen .feature dosyasını yerel Ollama ile temizle ve açıklamalandır"
        >
          🪄 {polish.loading ? "Polish yapılıyor…" : "AI Polish Son Kayıt"}
        </button>
        <button onClick={start} disabled={phase === "starting"} className="px-5 py-2 rounded-lg bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-sm font-semibold disabled:opacity-50">
          {phase === "starting" ? "Başlatılıyor (Maven derleniyor)…" : "🎬 Recorder'ı Başlat"}
        </button>
      </div>

      {/* 🪄 AI Polish modal — overlays everything when open */}
      {polish.open && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 sm:p-6">
          <div className="bg-slate-950 border border-fuchsia-500/40 rounded-xl shadow-2xl w-full max-w-6xl max-h-[88vh] flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-800 flex items-start justify-between gap-3">
              <div>
                <h3 className="font-bold text-white text-base">🪄 AI Polish — Önizleme</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {polish.path ? polish.path.split("/").pop() : "son kayıt"}  ·  Model: <code className="text-fuchsia-300">{polish.model}</code>
                </p>
              </div>
              <button onClick={closePolish} className="text-slate-400 hover:text-white text-2xl leading-none">×</button>
            </div>

            {polish.loading && (
              <div className="flex-1 flex flex-col overflow-hidden">
                {polish.streamingTokens ? (
                  /* Live streaming preview */
                  <div className="flex-1 flex flex-col overflow-hidden p-3">
                    <div className="text-[11px] uppercase tracking-wide text-fuchsia-400 mb-1 font-semibold flex items-center gap-2">
                      <span className="inline-block w-2 h-2 rounded-full bg-fuchsia-500 animate-pulse" />
                      AI yazıyor…
                    </div>
                    <pre className="flex-1 overflow-auto bg-slate-900 border border-fuchsia-500/30 rounded-lg p-3 text-[11px] font-mono text-emerald-200 whitespace-pre-wrap">
                      {polish.streamingTokens}
                    </pre>
                  </div>
                ) : (
                  <div className="flex-1 grid place-items-center text-slate-400 text-sm py-16 px-6 text-center">
                    <div>
                      <div className="text-3xl mb-3 animate-spin">⚙</div>
                      <div>Ollama'ya bağlanılıyor…</div>
                      <div className="text-xs text-slate-600 mt-2">İlk tokenler birkaç saniye içinde görünür</div>
                    </div>
                  </div>
                )}
                <div className="px-4 py-2 border-t border-slate-800 flex justify-end">
                  <button
                    onClick={cancelPolish}
                    className="px-4 py-2 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-sm border border-rose-500/30"
                  >
                    ✕ İptal Et
                  </button>
                </div>
              </div>
            )}

            {polish.error && !polish.loading && (
              <div className="m-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
                ✗ {polish.error}
                <div className="mt-1 text-xs text-slate-500">Ollama çalışıyor mu? <code>curl http://127.0.0.1:11434/api/tags</code></div>
              </div>
            )}

            {!polish.loading && polish.original && polish.enhanced && (
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-3 p-3 overflow-hidden min-h-0">
                <div className="flex flex-col overflow-hidden min-h-0">
                  <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1 font-semibold">Eski (kayıt)</div>
                  <pre className="flex-1 overflow-auto bg-slate-900 border border-slate-800 rounded-lg p-3 text-[11px] font-mono text-slate-300 whitespace-pre-wrap">{polish.original}</pre>
                </div>
                <div className="flex flex-col overflow-hidden min-h-0">
                  <div className="text-[11px] uppercase tracking-wide text-fuchsia-400 mb-1 font-semibold">Yeni (AI polish)</div>
                  <pre className="flex-1 overflow-auto bg-slate-900 border border-fuchsia-500/30 rounded-lg p-3 text-[11px] font-mono text-emerald-200 whitespace-pre-wrap">{polish.enhanced}</pre>
                </div>
              </div>
            )}

            <div className="px-4 py-3 border-t border-slate-800 flex items-center justify-between gap-2 flex-wrap">
              <span className="text-xs text-slate-500">
                {polish.enhanced && !polish.loading
                  ? "Kabul edersen mevcut .feature dosyası üzerine yazılır (geri alınamaz)."
                  : ""}
              </span>
              <div className="flex gap-2 ml-auto">
                <button onClick={closePolish} className="px-4 py-2 rounded-lg text-slate-400 hover:text-white text-sm">Kapat</button>
                <button
                  onClick={acceptPolish}
                  disabled={!polish.enhanced || polish.saving || polish.loading}
                  className="px-5 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {polish.saving ? "Yazılıyor…" : "✓ Kabul Et & Kaydet"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-2.5">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="w-4 h-4 grid place-items-center rounded-full bg-fuchsia-500/20 text-fuchsia-300 text-[10px] font-bold">{n}</span>
        <span className="text-xs font-semibold text-white">{title}</span>
      </div>
      <p className="text-[11px] text-slate-400 leading-snug">{children}</p>
    </div>
  );
}

function ActionRow({ a }: { a: RecordedAction }) {
  const label = (() => {
    switch (a.type) {
      case "navigate":       return <><span className="text-emerald-400">nav</span> → {(a as { url?: string }).url?.slice(0, 50) || ""}</>;
      case "click":          return <><span className="text-amber-400">click</span> {a.element?.text ? `"${a.element.text.slice(0, 30)}"` : `<${a.element?.tag}>`}</>;
      case "fill":           return <><span className="text-cyan-400">fill</span> "{a.text?.slice(0, 30) ?? ""}"</>;
      case "press":          return <><span className="text-purple-400">press</span> {a.key}</>;
      case "wait":           return <><span className="text-slate-400">wait</span> {a.seconds}s</>;
      case "assert_visible": return <><span className="text-fuchsia-400">assert</span> visible{a.element?.text ? ` "${a.element.text.slice(0, 25)}"` : ""}</>;
      case "assert_text":    return <><span className="text-fuchsia-400">assert</span> text "{a.text?.slice(0, 25)}"</>;
      case "comment":        return <><span className="text-slate-500"># {a.text?.slice(0, 60) ?? ""}</span></>;
      case "custom":         return <><span className="text-pink-400">*</span> <span className="text-slate-300">{a.text?.slice(0, 60)}</span></>;
      case "reload":         return <span className="text-emerald-400">reload</span>;
      case "back":           return <span className="text-emerald-400">back</span>;
      default:               return <span>{a.type}</span>;
    }
  })();
  return <div className="text-slate-300 px-2 py-1 hover:bg-slate-900/60 rounded">{label}</div>;
}

/* ───── Cleanup button: kills orphan Playwright Chromium processes ── */

function CleanupButton() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const cleanup = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/cleanup`, { method: "POST" });
      const j = await r.json();
      if (j.ok) {
        setMsg(j.killed > 0 ? `${j.killed} tarayıcı kapatıldı` : "Açık tarayıcı yoktu");
      } else {
        setMsg("Hata: " + (j.error || "Bilinmeyen"));
      }
    } catch (e) {
      setMsg("Bağlantı hatası");
    } finally {
      setBusy(false);
      setTimeout(() => setMsg(null), 4000);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={cleanup}
        disabled={busy}
        title="Açık kalan Chromium pencerelerini öldür (orphan process cleanup)"
        className="px-4 py-2 rounded-lg bg-amber-900/40 hover:bg-amber-900/60 text-amber-200 text-sm font-medium border border-amber-700/40 disabled:opacity-50"
      >
        {busy ? "Temizleniyor…" : "🧹 Tarayıcıları kapat"}
      </button>
      {msg && (
        <div className="absolute top-full mt-1 left-0 z-10 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-amber-200 whitespace-nowrap shadow-lg">
          {msg}
        </div>
      )}
    </div>
  );
}

/* ───── Logs button + modal ─────────────────────────────────────── */

function LogsButton() {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const fetchLog = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/log?lines=300`);
      const j = await r.json();
      setContent(j.content || j.error || "(log bos)");
    } catch (e) {
      setContent("Hata: " + (e instanceof Error ? e.message : String(e)));
    } finally { setLoading(false); }
  };

  useEffect(() => {
    if (!open) return;
    fetchLog();
    const id = setInterval(fetchLog, 2500);
    return () => clearInterval(id);
  }, [open]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium border border-slate-700"
        title="Recorder JVM stdout/stderr"
      >
        📋 Logs
      </button>
      {open && (
        <div className="fixed inset-0 z-[60] bg-black/80 grid place-items-center p-6" onClick={() => setOpen(false)}>
          <div className="bg-slate-950 border border-slate-700 rounded-2xl max-w-5xl w-full max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
              <div>
                <p className="text-sm font-bold text-white">📋 Recorder Log (JVM stdout/stderr)</p>
                <p className="text-xs text-slate-500">logs/recorder.log · {loading ? "yukleniyor…" : "her 2.5sn yenilenir"}</p>
              </div>
              <button onClick={() => setOpen(false)} className="w-7 h-7 rounded bg-slate-800 hover:bg-slate-700 text-white">✕</button>
            </div>
            <pre className="flex-1 overflow-auto p-4 m-0 text-xs font-mono text-green-300 bg-black whitespace-pre-wrap break-all leading-relaxed">{content}</pre>
            <div className="px-4 py-2 border-t border-slate-800 flex justify-between items-center">
              <span className="text-xs text-slate-500">{content.length} bytes</span>
              <button onClick={fetchLog} disabled={loading} className="px-3 py-1.5 rounded bg-fuchsia-500/20 text-fuchsia-300 text-xs font-medium hover:bg-fuchsia-500/30 disabled:opacity-50">⟳ Yenile</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ───── Quick-add panel (recording state) ───────────────────────── */

interface LastElement { tag?: string; text?: string; placeholder?: string; ariaLabel?: string }

interface ScannedElement {
  index: number;
  tag: string;
  id?: string | null;
  name?: string | null;
  text?: string;
  placeholder?: string | null;
  ariaLabel?: string | null;
  dataTestId?: string | null;
  role?: string | null;
  href?: string | null;
  isPassword?: boolean;
  xpath?: string;
  cssPath?: string;
  label: string;
}

interface PageScan {
  url?: string;
  title?: string;
  count?: number;
  scannedAt?: number;
  elements?: ScannedElement[];
}

function QuickAddPanel({ disabled, onInjected }: { disabled: boolean; onInjected: () => void }) {
  const [lastEl, setLastEl] = useState<LastElement | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  // Poll the recorder for the most recently captured element
  useEffect(() => {
    if (disabled) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/last-element`);
        const j = await r.json();
        if (!cancelled) setLastEl(j && typeof j === "object" ? j : null);
      } catch {/* ignore */}
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => { cancelled = true; clearInterval(id); };
  }, [disabled]);

  const inject = async (label: string, body: Record<string, unknown>) => {
    setBusy(label); setErr(null); setOk(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/inject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const j = await r.json();
      if (!r.ok || !j.ok) throw new Error(j.error || "Inject failed");
      setOk(`✓ ${label} eklendi`);
      onInjected();
      setTimeout(() => setOk(null), 1500);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Failed");
      setTimeout(() => setErr(null), 3000);
    } finally { setBusy(null); }
  };

  const wait = (sec: number) => inject(`Bekleme ${sec}sn`, { type: "wait", seconds: sec });

  const comment = () => {
    const text = window.prompt("Yorum / not metni:");
    if (text?.trim()) inject("Yorum", { type: "comment", text: text.trim() });
  };

  const customStep = () => {
    const text = window.prompt(
      "Manuel Gherkin satırı (örn. 'I see \"loginButton\"'):"
    );
    if (text?.trim()) inject("Manuel adım", { type: "custom", text: text.trim() });
  };

  const assertVisible = () => inject("Doğrulama (görünür)", { type: "assert_visible", useLastElement: true });

  const assertText = () => {
    const text = window.prompt("Beklenen metin (içerir):");
    if (text?.trim()) inject("Metin doğrula", { type: "assert_text", text: text.trim(), useLastElement: true });
  };

  const reload   = () => inject("Sayfa yenile",  { type: "reload" });
  const goBack   = () => inject("Geri git",      { type: "back" });

  const elLabel = lastEl
    ? (lastEl.text || lastEl.placeholder || lastEl.ariaLabel || `<${lastEl.tag || "?"}>`).slice(0, 36)
    : null;

  const [tab, setTab] = useState<"actions" | "elements">("actions");
  const [scan, setScan] = useState<PageScan | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (disabled) return;
    let cancelled = false;
    const fetchScan = async () => {
      try {
        const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/elements`);
        const j = await r.json();
        if (!cancelled && j && j.elements) setScan(j);
      } catch {/* ignore */}
    };
    fetchScan();
    const id = setInterval(fetchScan, 2500);
    return () => { cancelled = true; clearInterval(id); };
  }, [disabled]);

  const filteredElements = useMemo(() => {
    const list = scan?.elements || [];
    if (!filter) return list;
    const f = filter.toLowerCase();
    return list.filter((e) =>
      e.label.toLowerCase().includes(f) ||
      e.tag.toLowerCase().includes(f) ||
      (e.text || "").toLowerCase().includes(f) ||
      (e.dataTestId || "").toLowerCase().includes(f) ||
      (e.id || "").toLowerCase().includes(f) ||
      (e.placeholder || "").toLowerCase().includes(f)
    );
  }, [scan, filter]);

  const elementAction = async (el: ScannedElement, type: string, label: string, askText?: string) => {
    let text: string | undefined;
    if (askText) {
      const v = window.prompt(askText);
      if (v == null || v.trim() === "") return;
      text = v.trim();
    }
    const elementInfo = {
      tag: el.tag, id: el.id, name: el.name, text: el.text,
      placeholder: el.placeholder, ariaLabel: el.ariaLabel, dataTestId: el.dataTestId,
      role: el.role, href: el.href, isPassword: el.isPassword,
      xpath: el.xpath, cssPath: el.cssPath,
    };

    // Build the best selector for Playwright to use
    const selector =
      el.dataTestId   ? `[data-testid="${el.dataTestId}"]` :
      el.id           ? `#${el.id}` :
      el.name         ? `${el.tag}[name="${el.name}"]` :
      el.cssPath      ? el.cssPath :
      el.xpath        ? `xpath=${el.xpath}` :
      `${el.tag}`;

    // Step 1: RECORD the action in the recording
    await inject(`${label} · ${el.label.slice(0, 30)}`, { type, element: elementInfo, ...(text ? { text } : {}) });

    // Step 2: PERFORM the action in the actual browser (trusted CDP event)
    if (type === "click" || type === "fill" || type === "hover" || type === "scroll") {
      try {
        const r = await fetch(`${DASHBOARD_URL}/api/cortex/recorder/perform`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: type,
            selector,
            ...(text ? { text } : {}),
            timeoutMs: 8000,
          }),
        });
        const pj = await r.json();
        if (!pj.ok) {
          console.warn("[perform] failed:", pj.error);
        } else {
          console.log("[perform]", type, "OK", pj);
        }
      } catch (e) {
        console.error("[perform] error", e);
      }
    }
    // assert_visible / assert_text don't need a browser action — just recorded
  };

  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-3 space-y-3">
      {/* Tab toggle */}
      <div className="flex gap-1 p-1 bg-slate-900 rounded-lg border border-slate-800">
        <button
          onClick={() => setTab("actions")}
          className={`flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${tab === "actions" ? "bg-fuchsia-500/80 text-white" : "text-slate-400 hover:text-white"}`}
        >
          ⚡ Hızlı Ekle
        </button>
        <button
          onClick={() => setTab("elements")}
          className={`flex-1 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${tab === "elements" ? "bg-fuchsia-500/80 text-white" : "text-slate-400 hover:text-white"}`}
        >
          🗂 Sayfa Elementleri{scan?.count ? ` (${scan.count})` : ""}
        </button>
      </div>

      {tab === "actions" ? (
        <>
          <Section title="Bekleme">
            <div className="grid grid-cols-4 gap-1">
              {[1, 2, 5, 10].map((s) => (
                <QButton key={s} onClick={() => wait(s)} busy={busy === `Bekleme ${s}sn`} disabled={disabled}>{s}sn</QButton>
              ))}
            </div>
          </Section>

          <Section title={`Doğrulama${elLabel ? ` · son: "${elLabel}"` : ""}`}>
            <div className="grid grid-cols-2 gap-1">
              <QButton onClick={assertVisible} busy={busy?.startsWith("Doğrulama")} disabled={disabled || !lastEl}>👁 Görünür</QButton>
              <QButton onClick={assertText}    busy={busy === "Metin doğrula"}      disabled={disabled || !lastEl}>📝 Metin içerir</QButton>
            </div>
            {!lastEl && <p className="text-[10px] text-amber-400/80 mt-1">Önce Chromium'da bir elemana tıklayın</p>}
          </Section>

          <Section title="Navigasyon">
            <div className="grid grid-cols-2 gap-1">
              <QButton onClick={reload} busy={busy === "Sayfa yenile"} disabled={disabled}>🔄 Yenile</QButton>
              <QButton onClick={goBack} busy={busy === "Geri git"}     disabled={disabled}>← Geri</QButton>
            </div>
          </Section>

          <Section title="Serbest">
            <div className="grid grid-cols-1 gap-1">
              <QButton onClick={comment}    busy={busy === "Yorum"}      disabled={disabled}>💬 Yorum / Not ekle</QButton>
              <QButton onClick={customStep} busy={busy === "Manuel adım"} disabled={disabled}>✏️ Manuel Gherkin satırı</QButton>
            </div>
          </Section>
        </>
      ) : (
        <ElementListPanel
          scan={scan}
          filter={filter}
          onFilterChange={setFilter}
          filteredElements={filteredElements}
          onAction={elementAction}
          disabled={disabled}
        />
      )}

      {ok  && <p className="text-[11px] text-emerald-300 mt-1">{ok}</p>}
      {err && <p className="text-[11px] text-rose-300 mt-1">✗ {err}</p>}
    </div>
  );
}

function ElementListPanel({
  scan, filter, onFilterChange, filteredElements, onAction, disabled,
}: {
  scan: PageScan | null;
  filter: string;
  onFilterChange: (v: string) => void;
  filteredElements: ScannedElement[];
  onAction: (el: ScannedElement, type: string, label: string, askText?: string) => Promise<void>;
  disabled: boolean;
}) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (!scan) {
    return <p className="text-[11px] text-slate-500 italic">Sayfa taraması bekleniyor (Chromium yüklendi mi?)…</p>;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase tracking-wide">
        <span>{scan.count ?? 0} interaktif element</span>
        <span className="opacity-60">·</span>
        <span className="truncate flex-1">{scan.title || scan.url}</span>
      </div>

      <input
        value={filter}
        onChange={(e) => onFilterChange(e.target.value)}
        placeholder="🔍 ara (text/id/data-testid)…"
        className="w-full px-2 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-white text-xs focus:border-fuchsia-500 focus:outline-none"
      />

      <div className="max-h-[400px] overflow-y-auto space-y-1">
        {filteredElements.length === 0 && (
          <p className="text-[11px] text-slate-500 italic p-2">Hiç element bulunamadı.</p>
        )}
        {filteredElements.map((el) => {
          const isOpen = expandedIdx === el.index;
          const typeColorCss = el.tag === "input" || el.tag === "textarea" || el.tag === "select"
            ? "border-cyan-500/40 hover:border-cyan-400"
            : el.tag === "button" || el.role === "button"
            ? "border-amber-500/40 hover:border-amber-400"
            : el.tag === "a"
            ? "border-purple-500/40 hover:border-purple-400"
            : "border-slate-700 hover:border-fuchsia-500/50";
          return (
            <div key={el.index} className={`rounded-md bg-slate-900/60 border ${typeColorCss} overflow-hidden`}>
              <button
                onClick={() => setExpandedIdx(isOpen ? null : el.index)}
                className="w-full text-left px-2 py-1.5 flex items-center gap-1.5 hover:bg-slate-900"
              >
                <span className="text-[10px] text-slate-500 w-6 text-right">{el.index}</span>
                <span className="text-[10px] font-mono uppercase text-slate-400">{el.tag}</span>
                <span className="text-xs text-slate-200 font-mono truncate flex-1">{el.label}</span>
                <span className="text-[10px] text-slate-600">{isOpen ? "▲" : "▼"}</span>
              </button>
              {isOpen && (
                <div className="px-2 py-2 border-t border-slate-800 bg-black/30 space-y-1.5">
                  {el.dataTestId && <DetailLine k="data-testid" v={el.dataTestId} c="emerald" />}
                  {el.id          && <DetailLine k="id"          v={el.id} c="emerald" />}
                  {el.name        && <DetailLine k="name"        v={el.name} c="cyan" />}
                  {el.ariaLabel   && <DetailLine k="aria-label"  v={el.ariaLabel} c="purple" />}
                  {el.placeholder && <DetailLine k="placeholder" v={el.placeholder} c="amber" />}
                  {el.text        && <DetailLine k="text"        v={el.text} c="slate" />}
                  {el.cssPath     && <DetailLine k="css"         v={el.cssPath} c="blue" mono />}
                  {el.xpath       && <DetailLine k="xpath"       v={el.xpath} c="rose"  mono />}

                  <div className="grid grid-cols-3 gap-1 pt-1">
                    <MiniBtn onClick={() => onAction(el, "click", "Tıkla")} disabled={disabled}>👆 Tıkla</MiniBtn>
                    <MiniBtn onClick={() => onAction(el, "assert_visible", "Gör")} disabled={disabled}>👁 Gör</MiniBtn>
                    <MiniBtn onClick={() => onAction(el, "hover", "Hover")} disabled={disabled}>🖱 Hover</MiniBtn>
                    <MiniBtn onClick={() => onAction(el, "fill", "Yaz", "Bu alana ne yazilsin?")} disabled={disabled}>✏️ Yaz</MiniBtn>
                    <MiniBtn onClick={() => onAction(el, "assert_text", "Metin", "Beklenen metin?")} disabled={disabled}>📝 Metin</MiniBtn>
                    <MiniBtn onClick={() => onAction(el, "scroll", "Scroll")} disabled={disabled}>⬇ Scroll</MiniBtn>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DetailLine({ k, v, c, mono }: { k: string; v: string; c: string; mono?: boolean }) {
  const cls = {
    emerald: "text-emerald-300", cyan: "text-cyan-300", purple: "text-purple-300",
    amber: "text-amber-300",     slate: "text-slate-300", blue: "text-blue-300",
    rose: "text-rose-300",
  }[c] || "text-slate-300";
  return (
    <div className="text-[10.5px] flex gap-1.5 items-baseline">
      <span className="text-slate-600 min-w-[64px]">{k}:</span>
      <span className={`${cls} ${mono ? "font-mono" : ""} break-all`}>{v}</span>
    </div>
  );
}

function MiniBtn({ onClick, disabled, children }: { onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-2 py-1 rounded bg-slate-800 hover:bg-fuchsia-500/20 hover:border-fuchsia-500/40 border border-slate-700 text-white text-[10.5px] font-medium disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">{title}</p>
      {children}
    </div>
  );
}

function QButton({ onClick, busy, disabled, children }: { onClick: () => void; busy?: boolean; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || busy}
      className="px-2.5 py-1.5 rounded-md bg-slate-800 hover:bg-fuchsia-500/20 hover:border-fuchsia-500/40 border border-slate-700 text-white text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-slate-800"
    >
      {busy ? "…" : children}
    </button>
  );
}

/* ============================================================== */
/*  2. AI Üret tab                                                 */
/* ============================================================== */

function AiTab({ onClose }: { onClose: () => void }) {
  const [prompt, setPrompt] = useState("");
  const [tag, setTag] = useState("@cortex @smoke @pw");
  const [generated, setGenerated] = useState<{ feature_name: string; content: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<{ feature_path: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const generate = async () => {
    if (!prompt.trim()) return;
    setBusy(true); setErr(null); setSaved(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/generate-from-prompt`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, tag }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "Generate failed");
      setGenerated(j);
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(false); }
  };

  const save = async (target: "features" | "recordings") => {
    if (!generated) return;
    setSaving(true); setErr(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/feature`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: generated.feature_name, content: generated.content, target_dir: target }),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Save failed");
      setSaved({ feature_path: j.feature_path });
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : "Failed"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
        <p className="text-sm text-slate-300">
          <strong className="text-fuchsia-300">Bir cümle yaz, Gherkin üret.</strong> Şu an template-based; AI Gateway bağlanınca LLM destekli olur.
        </p>
      </div>
      <FormField label="Senaryo açıklaması">
        <textarea rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Örnek: Kullanıcı geçerli kredentials ile login olsun, dashboard'a yönlendirilsin." className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none resize-none font-mono" />
      </FormField>
      <FormField label="Tag'ler">
        <input type="text" value={tag} onChange={(e) => setTag(e.target.value)} className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none font-mono" />
      </FormField>
      <button onClick={generate} disabled={busy || !prompt.trim()} className="w-full px-5 py-2.5 rounded-lg bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-sm font-semibold disabled:opacity-50">
        {busy ? "Üretiliyor…" : "🤖 AI ile Üret"}
      </button>
      {generated && (
        <>
          <FormField label={`Önizleme · ${generated.feature_name}.feature`}>
            <textarea rows={14} value={generated.content} onChange={(e) => setGenerated({ ...generated, content: e.target.value })} className="w-full px-3 py-2 rounded-lg bg-black/50 border border-slate-700 text-fuchsia-100 text-xs focus:border-fuchsia-500 focus:outline-none resize-y font-mono" />
          </FormField>
          <div className="flex gap-2 justify-end">
            <button onClick={() => save("recordings")} disabled={saving} className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm font-medium border border-slate-700 hover:bg-slate-700 disabled:opacity-50">recordings/'e kaydet</button>
            <button onClick={() => save("features")} disabled={saving} className="px-5 py-2 rounded-lg bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-sm font-semibold disabled:opacity-50">
              {saving ? "Kaydediliyor…" : "projects/cortex/'e kaydet"}
            </button>
          </div>
        </>
      )}
      {saved && <div className="rounded-xl p-4 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm">✓ {saved.feature_path}</div>}
      {err && <div className="rounded-xl p-4 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">✗ {err}</div>}
    </div>
  );
}

/* ============================================================== */
/*  3. Manuel tab — enriched editor + locator inspector + builder  */
/* ============================================================== */

type ManualPane = "feature" | "locator-json";
type SidebarTab = "templates" | "steps" | "locators" | "builder";

function ManualTab({ onClose }: { onClose: () => void }) {
  const [pane, setPane] = useState<ManualPane>("feature");
  const [name, setName] = useState("");

  // Feature editor state
  const [featureContent, setFeatureContent] = useState(DEFAULT_FEATURE);
  const featureRef = useRef<HTMLTextAreaElement | null>(null);

  // Locator JSON editor state
  const [locatorContent, setLocatorContent] = useState(DEFAULT_LOCATOR_JSON);
  const locatorRef = useRef<HTMLTextAreaElement | null>(null);

  // Sidebar
  const [tab, setTab] = useState<SidebarTab>("steps");
  const [filter, setFilter] = useState("");

  // Live data
  const [steps, setSteps] = useState<StepPhrase[]>([]);
  const [entries, setEntries] = useState<Record<string, LocatorEntry[]>>({});
  const [files, setFiles] = useState<LocatorFile[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);

  // Save state
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<{ feature_path: string; locator_path?: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Load endpoint data
  const refreshLocators = () =>
    fetch(`${DASHBOARD_URL}/api/cortex/locator-entries`).then((r) => r.json()).then(setEntries).catch(() => {});

  useEffect(() => {
    fetch(`${DASHBOARD_URL}/api/cortex/steps`).then((r) => r.json()).then(setSteps).catch(() => {});
    fetch(`${DASHBOARD_URL}/api/cortex/locator-files`).then((r) => r.json()).then(setFiles).catch(() => {});
    fetch(`${DASHBOARD_URL}/api/cortex/templates`).then((r) => r.json()).then(setTemplates).catch(() => {});
    refreshLocators();
  }, []);

  /* ── Editor helpers ─────────────────────────────────────────── */

  const insertIntoFeature = (text: string) => {
    const ta = featureRef.current;
    if (!ta) { setFeatureContent((c) => c + "\n    " + text); return; }
    const start = ta.selectionStart, end = ta.selectionEnd;
    const before = featureContent.slice(0, start), after = featureContent.slice(end);
    const indent = "    ";
    const inserted = (before.endsWith("\n") ? indent : "\n" + indent) + text + "\n";
    setFeatureContent(before + inserted + after);
    setPane("feature");
    setTimeout(() => { ta.focus(); ta.selectionStart = ta.selectionEnd = (before + inserted).length; }, 0);
  };

  const applyTemplate = (t: Template) => {
    setFeatureContent(t.content);
    if (!name) setName(t.id);
    setPane("feature");
    setTab("steps");
  };

  /* ── Save ───────────────────────────────────────────────────── */

  const save = async () => {
    if (!name.trim() || !featureContent.trim()) {
      setErr("Dosya adı ve içerik zorunlu"); return;
    }

    let locators: unknown[] | undefined = undefined;
    if (locatorContent.trim() && locatorContent.trim() !== "[]") {
      try {
        const parsed = JSON.parse(locatorContent);
        if (!Array.isArray(parsed)) throw new Error("Locator JSON bir dizi olmalı");
        locators = parsed;
      } catch (e) {
        setErr(`Locator JSON parse hatası: ${e instanceof Error ? e.message : "bilinmiyor"}`);
        return;
      }
    }

    setSaving(true); setErr(null); setSaved(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/feature`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, content: featureContent, target_dir: "features", locators }),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Save failed");
      setSaved({ feature_path: j.feature_path, locator_path: j.locator_path });
      refreshLocators();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : "Failed"); }
    finally { setSaving(false); }
  };

  /* ── Filter ─────────────────────────────────────────────────── */

  const filteredSteps = useMemo(() => {
    if (!filter) return steps;
    const f = filter.toLowerCase();
    return steps.filter((s) => s.phrase.toLowerCase().includes(f) || s.kind.toLowerCase().includes(f));
  }, [steps, filter]);

  const filteredKeys = useMemo(() => {
    const keys = Object.keys(entries).sort();
    if (!filter) return keys;
    const f = filter.toLowerCase();
    return keys.filter((k) => k.toLowerCase().includes(f) || entries[k].some((e) => e.value.toLowerCase().includes(f)));
  }, [entries, filter]);

  /* ── Render ─────────────────────────────────────────────────── */

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
      {/* ───── LEFT: Editors with pane toggle ──────────────────── */}
      <div className="space-y-3">
        <FormField label="Feature dosya adı">
          <input type="text" placeholder="my-new-scenario" value={name} onChange={(e) => setName(e.target.value)} pattern="[A-Za-z0-9_-]+" className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-fuchsia-500 focus:outline-none font-mono" />
        </FormField>

        <div className="flex gap-1 p-1 bg-slate-900 rounded-lg border border-slate-800 w-fit">
          {(["feature", "locator-json"] as ManualPane[]).map((p) => (
            <button key={p} onClick={() => setPane(p)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${pane === p ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}>
              {p === "feature" ? "📜 Feature" : "🔑 Locator JSON"}
            </button>
          ))}
        </div>

        {pane === "feature" ? (
          <FormField label="Gherkin">
            <textarea
              ref={featureRef} rows={20} value={featureContent} onChange={(e) => setFeatureContent(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-black/50 border border-slate-700 text-fuchsia-100 text-xs focus:border-fuchsia-500 focus:outline-none resize-y font-mono leading-relaxed"
            />
          </FormField>
        ) : (
          <FormField label={`Locator JSON · ${name || "<isim girilmedi>"}.json`}>
            <textarea
              ref={locatorRef} rows={20} value={locatorContent} onChange={(e) => setLocatorContent(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-black/50 border border-slate-700 text-amber-100 text-xs focus:border-amber-500 focus:outline-none resize-y font-mono leading-relaxed"
            />
            <p className="text-xs text-slate-500 mt-1.5">Aynı <code className="text-fuchsia-300">key</code> birden fazla geçerse MultiBy fallback olur (data-testid → id → xpath).</p>
          </FormField>
        )}

        {saved && (
          <div className="rounded-xl p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm space-y-1">
            <div>✓ Feature: <code className="text-white">{saved.feature_path}</code></div>
            {saved.locator_path && <div>✓ Locator: <code className="text-white">{saved.locator_path}</code></div>}
          </div>
        )}
        {err && <div className="rounded-xl p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">✗ {err}</div>}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-slate-400 hover:text-white text-sm">İptal</button>
          <button onClick={save} disabled={saving || !name || !featureContent} className="px-5 py-2 rounded-lg bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-sm font-semibold disabled:opacity-50">
            {saving ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </div>

      {/* ───── RIGHT: Sidebar tabs ─────────────────────────────── */}
      <div className="space-y-3 lg:max-h-[640px] lg:overflow-y-auto pr-1">
        <div className="grid grid-cols-4 gap-1 p-1 bg-slate-900 rounded-lg border border-slate-800 sticky top-0 z-10">
          {([
            { id: "templates", label: "Şablon" },
            { id: "steps",     label: "Adım" },
            { id: "locators",  label: "Locator" },
            { id: "builder",   label: "+ Yeni" },
          ] as { id: SidebarTab; label: string }[]).map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-2 py-1.5 rounded-md text-xs font-medium transition-all ${tab === t.id ? "bg-slate-700 text-white" : "text-slate-400 hover:text-white"}`}>
              {t.label}
            </button>
          ))}
        </div>

        {tab !== "templates" && tab !== "builder" && (
          <input type="text" placeholder="🔍 ara…" value={filter} onChange={(e) => setFilter(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-xs focus:border-fuchsia-500 focus:outline-none" />
        )}

        {tab === "templates" && <TemplatesPanel templates={templates} onApply={applyTemplate} />}
        {tab === "steps"     && <StepsPanel    steps={filteredSteps} onInsert={insertIntoFeature} />}
        {tab === "locators"  && <LocatorsPanel keys={filteredKeys} entries={entries} onInsertKey={(k) => insertIntoFeature(`"${k}"`)} />}
        {tab === "builder"   && <BuilderPanel  files={files} onAdded={() => refreshLocators()} />}
      </div>
    </div>
  );
}

/* ───── Sidebar panels ───── */

function TemplatesPanel({ templates, onApply }: { templates: Template[]; onApply: (t: Template) => void }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500 uppercase tracking-wide">Hazır Şablonlar ({templates.length})</p>
      {templates.map((t) => (
        <button key={t.id} onClick={() => onApply(t)} className="w-full text-left rounded-lg bg-slate-900/60 border border-slate-800 hover:border-fuchsia-500/50 p-3 transition-colors group">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-semibold text-white group-hover:text-fuchsia-300">{t.title}</span>
            <span className="text-[10px] font-mono text-fuchsia-400">{t.tag.split(" ").slice(0, 2).join(" ")}…</span>
          </div>
          <p className="text-xs text-slate-400 leading-snug">{t.description}</p>
        </button>
      ))}
    </div>
  );
}

function StepsPanel({ steps, onInsert }: { steps: StepPhrase[]; onInsert: (text: string) => void }) {
  return (
    <div className="space-y-1">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1.5">Adım Phrase'leri ({steps.length})</p>
      {steps.map((s, i) => {
        const keyword = s.kind === "Then" ? "Then" : s.kind === "When" ? "When" : "*";
        const color = s.kind === "Given" ? "text-emerald-400" : s.kind === "When" ? "text-amber-400" : "text-purple-400";
        return (
          <button key={i} onClick={() => onInsert(`${keyword} ${s.phrase}`)}
            className="w-full text-left px-2 py-1.5 rounded bg-slate-900/60 border border-slate-800 hover:border-fuchsia-500/50 hover:bg-slate-900 text-xs transition-colors">
            <span className={`mr-1.5 font-bold ${color}`}>{s.kind}</span>
            <span className="text-slate-300 font-mono">{s.phrase}</span>
          </button>
        );
      })}
    </div>
  );
}

function LocatorsPanel({ keys, entries, onInsertKey }: { keys: string[]; entries: Record<string, LocatorEntry[]>; onInsertKey: (k: string) => void }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  return (
    <div className="space-y-1">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1.5">Locator Kütüphanesi ({keys.length})</p>
      {keys.map((k) => {
        const list = entries[k] || [];
        const isOpen = expanded === k;
        return (
          <div key={k} className="rounded bg-slate-900/60 border border-slate-800 overflow-hidden">
            <div className="flex items-center justify-between px-2 py-1.5 hover:bg-slate-900">
              <button onClick={() => onInsertKey(k)} className="text-left flex-1 text-xs font-mono text-fuchsia-300 hover:text-fuchsia-200">
                "{k}"
              </button>
              <button onClick={() => setExpanded(isOpen ? null : k)} className="text-[10px] text-slate-500 hover:text-white px-1.5 py-0.5 rounded">
                {list.length} fallback {isOpen ? "▲" : "▼"}
              </button>
            </div>
            {isOpen && (
              <div className="border-t border-slate-800 p-2 space-y-1 bg-black/40">
                {list.map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-[10.5px]">
                    <span className={`shrink-0 px-1.5 py-0.5 rounded font-mono uppercase ${typeColor(e.type)}`}>{e.type}</span>
                    <span className="font-mono text-slate-300 break-all leading-tight">{e.value}</span>
                  </div>
                ))}
                <div className="pt-1 text-[10px] text-slate-600 font-mono">{list[0]?.source}</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function BuilderPanel({ files, onAdded }: { files: LocatorFile[]; onAdded: () => void }) {
  const [key,   setKey]   = useState("");
  const [type,  setType]  = useState("css");
  const [value, setValue] = useState("");
  const [file,  setFile]  = useState(files[0]?.path || "");
  const [newFile, setNewFile] = useState("");
  const [busy,  setBusy]  = useState(false);
  const [out,   setOut]   = useState<string | null>(null);
  const [err,   setErr]   = useState<string | null>(null);

  useEffect(() => { if (!file && files[0]) setFile(files[0].path); }, [files, file]);

  const submit = async () => {
    if (!key.trim() || !value.trim()) { setErr("Key ve value zorunlu"); return; }
    const target = newFile.trim() ? newFile.trim() : file;
    if (!target) { setErr("Hedef dosya seç veya yeni isim gir"); return; }
    setBusy(true); setErr(null); setOut(null);
    try {
      const r = await fetch(`${DASHBOARD_URL}/api/cortex/locator-entry`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file: newFile.trim() ? `${newFile.trim()}.json` : target,
          base: "projects/cortex",
          entry: { key, type, value },
        }),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "Append failed");
      setOut(`✓ ${j.file} → şimdi ${j.total_entries_in_file} entry`);
      setKey(""); setValue("");
      onAdded();
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : "Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-3 text-xs">
      <p className="text-xs text-slate-500 uppercase tracking-wide">Yeni Locator Tanımla</p>

      <SmallField label="Key (camelCase)">
        <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="loginButton" className="w-full px-2 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-white text-xs font-mono focus:border-fuchsia-500 focus:outline-none" />
      </SmallField>

      <SmallField label="Tip">
        <select value={type} onChange={(e) => setType(e.target.value)} className="w-full px-2 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-white text-xs focus:border-fuchsia-500 focus:outline-none">
          {LOCATOR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <p className="text-[10px] text-slate-500 mt-1">Öncelik: data-testid &gt; id &gt; name &gt; aria &gt; css &gt; xpath</p>
      </SmallField>

      <SmallField label={`Value (${type === "css" ? "CSS selector" : type === "xpath" ? "XPath ifadesi" : "değer"})`}>
        <textarea rows={2} value={value} onChange={(e) => setValue(e.target.value)}
          placeholder={hintFor(type)}
          className="w-full px-2 py-1.5 rounded-md bg-black/40 border border-slate-700 text-amber-200 text-xs font-mono focus:border-fuchsia-500 focus:outline-none resize-y" />
      </SmallField>

      <SmallField label="Hedef dosya">
        <select value={file} onChange={(e) => { setFile(e.target.value); setNewFile(""); }} className="w-full px-2 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-white text-xs focus:border-fuchsia-500 focus:outline-none">
          {files.map((f) => <option key={f.path} value={f.path}>{f.path}</option>)}
        </select>
      </SmallField>

      <SmallField label="… veya yeni dosya adı">
        <input value={newFile} onChange={(e) => setNewFile(e.target.value)} placeholder="my-feature" pattern="[A-Za-z0-9_-]+" className="w-full px-2 py-1.5 rounded-md bg-slate-900 border border-slate-700 text-white text-xs font-mono focus:border-fuchsia-500 focus:outline-none" />
        <p className="text-[10px] text-slate-500 mt-1">Doluysa projects/cortex/locators/&lt;isim&gt;.json olarak yaratılır</p>
      </SmallField>

      <button onClick={submit} disabled={busy} className="w-full px-3 py-2 rounded-md bg-gradient-to-r from-fuchsia-500 to-purple-600 text-white text-xs font-semibold disabled:opacity-50">
        {busy ? "Ekleniyor…" : "+ Locator JSON'a Ekle"}
      </button>

      {out && <div className="rounded-md p-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs">{out}</div>}
      {err && <div className="rounded-md p-2 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">✗ {err}</div>}

      {/* Preview JSON entry */}
      {key && value && (
        <div className="rounded-md p-2 bg-black/40 border border-slate-800">
          <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-1">Önizleme</p>
          <pre className="text-[11px] text-amber-200 font-mono whitespace-pre-wrap leading-tight">{`{ "key": "${key}", "type": "${type}", "value": "${value.replace(/"/g, '\\"')}" }`}</pre>
        </div>
      )}
    </div>
  );
}

/* ───── Helpers ───── */

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">{label}</span>
      {children}
    </label>
  );
}

function SmallField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1">{label}</span>
      {children}
    </label>
  );
}

function typeColor(type: string): string {
  const t = type.toLowerCase();
  if (t === "css") return "bg-blue-500/20 text-blue-300";
  if (t === "id") return "bg-emerald-500/20 text-emerald-300";
  if (t === "xpath") return "bg-amber-500/20 text-amber-300";
  if (t === "name") return "bg-purple-500/20 text-purple-300";
  return "bg-slate-700/40 text-slate-300";
}

function hintFor(type: string): string {
  switch (type) {
    case "css":             return "[data-testid='login-submit'] veya #btnLogin";
    case "xpath":           return "//button[normalize-space()='Giriş Yap']";
    case "id":              return "btnLogin";
    case "name":            return "username";
    case "linktext":        return "Şifremi Unuttum";
    case "partiallinktext": return "Unuttum";
    default:                return "";
  }
}

/* ───── Defaults ───── */

const DEFAULT_FEATURE = `@cortex @smoke @pw
Feature: Yeni senaryo

  Background:
    Given I open "cortex.url" link
    * I wait for page to load
    * I click "cookieAcceptButton" if it exists

  Scenario: Smoke check
    Then I see "loginContainer"
`;

const DEFAULT_LOCATOR_JSON = `[
  { "key": "myButton", "type": "css", "value": "[data-testid='my-button']" },
  { "key": "myButton", "type": "id",  "value": "btnMyAction" }
]
`;
