"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { useQuery, type UseMutationResult } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
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
  type TestCase,
  type TestRun,
  type ReleaseChecklistItem,
  type ReleaseSignoff,
  type RegressionSet,
  type DefectLink,
  type RunTrendPoint,
  type ExecutionSummary,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
  trivial:  { label: "Trivial",  color: "text-fg-muted",  bar: "bg-slate-500"  },
};

const DATE_RANGE_OPTIONS = [
  { label: "Son 7 gün",  value: 7  },
  { label: "Son 30 gün", value: 30 },
  { label: "Son 90 gün", value: 90 },
];

const CUSTOM_RANGE_VALUE = -1;

const DAY_LABELS = ["G-6", "G-5", "G-4", "G-3", "G-2", "Dün", "Bugün"];

// ─── Helpers ────────────────────────────────────────────────────────────────

/** RFC 4180 compliant CSV field escaping */
function csvEscape(val: string | number | undefined): string {
  const s = String(val ?? "");
  if (s.includes(",") || s.includes('"') || s.includes("\n")) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function downloadCSV(rows: { metric: string; value: string | number }[], filename: string) {
  const header = "Metric,Value\n";
  const body = rows.map(r => `${csvEscape(r.metric)},${csvEscape(r.value)}`).join("\n");
  const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadXLSX(
  payload: {
    summary: ExecutionSummary | undefined;
    runs: TestRun[];
    defects: DefectLink[];
    regressionSets: RegressionSet[];
    signoffs: ReleaseSignoff[];
    cases: TestCase[];
    passRate: number;
    openDefects: number;
    activeRuns: number;
    userIdMap: Record<string, string>;
  },
  filename: string,
) {
  const XLSX = await import("xlsx");
  const wb = XLSX.utils.book_new();

  // ── Sheet 1: Execution Summary ──────────────────────────────────────────
  const summaryRows = [
    ["Metrik", "Değer"],
    ["Toplam Case",      payload.summary?.total ?? 0],
    ["Geçti",            payload.summary?.passed ?? 0],
    ["Başarısız",        payload.summary?.failed ?? 0],
    ["Engellendi",       payload.summary?.blocked ?? 0],
    ["Çalıştırılmadı",  payload.summary?.not_run ?? 0],
    ["Geçme Oranı (%)", payload.passRate.toFixed(1)],
    ["Aktif Run",        payload.activeRuns],
    ["Açık Defect",      payload.openDefects],
    ["Dışa Aktarım Tarihi", new Date().toLocaleString("tr-TR")],
  ];
  const ws1 = XLSX.utils.aoa_to_sheet(summaryRows);
  ws1["!cols"] = [{ wch: 24 }, { wch: 16 }];
  XLSX.utils.book_append_sheet(wb, ws1, "Yürütme Özeti");

  // ── Sheet 2: Test Runs ──────────────────────────────────────────────────
  const runHeaders = ["Run Adı", "Durum", "Ortam", "Başlangıç", "Tamamlanma"];
  const runRows = payload.runs.map(r => [
    r.name,
    r.status,
    r.environment ?? "",
    r.created_at ? new Date(r.created_at).toLocaleDateString("tr-TR") : "",
    r.completed_at ? new Date(r.completed_at as string).toLocaleDateString("tr-TR") : "",
  ]);
  const ws2 = XLSX.utils.aoa_to_sheet([runHeaders, ...runRows]);
  ws2["!cols"] = [{ wch: 32 }, { wch: 14 }, { wch: 12 }, { wch: 14 }, { wch: 14 }];
  XLSX.utils.book_append_sheet(wb, ws2, "Test Koşumları");

  // ── Sheet 3: Defects ────────────────────────────────────────────────────
  const defHeaders = ["Defect Başlığı", "Durum", "Severity", "Priority", "External Key", "Oluşturulma"];
  const defRows = payload.defects.map(d => [
    d.title,
    d.status,
    d.severity,
    d.priority,
    d.external_key ?? "",
    d.created_at ? new Date(d.created_at).toLocaleDateString("tr-TR") : "",
  ]);
  const ws3 = XLSX.utils.aoa_to_sheet([defHeaders, ...defRows]);
  ws3["!cols"] = [{ wch: 40 }, { wch: 14 }, { wch: 12 }, { wch: 10 }, { wch: 14 }, { wch: 14 }];
  XLSX.utils.book_append_sheet(wb, ws3, "Defektler");

  // ── Sheet 4: Regression Sets ────────────────────────────────────────────
  const regHeaders = ["Regresyon Seti", "Tip", "Case Sayısı", "Oluşturulma"];
  const regRows = payload.regressionSets.map(rs => [
    rs.name,
    rs.set_type ?? "",
    rs.cases?.length ?? 0,
    rs.created_at ? new Date(rs.created_at).toLocaleDateString("tr-TR") : "",
  ]);
  const ws4 = XLSX.utils.aoa_to_sheet([regHeaders, ...regRows]);
  ws4["!cols"] = [{ wch: 32 }, { wch: 14 }, { wch: 12 }, { wch: 18 }];
  XLSX.utils.book_append_sheet(wb, ws4, "Regresyon Setleri");

  // ── Sheet 5: Test Cases ─────────────────────────────────────────────────
  const caseHeaders = ["Case Key", "Başlık", "Öncelik", "Tip", "Durum", "Son Koşum", "Sahip"];
  const caseRows = payload.cases.map(c => [
    c.case_key ?? "",
    c.title,
    c.priority ?? "",
    c.type ?? "",
    c.status ?? "",
    c.last_run_status ?? "",
    payload.userIdMap[c.owner_id ?? ""] ?? "",
  ]);
  const ws5 = XLSX.utils.aoa_to_sheet([caseHeaders, ...caseRows]);
  ws5["!cols"] = [{ wch: 12 }, { wch: 40 }, { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 14 }, { wch: 20 }];
  XLSX.utils.book_append_sheet(wb, ws5, "Test Case'leri");

  XLSX.writeFile(wb, filename);
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
        <div key={i} className="h-12 w-full animate-pulse rounded-xl bg-surface-overlay" />
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
    { label: "Bekliyor",  count: notRun,  heightPct: (notRun  / total) * 100, color: "bg-slate-600",   text: "text-fg-muted"   },
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
    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-overlay/30 px-4 py-3">
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
      <span className="flex-1 text-[13px] text-fg">{item.label}</span>
      <div className="flex items-center gap-2 w-40">
        <div className="h-1 flex-1 rounded-full bg-surface-accent overflow-hidden">
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
  summary: ExecutionSummary | undefined; runs: TestRun[] | undefined; filteredRuns: TestRun[];
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
                { n: notRun,  c: "bg-surface-accent"},
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
          <span className="text-[11px] text-fg-subtle">Son 7 gün</span>
        </div>
        <PassRateAreaChart points={trendPoints ?? []} />
      </div>

      {/* Recent Runs Table */}
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3 flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Son Runlar</h2>
          {filteredRuns.length > 8 && (
            <span className="text-[11px] text-fg-subtle">Son 8 / {filteredRuns.length} run gösteriliyor</span>
          )}
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
                  <tr key={run.id} className="border-b border-border hover:bg-surface-overlay transition-colors">
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
                        <div className="h-1.5 w-full rounded-full bg-surface-accent" />
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
  regressionSets, regressionLoading, regressionError, runs, filteredRuns,
}: {
  regressionSets: RegressionSet[] | undefined;
  regressionLoading: boolean;
  regressionError: boolean;
  runs: TestRun[] | undefined;
  filteredRuns: TestRun[];
}) {
  const sets = regressionSets ?? [];
  const displayRuns = filteredRuns.length > 0 ? filteredRuns : (runs ?? []);

  const getLastRunStatus = (setId: string): string => {
    const setRuns = displayRuns
      .filter(r => r.source_type === "regression" && r.source_ref === setId)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return setRuns[0]?.status ?? "—";
  };

  // KPI aggregates across all sets
  const totalCases = sets.reduce((s, set) => s + set.cases.length, 0);
  const allCases = sets.flatMap(s => s.cases);
  const runCases = allCases.filter(c => c.last_run_status && c.last_run_status !== "not_run");
  const passedCases = allCases.filter(c => c.last_run_status === "passed");
  const failedCases = allCases.filter(c => c.last_run_status === "failed");
  const overallPassPct = runCases.length > 0 ? Math.round((passedCases.length / runCases.length) * 100) : null;
  const setsWithRuns = sets.filter(s => s.cases.some(c => c.last_run_status && c.last_run_status !== "not_run")).length;

  return (
    <div className="space-y-6">

      {/* KPI summary row */}
      {!regressionLoading && sets.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Toplam Set",      value: String(sets.length),                        color: "text-fg",           sub: `${setsWithRuns} koşuldu` },
            { label: "Toplam Case",     value: String(totalCases),                          color: "text-fg",           sub: `tüm setlerde` },
            { label: "Geçme Oranı",     value: overallPassPct !== null ? `${overallPassPct}%` : "—", color: overallPassPct !== null && overallPassPct >= 80 ? "text-emerald-400" : overallPassPct !== null && overallPassPct >= 50 ? "text-amber-400" : "text-red-400", sub: `${passedCases.length} geçti` },
            { label: "Başarısız Case",  value: String(failedCases.length),                  color: failedCases.length > 0 ? "text-red-400" : "text-fg", sub: `${runCases.length} koşuldu` },
          ].map(kpi => (
            <div key={kpi.label} className="rounded-xl border border-border bg-surface-raised px-4 py-3">
              <p className="text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">{kpi.label}</p>
              <p className={cn("mt-1 text-[22px] font-bold tabular-nums", kpi.color)}>{kpi.value}</p>
              <p className="text-[10px] text-fg-muted">{kpi.sub}</p>
            </div>
          ))}
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3 flex items-center justify-between">
          <div>
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Regresyon Setleri</h2>
          </div>
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
                {["Set Adı", "Case", "Dağılım", "Geçme", "Son Run", "Oluşturulma"].map((h, i) => (
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
                const total   = set.cases.length;
                const passed  = set.cases.filter(c => c.last_run_status === "passed").length;
                const failed  = set.cases.filter(c => c.last_run_status === "failed").length;
                const blocked = set.cases.filter(c => c.last_run_status === "blocked").length;
                const notRun  = set.cases.filter(c => !c.last_run_status || c.last_run_status === "not_run").length;
                const runCount = passed + failed + blocked;
                const passRate = runCount > 0 ? Math.round((passed / runCount) * 100) : null;
                return (
                  <tr key={set.id} className="border-b border-border hover:bg-surface-overlay transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-[13px] text-fg">{set.name}</p>
                        {set.description && <p className="text-[11px] text-fg-subtle mt-0.5 truncate max-w-xs">{set.description}</p>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[13px] text-fg-muted tabular-nums">{total}</span>
                    </td>
                    <td className="px-4 py-3 w-32">
                      {total > 0 ? (
                        <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-surface-overlay">
                          {passed  > 0 && <div className="bg-emerald-500/70" style={{width:`${(passed/total)*100}%`}} title={`Geçti: ${passed}`}/>}
                          {failed  > 0 && <div className="bg-red-500/70"     style={{width:`${(failed/total)*100}%`}} title={`Başarısız: ${failed}`}/>}
                          {blocked > 0 && <div className="bg-amber-500/60"   style={{width:`${(blocked/total)*100}%`}} title={`Engel: ${blocked}`}/>}
                          {notRun  > 0 && <div className="bg-surface-accent" style={{width:`${(notRun/total)*100}%`}} title={`Koşulmadı: ${notRun}`}/>}
                        </div>
                      ) : <span className="text-[10px] text-fg-disabled">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {passRate !== null ? (
                        <span className={cn("font-mono text-[12px] font-semibold tabular-nums",
                          passRate >= 80 ? "text-emerald-400" :
                          passRate >= 50 ? "text-amber-400" : "text-red-400")}>
                          {passRate}%
                        </span>
                      ) : <span className="text-[11px] text-fg-disabled">—</span>}
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
          <KpiCard label="Son Run" value={displayRuns.filter(r => r.status === "in_progress").length > 0 ? "Aktif" : "Tamamlandı"} sub="run durumu" />
        </div>
      )}
    </div>
  );
}

// ─── Defect Summary Tab ───────────────────────────────────────────────────────

function DefectSummaryTab({
  defects,
  dateRangeDays,
  customRange,
}: {
  defects: DefectLink[] | undefined;
  dateRangeDays: number;
  customRange: { start: string; end: string } | null;
}) {
  const allDefects = useMemo(() => {
    const raw = defects ?? [];
    if (customRange) {
      const start = new Date(customRange.start).getTime();
      const end = new Date(customRange.end).getTime() + 24 * 60 * 60 * 1000 - 1;
      return raw.filter(d => {
        const t = d.created_at ? new Date(d.created_at).getTime() : null;
        return t === null || (t >= start && t <= end);
      });
    }
    if (dateRangeDays > 0) {
      const cutoff = Date.now() - dateRangeDays * 24 * 60 * 60 * 1000;
      return raw.filter(d => {
        const t = d.created_at ? new Date(d.created_at).getTime() : null;
        return t === null || t >= cutoff;
      });
    }
    return raw;
  }, [defects, dateRangeDays, customRange]);
  const openDefects = allDefects.filter(d => !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase()));

  const severityCounts: Record<string, number> = {};
  for (const d of allDefects) {
    const sev = (d.severity ?? "unknown").toLowerCase();
    severityCounts[sev] = (severityCounts[sev] ?? 0) + 1;
  }
  const maxCount = Math.max(...Object.values(severityCounts), 1);
  const orderedSeverities = ["critical", "high", "medium", "low", "trivial"];

  // Priority distribution
  const priorityCounts: Record<string, number> = {};
  for (const d of allDefects) {
    const p = (d.priority ?? "unknown").toLowerCase();
    priorityCounts[p] = (priorityCounts[p] ?? 0) + 1;
  }
  const orderedPriorities = ["p0", "p1", "p2", "p3"];
  const priorityConfig: Record<string, { label: string; color: string; bar: string }> = {
    p0: { label: "P0 — Kritik",   color: "text-red-400",    bar: "bg-red-500"    },
    p1: { label: "P1 — Yüksek",   color: "text-orange-400", bar: "bg-orange-500" },
    p2: { label: "P2 — Orta",     color: "text-amber-400",  bar: "bg-amber-500"  },
    p3: { label: "P3 — Düşük",    color: "text-fg-muted",   bar: "bg-slate-500"  },
  };
  const maxPriority = Math.max(...Object.values(priorityCounts), 1);

  // Root cause distribution
  const rootCauseCounts: Record<string, number> = {};
  for (const d of allDefects) {
    if (d.root_cause) {
      const rc = d.root_cause.trim();
      rootCauseCounts[rc] = (rootCauseCounts[rc] ?? 0) + 1;
    }
  }
  const sortedRootCauses = Object.entries(rootCauseCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const maxRc = sortedRootCauses.length > 0 ? sortedRootCauses[0][1] : 1;

  // MTTR (mean time to resolve) in hours
  const resolvedDefects = allDefects.filter(d => d.resolved_at && d.created_at);
  const mttrHours = resolvedDefects.length > 0
    ? Math.round(resolvedDefects.reduce((acc, d) => {
        const diff = new Date(d.resolved_at!).getTime() - new Date(d.created_at).getTime();
        return acc + diff / (1000 * 60 * 60);
      }, 0) / resolvedDefects.length)
    : null;
  const mttrDisplay = mttrHours === null ? "—"
    : mttrHours < 24  ? `${mttrHours}s`
    : `${Math.round(mttrHours / 24)}g`;

  // Retest status breakdown
  const retestCounts: Record<string, number> = {};
  for (const d of allDefects) {
    const rs = (d.retest_status ?? "pending").toLowerCase();
    retestCounts[rs] = (retestCounts[rs] ?? 0) + 1;
  }
  const RETEST_CONFIG: Record<string, { label: string; color: string; bar: string; dot: string }> = {
    passed:       { label: "Geçti",        color: "text-emerald-400", bar: "bg-emerald-500", dot: "bg-emerald-500" },
    failed:       { label: "Başarısız",    color: "text-red-400",     bar: "bg-red-500",     dot: "bg-red-500"     },
    pending:      { label: "Bekliyor",     color: "text-amber-400",   bar: "bg-amber-500",   dot: "bg-amber-500"   },
    not_required: { label: "Gerekmiyor",   color: "text-fg-muted",    bar: "bg-slate-500",   dot: "bg-slate-500"   },
    in_progress:  { label: "Devam Ediyor", color: "text-blue-400",    bar: "bg-blue-500",    dot: "bg-blue-500"    },
  };
  const retestTotal = Object.values(retestCounts).reduce((s, v) => s + v, 0);
  const retestPassRate = retestTotal > 0 && retestCounts.passed
    ? Math.round((retestCounts.passed / retestTotal) * 100)
    : null;

  // Defect aging (open defects only)
  const now = Date.now();
  const agingBuckets = { lt7: 0, d7to30: 0, gt30: 0 };
  for (const d of openDefects) {
    const age = now - new Date(d.created_at).getTime();
    const days = age / (1000 * 60 * 60 * 24);
    if (days < 7)  agingBuckets.lt7++;
    else if (days < 30) agingBuckets.d7to30++;
    else agingBuckets.gt30++;
  }
  const agingMax = Math.max(agingBuckets.lt7, agingBuckets.d7to30, agingBuckets.gt30, 1);

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
              const cfg = SEVERITY_CONFIG[sev] ?? { label: sev, color: "text-fg-muted", bar: "bg-slate-500" };
              const widthPct = (count / maxCount) * 100;
              return (
                <div key={sev} className="flex items-center gap-3">
                  <span className={`w-16 text-[11px] font-medium shrink-0 ${cfg.color}`}>{cfg.label}</span>
                  <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
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
                    <span className="w-16 text-[11px] font-medium shrink-0 text-fg-muted capitalize">{sev}</span>
                    <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCard label="Toplam Defect" value={allDefects.length} sub="tüm zamanlar" />
        <KpiCard label="Açık" value={openDefects.length} sub="çözülmemiş" />
        <KpiCard label="Kapalı" value={allDefects.length - openDefects.length} sub="çözüldü/kapatıldı" />
        <KpiCard label="MTTR" value={mttrDisplay} sub={resolvedDefects.length > 0 ? `${resolvedDefects.length} çözümden` : "çözüm yok"} />
      </div>

      {/* Retest Status & Defect Aging row */}
      {allDefects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Retest Status */}
          <div className="rounded-xl border border-border bg-surface-raised p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Retest Durumu</h2>
              {retestPassRate !== null && (
                <span className="text-[11px] font-semibold text-emerald-400 tabular-nums">{retestPassRate}% geçti</span>
              )}
            </div>
            {retestTotal === 0 ? (
              <p className="text-[12px] text-fg-subtle">Retest verisi yok.</p>
            ) : (
              <div className="space-y-2.5">
                {["pending","failed","passed","in_progress","not_required"].map(rs => {
                  const count = retestCounts[rs] ?? 0;
                  if (count === 0) return null;
                  const cfg = RETEST_CONFIG[rs] ?? { label: rs, color: "text-fg-muted", bar: "bg-slate-500", dot: "bg-slate-500" };
                  return (
                    <div key={rs} className="flex items-center gap-3">
                      <span className={`w-24 text-[11px] font-medium shrink-0 ${cfg.color}`}>{cfg.label}</span>
                      <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
                        <div className={`h-full rounded-full ${cfg.bar} transition-all duration-500`} style={{ width: `${(count / retestTotal) * 100}%` }} />
                      </div>
                      <span className="w-6 text-right text-[12px] text-fg-muted shrink-0 tabular-nums">{count}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          {/* Defect Aging (open only) */}
          <div className="rounded-xl border border-border bg-surface-raised p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Açık Defect Yaşı</h2>
              {openDefects.length > 0 && (
                <span className="text-[11px] text-fg-subtle">{openDefects.length} açık</span>
              )}
            </div>
            {openDefects.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-4 gap-1">
                <span className="text-2xl">🎉</span>
                <p className="text-[12px] text-emerald-400 font-medium">Açık defect yok</p>
              </div>
            ) : (
              <div className="space-y-3">
                {[
                  { label: "< 7 gün",   count: agingBuckets.lt7,    bar: "bg-emerald-500", color: "text-emerald-400" },
                  { label: "7–30 gün",  count: agingBuckets.d7to30, bar: "bg-amber-500",   color: "text-amber-400"   },
                  { label: "> 30 gün",  count: agingBuckets.gt30,   bar: "bg-red-500",     color: "text-red-400"     },
                ].map(({ label, count, bar, color }) => (
                  <div key={label} className="flex items-center gap-3">
                    <span className={`w-16 text-[11px] font-medium shrink-0 ${color}`}>{label}</span>
                    <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
                      <div className={`h-full rounded-full ${bar} transition-all duration-500`} style={{ width: `${(count / agingMax) * 100}%` }} />
                    </div>
                    <span className="w-6 text-right text-[12px] text-fg-muted shrink-0 tabular-nums">{count}</span>
                  </div>
                ))}
                {agingBuckets.gt30 > 0 && (
                  <p className="text-[10px] text-red-400/80 mt-1">
                    ⚠ {agingBuckets.gt30} defect 30+ gündür çözülmedi
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Priority & Root Cause row */}
      {allDefects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Priority distribution */}
          <div className="rounded-xl border border-border bg-surface-raised p-5">
            <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Öncelik Dağılımı</h2>
            <div className="space-y-3">
              {orderedPriorities.map(p => {
                const count = priorityCounts[p] ?? 0;
                const allOther = !orderedPriorities.includes(p);
                if (count === 0 && allOther) return null;
                const cfg = priorityConfig[p] ?? { label: p.toUpperCase(), color: "text-fg-muted", bar: "bg-slate-500" };
                const widthPct = (count / maxPriority) * 100;
                return (
                  <div key={p} className="flex items-center gap-3">
                    <span className={`w-24 text-[11px] font-medium shrink-0 ${cfg.color}`}>{cfg.label}</span>
                    <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
                      <div className={`h-full rounded-full ${cfg.bar} transition-all duration-500`} style={{ width: `${widthPct}%` }} />
                    </div>
                    <span className="w-6 text-right text-[12px] text-fg-muted shrink-0 tabular-nums">{count}</span>
                  </div>
                );
              })}
              {Object.entries(priorityCounts)
                .filter(([k]) => !orderedPriorities.includes(k))
                .map(([p, count]) => (
                  <div key={p} className="flex items-center gap-3">
                    <span className="w-24 text-[11px] font-medium shrink-0 text-fg-muted capitalize">{p}</span>
                    <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
                      <div className="h-full rounded-full bg-slate-500 transition-all duration-500" style={{ width: `${(count / maxPriority) * 100}%` }} />
                    </div>
                    <span className="w-6 text-right text-[12px] text-fg-muted shrink-0 tabular-nums">{count}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Root cause distribution */}
          <div className="rounded-xl border border-border bg-surface-raised p-5">
            <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Kök Neden Analizi</h2>
            {sortedRootCauses.length === 0 ? (
              <p className="text-[12px] text-fg-subtle">Kök neden verisi girilmemiş.</p>
            ) : (
              <div className="space-y-3">
                {sortedRootCauses.map(([rc, count]) => {
                  const widthPct = (count / maxRc) * 100;
                  return (
                    <div key={rc} className="flex items-center gap-3">
                      <span className="w-28 text-[11px] text-fg-muted shrink-0 truncate" title={rc}>{rc}</span>
                      <div className="flex-1 h-2 rounded-full bg-surface-accent overflow-hidden">
                        <div className="h-full rounded-full bg-brand/70 transition-all duration-500" style={{ width: `${widthPct}%` }} />
                      </div>
                      <span className="w-6 text-right text-[12px] text-fg-muted shrink-0 tabular-nums">{count}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Defect list */}
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3 flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Defect Listesi</h2>
          {allDefects.length > 20 && (
            <span className="text-[11px] text-fg-subtle">20 / {allDefects.length} gösteriliyor — tam listeyi CSV ile dışa aktarın</span>
          )}
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
                const sevCfg = SEVERITY_CONFIG[(d.severity ?? "").toLowerCase()] ?? { label: d.severity, color: "text-fg-muted" };
                const isOpen = !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase());
                return (
                  <tr key={d.id} className="border-b border-border hover:bg-surface-overlay transition-colors">
                    <td className="px-4 py-3">
                      {d.url && /^https?:\/\//i.test(d.url) ? (
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
  createSignoff: UseMutationResult<
    ReleaseSignoff,
    Error,
    {
      release_name?: string | null;
      role?: string | null;
      decision: string;
      comment?: string | null;
      report_snapshot?: Record<string, unknown>;
    }
  >;
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
        <div className="h-2.5 w-full rounded-full bg-surface-accent overflow-hidden">
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
                className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40">
                {["QA Lead", "Dev Lead", "Product Owner", "Release Manager", "Security", "CTO"].map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] text-fg-subtle">Karar</label>
              <select value={signoffDecision} onChange={e => setSignoffDecision(e.target.value as "approved" | "rejected")}
                className="w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40">
                <option value="approved">Onaylandı</option>
                <option value="rejected">Reddedildi</option>
              </select>
            </div>
          </div>
          <textarea value={signoffComment} onChange={e => setSignoffComment(e.target.value)}
            rows={2} placeholder="Opsiyonel yorum…"
            className="w-full resize-none rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/40" />
          <div className="flex justify-end">
            <Button type="button" variant="primary"
              onClick={async () => {
                await createSignoff.mutateAsync({
                  decision: signoffDecision,
                  comment: `[${signoffRole}] ${signoffComment}`.trim() || undefined,
                });
                setSignoffComment("");
              }}
              disabled={createSignoff.isPending}
              className={cn(
                "text-[13px] font-semibold text-white",
                signoffDecision === "approved" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-red-600 hover:bg-red-500"
              )}>
              {createSignoff.isPending ? "İmzalanıyor…" : signoffDecision === "approved" ? "Onayla" : "Reddet"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Tester Performance Tab ──────────────────────────────────────────────────

type SortKey = "assigned" | "completed" | "passRate" | "completionRate";
type SortDir = "asc" | "desc";

function PassRateBar({ value, size = "md" }: { value: number; size?: "sm" | "md" }) {
  const color = value >= 80 ? "bg-emerald-500" : value >= 50 ? "bg-amber-500" : "bg-red-500";
  const h = size === "sm" ? "h-1" : "h-1.5";
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className={`flex-1 ${h} rounded-full bg-surface-overlay overflow-hidden`}>
        <div className={`${h} rounded-full ${color} transition-all duration-500`} style={{ width: `${value}%` }} />
      </div>
      <span className={`text-[11px] font-semibold tabular-nums w-8 text-right ${
        value >= 80 ? "text-emerald-400" : value >= 50 ? "text-amber-400" : "text-red-400"
      }`}>{value}%</span>
    </div>
  );
}

function TesterPerformanceTab({
  cases,
  runs,
  filteredRuns,
  loading,
  userIdMap = {},
}: {
  cases: TestCase[] | undefined;
  runs: TestRun[] | undefined;
  filteredRuns: TestRun[];
  loading: boolean;
  userIdMap?: Record<string, string>;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("assigned");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const displayRuns = filteredRuns.length > 0 ? filteredRuns : (runs ?? []);

  const resolveUser = (rawId: string): string => {
    if (!rawId) return "Atanmamış";
    return userIdMap[rawId] ?? `…${rawId.slice(-8)}`;
  };

  const testerRows = useMemo(() => {
    if (!cases) return [];

    const map = new Map<string, { userId: string; assigned: number; completed: number; passed: number; failed: number; blocked: number }>();

    for (const tc of cases) {
      const rawKey = (tc.owner_id ?? "").trim();
      const displayKey = rawKey ? (userIdMap[rawKey] ?? `…${rawKey.slice(-8)}`) : "Atanmamış";
      const row = map.get(displayKey) ?? { userId: rawKey, assigned: 0, completed: 0, passed: 0, failed: 0, blocked: 0 };
      row.assigned += 1;
      const st = tc.last_run_status ?? "";
      if (["passed", "failed", "blocked"].includes(st)) row.completed += 1;
      if (st === "passed")  row.passed  += 1;
      if (st === "failed")  row.failed  += 1;
      if (st === "blocked") row.blocked += 1;
      map.set(displayKey, row);
    }

    // Add run-level tester info (assigned_to is a UUID when present)
    for (const run of displayRuns) {
      const rawKey = (run.assigned_to ?? "").trim();
      if (!rawKey) continue;
      const displayKey = userIdMap[rawKey] ?? `…${rawKey.slice(-8)}`;
      if (!map.has(displayKey)) map.set(displayKey, { userId: rawKey, assigned: 0, completed: 0, passed: 0, failed: 0, blocked: 0 });
    }

    return [...map.entries()].map(([tester, data]) => ({
      tester,
      userId: data.userId,
      assigned: data.assigned,
      completed: data.completed,
      passed:    data.passed,
      failed:    data.failed,
      blocked:   data.blocked,
      passRate:         data.completed > 0 ? Math.round((data.passed  / data.completed) * 100) : 0,
      completionRate:   data.assigned   > 0 ? Math.round((data.completed / data.assigned) * 100) : 0,
      active: displayRuns.some(r =>
        r.status === "in_progress" &&
        r.assigned_to != null &&
        (r.assigned_to === data.userId || r.assigned_to.endsWith(data.userId.slice(-8)))
      ),
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases, displayRuns, userIdMap]);

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
    if (sortKey !== key) return <span className="text-fg-disabled opacity-50">↕</span>;
    return <span className="text-brand">{sortDir === "asc" ? "↑" : "↓"}</span>;
  };

  // Aggregate KPIs
  const totalAssigned   = testerRows.reduce((s, r) => s + r.assigned, 0);
  const totalCompleted  = testerRows.reduce((s, r) => s + r.completed, 0);
  const totalPassed     = testerRows.reduce((s, r) => s + r.passed, 0);
  const overallPassRate = totalCompleted > 0 ? Math.round((totalPassed / totalCompleted) * 100) : 0;
  const activeTesterCount = sorted.filter(r => r.active).length;

  return (
    <div className="space-y-6">
      {/* KPI summary bar */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KpiCard label="Toplam Tester"   value={sorted.length}       sub="case atanmış"       />
        <KpiCard label="Toplam Atanan"   value={totalAssigned}       sub="test case"          />
        <KpiCard label="Tamamlama"       value={`${totalCompleted > 0 ? Math.round((totalCompleted/totalAssigned)*100) : 0}%`} sub={`${totalCompleted}/${totalAssigned}`} />
        <KpiCard label="Genel Pass Rate" value={`${overallPassRate}%`} sub="tamamlananlar üzerinden" />
      </div>

      {/* Detailed table */}
      <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
        <div className="border-b border-border px-5 py-3 flex items-center justify-between">
          <div>
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-fg-subtle">Tester Performans Detayı</h2>
            <p className="mt-0.5 text-[10px] text-fg-disabled">
              Proje üyeleri üzerinden çözümlendi.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {activeTesterCount > 0 && (
              <span className="flex items-center gap-1.5 text-[10px] text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                {activeTesterCount} aktif
              </span>
            )}
            <span className="text-[10px] text-fg-subtle">{sorted.length} tester</span>
          </div>
        </div>
        {loading ? (
          <div className="p-6"><SkeletonRows /></div>
        ) : sorted.length === 0 ? (
          <p className="px-5 py-6 text-[13px] text-fg-subtle">Case veya tester ataması bulunamadı.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border bg-surface-overlay/30">
                  <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Tester</th>
                  <th
                    className="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-fg-subtle cursor-pointer select-none hover:text-fg transition-colors"
                    onClick={() => toggleSort("assigned")}
                  >
                    Atanan {arrow("assigned")}
                  </th>
                  <th
                    className="px-4 py-2.5 text-right text-[10px] font-semibold uppercase tracking-wider text-fg-subtle cursor-pointer select-none hover:text-fg transition-colors"
                    onClick={() => toggleSort("completed")}
                  >
                    Tamamlanan {arrow("completed")}
                  </th>
                  <th
                    className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-fg-subtle cursor-pointer select-none hover:text-fg transition-colors"
                    onClick={() => toggleSort("completionRate")}
                  >
                    Tamamlama % {arrow("completionRate")}
                  </th>
                  <th
                    className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-fg-subtle cursor-pointer select-none hover:text-fg transition-colors"
                    onClick={() => toggleSort("passRate")}
                  >
                    Pass Rate {arrow("passRate")}
                  </th>
                  <th className="px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Sonuçlar</th>
                  <th className="px-4 py-2.5 text-center text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">Durum</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((row, idx) => (
                  <tr
                    key={row.tester}
                    className={`border-b border-border hover:bg-surface-overlay/50 transition-colors ${idx % 2 === 0 ? "" : "bg-surface-overlay/10"}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand/10 text-[10px] font-bold text-brand">
                          {row.tester === "Atanmamış" ? "?" : row.tester.slice(-1).toUpperCase()}
                        </div>
                        <span className="text-[13px] text-fg font-medium">{row.tester}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-[13px] text-fg-muted tabular-nums">{row.assigned}</td>
                    <td className="px-4 py-3 text-right text-[13px] text-fg-muted tabular-nums">{row.completed}</td>
                    <td className="px-4 py-3 min-w-[130px]">
                      <PassRateBar value={row.completionRate} />
                    </td>
                    <td className="px-4 py-3 min-w-[130px]">
                      <PassRateBar value={row.passRate} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2 text-[11px]">
                        {row.passed  > 0 && <span className="flex items-center gap-1 text-emerald-400"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500"/>{row.passed}</span>}
                        {row.failed  > 0 && <span className="flex items-center gap-1 text-red-400"><span className="h-1.5 w-1.5 rounded-full bg-red-500"/>{row.failed}</span>}
                        {row.blocked > 0 && <span className="flex items-center gap-1 text-amber-400"><span className="h-1.5 w-1.5 rounded-full bg-amber-500"/>{row.blocked}</span>}
                        {row.passed === 0 && row.failed === 0 && row.blocked === 0 && (
                          <span className="text-fg-disabled">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {row.active ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          Aktif
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-disabled">
                          İdle
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Module Coverage Tab ──────────────────────────────────────────────────────

function ModuleCoverageTab({
  cases,
  loading,
}: {
  cases: TestCase[] | undefined;
  loading: boolean;
  filteredRuns?: TestRun[];
}) {
  const suiteRows = useMemo(() => {
    if (!cases) return [];
    const map = new Map<string, { total: number; passed: number; failed: number; blocked: number }>();
    for (const tc of cases) {
      const cf = tc.custom_fields;
      const rawKey = (typeof cf?.component === "string" ? cf.component : null)
        ?? (typeof cf?.module === "string" ? cf.module : null)
        ?? tc.suite_id
        ?? "Genel";
      const key = rawKey.trim() || "Genel";
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
                <tr key={row.suite} className="border-b border-border hover:bg-surface-overlay transition-colors">
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
  const [customRange,     setCustomRange]     = useState<{ start: string; end: string } | null>(null);
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

  const { data: membersData } = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () =>
      apiFetch<Array<{ user_id: string; email: string; full_name?: string }>>(
        `/api/v1/organizations/projects/${projectId}/members`
      ).then(d => (Array.isArray(d) ? d : [])),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
  const userIdMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const m of membersData ?? []) {
      map[m.user_id] = m.full_name?.trim() || m.email;
    }
    return map;
  }, [membersData]);

  // Derive unique module names dynamically from cases data
  const moduleOptions = useMemo(() =>
    [...new Set(
      (casesData ?? [])
        .map((c: TestCase) => {
          const cf = c.custom_fields;
          const mod = cf?.module ?? cf?.component;
          return typeof mod === "string" ? mod : null;
        })
        .filter((m): m is string => m !== null && m.length > 0)
    )],
    [casesData],
  );

  const passRate    = summary?.pass_rate_pct ?? 0;
  const totalCases  = summary?.total ?? 0;
  const openDefects = (defects ?? []).filter(d => !["closed", "resolved", "fixed", "done"].includes(d.status.toLowerCase())).length;
  const activeRuns  = (runs ?? []).filter(r => r.status === "in_progress").length;

  // Filtered runs: dateRange (days) + customRange + moduleFilter + platformFilter
  const filteredRuns = useMemo(() => {
    if (!runs) return [];
    return runs.filter(r => {
      // Date filter: use created_at or started_at if available
      const dateField = r.created_at || r.started_at;
      if (customRange || dateRange > 0) {
        // Null tarihli run'lar tarih filtresi aktifken dışlanır
        if (!dateField) return false;
        const ts = new Date(dateField).getTime();
        if (customRange) {
          const start = new Date(customRange.start).getTime();
          const end = new Date(customRange.end).getTime() + 24 * 60 * 60 * 1000 - 1;
          if (ts < start || ts > end) return false;
        } else {
          const cutoffMs = dateRange * 24 * 60 * 60 * 1000;
          if (Date.now() - ts > cutoffMs) return false;
        }
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
  }, [runs, dateRange, customRange, moduleFilter, platformFilter]);

  const checklist: ReleaseChecklistItem[] = release?.checklist ?? [];

  // Real run trend points from the API.
  const trendPoints: TrendPoint[] = useMemo(() => {
    const data = runTrend ?? [];
    const sorted = [...data]
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .slice(-7);
    const points: TrendPoint[] = sorted.map((p: RunTrendPoint) => ({
      label: new Date(p.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" }),
      value: Math.round(p.pass_rate_pct),
    }));
    // Pad to 7 points with value 0 when API has fewer entries (no fake data)
    return points;
  }, [runTrend]);
  const trendData = trendPoints.map(point => point.value);

  function handleCSVExport() {
    const dateLabel = customRange ? `${customRange.start} – ${customRange.end}` : `Son ${dateRange} gün`;
    if (activeTab === "tester") {
      const headers = ["Tester", "Atanan", "Tamamlanan", "Geçti", "Başarısız", "Engellendi", "Pass Rate"];
      const tMap = new Map<string, {assigned:number;completed:number;passed:number;failed:number;blocked:number}>();
      for (const tc of (casesData ?? [])) {
        const rawKey = (tc.owner_id ?? "").trim();
        const k = rawKey ? (userIdMap[rawKey] ?? `…${rawKey.slice(-8)}`) : "Atanmamış";
        const row = tMap.get(k) ?? {assigned:0,completed:0,passed:0,failed:0,blocked:0};
        row.assigned += 1;
        const st = tc.last_run_status ?? "";
        if (["passed","failed","blocked"].includes(st)) row.completed += 1;
        if (st === "passed")  row.passed  += 1;
        if (st === "failed")  row.failed  += 1;
        if (st === "blocked") row.blocked += 1;
        tMap.set(k, row);
      }
      const lines = [...tMap.entries()].map(([tester, r]) => {
        const pct = r.completed > 0 ? `${Math.round(r.passed / r.completed * 100)}%` : "—";
        return [tester, r.assigned, r.completed, r.passed, r.failed, r.blocked, pct]
          .map(v => `"${String(v).replace(/"/g, '""')}"`).join(",");
      });
      const csv = [headers.join(","), ...lines].join("\n");
      const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `tester-performance-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
      URL.revokeObjectURL(url);
      return;
    }
    if (activeTab === "defects") {
      const headers = ["Başlık", "Severity", "Öncelik", "Durum", "Atanan", "Oluşturulma"];
      const lines = (defects ?? []).map(d => [
        d.title, d.severity, d.priority, d.status,
        userIdMap[d.assignee_id ?? ""] ?? d.assignee_id ?? "",
        new Date(d.created_at).toLocaleDateString("tr-TR"),
      ].map(v => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","));
      const csv = [headers.join(","), ...lines].join("\n");
      const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob); const a = document.createElement("a");
      a.href = url; a.download = `defects-report-${new Date().toISOString().slice(0, 10)}.csv`; a.click();
      URL.revokeObjectURL(url);
      return;
    }
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
        { metric: "Tarih Aralığı", value: dateLabel },
      ],
      `neurex-report-${new Date().toISOString().slice(0, 10)}.csv`,
    );
  }

  const [xlsxExporting, setXlsxExporting] = useState(false);
  const [xlsxError, setXlsxError] = useState<string | null>(null);

  async function handleXLSXExport() {
    setXlsxExporting(true);
    setXlsxError(null);
    try {
      await downloadXLSX(
        {
          summary,
          runs: runs ?? [],
          defects: defects ?? [],
          regressionSets: regressionSets ?? [],
          signoffs: signoffs ?? [],
          cases: casesData ?? [],
          passRate,
          openDefects,
          activeRuns,
          userIdMap,
        },
        `neurex-report-${new Date().toISOString().slice(0, 10)}.xlsx`,
      );
    } catch (err) {
      console.error("[Reports] XLSX export failed:", err);
      setXlsxError("XLSX dışa aktarma başarısız oldu. Lütfen tekrar deneyin.");
    } finally {
      setXlsxExporting(false);
    }
  }

  return (
    <PageErrorBoundary>
    <div className="min-h-[calc(100vh-88px)] bg-surface-base text-fg">
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
            <Button
              variant="subtle"
              size="sm"
              onClick={handleCSVExport}
              className="text-[11px] text-fg-muted hover:bg-surface-accent hover:text-fg"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M8 1v8m0 0L5 6m3 3 3-3M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              CSV İndir
            </Button>
            <Button
              variant="subtle"
              size="sm"
              onClick={() => { void handleXLSXExport(); }}
              disabled={xlsxExporting}
              title="5 sayfalık kapsamlı Excel raporu"
              className="border-emerald-600/30 bg-emerald-600/10 text-[11px] text-emerald-400 hover:bg-emerald-600/20"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M9 1H4a1 1 0 00-1 1v12a1 1 0 001 1h8a1 1 0 001-1V5l-4-4z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M6 9l4 4M10 9l-4 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
              {xlsxExporting ? "Hazırlanıyor…" : "XLSX İndir"}
            </Button>
            <Button
              variant="subtle"
              size="sm"
              onClick={() => window.print()}
              className="text-[11px] text-fg-muted hover:bg-surface-accent hover:text-fg"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M4 6V2h8v4M4 12H2a1 1 0 01-1-1V7a1 1 0 011-1h12a1 1 0 011 1v4a1 1 0 01-1 1h-2m-8 0v3h8v-3H4z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              PDF İndir
            </Button>
          </div>
        </div>
        {xlsxError && (
          <p className="px-6 pb-2 text-[11px] text-danger" role="alert">{xlsxError}</p>
        )}
      </div>

      <div className="p-6 space-y-6">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-raised px-4 py-3">
          {/* Date Range */}
          <div className="flex items-center rounded-lg border border-border overflow-hidden">
            {DATE_RANGE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => { setDateRange(opt.value); setCustomRange(null); }}
                className={`px-3 py-1.5 text-[11px] font-medium transition-colors ${
                  dateRange === opt.value && !customRange
                    ? "bg-emerald-600/30 text-emerald-400"
                    : "text-fg-subtle hover:bg-surface-overlay hover:text-fg"
                }`}
              >
                {opt.label}
              </button>
            ))}
            <button
              onClick={() => {
                setDateRange(CUSTOM_RANGE_VALUE);
                setCustomRange(prev => prev ?? { start: "", end: "" });
              }}
              className={`px-3 py-1.5 text-[11px] font-medium transition-colors ${
                dateRange === CUSTOM_RANGE_VALUE
                  ? "bg-emerald-600/30 text-emerald-400"
                  : "text-fg-subtle hover:bg-surface-overlay hover:text-fg"
              }`}
            >
              Özel
            </button>
          </div>

          {/* Custom date inputs */}
          {dateRange === CUSTOM_RANGE_VALUE && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={customRange?.start ?? ""}
                onChange={e => setCustomRange(prev => ({ start: e.target.value, end: prev?.end ?? "" }))}
                className="rounded-lg border border-border bg-surface-overlay px-2 py-1.5 text-[11px] text-fg-muted focus:outline-none focus:ring-1 focus:ring-emerald-600/50"
              />
              <span className="text-[11px] text-fg-subtle">–</span>
              <input
                type="date"
                value={customRange?.end ?? ""}
                onChange={e => setCustomRange(prev => ({ start: prev?.start ?? "", end: e.target.value }))}
                className="rounded-lg border border-border bg-surface-overlay px-2 py-1.5 text-[11px] text-fg-muted focus:outline-none focus:ring-1 focus:ring-emerald-600/50"
              />
            </div>
          )}

          <select value={moduleFilter} onChange={e => setModuleFilter(e.target.value)}
            className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[11px] text-fg-muted focus:outline-none focus:ring-1 focus:ring-emerald-600/50">
            <option value="">Tüm Modüller</option>
            {moduleOptions.map(mod => (
              <option key={mod} value={mod}>{mod}</option>
            ))}
          </select>

          <select value={platformFilter} onChange={e => setPlatformFilter(e.target.value)}
            className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[11px] text-fg-muted focus:outline-none focus:ring-1 focus:ring-emerald-600/50">
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
            filteredRuns={filteredRuns}
          />
        )}

        {activeTab === "defects" && (
          <DefectSummaryTab
            defects={defects}
            dateRangeDays={dateRange > 0 ? dateRange : 0}
            customRange={customRange}
          />
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
            filteredRuns={filteredRuns}
            loading={casesLoading || runsLoading}
            userIdMap={userIdMap}
          />
        )}

        {activeTab === "coverage" && (
          <ModuleCoverageTab
            cases={casesData}
            loading={casesLoading}
            filteredRuns={filteredRuns}
          />
        )}
      </div>
    </div>
    </PageErrorBoundary>
  );
}
