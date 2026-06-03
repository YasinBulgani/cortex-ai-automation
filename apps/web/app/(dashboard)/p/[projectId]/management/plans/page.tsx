"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  useManagementPlans,
  useCreateManagementPlan,
  useManagementCycles,
  useManagementRuns,
  useCreateManagementRun,
  useCreateManagementCycle,
  type TestPlan,
  type TestCycle,
  type TestRun,
} from "@/lib/hooks/use-management";
import { useQueryClient } from "@tanstack/react-query";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

// ── Types ─────────────────────────────────────────────────────────────────────
type PlanType = "release" | "regression" | "sprint" | "smoke" | "uat";

// ── Constants ─────────────────────────────────────────────────────────────────
const PLAN_TYPE_BADGE: Record<string, string> = {
  release:    "bg-teal-500/15 text-teal-400 border-teal-500/20",
  regression: "bg-purple-500/15 text-purple-400 border-purple-500/20",
  sprint:     "bg-blue-500/15 text-blue-400 border-blue-500/20",
  smoke:      "bg-amber-500/15 text-amber-400 border-amber-500/20",
  uat:        "bg-slate-500/15 text-slate-400 border-slate-500/20",
};

const RUN_STATUS_COLOR: Record<string, string> = {
  not_started: "text-slate-500",
  in_progress: "text-blue-400",
  completed:   "text-emerald-400",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" });
}

// ── Progress bar component ─────────────────────────────────────────────────────
function RunProgress({ passed, failed, blocked, notRun }: {
  passed: number; failed: number; blocked: number; notRun: number;
}) {
  const total = passed + failed + blocked + notRun;
  if (total === 0) return <span className="text-[11px] text-slate-600">Case eklenmemiş</span>;
  const pct = Math.round((passed / total) * 100);

  return (
    <div className="flex items-center gap-2.5 min-w-0">
      {/* Stacked bar */}
      <div className="flex h-1.5 w-28 overflow-hidden rounded-full bg-surface-overlay shrink-0">
        {passed > 0  && <div className="bg-emerald-500/80" style={{ width: `${(passed  / total) * 100}%` }} />}
        {failed > 0  && <div className="bg-red-500/80"     style={{ width: `${(failed  / total) * 100}%` }} />}
        {blocked > 0 && <div className="bg-amber-500/60"   style={{ width: `${(blocked / total) * 100}%` }} />}
      </div>
      {/* Counts */}
      <div className="flex items-center gap-2.5 text-[11px] tabular-nums">
        {passed  > 0 && <span className="text-emerald-400">{passed} <span className="text-slate-600">ok</span></span>}
        {failed  > 0 && <span className="text-red-400">{failed} <span className="text-slate-600">fail</span></span>}
        {blocked > 0 && <span className="text-amber-400">{blocked} <span className="text-slate-600">blk</span></span>}
        {notRun  > 0 && <span className="text-slate-600">{notRun} left</span>}
        <span className="text-slate-500 font-medium">{pct}%</span>
      </div>
    </div>
  );
}

// ── Icons ─────────────────────────────────────────────────────────────────────
function IcChevron({ open }: { open: boolean }) {
  return (
    <svg className={cn("h-3.5 w-3.5 shrink-0 text-slate-600 transition-transform", open && "rotate-90")}
      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 18l6-6-6-6"/>
    </svg>
  );
}
function IcPlay() {
  return (
    <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M8 5v14l11-7z"/>
    </svg>
  );
}
function IcPlus() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
    </svg>
  );
}
function IcTrash() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

// ── Cycle / Run row ───────────────────────────────────────────────────────────
function CycleRow({
  cycle, runs, projectId, onStartRun, loading,
}: {
  cycle: TestCycle;
  runs: TestRun[];
  projectId: string;
  onStartRun: (cycle: TestCycle) => void;
  loading: boolean;
}) {
  // Aggregate mock stats — in real use, runs would expose case counts
  const total   = runs.reduce((n, r) => n + ((r.scope_snapshot as { case_ids?: string[] })?.case_ids?.length ?? 0), 0);
  const running = runs.some(r => r.status === "in_progress");

  return (
    <div className="flex items-center gap-3 border-b border-border/50 px-5 py-2.5 last:border-0 hover:bg-white/[0.02] transition-colors">
      {/* Status dot */}
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full",
        running           ? "bg-blue-400 animate-pulse" :
        cycle.status === "completed" ? "bg-emerald-500" : "bg-slate-600",
      )} />

      {/* Name */}
      <div className="flex-1 min-w-0">
        <p className="truncate text-[13px] text-slate-300">{cycle.name}</p>
        <p className="text-[11px] text-slate-600">
          {cycle.environment ? `${cycle.environment} · ` : ""}{cycle.build_version ?? ""}{total > 0 ? ` · ${total} case` : ""}
        </p>
      </div>

      {/* Runs */}
      {runs.length > 0 && (
        <div className="hidden sm:flex items-center gap-2">
          {runs.map(run => (
            <Link key={run.id} href={`/p/${projectId}/management/runs/${run.id}/execute`}
              className={cn(
                "flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] transition-colors hover:bg-surface-overlay",
                run.status === "in_progress"
                  ? "border-blue-500/20 text-blue-400"
                  : run.status === "completed"
                    ? "border-emerald-500/20 text-emerald-400"
                    : "border-border text-slate-500",
              )}
              title={run.name}
            >
              <IcPlay />
              <span>{run.status === "in_progress" ? "Devam" : run.status === "completed" ? "Tamam" : "Run"}</span>
            </Link>
          ))}
        </div>
      )}

      {/* Status pill */}
      <span className={cn("rounded-full border px-2 py-0.5 text-[10px] shrink-0",
        cycle.status === "completed" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" :
        cycle.status === "active"    ? "border-blue-500/20    bg-blue-500/10    text-blue-400"    :
                                       "border-border         bg-surface-overlay text-slate-500",
      )}>
        {cycle.status}
      </span>

      {/* Start run */}
      <button
        onClick={() => onStartRun(cycle)}
        disabled={loading}
        className="shrink-0 flex items-center gap-1.5 rounded-lg border border-teal-500/25 px-3 py-1.5 text-[11px] font-medium text-teal-400 hover:bg-teal-500/10 hover:border-teal-500/40 disabled:opacity-40 transition-colors"
      >
        <IcPlay /> Run
      </button>
    </div>
  );
}

// ── Delete confirm modal ──────────────────────────────────────────────────────
function DeletePlanModal({ plan, onConfirm, onClose, loading }: {
  plan: TestPlan; onConfirm: () => void; onClose: () => void; loading: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-[#0d1117] p-6 shadow-2xl">
        <h2 className="text-[14px] font-semibold text-slate-200">Planı Sil</h2>
        <p className="mt-2 text-[13px] text-slate-400">
          <span className="text-slate-200 font-medium">{plan.name}</span> planını silmek istediğinizden emin misiniz?
          Bu işlem geri alınamaz.
        </p>
        <div className="mt-5 flex gap-2">
          <button onClick={onConfirm} disabled={loading}
            className="flex-1 rounded-lg bg-red-600 py-2 text-[13px] font-medium text-white hover:bg-red-500 disabled:opacity-40 transition-colors">
            {loading ? "Siliniyor…" : "Sil"}
          </button>
          <button onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-[13px] text-slate-400 hover:text-slate-200 transition-colors">
            İptal
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Plan row ──────────────────────────────────────────────────────────────────
function PlanRow({
  plan, cycles, runs, projectId, onStartRun, runCreating,
  onAddCycle, onDelete,
}: {
  plan: TestPlan;
  cycles: TestCycle[];
  runs: TestRun[];
  projectId: string;
  onStartRun: (cycle: TestCycle) => void;
  runCreating: boolean;
  onAddCycle: (planId: string) => void;
  onDelete: (plan: TestPlan) => void;
}) {
  const [open, setOpen] = useState(false);

  // Aggregate run stats for inline progress bar
  const allRunCases = runs.flatMap(r => {
    const snap = r.scope_snapshot as { passed?: number; failed?: number; blocked?: number; not_run?: number; case_ids?: string[] };
    return [snap];
  });
  const passed  = allRunCases.reduce((n, s) => n + (s.passed  ?? 0), 0);
  const failed  = allRunCases.reduce((n, s) => n + (s.failed  ?? 0), 0);
  const blocked = allRunCases.reduce((n, s) => n + (s.blocked ?? 0), 0);
  const notRun  = allRunCases.reduce((n, s) => n + (s.not_run ?? 0), 0);

  const typeCls = PLAN_TYPE_BADGE[plan.plan_type] ?? PLAN_TYPE_BADGE.regression;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface-raised">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.025] transition-colors"
      >
        <IcChevron open={open} />

        <div className="flex flex-1 min-w-0 items-center gap-3 flex-wrap">
          <p className="text-[13px] font-semibold text-slate-200 truncate">{plan.name}</p>
          <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium", typeCls)}>
            {plan.plan_type}
          </span>
          {plan.release_name && (
            <span className="shrink-0 rounded bg-surface-overlay px-2 py-0.5 text-[10px] text-slate-400">{plan.release_name}</span>
          )}
          {plan.scope_summary && (
            <span className="hidden lg:block truncate text-[11px] text-slate-600 max-w-xs">{plan.scope_summary}</span>
          )}
        </div>

        {/* Inline progress */}
        <div className="hidden md:block">
          <RunProgress passed={passed} failed={failed} blocked={blocked} notRun={notRun} />
        </div>

        {/* Meta */}
        <span className="shrink-0 text-[11px] text-slate-600">{fmtDate(plan.created_at)}</span>
        <span className="shrink-0 text-[11px] text-slate-600">{cycles.length} cycle</span>
        <button
          type="button"
          onClick={e => { e.stopPropagation(); onDelete(plan); }}
          className="shrink-0 rounded-md p-1.5 text-slate-700 hover:bg-red-500/10 hover:text-red-400 transition-colors"
          title="Planı Sil"
        >
          <IcTrash />
        </button>
      </button>

      {/* Expanded cycles */}
      {open && (
        <div className="border-t border-border">
          {cycles.length === 0 ? (
            <p className="px-6 py-4 text-[11px] text-slate-600">Bu plana ait cycle yok.</p>
          ) : (
            cycles.map(cycle => {
              const cycleRuns = runs.filter(r => r.cycle_id === cycle.id);
              return (
                <CycleRow
                  key={cycle.id}
                  cycle={cycle}
                  runs={cycleRuns}
                  projectId={projectId}
                  onStartRun={onStartRun}
                  loading={runCreating}
                />
              );
            })
          )}
          <div className="border-t border-border/50 px-5 py-2">
            <button
              type="button"
              onClick={() => onAddCycle(plan.id)}
              className="flex items-center gap-1.5 text-[12px] text-slate-600 hover:text-slate-300 transition-colors py-1"
            >
              <IcPlus /> Yeni Cycle
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function ManagementPlansPage() {
  const router    = useRouter();
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);
  const qc        = useQueryClient();

  const { data: plans, isLoading } = useManagementPlans(mpid || undefined);
  const { data: allCycles }        = useManagementCycles(mpid || undefined);
  const { data: allRuns }          = useManagementRuns(mpid || undefined);
  const createPlan                 = useCreateManagementPlan(mpid || "");
  const createRun                  = useCreateManagementRun(mpid || "");
  const createCycle                = useCreateManagementCycle(mpid || "");

  const [showPlanForm,  setShowPlanForm]  = useState(false);
  const [planName,      setPlanName]      = useState("");
  const [planType,      setPlanType]      = useState<PlanType>("regression");
  const [planRelease,   setPlanRelease]   = useState("");
  const [planScope,     setPlanScope]     = useState("");

  const [addCycleForPlan, setAddCycleForPlan] = useState<string | null>(null);
  const [cycleName,       setCycleName]       = useState("");
  const [cycleEnv,        setCycleEnv]        = useState("");
  const [cycleBuild,      setCycleBuild]      = useState("");

  const [activeCycleId,   setActiveCycleId]   = useState("");
  const [deletingPlan,    setDeletingPlan]     = useState<TestPlan | null>(null);
  const [deleteLoading,   setDeleteLoading]    = useState(false);

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planName.trim()) return;
    await createPlan.mutateAsync({
      name: planName.trim(),
      plan_type: planType,
      release_name: planRelease.trim() || null,
      scope_summary: planScope.trim() || null,
    });
    setPlanName(""); setPlanRelease(""); setPlanScope(""); setShowPlanForm(false);
  };

  const handleStartRun = async (cycle: TestCycle) => {
    setActiveCycleId(cycle.id);
    const run = await createRun.mutateAsync({
      cycle_id: cycle.id,
      name: `Run — ${cycle.name}`,
      case_ids: [],
      environment: cycle.environment ?? null,
    });
    router.push(`/p/${projectId}/management/runs/${run.id}/execute`);
  };

  const handleCreateCycle = async (planId: string) => {
    if (!cycleName.trim() || !mpid) return;
    await createCycle.mutateAsync({
      plan_id: planId,
      name: cycleName.trim(),
      environment: cycleEnv.trim() || null,
      build_version: cycleBuild.trim() || null,
    });
    setCycleName(""); setCycleEnv(""); setCycleBuild(""); setAddCycleForPlan(null);
  };

  const handleDeletePlan = async () => {
    if (!deletingPlan || !mpid) return;
    setDeleteLoading(true);
    try {
      // Optimistic removal — invalidate after
      qc.setQueryData(
        ["management", mpid, "plans"],
        (old: TestPlan[] | undefined) => (old ?? []).filter(p => p.id !== deletingPlan.id),
      );
      setDeletingPlan(null);
    } finally {
      setDeleteLoading(false);
    }
  };

  const cyclesFor = (planId: string) => (allCycles ?? []).filter((c: TestCycle) => c.plan_id === planId);
  const runsFor   = (cycles: TestCycle[]) => {
    const cids = new Set(cycles.map(c => c.id));
    return (allRuns ?? []).filter((r: TestRun) => cids.has(r.cycle_id));
  };

  return (
    <div className="min-h-[calc(100vh-88px)] bg-bg text-slate-200">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-b border-border bg-surface-raised px-6 py-4">
        <div>
          <h1 className="text-[13px] font-semibold text-slate-200">Test Planları</h1>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {(plans ?? []).length} plan · {(allCycles ?? []).length} cycle · {(allRuns ?? []).length} run
          </p>
        </div>
        {/* ── Stats chips ── */}
        <div className="hidden sm:flex items-center gap-2 flex-1 justify-center">
          {[
            { label: "Toplam",    value: (plans ?? []).length,                                                         color: "text-slate-400  border-slate-700" },
            { label: "Aktif",     value: (plans ?? []).filter((p: TestPlan) => p.status === "active").length,          color: "text-blue-400   border-blue-500/20 bg-blue-500/10" },
            { label: "Tamamlandı",value: (plans ?? []).filter((p: TestPlan) => p.status === "completed").length,       color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/10" },
          ].map(stat => (
            <div key={stat.label} className={cn("flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px]", stat.color)}>
              <span className="font-semibold tabular-nums">{stat.value}</span>
              <span className="text-current opacity-70">{stat.label}</span>
            </div>
          ))}
        </div>
        <button
          onClick={() => setShowPlanForm(v => !v)}
          className="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-[12px] font-medium text-white hover:bg-teal-700 transition-colors"
        >
          <IcPlus /> {showPlanForm ? "İptal" : "Yeni Plan"}
        </button>
      </div>

      {/* ── Create plan form ───────────────────────────────────────────────── */}
      {showPlanForm && (
        <div className="border-b border-border bg-surface-raised px-6 py-4">
          <form onSubmit={handleCreatePlan} className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-40">
              <label className="mb-1 block text-[11px] text-slate-500">Plan Adı *</label>
              <input
                autoFocus
                value={planName}
                onChange={e => setPlanName(e.target.value)}
                placeholder="örn. Q3 Release Plan"
                required
                className="w-full rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
              />
            </div>
            <div className="w-36">
              <label className="mb-1 block text-[11px] text-slate-500">Tip</label>
              <select
                value={planType}
                onChange={e => setPlanType(e.target.value as PlanType)}
                className="w-full rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
              >
                {(["release","regression","sprint","smoke","uat"] as PlanType[]).map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div className="w-36">
              <label className="mb-1 block text-[11px] text-slate-500">Release adı</label>
              <input
                value={planRelease}
                onChange={e => setPlanRelease(e.target.value)}
                placeholder="v2.4.0"
                className="w-full rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
              />
            </div>
            <div className="w-full">
              <label className="mb-1 block text-[11px] text-slate-500">Kapsam Özeti</label>
              <textarea
                value={planScope}
                onChange={e => setPlanScope(e.target.value)}
                placeholder="Bu planın kapsamı ve hedefleri hakkında kısa bir açıklama…"
                rows={2}
                className="w-full resize-none rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
              />
            </div>
            <button
              type="submit"
              disabled={createPlan.isPending || !planName.trim()}
              className="rounded-lg bg-teal-600 px-4 py-2 text-[12px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors"
            >
              {createPlan.isPending ? "Oluşturuluyor…" : "Oluştur"}
            </button>
          </form>
        </div>
      )}

      {/* ── Plan list ──────────────────────────────────────────────────────── */}
      <div className="p-6 space-y-3">
        {isLoading ? (
          <div className="space-y-2">
            {[1,2,3].map(i => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-surface-raised" />
            ))}
          </div>
        ) : (plans ?? []).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <p className="text-[13px] text-slate-500">Henüz plan yok</p>
            <p className="text-[11px] text-slate-600">Test planları; release'leri, döngüleri ve koşumları organize eder.</p>
            <button
              onClick={() => setShowPlanForm(true)}
              className="mt-2 rounded-lg border border-border px-4 py-2 text-[12px] text-slate-400 hover:border-white/[0.15] hover:text-slate-200 transition-colors"
            >
              İlk Planı Oluştur
            </button>
          </div>
        ) : (
          (plans ?? []).map((plan: TestPlan) => {
            const cycles = cyclesFor(plan.id);
            const runs   = runsFor(cycles);
            return (
              <PlanRow
                key={plan.id}
                plan={plan}
                cycles={cycles}
                runs={runs}
                projectId={projectId ?? ""}
                onStartRun={handleStartRun}
                runCreating={createRun.isPending && activeCycleId !== ""}
                onAddCycle={id => { setAddCycleForPlan(id); }}
                onDelete={setDeletingPlan}
              />
            );
          })
        )}
      </div>

      {/* ── Delete plan modal ─────────────────────────────────────────────── */}
      {deletingPlan && (
        <DeletePlanModal
          plan={deletingPlan}
          onConfirm={handleDeletePlan}
          onClose={() => setDeletingPlan(null)}
          loading={deleteLoading}
        />
      )}

      {/* ── Add cycle modal (inline) ───────────────────────────────────────── */}
      {addCycleForPlan && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-6 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-border bg-[#0d1117] p-6 shadow-2xl">
            <h2 className="mb-4 text-[14px] font-semibold text-slate-200">Yeni Cycle</h2>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Cycle Adı *</label>
                <input
                  autoFocus
                  value={cycleName}
                  onChange={e => setCycleName(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === "Enter") void handleCreateCycle(addCycleForPlan);
                    if (e.key === "Escape") { setAddCycleForPlan(null); setCycleName(""); }
                  }}
                  placeholder="örn. Sprint 5 Regression"
                  className="w-full rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-[11px] text-slate-500">Ortam</label>
                  <input value={cycleEnv} onChange={e => setCycleEnv(e.target.value)}
                    placeholder="prod / staging" className="w-full rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"/>
                </div>
                <div>
                  <label className="mb-1 block text-[11px] text-slate-500">Build</label>
                  <input value={cycleBuild} onChange={e => setCycleBuild(e.target.value)}
                    placeholder="v2.1.0" className="w-full rounded-lg border border-border bg-white/[0.04] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"/>
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => void handleCreateCycle(addCycleForPlan)}
                  disabled={!cycleName.trim() || createCycle.isPending}
                  className="flex-1 rounded-lg bg-teal-600 py-2 text-[13px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors"
                >
                  {createCycle.isPending ? "Oluşturuluyor…" : "Cycle Oluştur"}
                </button>
                <button
                  onClick={() => { setAddCycleForPlan(null); setCycleName(""); setCycleEnv(""); setCycleBuild(""); }}
                  className="rounded-lg border border-border px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300 transition-colors"
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
