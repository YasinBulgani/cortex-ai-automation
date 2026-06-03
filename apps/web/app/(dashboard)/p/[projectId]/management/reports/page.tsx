"use client";

import {
  useExecutionSummary,
  useReleaseReport,
  useManagementRuns,
  useManagementDefects,
  type TestRun,
  type ReleaseChecklistItem,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const RUN_STATUS_DOT: Record<string, string> = {
  in_progress: "bg-blue-500 animate-pulse",
  completed:   "bg-emerald-500",
  failed:      "bg-red-500",
  not_started: "bg-slate-600",
};

function KpiCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0d1221] p-4">
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
    <div className="flex items-center gap-3 rounded-lg border border-white/[0.04] bg-white/[0.02] px-4 py-3">
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

export default function ManagementReportsPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: summary, isLoading: sumLoading, isError: sumError }   = useExecutionSummary(mpid || undefined);
  const { data: release, isLoading: relLoading, isError: relError }   = useReleaseReport(mpid || undefined);
  const { data: runs, isLoading: runsLoading, isError: runsError }    = useManagementRuns(mpid || undefined);
  const { data: defects }                                              = useManagementDefects(mpid || undefined);

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

  return (
    <div className="min-h-[calc(100vh-88px)] bg-[#0a0f1e] text-slate-200">
      {/* Header */}
      <div className="border-b border-white/[0.06] bg-[#0d1221] px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Raporlar</h1>
      </div>

      <div className="p-6 space-y-6">
        {/* KPI cards */}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard label="Toplam Case"  value={sumLoading ? "…" : totalCases}   sub="repository" />
          <KpiCard label="Pass Rate"    value={sumLoading ? "…" : `${passRate.toFixed(1)}%`} sub="executed" />
          <KpiCard label="Açık Defect"  value={openDefects}                     sub="open defects" />
          <KpiCard label="Aktif Run"    value={runsLoading ? "…" : activeRuns}  sub="in progress" />
        </div>

        {/* Execution Summary */}
        <div className="rounded-xl border border-white/[0.06] bg-[#0d1221] p-5">
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
        <div className="rounded-xl border border-white/[0.06] bg-[#0d1221] p-5">
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
        <div className="rounded-xl border border-white/[0.06] bg-[#0d1221] overflow-hidden">
          <div className="border-b border-white/[0.06] px-5 py-3">
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
                <tr className="border-b border-white/[0.04]">
                  {["", "Run Adı", "Durum", "Tarih"].map(h => (
                    <th key={h} className="px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run: TestRun) => {
                  const dot = RUN_STATUS_DOT[run.status] ?? "bg-slate-600";
                  return (
                    <tr key={run.id} className="border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                      <td className="w-6 pl-4 py-3">
                        <span className={`inline-block h-1.5 w-1.5 rounded-full ${dot}`} />
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[13px] text-slate-200">{run.name}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] text-slate-400">{run.status}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-[11px] text-slate-500">
                          {run.started_at
                            ? new Date(run.started_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
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
      </div>
    </div>
  );
}
