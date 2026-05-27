"use client";

import {
  useEnsureManagementProject,
  useExecutionSummary,
  useManagementCases,
  useManagementProjects,
  useManagementRuns,
} from "@/lib/hooks/use-management";
import { ManagementPanel, ManagementShell, ManagementStat } from "./_components/ManagementShell";

export default function ManagementDashboardPage({ params }: { params: { projectId: string } }) {
  const { projectId } = params;

  const casesQuery  = useManagementCases(projectId);
  const summaryQuery = useExecutionSummary(projectId);
  const activeRuns  = useManagementRuns(projectId, "running");
  const projectsQuery = useManagementProjects();
  const ensureProject = useEnsureManagementProject(projectId);

  const totalCases  = casesQuery.data?.length ?? null;
  const activeCount = activeRuns.data?.length ?? null;
  const summary     = summaryQuery.data ?? null;
  const managementProject = projectsQuery.data?.find(
    (project) => project.id === projectId || project.tspm_project_id === projectId,
  );

  // Release readiness rows derived from execution summary
  const readiness: [string, string, string][] = summary
    ? [
        [
          "Execution progress",
          `${summary.progress_pct.toFixed(0)}%`,
          summary.progress_pct >= 80 ? "bg-teal-500" : summary.progress_pct >= 50 ? "bg-amber-500" : "bg-rose-500",
        ],
        [
          "Pass rate",
          `${summary.pass_rate_pct.toFixed(1)}%`,
          summary.pass_rate_pct >= 90 ? "bg-emerald-500" : summary.pass_rate_pct >= 70 ? "bg-amber-500" : "bg-rose-500",
        ],
        [
          "Failed cases",
          String(summary.failed),
          summary.failed === 0 ? "bg-emerald-500" : summary.failed <= 5 ? "bg-amber-500" : "bg-rose-500",
        ],
        [
          "Blocked cases",
          String(summary.blocked),
          summary.blocked === 0 ? "bg-emerald-500" : summary.blocked <= 3 ? "bg-amber-500" : "bg-rose-500",
        ],
      ]
    : [
        ["Execution progress", "—", "bg-slate-700"],
        ["Pass rate",          "—", "bg-slate-700"],
        ["Failed cases",       "—", "bg-slate-700"],
        ["Blocked cases",      "—", "bg-slate-700"],
      ];

  const loading = casesQuery.isLoading || summaryQuery.isLoading || activeRuns.isLoading;

  return (
    <ManagementShell
      projectId={projectId}
      title="Management Dashboard"
      description="Manuel test repository, aktif run, blocked/failed risk ve tester workload durumunu tek ekranda izleyin."
      active="management"
    >
      <ManagementPanel title="Management Workspace">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-white">
              {managementProject ? managementProject.name : projectsQuery.isLoading ? "Workspace kontrol ediliyor..." : "Bu TSPM projesi için Management workspace hazırlanmadı."}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {managementProject
                ? `Key: ${managementProject.key} · Canonical ID: ${managementProject.id}`
                : "Repository, regression set, plan ve run verileri bu workspace altında tutulur."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => ensureProject.mutate()}
            disabled={ensureProject.isPending}
            className="rounded-lg border border-teal-500/40 px-3 py-2 text-sm font-semibold text-teal-200 hover:bg-teal-500/10 disabled:opacity-40"
          >
            {ensureProject.isPending ? "Hazırlanıyor..." : managementProject ? "Workspace'i Doğrula" : "Workspace Oluştur"}
          </button>
        </div>
      </ManagementPanel>

      {/* ── Top stat cards ── */}
      <div className="mt-4 grid gap-4 md:grid-cols-4">
        <ManagementStat
          label="Manual Cases"
          value={loading ? "…" : (totalCases?.toLocaleString() ?? "—")}
          note={casesQuery.data ? `${casesQuery.data.filter(c => !c.archived).length} aktif case` : "yükleniyor"}
        />
        <ManagementStat
          label="Active Runs"
          value={loading ? "…" : (activeCount?.toLocaleString() ?? "—")}
          note={
            activeRuns.data
              ? `${activeRuns.data.filter(r => r.status === "running").length} run devam ediyor`
              : "yükleniyor"
          }
        />
        <ManagementStat
          label="Pass Rate"
          value={summary ? `${summary.pass_rate_pct.toFixed(1)}%` : loading ? "…" : "—"}
          note={summary ? `${summary.passed}/${summary.total} geçti` : ""}
        />
        <ManagementStat
          label="Blocked"
          value={summary ? String(summary.blocked) : loading ? "…" : "—"}
          note={summary ? `${summary.failed} başarısız case` : ""}
        />
      </div>

      {/* ── Detail panels ── */}
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ManagementPanel title="Release Readiness">
          <div className="space-y-3 text-sm">
            {readiness.map(([label, value, color]) => (
              <div
                key={label}
                className="flex items-center justify-between rounded-lg bg-slate-950 px-3 py-2"
              >
                <span className="text-slate-300">{label}</span>
                <span className={`rounded-full px-2 py-1 text-xs font-semibold text-white ${color}`}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </ManagementPanel>

        <ManagementPanel title="Run Status Breakdown">
          {summary ? (
            <div className="space-y-2">
              {(
                [
                  ["passed",   summary.passed,   "bg-emerald-500"],
                  ["failed",   summary.failed,   "bg-rose-500"],
                  ["blocked",  summary.blocked,  "bg-amber-500"],
                  ["not_run",  summary.not_run,  "bg-slate-600"],
                  ["skipped",  summary.skipped,  "bg-slate-500"],
                ] as [string, number, string][]
              ).map(([lbl, cnt, color]) => (
                <div key={lbl} className="flex items-center gap-3 text-sm">
                  <span className={`inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full ${color}`} />
                  <span className="flex-1 capitalize text-slate-300">{lbl.replace("_", " ")}</span>
                  <span className="font-mono text-slate-200">{cnt}</span>
                  <span className="w-24 text-right text-xs text-slate-500">
                    {summary.total > 0 ? `${((cnt / summary.total) * 100).toFixed(0)}%` : "—"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">{loading ? "Yükleniyor…" : "Veri yok"}</p>
          )}
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
