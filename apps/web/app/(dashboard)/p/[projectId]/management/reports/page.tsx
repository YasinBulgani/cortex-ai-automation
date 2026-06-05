"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  useExecutionSummary,
  useReleaseReport,
  useManagementRuns,
  useManagementDefects,
  useRegressionSets,
  useReleaseSignoffs,
  useCreateReleaseSignoff,
  useManagementRunTrend,
  useManagementCases,
  type TestRun,
  type ReleaseChecklistItem,
  type ReleaseSignoff,
  type RegressionSet,
  type DefectLink,
  type RunTrendPoint,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";

// ─── Constants ──────────────────────────────────────────────────────────────

type ReportTab = "execution" | "regression" | "defects" | "release" | "tester" | "coverage";

const REPORT_TABS: { id: ReportTab; label: string }[] = [
  { id: "execution",  label: "Yürütme Özeti"      },
  { id: "regression", label: "Regresyon Raporu"   },
  { id: "defects",    label: "Defekt Özeti"        },
  { id: "release",    label: "Sürüm Hazırlığı"    },
  { id: "tester",     label: "Tester Performansı" },
  { id: "coverage",   label: "Modül Kapsamı"      },
];

const RUN_STATUS_DOT: Record<string, string> = {
  in_progress: "bg-blue-500 animate-pulse",
  completed:   "bg-emerald-500",
  failed:      "bg-red-500",
  not_started: "bg-slate-600",
};

const SEVERITY_CONFIG: Record<string, { label: string; color: string; bar: string }> = {
  critical: { label: "Critical", color: "text-red-400",    bar: "bg-red-500"    },
  high:     { label: "High",     color: "text-orange-400", bar: "bg-orange-500" },
  medium:   { label: "Medium",   color: "text-amber-400",  bar: "bg-amber-500"  },
  low:      { label: "Low",      color: "text-sky-400",    bar: "bg-sky-500"    },
  trivial:  { label: "Trivial",  color: "text-slate-400",  bar: "bg-slate-500"  },
};

const DATE_RANGE_OPTIONS = [
  { label: "Son 7 gün",  value: 7  },
  { label: "Son 30 gün", value: 30 },
  { label: "Son 90 gün", value: 90 },
];

const DAY_LABELS = ["G-6", "G-5", "G-4", "G-3", "G-2", "Dün", "Bugün"];

// ─── Helpers ────────────────────────────────────────────────────────────────

function downloadCSV(rows: { metric: string; value: string | number }[], filename: string) {
  const header = "Metric,Value\n";
  const body = rows.map(r => `"${r.metric}","${r.value}"`).join("\n");
  const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Small Components ────────────────────────────────────────────────────────

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-4">
      <p className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold text-fg">{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-fg-subtle">{sub}</p>}
    </div>
  );
}

function SkeletonRows({ n = 4 }: { n?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="h-12 w-full animate-pulse rounded-xl bg-white/[0.04]" />
      ))}
    </div>
  );
}

function ErrorState({ msg = "Veri yüklenemedi — lütfen sayfayı yenileyin" }: { msg?: string }) {
  return (
    <div className="flex items-center justify-center py-16">
      <p className="text-sm text-red-400/80">{msg}</p>
    </div>
  );
}

// ─── Pass Rate Area Chart ─────────────────────────────────────────────────────

interface TrendPoint { label: string; value: number; }

function PassRateAreaChart({ points }: { points: TrendPoint[] }) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; point: TrendPoint } | null>(null);

  const W = 480;
  const H = 100;
  const PAD_L = 32;
  const PAD_R = 12;
  const PAD_T = 12;
  const PAD_B = 24;
  const chartW = W - PAD_L - PAD_R;
  const chartH = H - PAD_T - PAD_B;

  const maxVal = Math.max(...points.map(p => p.value), 100);
  const minVal = 0;

  const toX = useCallback((i: number) =>
    PAD_L + (points.length > 1 ? (i / (points.length - 1)) * chartW : chartW / 2),
    [chartW, points.length],
  );
  const toY = useCallback((v: number) =>
    PAD_T + chartH - ((v - minVal) / (maxVal - minVal)) * chartH,
    [chartH, maxVal, minVal],
  );

  const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i).toFixed(1)} ${toY(p.value).toFixed(1)}`).join(" ");
  const areaD = points.length > 0
    ? `${pathD} L ${toX(points.length - 1).toFixed(1)} ${(PAD_T + chartH).toFixed(1)} L ${toX(0).toFixed(1)} ${(PAD_T + chartH).toFixed(1)} Z`
    : "";

  const yTicks = [0, 25, 50, 75, 100];

  if (points.length === 0) {
    return <p className="py-6 text-center text-[12px] text-fg-muted">Trend verisi bulunamadı</p>;
  }

  return (
    <div className="relative w-full select-none">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        className="w-full overflow-visible"
        style={{ height: "120px" }}
        onMouseLeave={() => setTooltip(null)}
      >
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.03" />
          </linearGradient>
        </defs>

        {/* Y grid lines */}
        {yTicks.map(tick => {
          const y = toY(tick);
          return (
            <g key={tick}>
              <line x1={PAD_L} y1={y} x2={W - PAD_R} y2={y}
                stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
              <text x={PAD_L - 4} y={y + 3} textAnchor="end" fontSize="7" fill="rgba(148,163,184,0.6)">{tick}</text>
            </g>
          );
        })}

        {/* Area fill */}
        {areaD && <path d={areaD} fill="url(#areaGrad)" />}

        {/* Line */}
        {pathD && (
          <path d={pathD} fill="none" stroke="#10b981" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        )}

        {/* X-axis labels + hover targets */}
        {points.map((p, i) => {
          const x = toX(i);
          const y = toY(p.value);
          const showLabel = points.length <= 10 || i % Math.ceil(points.length / 8) === 0 || i === points.length - 1;
          return (
            <g key={i}
              onMouseEnter={() => setTooltip({ x, y, point: p })}
            >
              {/* Invisible wide hit target */}
              <rect
                x={x - (chartW / (points.length * 2))}
                y={PAD_T}
                width={chartW / points.length}
                height={chartH}
                fill="transparent"
              />
              {/* Dot */}
              <circle cx={x} cy={y} r={tooltip?.point === p ? 4 : 2.5}
                fill={tooltip?.point === p ? "#10b981" : "#059669"}
                stroke={tooltip?.point === p ? "rgba(16,185,129,0.4)" : "none"}
                strokeWidth={tooltip?.point === p ? 4 : 0}
              />
              {/* X label */}
              {showLabel && (
                <text x={x} y={PAD_T + chartH + 14} textAnchor="middle" fontSize="7" fill="rgba(148,163,184,0.7)">
                  {p.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 rounded-lg border border-emerald-500/30 bg-surface-raised px-2.5 py-1.5 shadow-elevated"
          style={{
            left: `${(tooltip.x / W) * 100}%`,
            top: `${(tooltip.y / H) * 100}%`,
            transform: "translate(-50%, -120%)",
          }}
        >
          <p className="text-[11px] font-semibold text-emerald-400">{tooltip.point.value}%</p>
          <p className="text-[9px] text-fg-subtle">{tooltip.point.label}</p>
        </div>
      )}
    </div>
  );
}

// ─── Legacy bar chart (kept for fallback) ────────────────────────────────────

function TrendChart({ trendData }: { trendData: number[] }) {
  const points: TrendPoint[] = trendData.map((val, i) => ({
    label: DAY_LABELS[i] ?? `G-${trendData.length - 1 - i}`,
    value: val,
  }));
  return <PassRateAreaChart points={points} />;
}

// ─── Pass/Fail/Blocked/NotRun Bar Chart ───────────────────────────────────────

function ExecutionBarChart({
  passed, failed, blocked, notRun,
}: {
  passed: number; failed: number; blocked: number; notRun: number;
}) {
  const total = passed + failed + blocked + notRun || 1;
  const bars = [
    { label: "Geçti",     count: passed,  heightPct: (passed  / total) * 100, color: "bg-emerald-500", text: "text-emerald-400" },
    { label: "Başarısız", count: failed,  heightPct: (failed  / total) * 100, color: "bg-red-500",     text: "text-red-400"     },
    { label: "Engellendi",count: blocked, heightPct: (blocked / total) * 100, color: "bg-amber-500",   text: "text-amber-400"   },
    { label: "Bekliyor",  count: notRun,  heightPct: (notRun  / total) * 100, color: "bg-slate-600",   text: "text-slate-400"   },
  ];

  return (
    <div className="flex items-end gap-6 pt-4 pb-2 pl-2">
      {bars.map(({ label, count, heightPct, color, text }) => (
        <div key={label} className="flex flex-col items-center gap-2">
          <span className={`text-[13px] font-semibold ${text}`}>{count}</span>
          <div className="relative flex items-end" style={{ height: "80px", width: "36px" }}>
            <div
              className={`w-full rounded-t-md ${color} transition-all duration-500`}
              style={{ height: `${Math.max(heightPct, 3)}%` }}
            />
          </div>
          <span className="text-[10px] text-fg-subtle">{label}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Checklist Row ────────────────────────────────────────────────────────────

function ChecklistRow({ item }: { item: ReleaseChecklistItem }) {
  const dot =
    item.status === "pass"  ? "bg-emerald-500" :
    item.status === "warn"  ? "bg-amber-500"   :
    item.status === "fail"  ? "bg-red-500"      : "bg-slate-600";
  const bar =
    item.status === "pass" ? "bg-emerald-500" :
    item.status === "warn" ? "bg-amber-500"   : "bg-red-500";
  const pct =
    item.status === "pass" ? 100 :
    item.status === "warn" ? 60  : 25;

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-white/[0.02] px-4 py-3">
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
      <span className="flex-1 text-[13px] text-fg">{item.label}</span>
      <div className="flex items-center gap-2 w-40">
        <div className="h-1 flex-1 rounded-full bg-white/[0.06] overflow-hidden">
          <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[11px] text-fg-subtle w-12 text-right truncate">{item.metric}</span>
      </div>
    </div>
  );
}

// ─── Execution Summary Tab ────────────────────────────────────────────────────

function ExecutionSummaryTab({
  summary, runs, filteredRuns, sumLoading, sumError, runsLoading, runsError, projectId, trendData, trendPoints,
}: {
  summary: any; runs: TestRun[] | undefined; filteredRuns: TestRun[];
  sumLoading: boolean; sumError: boolean;
  runsLoading: boolean; runsError: boolean;
  projectId: string | null;
  trendData: number[];
  trendPoints?: TrendPoint[];
}) {
  const passed  = summary?.passed  ?? 0;
  const failed  = summary?.failed  ?? 0;
  const blocked = summary?.blocked ?? 0;
  const notRun  = summary?.not_run ?? 0;
  const execTotal = passed + failed + blocked + notRun;
  const recentRuns = filteredRuns.slice(0, 8);

  return (
    <div className="space-y-6">
      {/* Execution Bar Chart */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <h2 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Pass / Fail / Blocked / Not Run</h2>
        {sumLoading ? <SkeletonRows n={2} /> : sumError ? <ErrorState /> : execTotal === 0 ? (
          <p className="text-[13px] text-fg-subtle">Henüz execution verisi yok.</p>
        ) : (
          <>
            <ExecutionBarChart passed={passed} failed={failed} blocked={blocked} notRun={notRun} />
            {/* Horizontal stacked bar */}
            <div className="mt-4 flex h-2.5 overflow-hidden rounded-full gap-px">
              {[
                { n: passed,  c: "bg-emerald-500" },
                { n: failed,  c: "bg-red-500"     },
                { n: blocked, c: "bg-amber-500"   },
                { n: notRun,  c: "bg-white/[0.08]"},
              ].map(({ n, c }, i) => n > 0 ? (
                <div key={i} className={`${c} h-full`} style={{ width: `${(n / execTotal) * 100}%` }} />
              ) : null)}
            </div>
          </>
        )}
      </div>

      {/* Pass Rate Trend */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Pass Rate Trendi</h2>
          <span className="text-[11px] text-fg-subtle">
            {trendPoints && trendPoints.length > 0 ? `Son ${trendPoints.length} koşum` : "Son 7 gün"}
          </span>
        </div>
        {trendPoints && trendPoints.length > 0
          ? <PassRateAreaChart points={trendPoints} />
          : <TrendChart trendData={trendData} />
        }
      </div>

      {/* Recent Runs Table */}
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Son Runlar</h2>
        </div>
        {runsLoading ? (
          <div className="p-6"><SkeletonRows /></div>
        ) : runsError ? (
          <ErrorState />
        ) : recentRuns.length === 0 ? (
          <p className="px-5 py-6 text-[13px] text-fg-subtle">Henüz run yok.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["", "Run Adı", "Durum", "İlerleme", "Tarih", ""].map((h, idx) => (
                  <th key={idx} className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run: TestRun) => {
                const dot = RUN_STATUS_DOT[run.status] ?? "bg-slate-600";
                const snap = run.scope_snapshot as { passed?: number; failed?: number; blocked?: number };
                const runPassed  = snap?.passed  ?? 0;
                const runFailed  = snap?.failed  ?? 0;
                const runBlocked = snap?.blocked ?? 0;
                const runTotal   = runPassed + runFailed + runBlocked;
                return (
                  <tr key={run.id} className="border-b border-border hover:bg-white/[0.04] transition-colors">
                    <td className="w-6 pl-4 py-3">
                      <span className={`inline-block h-1.5 w-1.5 rounded-full ${dot}`} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[13px] text-fg">{run.name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] text-fg-muted">{run.status}</span>
                    </td>
                    <td className="px-4 py-3 w-32">
                      {runTotal > 0 ? (
                        <div className="flex h-1.5 w-full overflow-hidden rounded-full gap-px">
                          {runPassed > 0 && <div className="bg-emerald-500 h-full" style={{ width: `${(runPassed / runTotal) * 100}%` }} />}
                          {runFailed > 0 && <div className="bg-red-500 h-full" style={{ width: `${(runFailed / runTotal) * 100}%` }} />}
                          {runBlocked > 0 && <div className="bg-amber-500 h-full" style={{ width: `${(runBlocked / runTotal) * 100}%` }} />}
                        </div>
                      ) : (
                        <div className="h-1.5 w-full rounded-full bg-white/[0.06]" />
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] text-fg-subtle">
                        {run.started_at
                          ? new Date(run.started_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
                          : "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {projectId && (
                        <Link href={`/p/${projectId}/management/runs/${run.id}/execute`}
                          className="text-[11px] text-brand-fg hover:opacity-80 transition-opacity">
                          Execute
                        </Link>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Regression Report Tab ────────────────────────────────────────────────────

function RegressionReportTab({
  regressionSets, regressionLoading, regressionError, runs,
}: {
  regressionSets: RegressionSet[] | undefined;
  regressionLoading: boolean;
  regressionError: boolean;
  runs: TestRun[] | undefined;
}) {
  const sets = regressionSets ?? [];

  const getLastRunStatus = (setId: string): string => {
    if (!runs) return "—";
    const relatedRuns = (runs ?? []).filter(r => r.name?.toLowerCase().includes("regress"));
    if (!relatedRuns.length) return "—";
    return relatedRuns[0].status;
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3 flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Regresyon Setleri</h2>
          <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-subtle">{sets.length} set</span>
        </div>
        {regressionLoading ? (
          <div className="p-6"><SkeletonRows /></div>
        ) : regressionError ? (
          <ErrorState />
        ) : sets.length === 0 ? (
          <p className="px-5 py-6 text-[13px] text-fg-subtle">Henüz regresyon seti tanımlanmamış.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["Set Adı", "Case Sayısı", "Son Run Durumu", "Oluşturulma"].map((h, i) => (
                  <th key={i} className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sets.map((set: RegressionSet) => {
                const lastStatus = getLastRunStatus(set.id);
                const statusColor =
                  lastStatus === "completed" ? "text-emerald-400" :
                  lastStatus === "failed"    ? "text-red-400"     :
                  lastStatus === "in_progress" ? "text-blue-400"  : "text-fg-subtle";
                return (
                  <tr key={set.id} className="border-b border-border hover:bg-white/[0.04] transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-[13px] text-fg">{set.name}</p>
                        {set.description && <p className="text-[11px] text-fg-subtle mt-0.5 truncate max-w-xs">{set.description}</p>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[13px] text-fg-muted">{set.cases.length}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[12px] font-medium ${statusColor}`}>{lastStatus}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] text-fg-subtle">
                        {set.created_at
                          ? new Date(set.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
                          : "—"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Summary stats */}
      {sets.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Toplam Set" value={sets.length} sub="tanımlı regresyon seti" />
          <KpiCard label="Toplam Case" value={sets.reduce((acc, s) => acc + s.cases.length, 0)} sub="regresyon kapsamı" />
          <KpiCard label="Son Run" value={(runs ?? []).filter(r => r.status === "in_progress").length > 0 ? "Aktif" : "Tamamlandı"} sub="run durumu" />
        </div>
      )}
    </div>
  );
}

// ─── Defect Summary Tab ───────────────────────────────────────────────────────

function DefectSummaryTab({
  defects,
}: {
  defects: DefectLink[] | undefined;
}) {
  const allDefects = defects ?? [];
  const openDefects = allDefects.filter(d => !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase()));

  const severityCounts: Record<string, number> = {};
  for (const d of allDefects) {
    const sev = (d.severity ?? "unknown").toLowerCase();
    severityCounts[sev] = (severityCounts[sev] ?? 0) + 1;
  }

  const maxCount = Math.max(...Object.values(severityCounts), 1);
  const orderedSeverities = ["critical", "high", "medium", "low", "trivial"];

  return (
    <div className="space-y-6">
      {/* Severity breakdown chart */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Severity Dağılımı</h2>
        {allDefects.length === 0 ? (
          <p className="text-[13px] text-fg-subtle">Defect verisi yok.</p>
        ) : (
          <div className="space-y-3">
            {orderedSeverities.map(sev => {
              const count = severityCounts[sev] ?? 0;
              if (count === 0 && !severityCounts[sev]) return null;
              const cfg = SEVERITY_CONFIG[sev] ?? { label: sev, color: "text-slate-400", bar: "bg-slate-500" };
              const widthPct = (count / maxCount) * 100;
              return (
                <div key={sev} className="flex items-center gap-3">
                  <span className={`w-16 text-[11px] font-medium shrink-0 ${cfg.color}`}>{cfg.label}</span>
                  <div className="flex-1 h-2 rounded-full bg-white/[0.06] overflow-hidden">
                    <div className={`h-full rounded-full ${cfg.bar} transition-all duration-500`} style={{ width: `${widthPct}%` }} />
                  </div>
                  <span className="w-8 text-right text-[12px] text-fg-muted shrink-0">{count}</span>
                </div>
              );
            })}
            {/* unknowns */}
            {Object.keys(severityCounts)
              .filter(k => !orderedSeverities.includes(k))
              .map(sev => {
                const count = severityCounts[sev];
                const widthPct = (count / maxCount) * 100;
                return (
                  <div key={sev} className="flex items-center gap-3">
                    <span className="w-16 text-[11px] font-medium shrink-0 text-slate-400 capitalize">{sev}</span>
                    <div className="flex-1 h-2 rounded-full bg-white/[0.06] overflow-hidden">
                      <div className="h-full rounded-full bg-slate-500 transition-all duration-500" style={{ width: `${widthPct}%` }} />
                    </div>
                    <span className="w-8 text-right text-[12px] text-fg-muted shrink-0">{count}</span>
                  </div>
                );
              })}
          </div>
        )}
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-3 gap-3">
        <KpiCard label="Toplam Defect" value={allDefects.length} sub="tüm zamanlar" />
        <KpiCard label="Açık" value={openDefects.length} sub="çözülmemiş" />
        <KpiCard label="Kapalı" value={allDefects.length - openDefects.length} sub="çözüldü/kapatıldı" />
      </div>

      {/* Defect list */}
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Defect Listesi</h2>
        </div>
        {allDefects.length === 0 ? (
          <p className="px-5 py-6 text-[13px] text-fg-subtle">Defect kaydı yok.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["Key", "Başlık", "Severity", "Durum", "Retest"].map((h, i) => (
                  <th key={i} className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {allDefects.slice(0, 20).map((d: DefectLink) => {
                const sevCfg = SEVERITY_CONFIG[(d.severity ?? "").toLowerCase()] ?? { label: d.severity, color: "text-slate-400" };
                const isOpen = !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase());
                return (
                  <tr key={d.id} className="border-b border-border hover:bg-white/[0.04] transition-colors">
                    <td className="px-4 py-3">
                      {d.url ? (
                        <a href={d.url} target="_blank" rel="noopener noreferrer"
                          className="text-[12px] text-brand-fg hover:opacity-80 font-mono">
                          {d.external_key}
                        </a>
                      ) : (
                        <span className="text-[12px] text-fg-muted font-mono">{d.external_key}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <span className="text-[13px] text-fg truncate block">{d.title}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-[11px] font-medium capitalize ${sevCfg.color}`}>{d.severity ?? "—"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${isOpen ? "text-amber-400" : "text-emerald-400"}`}>
                        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${isOpen ? "bg-amber-500" : "bg-emerald-500"}`} />
                        {d.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[11px] text-fg-subtle capitalize">{d.retest_status ?? "—"}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ─── Release Readiness Tab ────────────────────────────────────────────────────

function ReleaseReadinessTab({
  checklist, relLoading, relError,
  passRate, openDefects, signoffs, createSignoff,
}: {
  checklist: ReleaseChecklistItem[];
  relLoading: boolean;
  relError: boolean;
  passRate: number;
  openDefects: number;
  signoffs: ReleaseSignoff[] | undefined;
  createSignoff: any;
}) {
  const [signoffRole,     setSignoffRole]     = useState("QA Lead");
  const [signoffComment,  setSignoffComment]  = useState("");
  const [signoffDecision, setSignoffDecision] = useState<"approved" | "rejected">("approved");

  const passedChecks = checklist.filter(c => c.status === "pass").length;
  const totalChecks  = checklist.length;

  // Derived readiness score (0-100)
  const checklistScore = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 100) : 0;
  const defectPenalty  = Math.min(openDefects * 5, 40);
  const passRateBonus  = Math.round(passRate * 0.4);
  const readinessScore = Math.max(0, Math.min(100, checklistScore + passRateBonus - defectPenalty));

  const scoreColor =
    readinessScore >= 80 ? "text-emerald-400" :
    readinessScore >= 50 ? "text-amber-400"   : "text-red-400";
  const scoreBar =
    readinessScore >= 80 ? "bg-emerald-500" :
    readinessScore >= 50 ? "bg-amber-500"   : "bg-red-500";

  return (
    <div className="space-y-6">
      {/* Score card */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Hazırlık Skoru</h2>
          <span className={`text-3xl font-bold ${scoreColor}`}>{readinessScore}<span className="text-lg">/100</span></span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-700 ${scoreBar}`} style={{ width: `${readinessScore}%` }} />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-center">
          <div>
            <p className="text-[10px] text-fg-subtle">Checklist</p>
            <p className="text-[13px] font-semibold text-fg">{passedChecks}/{totalChecks}</p>
          </div>
          <div>
            <p className="text-[10px] text-fg-subtle">Pass Rate</p>
            <p className="text-[13px] font-semibold text-fg">{passRate.toFixed(1)}%</p>
          </div>
          <div>
            <p className="text-[10px] text-fg-subtle">Açık Defect</p>
            <p className={`text-[13px] font-semibold ${openDefects > 0 ? "text-red-400" : "text-emerald-400"}`}>{openDefects}</p>
          </div>
        </div>
      </div>

      {/* Checklist */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Release Checklist</h2>
          {!relLoading && totalChecks > 0 && (
            <span className="text-[11px] text-fg-subtle">{passedChecks}/{totalChecks} geçti</span>
          )}
        </div>
        {relLoading ? (
          <SkeletonRows />
        ) : relError ? (
          <ErrorState />
        ) : checklist.length === 0 ? (
          <p className="text-[13px] text-fg-subtle">Checklist verisi yok.</p>
        ) : (
          <div className="space-y-2">
            {checklist.map((item, i) => <ChecklistRow key={i} item={item} />)}
          </div>
        )}
      </div>

      {/* Release Signoff */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-fg">Release Signoff</h2>
          <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-subtle">
            {(signoffs ?? []).length} imza
          </span>
        </div>

        {(signoffs ?? []).length > 0 && (
          <div className="mb-4 space-y-2">
            {(signoffs as ReleaseSignoff[]).map(s => (
              <div key={s.id} className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
                s.decision === "approved"
                  ? "border-emerald-500/20 bg-emerald-500/5"
                  : "border-red-500/20 bg-red-500/5"
              }`}>
                <span className={`h-2 w-2 rounded-full shrink-0 ${s.decision === "approved" ? "bg-emerald-500" : "bg-red-500"}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium text-fg">{s.signed_by ?? "İmzalandı"}</p>
                  {s.comment && <p className="text-[11px] text-fg-subtle truncate">{s.comment}</p>}
                </div>
                <span className="text-[10px] text-fg-subtle">
                  {new Date(s.signed_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                </span>
                <span className={`text-[11px] font-semibold ${s.decision === "approved" ? "text-emerald-400" : "text-red-400"}`}>
                  {s.decision === "approved" ? "Onaylandı" : "Reddedildi"}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="space-y-3 rounded-xl border border-border bg-surface-overlay p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Yeni İmza</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-[10px] text-fg-subtle">Rol</label>
              <select value={signoffRole} onChange={e => setSignoffRole(e.target.value)}
                className="w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40">
                {["QA Lead", "Dev Lead", "Product Owner", "Release Manager", "Security", "CTO"].map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] text-fg-subtle">Karar</label>
              <select value={signoffDecision} onChange={e => setSignoffDecision(e.target.value as "approved" | "rejected")}
                className="w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40">
                <option value="approved">Onaylandı</option>
                <option value="rejected">Reddedildi</option>
              </select>
            </div>
          </div>
          <textarea value={signoffComment} onChange={e => setSignoffComment(e.target.value)}
            rows={2} placeholder="Opsiyonel yorum…"
            className="w-full resize-none rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/40" />
          <div className="flex justify-end">
            <button type="button"
              onClick={async () => {
                await createSignoff.mutateAsync({
                  decision: signoffDecision,
                  comment: `[${signoffRole}] ${signoffComment}`.trim() || undefined,
                });
                setSignoffComment("");
              }}
              disabled={createSignoff.isPending}
              className={`rounded-xl px-4 py-2 text-[13px] font-semibold text-white transition-colors disabled:opacity-40 ${
                signoffDecision === "approved" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-red-600 hover:bg-red-500"
              }`}>
              {createSignoff.isPending ? "İmzalanıyor…" : signoffDecision === "approved" ? "Onayla" : "Reddet"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Tester Performance Tab ──────────────────────────────────────────────────

type SortKey = "assigned" | "completed" | "passRate";
type SortDir = "asc" | "desc";

function TesterPerformanceTab({
  cases,
  runs,
  loading,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  cases: any[] | undefined;
  runs: TestRun[] | undefined;
  loading: boolean;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("assigned");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const testerRows = useMemo(() => {
    if (!cases) return [];
    const map = new Map<string, { assigned: number; completed: number; passed: number }>();

    for (const tc of cases) {
      const key = (tc.owner_id ?? tc.assigned_to ?? "Atanmamış").trim() || "Atanmamış";
      const row = map.get(key) ?? { assigned: 0, completed: 0, passed: 0 };
      row.assigned += 1;
      if (["passed", "failed", "blocked"].includes(tc.last_run_status ?? "")) row.completed += 1;
      if (tc.last_run_status === "passed") row.passed += 1;
      map.set(key, row);
    }

    // Add run-level tester info
    if (runs) {
      for (const run of runs) {
        const key = (run.assigned_to ?? "").trim();
        if (!key) continue;
        const row = map.get(key) ?? { assigned: 0, completed: 0, passed: 0 };
        if (!map.has(key)) map.set(key, row);
      }
    }

    return [...map.entries()].map(([tester, data]) => ({
      tester,
      assigned: data.assigned,
      completed: data.completed,
      passRate: data.completed > 0 ? Math.round((data.passed / data.completed) * 100) : 0,
      active: (runs ?? []).some(r => r.status === "in_progress" && r.assigned_to === tester),
    }));
  }, [cases, runs]);

  const sorted = useMemo(() => {
    return [...testerRows].sort((a, b) => {
      const diff = a[sortKey] - b[sortKey];
      return sortDir === "asc" ? diff : -diff;
    });
  }, [testerRows, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const arrow = (key: SortKey) => {
    if (sortKey !== key) return <span className="text-fg-subtle">↕</span>;
    return <span className="text-emerald-400">{sortDir === "asc" ? "↑" : "↓"}</span>;
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3 flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Tester Performansı</h2>
          <span className="text-[10px] text-fg-subtle">{sorted.length} tester</span>
        </div>
        {loading ? (
          <div className="p-6"><SkeletonRows /></div>
        ) : sorted.length === 0 ? (
          <p className="px-5 py-6 text-[13px] text-fg-subtle">Case veya tester ataması bulunamadı.</p>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Tester</th>
                <th
                  className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle cursor-pointer select-none"
                  onClick={() => toggleSort("assigned")}
                >
                  Atanan {arrow("assigned")}
                </th>
                <th
                  className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle cursor-pointer select-none"
                  onClick={() => toggleSort("completed")}
                >
                  Tamamlanan {arrow("completed")}
                </th>
                <th
                  className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle cursor-pointer select-none"
                  onClick={() => toggleSort("passRate")}
                >
                  Geçme % {arrow("passRate")}
                </th>
                <th className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle">Aktif</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(row => (
                <tr key={row.tester} className="border-b border-border hover:bg-white/[0.04] transition-colors">
                  <td className="px-4 py-3 text-[13px] text-fg">{row.tester}</td>
                  <td className="px-4 py-3 text-[13px] text-fg-muted">{row.assigned}</td>
                  <td className="px-4 py-3 text-[13px] text-fg-muted">{row.completed}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[12px] font-semibold ${
                      row.passRate >= 80 ? "text-emerald-400" :
                      row.passRate >= 50 ? "text-amber-400" : "text-red-400"
                    }`}>{row.passRate}%</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-block h-2 w-2 rounded-full ${row.active ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {sorted.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Toplam Tester" value={sorted.length} sub="case atanmış" />
          <KpiCard
            label="Ort. Pass Rate"
            value={`${Math.round(sorted.reduce((s, r) => s + r.passRate, 0) / sorted.length)}%`}
            sub="tüm testerlar"
          />
          <KpiCard
            label="Aktif Tester"
            value={sorted.filter(r => r.active).length}
            sub="şu anda çalışıyor"
          />
        </div>
      )}
    </div>
  );
}

// ─── Module Coverage Tab ──────────────────────────────────────────────────────

function ModuleCoverageTab({
  cases,
  loading,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  cases: any[] | undefined;
  loading: boolean;
}) {
  const suiteRows = useMemo(() => {
    if (!cases) return [];
    const map = new Map<string, { total: number; passed: number; failed: number; blocked: number }>();
    for (const tc of cases) {
      const key = (tc.custom_fields?.component ?? tc.custom_fields?.module ?? tc.suite_id ?? "Genel").trim() || "Genel";
      const row = map.get(key) ?? { total: 0, passed: 0, failed: 0, blocked: 0 };
      row.total += 1;
      if (tc.last_run_status === "passed")  row.passed  += 1;
      if (tc.last_run_status === "failed")  row.failed  += 1;
      if (tc.last_run_status === "blocked") row.blocked += 1;
      map.set(key, row);
    }
    return [...map.entries()]
      .map(([suite, data]) => ({
        suite,
        total: data.total,
        passed: data.passed,
        failed: data.failed,
        blocked: data.blocked,
        passRate: data.total > 0 ? Math.round((data.passed / data.total) * 100) : 0,
        coverage: data.total > 0 ? Math.round(((data.passed + data.failed + data.blocked) / data.total) * 100) : 0,
      }))
      .sort((a, b) => b.total - a.total);
  }, [cases]);

  const maxTotal = Math.max(...suiteRows.map(r => r.total), 1);

  const W = 400;
  const ROW_H = 32;
  const PAD_L = 120;
  const PAD_R = 60;
  const chartW = W - PAD_L - PAD_R;
  const H = Math.max(suiteRows.length * ROW_H + 20, 60);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Suite / Modül Bazlı Kapsam</h2>
        {loading ? (
          <SkeletonRows />
        ) : suiteRows.length === 0 ? (
          <p className="text-[13px] text-fg-subtle">Case bulunamadı.</p>
        ) : (
          <div className="overflow-x-auto">
            <svg
              viewBox={`0 0 ${W} ${H}`}
              className="w-full"
              style={{ height: `${H}px`, maxHeight: "480px" }}
            >
              {suiteRows.map((row, i) => {
                const y = i * ROW_H + 10;
                const barW = (row.total / maxTotal) * chartW;
                const passW = row.total > 0 ? (row.passed / row.total) * barW : 0;
                const failW = row.total > 0 ? (row.failed / row.total) * barW : 0;
                const blockW = row.total > 0 ? (row.blocked / row.total) * barW : 0;
                const label = row.suite.length > 16 ? row.suite.slice(0, 14) + "…" : row.suite;
                return (
                  <g key={row.suite}>
                    <text
                      x={PAD_L - 6}
                      y={y + ROW_H / 2 + 4}
                      textAnchor="end"
                      fontSize="10"
                      fill="rgba(148,163,184,0.8)"
                    >
                      {label}
                    </text>
                    {/* background bar */}
                    <rect x={PAD_L} y={y + 4} width={barW} height={ROW_H - 12} rx="3" fill="rgba(255,255,255,0.05)" />
                    {/* passed */}
                    <rect x={PAD_L} y={y + 4} width={passW} height={ROW_H - 12} rx="3" fill="#10b981" opacity="0.8" />
                    {/* failed */}
                    <rect x={PAD_L + passW} y={y + 4} width={failW} height={ROW_H - 12} rx="3" fill="#ef4444" opacity="0.8" />
                    {/* blocked */}
                    <rect x={PAD_L + passW + failW} y={y + 4} width={blockW} height={ROW_H - 12} rx="3" fill="#f59e0b" opacity="0.8" />
                    {/* pass rate label */}
                    <text
                      x={PAD_L + barW + 8}
                      y={y + ROW_H / 2 + 4}
                      fontSize="10"
                      fill={row.passRate >= 80 ? "#34d399" : row.passRate >= 50 ? "#fbbf24" : "#f87171"}
                    >
                      {row.passRate}%
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Legend */}
            <div className="mt-3 flex items-center gap-4 text-[10px] text-fg-subtle">
              <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-3 rounded-sm bg-emerald-500" />Geçti</span>
              <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-3 rounded-sm bg-red-500" />Başarısız</span>
              <span className="flex items-center gap-1.5"><span className="inline-block h-2 w-3 rounded-sm bg-amber-500" />Engellendi</span>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      {suiteRows.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
          <div className="border-b border-border px-5 py-3">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Kapsam Detayı</h2>
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["Suite / Modül", "Toplam", "Geçti", "Başarısız", "Kapsam %", "Pass %"].map((h, i) => (
                  <th key={i} className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-fg-subtle">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {suiteRows.map(row => (
                <tr key={row.suite} className="border-b border-border hover:bg-white/[0.04] transition-colors">
                  <td className="px-4 py-3 text-[13px] text-fg">{row.suite}</td>
                  <td className="px-4 py-3 text-[13px] text-fg-muted">{row.total}</td>
                  <td className="px-4 py-3 text-[12px] text-emerald-400">{row.passed}</td>
                  <td className="px-4 py-3 text-[12px] text-red-400">{row.failed}</td>
                  <td className="px-4 py-3 text-[12px] text-fg-muted">{row.coverage}%</td>
                  <td className="px-4 py-3">
                    <span className={`text-[12px] font-semibold ${
                      row.passRate >= 80 ? "text-emerald-400" :
                      row.passRate >= 50 ? "text-amber-400" : "text-red-400"
                    }`}>{row.passRate}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ManagementReportsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const [activeTab,       setActiveTab]       = useState<ReportTab>("execution");
  const [dateRange,       setDateRange]       = useState(30);
  const [moduleFilter,    setModuleFilter]    = useState("");
  const [platformFilter,  setPlatformFilter]  = useState("");

  const { data: summary,        isLoading: sumLoading,        isError: sumError        } = useExecutionSummary(mpid || undefined);
  const { data: release,        isLoading: relLoading,        isError: relError        } = useReleaseReport(mpid || undefined);
  const { data: runs,           isLoading: runsLoading,       isError: runsError       } = useManagementRuns(mpid || undefined);
  const { data: defects                                                                  } = useManagementDefects(mpid || undefined);
  const { data: regressionSets, isLoading: regressionLoading, isError: regressionError } = useRegressionSets(mpid || undefined);
  const { data: signoffs }                                                                 = useReleaseSignoffs(mpid || undefined);
  const createSignoff                                                                     = useCreateReleaseSignoff(mpid || "");
  const { data: runTrend }                                                                = useManagementRunTrend(mpid || undefined);
  const { data: casesData, isLoading: casesLoading }                                      = useManagementCases(mpid || undefined);

  const passRate    = summary?.pass_rate_pct ?? 0;
  const totalCases  = summary?.total ?? 0;
  const openDefects = (defects ?? []).filter(d => !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase())).length;
  const activeRuns  = (runs ?? []).filter(r => r.status === "in_progress").length;

  // Filtered runs: dateRange (days) + moduleFilter + platformFilter
  const filteredRuns = useMemo(() => {
    if (!runs) return [];
    const now = Date.now();
    const cutoffMs = dateRange * 24 * 60 * 60 * 1000;
    return runs.filter(r => {
      // Date filter: use created_at or started_at if available
      const dateField = r.created_at || r.started_at;
      if (dateField) {
        const age = now - new Date(dateField).getTime();
        if (age > cutoffMs) return false;
      }
      // Module filter: match run name
      if (moduleFilter && !r.name.toLowerCase().includes(moduleFilter.toLowerCase())) return false;
      // Platform filter: match against platform field if exists
      if (platformFilter) {
        const platform = (r.environment ?? "").toLowerCase();
        if (platform && !platform.includes(platformFilter.toLowerCase())) return false;
      }
      return true;
    });
  }, [runs, dateRange, moduleFilter, platformFilter]);

  const checklist: ReleaseChecklistItem[] = release?.checklist ?? [];

  // Real run trend points from the API.
  const trendPoints: TrendPoint[] = useMemo(() => {
    if (!runTrend || runTrend.length === 0) return [];
    const sorted = [...runTrend]
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .slice(-30);
    return sorted.map((p: RunTrendPoint) => ({
      label: new Date(p.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" }),
      value: Math.round(p.pass_rate_pct),
    }));
  }, [runTrend]);
  const trendData = trendPoints.map(point => point.value);

  function handleCSVExport() {
    const passed  = summary?.passed  ?? 0;
    const failed  = summary?.failed  ?? 0;
    const blocked = summary?.blocked ?? 0;
    const notRun  = summary?.not_run ?? 0;
    downloadCSV(
      [
        { metric: "Toplam Case",  value: totalCases },
        { metric: "Pass Rate",    value: `${passRate.toFixed(1)}%` },
        { metric: "Passed",       value: passed  },
        { metric: "Failed",       value: failed  },
        { metric: "Blocked",      value: blocked },
        { metric: "Not Run",      value: notRun  },
        { metric: "Açık Defect",  value: openDefects },
        { metric: "Aktif Run",    value: activeRuns  },
        { metric: "Tarih Aralığı", value: `Son ${dateRange} gün` },
      ],
      `cortex-report-${new Date().toISOString().slice(0, 10)}.csv`,
    );
  }

  return (
    <PageErrorBoundary>
    <div className="min-h-[calc(100vh-88px)] bg-bg text-fg">
      {/* Print CSS */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white !important; color: black !important; }
        }
      `}</style>

      {/* Header */}
      <div className="no-print border-b border-border bg-surface-raised px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-[13px] font-semibold text-fg">Raporlar</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCSVExport}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-fg-muted transition-colors hover:bg-white/[0.08] hover:text-fg"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M8 1v8m0 0L5 6m3 3 3-3M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              CSV İndir
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-fg-muted transition-colors hover:bg-white/[0.08] hover:text-fg"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M4 6V2h8v4M4 12H2a1 1 0 01-1-1V7a1 1 0 011-1h12a1 1 0 011 1v4a1 1 0 01-1 1h-2m-8 0v3h8v-3H4z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              PDF İndir
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-raised px-4 py-3">
          {/* Date Range */}
          <div className="flex items-center rounded-lg border border-border overflow-hidden">
            {DATE_RANGE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setDateRange(opt.value)}
                className={`px-3 py-1.5 text-[11px] font-medium transition-colors ${
                  dateRange === opt.value
                    ? "bg-emerald-600/30 text-emerald-400"
                    : "text-fg-subtle hover:bg-white/[0.04] hover:text-fg"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <select value={moduleFilter} onChange={e => setModuleFilter(e.target.value)}
            className="rounded-lg border border-border bg-bg px-3 py-1.5 text-[11px] text-fg-muted focus:outline-none focus:ring-1 focus:ring-emerald-600/50">
            <option value="">Tüm Modüller</option>
            <option value="auth">Auth</option>
            <option value="payment">Payment</option>
            <option value="dashboard">Dashboard</option>
            <option value="api">API</option>
          </select>

          <select value={platformFilter} onChange={e => setPlatformFilter(e.target.value)}
            className="rounded-lg border border-border bg-bg px-3 py-1.5 text-[11px] text-fg-muted focus:outline-none focus:ring-1 focus:ring-emerald-600/50">
            <option value="">Tüm Platformlar</option>
            <option value="web">Web</option>
            <option value="mobile">Mobile</option>
            <option value="api">API</option>
          </select>

          {(moduleFilter || platformFilter) && (
            <button
              onClick={() => { setModuleFilter(""); setPlatformFilter(""); }}
              className="text-[11px] text-fg-subtle hover:text-fg transition-colors"
            >
              Filtreleri temizle
            </button>
          )}
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard label="Toplam Case"  value={sumLoading  ? "…" : totalCases}                  sub="repository" />
          <KpiCard label="Pass Rate"    value={sumLoading  ? "…" : `${passRate.toFixed(1)}%`}   sub="executed" />
          <KpiCard label="Açık Defect"  value={openDefects}                                     sub="open defects" />
          <KpiCard label="Aktif Run"    value={runsLoading ? "…" : activeRuns}                  sub="in progress" />
        </div>

        {/* Report Type Tabs */}
        <div className="flex items-center gap-1 rounded-xl border border-border bg-surface-raised p-1">
          {REPORT_TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 rounded-lg px-3 py-2 text-[12px] font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-surface-overlay text-fg shadow-sm"
                  : "text-fg-subtle hover:text-fg"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === "execution" && (
          <ExecutionSummaryTab
            summary={summary}
            runs={runs}
            filteredRuns={filteredRuns}
            sumLoading={sumLoading}
            sumError={sumError}
            runsLoading={runsLoading}
            runsError={runsError}
            projectId={projectId}
            trendData={trendData}
            trendPoints={trendPoints}
          />
        )}

        {activeTab === "regression" && (
          <RegressionReportTab
            regressionSets={regressionSets}
            regressionLoading={regressionLoading}
            regressionError={regressionError}
            runs={runs}
          />
        )}

        {activeTab === "defects" && (
          <DefectSummaryTab defects={defects} />
        )}

        {activeTab === "release" && (
          <ReleaseReadinessTab
            checklist={checklist}
            relLoading={relLoading}
            relError={relError}
            passRate={passRate}
            openDefects={openDefects}
            signoffs={signoffs}
            createSignoff={createSignoff}
          />
        )}

        {activeTab === "tester" && (
          <TesterPerformanceTab
            cases={casesData}
            runs={runs}
            loading={casesLoading || runsLoading}
          />
        )}

        {activeTab === "coverage" && (
          <ModuleCoverageTab
            cases={casesData}
            loading={casesLoading}
          />
        )}
      </div>
    </div>
    </PageErrorBoundary>
  );
}
