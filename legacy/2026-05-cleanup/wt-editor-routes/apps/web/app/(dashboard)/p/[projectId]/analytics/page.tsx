"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { useRealtimeExecution } from "@/lib/useRealtimeExecution";
import {
  PageHeader,
  StatCard,
  SectionCard,
  StatusBadge,
  MetricRow,
  TrendBadge,
} from "@/components/nexus";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type TrendPoint = { date: string; pass_rate: number; total_runs: number };
type ExecStats = { total_runs: number; avg_pass_rate: number; total_scenarios: number };
type FlakyTest = {
  scenario_id: string;
  scenario_title: string;
  inconsistency_rate: number;
  recent_results: string[];
};
type AnomalyResult = {
  anomalies: Array<{
    execution_id: string;
    execution_name: string;
    duration_seconds: number;
    z_score: number;
    issue: string;
  }>;
  total_analyzed: number;
  anomaly_count: number;
  avg_duration: number;
};

type TimeRange = "7" | "30" | "90";

const resultColor: Record<string, string> = {
  passed:  "bg-emerald-500",
  failed:  "bg-red-500",
  skipped: "bg-amber-400",
  error:   "bg-orange-500",
};

const TIME_RANGE_LABEL: Record<TimeRange, string> = {
  "7": "7 gün",
  "30": "30 gün",
  "90": "90 gün",
};

export default function AnalyticsPage() {
  const projectId = useRouteParam("projectId");

  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [stats, setStats] = useState<ExecStats | null>(null);
  const [flaky, setFlaky] = useState<FlakyTest[]>([]);
  const [anomalyResult, setAnomalyResult] = useState<AnomalyResult | null>(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [showAnomalyPanel, setShowAnomalyPanel] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>("30");

  const load = useCallback(() => {
    apiFetch<TrendPoint[]>(`/api/v1/tspm/projects/${projectId}/execution-trends?days=${timeRange}`)
      .then(setTrends).catch(() => {});
    apiFetch<ExecStats>(`/api/v1/tspm/projects/${projectId}/execution-stats`)
      .then(setStats).catch(() => {});
    apiFetch<FlakyTest[]>(`/api/v1/tspm/projects/${projectId}/flaky-tests`)
      .then(setFlaky).catch(() => {});
  }, [projectId, timeRange]);

  useEffect(() => { load(); }, [load]);
  useRealtimeExecution(projectId, load);

  async function runAnomalyDetect() {
    setAnomalyLoading(true);
    setShowAnomalyPanel(true);
    try {
      const result = await apiFetch<AnomalyResult>(
        `/api/v1/ai/projects/${projectId}/anomaly-detect`, { method: "POST" }
      );
      setAnomalyResult(result);
    } finally { setAnomalyLoading(false); }
  }

  /* SVG chart geometry */
  const W = 720;
  const H = 200;
  const pad = { t: 16, r: 16, b: 28, l: 40 };
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;
  const maxRuns = Math.max(...trends.map(t => t.total_runs), 1);

  function pts(): string {
    if (trends.length === 0) return "";
    return trends.map((p, i) => {
      const x = pad.l + (i / Math.max(trends.length - 1, 1)) * cw;
      const y = pad.t + ch - (p.pass_rate / 100) * ch;
      return `${x},${y}`;
    }).join(" ");
  }

  const avgRate = stats ? Math.round(stats.avg_pass_rate) : 0;
  const rateColor: "emerald" | "amber" | "red" =
    avgRate >= 80 ? "emerald" : avgRate >= 50 ? "amber" : "red";
  const trendDir: "up" | "down" | "neutral" =
    avgRate >= 80 ? "up" : avgRate < 50 ? "down" : "neutral";

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="analytics-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        }
        title="Analitik"
        description="Test koşum trendleri, başarı oranları ve anomali tespiti"
        right={
          <Tabs variant="pill" value={timeRange} onValueChange={(v) => setTimeRange(v as TimeRange)}>
            <TabsList>
              {(["7", "30", "90"] as TimeRange[]).map(r => (
                <TabsTrigger key={r} value={r}>{TIME_RANGE_LABEL[r]}</TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        }
      />

      {/* Stat cards */}
      <MetricRow cols={4} className="mb-6">
        <StatCard
          icon={<svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          label="Toplam Koşu"
          value={stats?.total_runs ?? "—"}
          color="blue"
        />
        <StatCard
          icon={<svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          label="Ort. Başarı Oranı"
          value={stats ? `${avgRate}%` : "—"}
          color={rateColor}
          trend={trendDir}
          sub={stats ? TIME_RANGE_LABEL[timeRange] : undefined}
        />
        <StatCard
          icon={<svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>}
          label="Toplam Senaryo"
          value={stats?.total_scenarios ?? "—"}
          color="violet"
        />
        <StatCard
          icon={<svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
          label="Flaky Test"
          value={flaky.length}
          color={flaky.length > 0 ? "amber" : "slate"}
          sub={flaky.length > 0 ? "dikkat gerekiyor" : "temiz"}
        />
      </MetricRow>

      {/* Charts grid */}
      <div className="mb-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Line chart */}
        <SectionCard
          title="Başarı Oranı Trendi"
          className="lg:col-span-2"
          right={stats ? <TrendBadge value={avgRate - 50} direction={trendDir} label={`${avgRate}%`} /> : undefined}
        >
          {trends.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">Trend verisi yok</p>
          ) : (
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-label="Başarı oranı grafiği">
              {[0, 25, 50, 75, 100].map(v => {
                const y = pad.t + ch - (v / 100) * ch;
                return (
                  <g key={v}>
                    <line x1={pad.l} x2={W - pad.r} y1={y} y2={y} stroke="#334155" strokeDasharray="4 4" />
                    <text x={pad.l - 6} y={y + 4} textAnchor="end" fill="#64748b" fontSize={10}>{v}%</text>
                  </g>
                );
              })}

              {[0, Math.floor(trends.length / 2), trends.length - 1]
                .filter((i, idx, arr) => arr.indexOf(i) === idx && trends[i])
                .map(i => {
                  const x = pad.l + (i / Math.max(trends.length - 1, 1)) * cw;
                  return (
                    <text key={i} x={x} y={H - 4} textAnchor="middle" fill="#64748b" fontSize={10}>
                      {trends[i].date.slice(5)}
                    </text>
                  );
                })}

              {trends.length > 1 && (
                <polygon
                  points={pts() + ` ${pad.l + cw},${pad.t + ch} ${pad.l},${pad.t + ch}`}
                  fill="url(#areaGrad)"
                  opacity={0.15}
                />
              )}
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="1" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                </linearGradient>
              </defs>

              <polyline points={pts()} fill="none" stroke="#3b82f6" strokeWidth={2} strokeLinejoin="round" />

              {trends.map((p, i) => {
                const x = pad.l + (i / Math.max(trends.length - 1, 1)) * cw;
                const y = pad.t + ch - (p.pass_rate / 100) * ch;
                return (
                  <circle key={i} cx={x} cy={y} r={3} fill="#3b82f6" stroke="#0f172a" strokeWidth={1.5}>
                    <title>{p.date}: %{p.pass_rate} ({p.total_runs} koşu)</title>
                  </circle>
                );
              })}
            </svg>
          )}
        </SectionCard>

        {/* Bar chart */}
        <SectionCard title="Günlük Koşu Sayısı">
          {trends.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">Veri yok</p>
          ) : (
            <div className="flex items-end gap-0.5" style={{ height: 100 }}>
              {trends.map(t => (
                <div
                  key={t.date}
                  className="flex-1 cursor-default rounded-t bg-blue-500/40 transition-colors hover:bg-blue-500/70"
                  style={{ height: `${(t.total_runs / maxRuns) * 100}%`, minHeight: t.total_runs > 0 ? 3 : 0 }}
                  title={`${t.date}: ${t.total_runs} koşu`}
                />
              ))}
            </div>
          )}
        </SectionCard>

        {/* AI Anomaly Detection */}
        <SectionCard
          title="AI Anomali Tespiti"
          icon={<svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          right={
            <button
              onClick={runAnomalyDetect}
              disabled={anomalyLoading}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1 text-xs font-medium text-slate-300 transition-all hover:border-slate-500 hover:text-white disabled:opacity-50"
            >
              {anomalyLoading ? (
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-slate-600 border-t-violet-400" />
              ) : (
                <svg className="h-3 w-3 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              )}
              Anomali Tara
            </button>
          }
        >
          <p className="mb-3 text-xs text-slate-500">İstatistiksel sapma analizi ile olağandışı koşuları tespit eder</p>
          {showAnomalyPanel && (
            anomalyLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-800" />
                ))}
              </div>
            ) : anomalyResult ? (
              <div className="space-y-3">
                <MetricRow cols={3} gap="sm">
                  <StatCard label="Analiz Edilen" value={anomalyResult.total_analyzed} color="slate" />
                  <StatCard label="Anomali" value={anomalyResult.anomaly_count} color={anomalyResult.anomaly_count > 0 ? "red" : "emerald"} />
                  <StatCard label="Ort. Süre" value={`${Math.round(anomalyResult.avg_duration)}s`} color="slate" />
                </MetricRow>
                {anomalyResult.anomalies.length > 0 ? (
                  <div className="divide-y divide-slate-800 overflow-hidden rounded-lg border border-slate-700">
                    {anomalyResult.anomalies.map(a => (
                      <div key={a.execution_id} className="flex items-start justify-between gap-2 px-3 py-2 hover:bg-slate-800/40">
                        <div>
                          <p className="text-sm font-medium text-white">{a.execution_name}</p>
                          <p className="text-xs text-slate-500">{a.issue} · {a.duration_seconds}s · z={a.z_score.toFixed(2)}</p>
                        </div>
                        <StatusBadge status="warning" label="Anomali" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="py-3 text-center text-sm text-emerald-400">✓ Anomali tespit edilmedi</p>
                )}
              </div>
            ) : null
          )}
        </SectionCard>
      </div>

      {/* Flaky tests */}
      <SectionCard title="Flaky Testler" noPad>
        {flaky.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-500">Flaky test bulunamadı ✓</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Senaryo</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tutarsızlık</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Son Sonuçlar</th>
              </tr>
            </thead>
            <tbody>
              {flaky.map(f => (
                <tr key={f.scenario_id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <td className="px-4 py-3 text-sm font-medium text-white">{f.scenario_title}</td>
                  <td className="px-4 py-3">
                    <span className={`text-sm font-semibold ${f.inconsistency_rate > 0.5 ? "text-red-400" : "text-amber-400"}`}>
                      %{Math.round(f.inconsistency_rate * 100)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {f.recent_results.map((r, i) => (
                        <span
                          key={i}
                          className={`inline-block h-3 w-3 rounded-full ${resultColor[r] ?? "bg-slate-600"}`}
                          title={r}
                        />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
    </div>
  );
}
