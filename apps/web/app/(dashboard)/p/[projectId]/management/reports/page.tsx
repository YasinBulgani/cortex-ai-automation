"use client";

import { useState } from "react";
import Link from "next/link";
import {
  useExecutionSummary,
  useReleaseReport,
  useManagementRuns,
  useManagementDefects,
  useReleaseSignoffs,
  useCreateReleaseSignoff,
  type TestRun,
  type ReleaseChecklistItem,
  type ReleaseSignoff,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const RUN_STATUS_DOT: Record<string, string> = {
  in_progress: "bg-blue-500 animate-pulse",
  completed:   "bg-emerald-500",
  failed:      "bg-red-500",
  not_started: "bg-slate-600",
};

const DATE_RANGE_OPTIONS = [
  { label: "Son 7 gün",  value: 7  },
  { label: "Son 30 gün", value: 30 },
  { label: "Son 90 gün", value: 90 },
];

const DAY_LABELS = ["G-6", "G-5", "G-4", "G-3", "G-2", "Dün", "Bugün"];

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

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-4">
      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-600">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold text-slate-100">{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-500">{sub}</p>}
    </div>
  );
}

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
      <span className="flex-1 text-[13px] text-slate-300">{item.label}</span>
      <div className="flex items-center gap-2 w-40">
        <div className="h-1 flex-1 rounded-full bg-white/[0.06] overflow-hidden">
          <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="text-[11px] text-slate-500 w-12 text-right truncate">{item.metric}</span>
      </div>
    </div>
  );
}

function TrendChart({ trendData }: { trendData: number[] }) {
  const max = Math.max(...trendData, 1);
  const chartHeight = 60;
  const barWidth = 28;
  const gap = 8;
  const totalBars = trendData.length;
  const svgWidth = totalBars * (barWidth + gap) - gap;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${svgWidth} ${chartHeight + 32}`}
        style={{ width: "100%", height: "80px" }}
        preserveAspectRatio="xMidYMid meet"
      >
        {trendData.map((val, i) => {
          const barH = Math.max((val / max) * chartHeight, 4);
          const x = i * (barWidth + gap);
          const y = chartHeight - barH;
          const isLast = i === trendData.length - 1;
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barH}
                rx={3}
                className={isLast ? "fill-emerald-400" : "fill-emerald-600/60"}
              />
              {/* percentage label above bar */}
              <text
                x={x + barWidth / 2}
                y={y - 3}
                textAnchor="middle"
                fontSize="7"
                className="fill-slate-400"
              >
                {val}%
              </text>
              {/* day label below bar */}
              <text
                x={x + barWidth / 2}
                y={chartHeight + 12}
                textAnchor="middle"
                fontSize="7"
                className="fill-slate-500"
              >
                {DAY_LABELS[i] ?? `G-${totalBars - 1 - i}`}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function ManagementReportsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const [dateRange, setDateRange] = useState(30);
  const [moduleFilter, setModuleFilter] = useState("");
  const [platformFilter, setPlatformFilter] = useState("");

  const { data: summary, isLoading: sumLoading, isError: sumError }   = useExecutionSummary(mpid || undefined);
  const { data: release, isLoading: relLoading, isError: relError }   = useReleaseReport(mpid || undefined);
  const { data: runs, isLoading: runsLoading, isError: runsError }    = useManagementRuns(mpid || undefined);
  const { data: defects }                                              = useManagementDefects(mpid || undefined);
  const { data: signoffs }                                             = useReleaseSignoffs(mpid || undefined);
  const createSignoff                                                  = useCreateReleaseSignoff(mpid || "");

  const [signoffRole,    setSignoffRole]    = useState("QA Lead");
  const [signoffComment, setSignoffComment] = useState("");
  const [signoffDecision, setSignoffDecision] = useState<"approved" | "rejected">("approved");

  const totalCases  = summary?.total ?? 0;
  const passRate    = summary?.pass_rate_pct ?? 0;
  const openDefects = (defects ?? []).filter(d => !["closed","resolved","fixed","done"].includes(d.status.toLowerCase())).length;
  const activeRuns  = (runs ?? []).filter(r => r.status === "in_progress").length;

  const passed  = summary?.passed  ?? 0;
  const failed  = summary?.failed  ?? 0;
  const blocked = summary?.blocked ?? 0;
  const notRun  = summary?.not_run ?? 0;
  const execTotal = passed + failed + blocked + notRun;

  const checklist: ReleaseChecklistItem[] = release?.checklist ?? [];
  const passedChecks = checklist.filter(c => c.status === "pass").length;
  const recentRuns   = (runs ?? []).slice(0, 8);

  const trendData = [62, 68, 71, 65, 74, 78, Math.round(passRate)];

  function handleCSVExport() {
    downloadCSV(
      [
        { metric: "Toplam Case",  value: totalCases },
        { metric: "Pass Rate",    value: `${passRate.toFixed(1)}%` },
        { metric: "Failed",       value: failed },
        { metric: "Blocked",      value: blocked },
        { metric: "Not Run",      value: notRun },
        { metric: "Açık Defect",  value: openDefects },
        { metric: "Aktif Run",    value: activeRuns },
      ],
      `cortex-report-${new Date().toISOString().slice(0, 10)}.csv`,
    );
  }

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">
      {/* Header */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-[13px] font-semibold text-slate-200">Raporlar</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCSVExport}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-slate-300 transition-colors hover:bg-white/[0.08] hover:text-slate-100"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M8 1v8m0 0L5 6m3 3 3-3M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              CSV İndir
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-slate-300 transition-colors hover:bg-white/[0.08] hover:text-slate-100"
            >
              <svg className="h-3 w-3" viewBox="0 0 16 16" fill="none">
                <path d="M4 6V2h8v4M4 12H2a1 1 0 01-1-1V7a1 1 0 011-1h12a1 1 0 011 1v4a1 1 0 01-1 1h-2m-8 0v3h8v-3H4z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Rapor Yazdır
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-raised px-4 py-3">
          {/* Date Range Tabs */}
          <div className="flex items-center rounded-lg border border-border overflow-hidden">
            {DATE_RANGE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setDateRange(opt.value)}
                className={`px-3 py-1.5 text-[11px] font-medium transition-colors ${
                  dateRange === opt.value
                    ? "bg-emerald-600/30 text-emerald-400"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Module Filter */}
          <select
            value={moduleFilter}
            onChange={e => setModuleFilter(e.target.value)}
            className="rounded-lg border border-border bg-bg px-3 py-1.5 text-[11px] text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-600/50"
          >
            <option value="">Tüm Modüller</option>
            <option value="auth">Auth</option>
            <option value="payment">Payment</option>
            <option value="dashboard">Dashboard</option>
            <option value="api">API</option>
          </select>

          {/* Platform Filter */}
          <select
            value={platformFilter}
            onChange={e => setPlatformFilter(e.target.value)}
            className="rounded-lg border border-border bg-bg px-3 py-1.5 text-[11px] text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-600/50"
          >
            <option value="">Tüm Platformlar</option>
            <option value="web">Web</option>
            <option value="mobile">Mobile</option>
            <option value="api">API</option>
          </select>

          {(moduleFilter || platformFilter) && (
            <button
              onClick={() => { setModuleFilter(""); setPlatformFilter(""); }}
              className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
            >
              Filtreleri temizle
            </button>
          )}
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard label="Toplam Case"  value={sumLoading ? "…" : totalCases}   sub="repository" />
          <KpiCard label="Pass Rate"    value={sumLoading ? "…" : `${passRate.toFixed(1)}%`} sub="executed" />
          <KpiCard label="Açık Defect"  value={openDefects}                     sub="open defects" />
          <KpiCard label="Aktif Run"    value={runsLoading ? "…" : activeRuns}  sub="in progress" />
        </div>

        {/* Pass Rate Trend Chart */}
        <div className="rounded-xl border border-border bg-surface-raised p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Pass Rate Trendi</h2>
            <span className="text-[11px] text-slate-600">Son 7 gün</span>
          </div>
          <TrendChart trendData={trendData} />
        </div>

        {/* Execution Summary */}
        <div className="rounded-xl border border-border bg-surface-raised p-5">
          <h2 className="mb-4 text-[11px] font-medium uppercase tracking-wider text-slate-500">Execution Summary</h2>
          {sumLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-white/[0.04]" />
              ))}
            </div>
          ) : sumError ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-red-400/80">Veri yüklenemedi — lütfen sayfayı yenileyin</p>
            </div>
          ) : execTotal === 0 ? (
            <p className="text-[13px] text-slate-600">Henüz execution verisi yok.</p>
          ) : (
            <>
              <div className="flex h-3 overflow-hidden rounded-full gap-px">
                {[
                  { n: passed,  c: "bg-emerald-500" },
                  { n: failed,  c: "bg-red-500"     },
                  { n: blocked, c: "bg-amber-500"   },
                  { n: notRun,  c: "bg-white/[0.08]"},
                ].map(({ n, c }, i) => n > 0 ? (
                  <div key={i} className={`${c} h-full`} style={{ width: `${(n / execTotal) * 100}%` }} />
                ) : null)}
              </div>
              <div className="mt-3 flex flex-wrap gap-4">
                {[
                  { label: "Passed",  count: passed,  dot: "bg-emerald-500" },
                  { label: "Failed",  count: failed,  dot: "bg-red-500"     },
                  { label: "Blocked", count: blocked, dot: "bg-amber-500"   },
                  { label: "Not Run", count: notRun,  dot: "bg-slate-600"   },
                ].map(({ label, count, dot }) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
                    <span className="text-[13px] font-medium text-slate-200">{count}</span>
                    <span className="text-[11px] text-slate-500">{label}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Release Readiness */}
        <div className="rounded-xl border border-border bg-surface-raised p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Release Readiness</h2>
            {!relLoading && checklist.length > 0 && (
              <span className="text-[11px] text-slate-500">{passedChecks}/{checklist.length} geçti</span>
            )}
          </div>
          {relLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-white/[0.04]" />
              ))}
            </div>
          ) : relError ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-red-400/80">Veri yüklenemedi — lütfen sayfayı yenileyin</p>
            </div>
          ) : checklist.length === 0 ? (
            <p className="text-[13px] text-slate-600">Checklist verisi yok.</p>
          ) : (
            <div className="space-y-2">
              {checklist.map((item, i) => <ChecklistRow key={i} item={item} />)}
            </div>
          )}
        </div>

        {/* Recent Runs */}
        <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
          <div className="border-b border-border px-5 py-3">
            <h2 className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Son Runlar</h2>
          </div>
          {runsLoading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-white/[0.04]" />
              ))}
            </div>
          ) : runsError ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-red-400/80">Veri yüklenemedi — lütfen sayfayı yenileyin</p>
            </div>
          ) : recentRuns.length === 0 ? (
            <p className="px-5 py-6 text-[13px] text-slate-600">Henüz run yok.</p>
          ) : (
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border">
                  {["", "Run Adı", "Durum", "İlerleme", "Tarih", ""].map((h, idx) => (
                    <th key={idx} className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run: TestRun) => {
                  const dot = RUN_STATUS_DOT[run.status] ?? "bg-slate-600";
                  const runPassed  = (run as any).passed  ?? 0;
                  const runFailed  = (run as any).failed  ?? 0;
                  const runBlocked = (run as any).blocked ?? 0;
                  const runTotal   = runPassed + runFailed + runBlocked;
                  return (
                    <tr key={run.id} className="border-b border-border hover:bg-white/[0.04] transition-colors">
                      <td className="w-6 pl-4 py-3">
                        <span className={`inline-block h-1.5 w-1.5 rounded-full ${dot}`} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[13px] text-slate-200">{run.name}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] text-slate-400">{run.status}</span>
                      </td>
                      <td className="px-4 py-3 w-32">
                        {runTotal > 0 ? (
                          <div className="flex h-1.5 w-full overflow-hidden rounded-full gap-px">
                            {runPassed > 0 && (
                              <div className="bg-emerald-500 h-full" style={{ width: `${(runPassed / runTotal) * 100}%` }} />
                            )}
                            {runFailed > 0 && (
                              <div className="bg-red-500 h-full" style={{ width: `${(runFailed / runTotal) * 100}%` }} />
                            )}
                            {runBlocked > 0 && (
                              <div className="bg-amber-500 h-full" style={{ width: `${(runBlocked / runTotal) * 100}%` }} />
                            )}
                          </div>
                        ) : (
                          <div className="h-1.5 w-full rounded-full bg-white/[0.06]" />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] text-slate-500">
                          {run.started_at
                            ? new Date(run.started_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
                            : "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {projectId && (
                          <Link
                            href={`/p/${projectId}/management/runs/${run.id}/execute`}
                            className="text-[11px] text-emerald-500 hover:text-emerald-400 transition-colors"
                          >
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

      {/* ── Release Signoff Panel ─────────────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-surface-raised p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[14px] font-semibold text-slate-200">Release Signoff</h2>
          <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-slate-500">
            {(signoffs ?? []).length} imza
          </span>
        </div>

        {/* Mevcut signoff'lar */}
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
                  <p className="text-[13px] font-medium text-slate-200">{s.signed_by ?? "İmzalandı"}</p>
                  {s.comment && <p className="text-[11px] text-slate-500 truncate">{s.comment}</p>}
                </div>
                <span className="text-[10px] text-slate-500">
                  {new Date(s.signed_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                </span>
                <span className={`text-[11px] font-semibold ${s.decision === "approved" ? "text-emerald-400" : "text-red-400"}`}>
                  {s.decision === "approved" ? "Onaylandı" : "Reddedildi"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Yeni signoff formu */}
        <div className="space-y-3 rounded-xl border border-border bg-surface-overlay p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">Yeni İmza</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-[10px] text-slate-600">Rol</label>
              <select value={signoffRole} onChange={e => setSignoffRole(e.target.value)}
                className="w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/40">
                {["QA Lead","Dev Lead","Product Owner","Release Manager","Security","CTO"].map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] text-slate-600">Karar</label>
              <select value={signoffDecision} onChange={e => setSignoffDecision(e.target.value as "approved" | "rejected")}
                className="w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/40">
                <option value="approved">Onaylandı</option>
                <option value="rejected">Reddedildi</option>
              </select>
            </div>
          </div>
          <textarea value={signoffComment} onChange={e => setSignoffComment(e.target.value)}
            rows={2} placeholder="Opsiyonel yorum…"
            className="w-full resize-none rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/40" />
          <div className="flex justify-end">
            <button type="button"
              onClick={async () => {
                await createSignoff.mutateAsync({ decision: signoffDecision, comment: `[${signoffRole}] ${signoffComment}`.trim() || undefined });
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
