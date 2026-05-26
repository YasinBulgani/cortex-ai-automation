"use client";

import {
  useExecutionSummary,
  useManagementDefects,
  useManagementRepository,
  useManagementRuns,
  useReleaseReport,
  useRequirementTraceability,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

type Decision = "GO" | "NO-GO" | "Conditional GO" | "Watch";
type CheckStatus = "pass" | "warn" | "fail";

const CLOSED_DEFECT_STATUSES = new Set(["closed", "done", "resolved", "fixed", "verified"]);
const STALE_CASE_DAYS = 14;
const MAX_DEFECT_AGE_DAYS = 7;

function daysSince(value?: string | null) {
  if (!value) return null;
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return null;
  return Math.max(0, Math.floor((Date.now() - time) / 86_400_000));
}

function readiness(
  progress: number,
  passRate: number,
  blocked: number,
  failed: number,
  coverage: number,
  staleRequirements: number,
  openDefects: number,
): Decision {
  if (failed > 0 || blocked > 0 || openDefects > 0) return "NO-GO";
  if (staleRequirements > 0 || coverage < 90) return "Conditional GO";
  if (progress >= 95 && passRate >= 95 && coverage >= 95) return "GO";
  return "Watch";
}

function decisionTone(decision: Decision) {
  if (decision === "GO") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (decision === "Conditional GO") return "border-amber-500/30 bg-amber-500/10 text-amber-100";
  if (decision === "NO-GO") return "border-rose-500/30 bg-rose-500/10 text-rose-100";
  return "border-sky-500/30 bg-sky-500/10 text-sky-100";
}

function checkTone(status: CheckStatus) {
  if (status === "pass") return "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30";
  if (status === "warn") return "bg-amber-500/15 text-amber-200 ring-amber-400/30";
  return "bg-rose-500/15 text-rose-200 ring-rose-400/30";
}

function percent(value: number) {
  return `${value.toFixed(0)}%`;
}

export default function ManagementReportsPage({ params }: { params: { projectId: string } }) {
  const summary = useExecutionSummary(params.projectId);
  const traceability = useRequirementTraceability(params.projectId);
  const defects = useManagementDefects(params.projectId);
  const runs = useManagementRuns(params.projectId);
  const repository = useManagementRepository(params.projectId);
  const releaseReport = useReleaseReport(params.projectId);

  const requirements = traceability.data ?? [];
  const covered = requirements.filter((row) => row.covered).length;
  const staleRequirements = requirements.filter((row) => row.stale).length;
  const uncoveredRequirements = requirements.length - covered;
  const coveragePct = requirements.length ? Math.round((covered / requirements.length) * 100) : 0;
  const staleCoveragePct = requirements.length ? Math.round((staleRequirements / requirements.length) * 100) : 0;
  const progress = summary.data?.progress_pct ?? 0;
  const passRate = summary.data?.pass_rate_pct ?? 0;
  const openDefects = (defects.data ?? []).filter((defect) => !CLOSED_DEFECT_STATUSES.has(defect.status.toLowerCase())).length;
  const defectAges = (defects.data ?? [])
    .filter((defect) => !CLOSED_DEFECT_STATUSES.has(defect.status.toLowerCase()))
    .map((defect) => daysSince(defect.created_at))
    .filter((age): age is number => age !== null);
  const oldestOpenDefectDays = defectAges.length ? Math.max(...defectAges) : 0;
  const avgOpenDefectDays = defectAges.length
    ? Math.round(defectAges.reduce((total, age) => total + age, 0) / defectAges.length)
    : 0;
  const activeRuns = (runs.data ?? []).filter((run) => ["running", "not_run"].includes(run.status)).length;
  const repositoryCases = repository.data?.cases ?? [];
  const staleCases = repositoryCases.filter((testCase) => {
    const age = daysSince(testCase.last_run_at);
    return age === null || age > STALE_CASE_DAYS;
  }).length;
  const staleCasePct = repositoryCases.length ? Math.round((staleCases / repositoryCases.length) * 100) : 0;
  const loading = summary.isLoading || traceability.isLoading || defects.isLoading || runs.isLoading || repository.isLoading || releaseReport.isLoading;
  const status = readiness(
    progress,
    passRate,
    summary.data?.blocked ?? 0,
    summary.data?.failed ?? 0,
    coveragePct,
    staleRequirements,
    openDefects,
  );
  const blockers = [
    ...(summary.data?.failed
      ? [{ label: "Failed run cases", value: summary.data.failed, detail: "Must be triaged before release signoff." }]
      : []),
    ...(summary.data?.blocked
      ? [{ label: "Blocked run cases", value: summary.data.blocked, detail: "Execution is waiting on environment, data, or product fixes." }]
      : []),
    ...(openDefects
      ? [{ label: "Open defect links", value: openDefects, detail: `Oldest open defect is ${oldestOpenDefectDays} day(s) old.` }]
      : []),
    ...(uncoveredRequirements
      ? [{ label: "Uncovered requirements", value: uncoveredRequirements, detail: "Traceability has release scope without linked coverage." }]
      : []),
    ...(staleRequirements
      ? [{ label: "Stale requirement links", value: staleRequirements, detail: "Requirement source changed after linked test coverage." }]
      : []),
  ];
  const checklist: Array<{ label: string; metric: string; status: CheckStatus }> = [
    { label: "Execution progress", metric: `${percent(progress)} / target 95%`, status: progress >= 95 ? "pass" : progress >= 80 ? "warn" : "fail" },
    { label: "Pass rate", metric: `${percent(passRate)} / target 95%`, status: passRate >= 95 ? "pass" : passRate >= 85 ? "warn" : "fail" },
    { label: "Failed cases", metric: `${summary.data?.failed ?? 0} open`, status: (summary.data?.failed ?? 0) === 0 ? "pass" : "fail" },
    { label: "Blocked cases", metric: `${summary.data?.blocked ?? 0} blocked`, status: (summary.data?.blocked ?? 0) === 0 ? "pass" : "fail" },
    { label: "Requirement coverage", metric: `${coveragePct}% covered`, status: coveragePct >= 95 ? "pass" : coveragePct >= 80 ? "warn" : "fail" },
    { label: "Requirement freshness", metric: `${staleRequirements} stale`, status: staleRequirements === 0 ? "pass" : "warn" },
    { label: "Defect aging", metric: `${oldestOpenDefectDays}d oldest / target ${MAX_DEFECT_AGE_DAYS}d`, status: openDefects === 0 ? "pass" : oldestOpenDefectDays <= MAX_DEFECT_AGE_DAYS ? "warn" : "fail" },
    { label: "Active runs", metric: `${activeRuns} in flight`, status: activeRuns === 0 ? "pass" : "warn" },
  ];
  const reportDecision = (releaseReport.data?.decision ?? status) as Decision;
  const reportBlockers = releaseReport.data?.blockers ?? blockers;
  const reportChecklist = releaseReport.data?.checklist ?? checklist;
  const readyChecks = reportChecklist.filter((item) => item.status === "pass").length;

  return (
    <ManagementShell
      projectId={params.projectId}
      title="Management Reports"
      description="Execution summary, coverage matrix, tester workload ve release GO/NO-GO raporları."
      active="management/reports"
    >
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Progress" value={summary.isLoading ? "..." : percent(progress)} note="terminal / total" />
        <ManagementStat label="Pass Rate" value={summary.isLoading ? "..." : percent(passRate)} note="passed / executed" />
        <ManagementStat label="Coverage" value={traceability.isLoading ? "..." : `${coveragePct}%`} note="covered / total linked" />
        <ManagementStat label="Readiness" value={loading ? "..." : reportDecision} note={`${readyChecks}/${reportChecklist.length} checklist passed`} />
      </div>

      <section className={`mt-4 rounded-lg border p-5 ${decisionTone(reportDecision)}`}>
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide opacity-70">Go / No-Go Decision</p>
            <h2 className="mt-2 text-4xl font-bold tracking-tight">{loading ? "..." : reportDecision}</h2>
            <p className="mt-2 max-w-3xl text-sm opacity-80">
              Release gate is calculated from execution progress, pass rate, failed/blocked work, open defects, requirement coverage, and stale traceability.
            </p>
          </div>
          <div className="grid min-w-64 grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-slate-950/40 p-3">
              <p className="text-xs uppercase text-slate-400">Failed</p>
              <p className="mt-1 text-2xl font-semibold text-white">{summary.data?.failed ?? 0}</p>
            </div>
            <div className="rounded-lg bg-slate-950/40 p-3">
              <p className="text-xs uppercase text-slate-400">Blocked</p>
              <p className="mt-1 text-2xl font-semibold text-white">{summary.data?.blocked ?? 0}</p>
            </div>
            <div className="rounded-lg bg-slate-950/40 p-3">
              <p className="text-xs uppercase text-slate-400">Open Defects</p>
              <p className="mt-1 text-2xl font-semibold text-white">{releaseReport.data?.open_defect_count ?? openDefects}</p>
            </div>
            <div className="rounded-lg bg-slate-950/40 p-3">
              <p className="text-xs uppercase text-slate-400">Stale Req.</p>
              <p className="mt-1 text-2xl font-semibold text-white">{releaseReport.data?.stale_requirement_count ?? staleRequirements}</p>
            </div>
          </div>
        </div>
      </section>

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <ManagementPanel title="Critical Blockers">
          {reportBlockers.length ? (
            <div className="space-y-3">
              {reportBlockers.map((blocker) => (
                <div key={blocker.label} className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-white">{blocker.label}</p>
                    <span className="rounded-full bg-rose-500/15 px-3 py-1 text-sm font-semibold text-rose-200 ring-1 ring-rose-400/30">
                      {blocker.value}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{blocker.detail}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
              No critical blockers detected from the current execution, defect, and traceability data.
            </p>
          )}
        </ManagementPanel>

        <ManagementPanel title="Release Readiness Checklist">
          <div className="space-y-3">
            {reportChecklist.map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3">
                <div>
                  <p className="text-sm font-medium text-white">{item.label}</p>
                  <p className="mt-1 text-xs text-slate-400">{item.metric}</p>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ring-1 ${checkTone(item.status as CheckStatus)}`}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </ManagementPanel>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <ManagementStat label="Stale Requirements" value={traceability.isLoading ? "..." : String(staleRequirements)} note={`${staleCoveragePct}% of linked requirements`} />
        <ManagementStat label="Uncovered Requirements" value={traceability.isLoading ? "..." : String(uncoveredRequirements)} note={`${covered}/${requirements.length} covered`} />
        <ManagementStat label="Stale Repository Cases" value={repository.isLoading ? "..." : String(staleCases)} note={`${staleCasePct}% not run in ${STALE_CASE_DAYS}d`} />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <ManagementStat label="Defect Aging" value={defects.isLoading ? "..." : `${oldestOpenDefectDays}d`} note={`oldest open, avg ${avgOpenDefectDays}d`} />
        <ManagementStat label="Failed Count" value={summary.isLoading ? "..." : String(summary.data?.failed ?? 0)} note="execution summary" />
        <ManagementStat label="Runs In Flight" value={runs.isLoading ? "..." : String(activeRuns)} note={`${runs.data?.length ?? 0} total runs`} />
      </div>

      <ManagementPanel title="Report Formulas">
        <div className="grid gap-3 text-sm text-slate-300 md:grid-cols-2">
          <p>Progress = terminal run cases / total assigned run cases.</p>
          <p>Pass Rate = passed / passed+failed+blocked+skipped.</p>
          <p>Coverage = covered linked requirements / total linked requirements; stale = source updated after coverage.</p>
          <p>GO/NO-GO = failed, blocked, open defects, stale requirements, coverage, progress ve pass rate eşikleri.</p>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
