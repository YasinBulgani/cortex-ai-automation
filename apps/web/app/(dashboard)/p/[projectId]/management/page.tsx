"use client";

import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  useExecutionSummary,
  useManagementRuns,
  useManagementDefects,
  useManagementRepository,
  useReleaseReport,
  useManagementAuditEvents,
  type TestRun,
  type ManagementAuditEvent,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins}dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}s önce`;
  return `${Math.floor(hrs / 24)}g önce`;
}

const RUN_DOT: Record<string, string> = {
  not_started: "bg-slate-600",
  in_progress: "bg-blue-500 animate-pulse",
  completed:   "bg-emerald-500/70",
  passed:      "bg-emerald-500/70",
  failed:      "bg-red-500/70",
  blocked:     "bg-amber-500/60",
};

const RUN_LABEL: Record<string, string> = {
  not_started: "Bekliyor",
  in_progress: "Devam Ediyor",
  completed:   "Tamamlandı",
  passed:      "Passed",
  failed:      "Failed",
  blocked:     "Bloke",
};

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, accent }: {
  label: string; value: string | number; sub?: string; accent?: string;
}) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827]/60 px-5 py-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">{label}</p>
      <p className={cn("mt-2 text-3xl font-bold tabular-nums tracking-tight", accent ?? "text-slate-100")}>
        {value}
      </p>
      {sub && <p className="mt-1 text-[11px] text-slate-600">{sub}</p>}
    </div>
  );
}

// ─── Run Row ──────────────────────────────────────────────────────────────────

function RunRow({ run, projectId }: { run: TestRun; projectId: string }) {
  return (
    <Link href={`/p/${projectId}/management/runs`}
      className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-white/[0.04] transition-colors group">
      <span className={cn("h-2 w-2 shrink-0 rounded-full", RUN_DOT[run.status] ?? "bg-slate-600")}/>
      <div className="flex-1 min-w-0">
        <p className="truncate text-[13px] text-slate-300 group-hover:text-slate-100 transition-colors">{run.name}</p>
        {run.environment && (
          <p className="text-[11px] text-slate-600">{run.environment}</p>
        )}
      </div>
      <span className="shrink-0 text-[11px] text-slate-600">{RUN_LABEL[run.status] ?? run.status}</span>
    </Link>
  );
}

// ─── Activity Row ─────────────────────────────────────────────────────────────

function ActivityRow({ event }: { event: ManagementAuditEvent }) {
  const actionLabel: Record<string, string> = {
    create: "oluşturdu",
    update: "güncelledi",
    delete: "sildi",
    archive: "arşivledi",
    move: "taşıdı",
    pass: "passed",
    fail: "failed",
    block: "blocked",
  };
  const entityLabel: Record<string, string> = {
    test_case: "test senaryosu",
    test_suite: "suite",
    test_folder: "folder",
    test_run: "run",
    defect: "defekt",
    regression_set: "regresyon seti",
  };

  const action = actionLabel[event.action] ?? event.action;
  const entity = entityLabel[event.entity_type] ?? event.entity_type;

  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-800 text-[10px] font-semibold text-slate-400">
        {(event.actor_id ?? "?")[0]?.toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] text-slate-400">
          <span className="text-slate-300">{event.actor_id ?? "Sistem"}</span>
          {" "}{action}{" "}
          <span className="text-slate-300">{entity}</span>
        </p>
      </div>
      <span className="shrink-0 text-[11px] text-slate-600">{relativeTime(event.created_at)}</span>
    </div>
  );
}

// ─── Release readiness bar ────────────────────────────────────────────────────

function ReadinessBar({ label, value, ok }: { label: string; value: number; ok: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", ok ? "bg-emerald-500/70" : "bg-red-500/70")}/>
      <span className="w-36 shrink-0 text-[12px] text-slate-400">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-slate-800">
        <div className={cn("h-full rounded-full transition-all duration-700", ok ? "bg-emerald-500/60" : value > 50 ? "bg-amber-500/60" : "bg-red-500/60")}
          style={{ width: `${value}%` }}/>
      </div>
      <span className="w-10 shrink-0 text-right text-[11px] text-slate-500 tabular-nums">%{value}</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ManagementDashboard() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);

  const summaryQ = useExecutionSummary(mpid || undefined);
  const runsQ    = useManagementRuns(mpid || undefined);
  const defQ     = useManagementDefects(mpid || undefined);
  const repoQ    = useManagementRepository(mpid || undefined);
  const releaseQ = useReleaseReport(mpid || undefined);
  const auditQ   = useManagementAuditEvents(mpid || undefined, 20);

  const summary  = summaryQ.data;
  const runs     = runsQ.data ?? [];
  const defects  = defQ.data ?? [];
  const cases    = repoQ.data?.cases ?? [];
  const release  = releaseQ.data;
  const audit    = auditQ.data ?? [];

  const activeRuns  = runs.filter(r => r.status === "in_progress");
  const openDefects = defects.filter(d => d.status !== "closed" && d.status !== "resolved");
  const passRate    = summary && summary.total > 0
    ? Math.round((summary.passed / summary.total) * 100)
    : null;

  const loading = summaryQ.isLoading || !mpid;
  const hasError = summaryQ.isError || runsQ.isError || repoQ.isError;

  if (hasError && !loading) {
    return (
      <div className="flex min-h-[calc(100vh-88px)] items-center justify-center bg-[#0a0f1e]">
        <div className="text-center">
          <p className="text-[13px] text-red-400">Veriler yüklenirken bir hata oluştu.</p>
          <button
            onClick={() => {
              summaryQ.refetch(); runsQ.refetch(); defQ.refetch(); repoQ.refetch();
            }}
            className="mt-3 rounded-md border border-white/[0.08] px-4 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-[#0a0f1e] px-8 py-8">
      <div className="mx-auto max-w-4xl space-y-8">

        {/* ── Header ──────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
            <p className="mt-1 text-[13px] text-slate-500">
              {new Date().toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link href={`/p/${projectId}/scenarios/new`}
              className="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-300 hover:bg-white/[0.07] hover:text-slate-100 transition-colors">
              + Senaryo Yaz
            </Link>
            <Link href={`/p/${projectId}/management/plans`}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-[13px] font-medium text-white hover:bg-blue-500 transition-colors">
              ▶ Run Başlat
            </Link>
          </div>
        </div>

        {/* ── KPI Cards ───────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            label="Test Senaryosu"
            value={loading ? "—" : cases.filter(c => !c.archived).length}
            sub={`${cases.filter(c => c.status === "active" && !c.archived).length} aktif`}
          />
          <KpiCard
            label="Pass Rate"
            value={loading || passRate === null ? "—" : `%${passRate}`}
            sub={summary ? `${summary.passed}/${summary.total} koşum` : undefined}
            accent={passRate !== null ? (passRate >= 80 ? "text-emerald-400" : passRate >= 50 ? "text-amber-400" : "text-red-400") : undefined}
          />
          <KpiCard
            label="Aktif Run"
            value={loading ? "—" : activeRuns.length}
            sub={`${runs.length} toplam run`}
          />
          <KpiCard
            label="Açık Defekt"
            value={loading ? "—" : openDefects.length}
            sub={`${openDefects.filter(d => d.severity === "critical").length} kritik`}
            accent={openDefects.length > 0 ? "text-red-400" : undefined}
          />
        </div>

        {/* ── Active runs + Recent activity ───────────────────── */}
        <div className="grid gap-6 lg:grid-cols-2">

          {/* Active Runs */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-[13px] font-semibold text-slate-300">Aktif Runlar</h2>
              <Link href={`/p/${projectId}/management/runs`}
                className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors">
                Tümü →
              </Link>
            </div>
            <div className="rounded-xl border border-white/[0.06] bg-[#111827]/40 divide-y divide-white/[0.04]">
              {runsQ.isLoading ? (
                <div className="space-y-2 p-3">
                  {[1,2,3].map(i => <div key={i} className="h-9 rounded-lg bg-slate-800/40 animate-pulse"/>)}
                </div>
              ) : runs.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <p className="text-[13px] text-slate-600">Henüz run yok</p>
                  <Link href={`/p/${projectId}/management/plans`}
                    className="mt-2 inline-block text-[12px] text-blue-500 hover:text-blue-400">
                    Plan oluştur ve run başlat →
                  </Link>
                </div>
              ) : (
                runs.slice(0, 6).map(run => <RunRow key={run.id} run={run} projectId={projectId}/>)
              )}
            </div>
          </div>

          {/* Recent Activity */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-[13px] font-semibold text-slate-300">Son Aktivite</h2>
            </div>
            <div className="rounded-xl border border-white/[0.06] bg-[#111827]/40 px-4 divide-y divide-white/[0.04]">
              {auditQ.isLoading ? (
                <div className="space-y-2 py-3">
                  {[1,2,3,4].map(i => <div key={i} className="h-8 rounded-lg bg-slate-800/40 animate-pulse"/>)}
                </div>
              ) : audit.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-[13px] text-slate-600">Henüz aktivite yok</p>
                </div>
              ) : (
                audit.slice(0, 7).map(e => <ActivityRow key={e.id} event={e}/>)
              )}
            </div>
          </div>
        </div>

        {/* ── Release Readiness ────────────────────────────────── */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[13px] font-semibold text-slate-300">Release Readiness</h2>
            {release && (
              <span className={cn(
                "rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
                release.decision === "go"     ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" :
                release.decision === "no_go"  ? "border-red-500/30 bg-red-500/10 text-red-400" :
                "border-slate-700 bg-slate-800 text-slate-400"
              )}>
                {release.decision === "go" ? "✓ Go" : release.decision === "no_go" ? "✗ No Go" : "Pending"}
              </span>
            )}
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#111827]/40 px-6 py-5 space-y-4">
            {releaseQ.isLoading ? (
              <div className="space-y-3">
                {[1,2,3,4].map(i => <div key={i} className="h-4 rounded-full bg-slate-800/40 animate-pulse"/>)}
              </div>
            ) : release ? (
              <>
                <ReadinessBar label="Test ilerlemesi"   value={release.progress_pct}             ok={release.progress_pct >= 95}/>
                <ReadinessBar label="Pass rate"         value={release.pass_rate_pct}             ok={release.pass_rate_pct >= 90}/>
                <ReadinessBar label="Req coverage"      value={release.requirement_coverage_pct}  ok={release.requirement_coverage_pct >= 80}/>
                <ReadinessBar label="Defekt temiz"      value={Math.max(0, 100 - (release.open_defect_count * 10))} ok={release.open_defect_count === 0}/>
                {release.blockers.length > 0 && (
                  <div className="mt-2 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 space-y-1">
                    {release.blockers.map(b => (
                      <p key={b.label} className="text-[12px] text-red-400">⚠ {b.label}</p>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="py-4 text-center">
                <p className="text-[13px] text-slate-600">Release raporu oluşturmak için test run başlatın</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
