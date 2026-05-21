"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import {
  PageHeader,
  StatCard,
  StatusBadge,
  SectionCard,
  EmptyState,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ENGINE_BASE } from "@/lib/api";

const BROWSERS = ["chromium", "firefox", "webkit"] as const;
type Browser = (typeof BROWSERS)[number];

type Run = {
  id: number;
  project_id: number | null;
  test_id: number | null;
  test_title: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  allure_path: string;
  feature_path: string;
  mock_mode: number;
};

function fmt(dt: string | null) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
}

function dur(start: string, end: string | null) {
  if (!end) return "—";
  const s = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

/* ── Log Terminal ─────────────────────────────────────────────────────────── */
function LogTerminal({ logs, status }: { logs: LogLine[]; status: string }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const lineColor = (type: string) => {
    if (type === "error") return "text-red-400";
    if (type === "summary") return "text-emerald-400";
    if (type === "test_result") return "text-blue-300";
    if (type === "info") return "text-amber-300";
    return "text-slate-300";
  };

  const linePrefix = (type: string) => {
    if (type === "error") return "✗ ";
    if (type === "summary") return "✅ ";
    if (type === "test_result") return "  ";
    if (type === "info") return "ℹ ";
    return "  ";
  };

  return (
    <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 font-mono text-xs">
      {/* Terminal header */}
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900 px-4 py-2">
        <div className="flex gap-1.5">
          <div className="h-3 w-3 rounded-full bg-red-500/60" />
          <div className="h-3 w-3 rounded-full bg-amber-500/60" />
          <div className="h-3 w-3 rounded-full bg-emerald-500/60" />
        </div>
        <span className="ml-2 text-slate-500">Canlı Test Çıktısı</span>
        {status === "running" && (
          <div className="ml-auto flex items-center gap-1.5 text-blue-400">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-400" />
            Koşuyor
          </div>
        )}
        {status === "done" && <span className="ml-auto text-emerald-400">Tamamlandı</span>}
        {status === "error" && <span className="ml-auto text-red-400">Hata</span>}
      </div>

      {/* Logs */}
      <div className="space-y-0.5 overflow-y-auto p-4" style={{ maxHeight: 360 }}>
        {logs.length === 0 ? (
          <span className="text-slate-600">Koşum bekleniyor...</span>
        ) : (
          logs.map((l, i) => (
            <div key={i} className={lineColor(l.type)}>
              <span className="mr-2 select-none text-slate-600">{String(i + 1).padStart(3, " ")}│</span>
              <span>{linePrefix(l.type)}{l.text ?? ""}</span>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function RunsPage() {
  const projectId = useRouteParam("projectId");
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Run | null>(null);

  /* New run */
  const [featurePath, setFeaturePath] = useState("");
  const [browser, setBrowser] = useState<Browser>("chromium");
  const [runId, setRunId] = useState<string | null>(null);
  const [liveStatus, setLiveStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [healCount, setHealCount] = useState(0);
  const esRef = useRef<EventSource | null>(null);

  /* AI analysis */
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<FailureAnalysis | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    fetch(`${ENGINE_BASE}/api/pipeline/manual-to-automation/runs?project_id=${projectId}&limit=50`)
      .then(r => r.json())
      .then(d => { setRuns(d.runs ?? []); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  async function startRun() {
    if (!featurePath.trim()) return;
    setLogs([]);
    setHealCount(0);
    setAnalysis(null);
    setLiveStatus("running");

    try {
      const res = await fetch(`${ENGINE_BASE}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feature: featurePath.trim(), browser }),
      });
      const data = await res.json();
      const id: string = data.run_id;
      setRunId(id);

      const es = new EventSource(`${ENGINE_BASE}/api/run/${id}/stream`);
      esRef.current = es;

      es.onmessage = (ev) => {
        try {
          const msg: LogLine = JSON.parse(ev.data);
          if (msg.type === "ping") return;
          if (msg.type === "done") { setLiveStatus("done"); es.close(); load(); return; }
          if (msg.type === "error") { setLiveStatus("error"); es.close(); return; }
          if (msg.type === "self_heal") setHealCount(msg.healed_count ?? 0);
          setLogs(prev => [...prev, msg]);
        } catch { /* noop */ }
      };
      es.onerror = () => { setLiveStatus("error"); es.close(); };
    } catch (e) {
      setLogs([{ type: "error", text: String(e) }]);
      setLiveStatus("error");
    }
  }

  function stopRun() { esRef.current?.close(); setLiveStatus("done"); }

  async function analyzeFailure(run: Run) {
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const res = await fetch(`${ENGINE_BASE}/api/ai/analyze-failure`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          test_title: run.test_title,
          feature_path: run.feature_path,
          status: run.status,
        }),
      });
      setAnalysis(await res.json());
    } finally { setAnalyzing(false); }
  }

  /* Stats */
  const totalRuns = runs.length;
  const passedRuns = runs.filter(r => r.status === "passed" || r.status === "completed").length;
  const failedRuns = runs.filter(r => r.status === "failed" || r.status === "error").length;
  const passRate = totalRuns > 0 ? Math.round((passedRuns / totalRuns) * 100) : 0;
  const passRateColor: "emerald" | "amber" | "red" | "slate" =
    totalRuns === 0 ? "slate" : passRate >= 80 ? "emerald" : passRate >= 50 ? "amber" : "red";

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="runs-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        }
        title="Test Koşuları (Engine)"
        description="Playwright engine üzerinden koşum geçmişi"
        right={
          <ToolbarActions>
            <Link
              href={`/p/${projectId}/executions/new`}
              className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 transition-all hover:border-slate-500 hover:text-white"
            >
              Execution Koşusu →
            </Link>
          </ToolbarActions>
        }
      />

      {/* Stats row */}
      <MetricRow cols={4} className="mb-5">
        <StatCard label="Toplam Koşu" value={totalRuns} color="slate" />
        <StatCard label="Başarılı" value={passedRuns} color="emerald" />
        <StatCard label="Başarısız" value={failedRuns} color={failedRuns > 0 ? "red" : "slate"} />
        <StatCard label="Başarı Oranı" value={totalRuns === 0 ? "—" : `${passRate}%`} color={passRateColor} />
      </MetricRow>

      {/* New Run Panel */}
      <SectionCard
        title="Yeni Koşu Başlat"
        icon={<svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        className="mb-4"
      >
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={featurePath}
              onChange={e => setFeaturePath(e.target.value)}
              placeholder="features/login.feature veya klasör yolu"
              className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-sm text-white placeholder-slate-500 transition-colors focus:border-slate-500 focus:outline-none"
            />
            <Tabs variant="pill" value={browser} onValueChange={(v) => setBrowser(v as Browser)}>
              <TabsList>
                {BROWSERS.map(b => (
                  <TabsTrigger key={b} value={b}>{b}</TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={startRun}
              disabled={liveStatus === "running" || !featurePath.trim()}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {liveStatus === "running" ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              ) : (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                </svg>
              )}
              Koşu Başlat
            </button>

            {liveStatus === "running" && (
              <button
                onClick={stopRun}
                className="flex items-center gap-2 rounded-xl border border-red-500/30 px-3 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/10"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10h6v4H9z" />
                </svg>
                Durdur
              </button>
            )}

            {healCount > 0 && (
              <span className="rounded-lg border border-violet-500/20 bg-violet-500/10 px-2 py-1 text-xs text-violet-400">
                🔧 {healCount} self-heal
              </span>
            )}

            {runId && (
              <span className="ml-auto font-mono text-xs text-slate-500">run: {runId}</span>
            )}
          </div>

          {(liveStatus !== "idle" || logs.length > 0) && (
            <LogTerminal logs={logs} status={liveStatus} />
          )}
        </div>
      </SectionCard>

      {/* Analysis panel */}
      {selected && selected.status === "failed" && (
        <SectionCard
          title="AI Hata Analizi"
          icon={<svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m1.636 6.364l.707-.707M12 21v-1m-6.364-1.636l-.707-.707" /></svg>}
          right={
            <button
              onClick={() => analyzeFailure(selected)}
              disabled={analyzing}
              className="flex items-center gap-1.5 rounded-lg border border-violet-500/30 px-3 py-1 text-xs font-medium text-violet-300 transition-all hover:border-violet-400/50 disabled:opacity-50"
            >
              {analyzing ? <div className="h-3 w-3 animate-spin rounded-full border-2 border-violet-400/30 border-t-violet-400" /> : null}
              {analyzing ? "Analiz ediliyor..." : "Analiz Et"}
            </button>
          }
          className="mb-4"
        >
          {analysis ? (
            <div className="space-y-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
                  <p className="mb-1 text-xs text-slate-400">Kategori</p>
                  <p className="text-sm font-semibold text-white">{analysis.category}</p>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
                  <p className="mb-1 text-xs text-slate-400">Otomatik Düzeltilebilir</p>
                  <p className={`text-sm font-semibold ${analysis.auto_fixable ? "text-emerald-400" : "text-slate-300"}`}>
                    {analysis.auto_fixable ? "✓ Evet" : "Hayır"}
                  </p>
                </div>
              </div>
              <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
                <p className="mb-1 text-xs text-slate-400">Sebep</p>
                <p className="text-sm text-slate-200">{analysis.reason}</p>
              </div>
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
                <p className="mb-1 text-xs text-blue-400">Öneri</p>
                <p className="text-sm text-slate-200">{analysis.fix_suggestion}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Seçili koşu için AI analizi yapmak için &ldquo;Analiz Et&rdquo; butonuna tıklayın.</p>
          )}
        </SectionCard>
      )}

      {/* Runs table */}
      <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-900/40">
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <h3 className="text-sm font-semibold text-white">Geçmiş Koşular</h3>
          <span className="text-xs text-slate-500">{runs.length} koşu</span>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Test</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Başladı</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Süre</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Mod</th>
              <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">İşlem</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="py-16 text-center text-sm text-slate-500">
                  <div className="flex items-center justify-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
                    Yükleniyor...
                  </div>
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={6}>
                  <EmptyState
                    icon="⚠️"
                    title="Engine bağlantısı kurulamadı"
                    description={`Engine (port 5001) çalışmıyor olabilir: ${error}`}
                  />
                </td>
              </tr>
            ) : runs.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <EmptyState
                    icon="🏃"
                    title="Henüz koşu yok"
                    description="Henüz tamamlanmış bir test koşusu bulunmuyor"
                  />
                </td>
              </tr>
            ) : (
              runs.map(r => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className={`group cursor-pointer border-b border-slate-800 transition-colors hover:bg-slate-800/40 ${selected?.id === r.id ? "bg-slate-800/30" : ""}`}
                >
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-white">{r.test_title || "—"}</p>
                    <p className="mt-0.5 max-w-64 truncate font-mono text-xs text-slate-500">{r.feature_path}</p>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-400">{fmt(r.started_at)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{dur(r.started_at, r.ended_at)}</td>
                  <td className="px-4 py-3">
                    {r.mock_mode ? (
                      <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">Mock</span>
                    ) : (
                      <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">Gerçek</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      {r.allure_path && (
                        <a
                          href={`${ENGINE_BASE}/allure/${r.id}/index.html`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="rounded-lg px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
                        >
                          Allure →
                        </a>
                      )}
                      {r.status === "failed" && (
                        <button
                          onClick={e => { e.stopPropagation(); setSelected(r); analyzeFailure(r); }}
                          className="rounded-lg px-2 py-1 text-xs text-violet-400 transition-colors hover:bg-violet-500/10"
                        >
                          AI Analiz
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
