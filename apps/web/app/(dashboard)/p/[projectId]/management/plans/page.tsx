"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  useManagementPlans,
  useCreateManagementPlan,
  useManagementCycles,
  useCreateManagementRun,
  useCreateManagementCycle,
  type TestPlan,
  type TestCycle,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const PLAN_TYPE_DOT: Record<string, string> = {
  release:    "bg-blue-500",
  regression: "bg-slate-500",
  sprint:     "bg-slate-500",
  smoke:      "bg-slate-500",
  uat:        "bg-slate-500",
};

const CYCLE_STATUS_DOT: Record<string, string> = {
  active:    "bg-blue-500 animate-pulse",
  completed: "bg-emerald-500",
  draft:     "bg-slate-600",
};

export default function ManagementPlansPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: plans, isLoading } = useManagementPlans(mpid || undefined);
  const { data: allCycles }        = useManagementCycles(mpid || undefined);
  const createPlan                 = useCreateManagementPlan(mpid || "");
  const createRun                  = useCreateManagementRun(mpid || "");

  const createCycle = useCreateManagementCycle(mpid || "");

  const [showForm,       setShowForm]       = useState(false);
  const [planName,       setPlanName]       = useState("");
  const [planType,       setPlanType]       = useState("regression");
  const [expandedPlanId, setExpandedPlanId] = useState<string | null>(null);
  const [addCycleForPlan, setAddCycleForPlan] = useState<string | null>(null);
  const [cycleName,      setCycleName]      = useState("");
  const [cycleEnv,       setCycleEnv]       = useState("");
  const [cycleBuild,     setCycleBuild]     = useState("");
  const [cycleRunPlanId, setCycleRunPlanId] = useState("");
  const [page,           setPage]           = useState(1);
  const PAGE_SIZE = 20;

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planName.trim()) return;
    await createPlan.mutateAsync({ name: planName.trim(), plan_type: planType });
    setPlanName("");
    setShowForm(false);
  };

  const handleStartRun = async (cycle: TestCycle) => {
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
    setCycleName("");
    setCycleEnv("");
    setCycleBuild("");
    setAddCycleForPlan(null);
  };

  const cyclesForPlan = (planId: string) =>
    (allCycles ?? []).filter((c: TestCycle) => c.plan_id === planId);

  return (
    <div className="min-h-[calc(100vh-88px)] bg-[#0a0f1e] text-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.06] bg-[#0d1221] px-6 py-4">
        <h1 className="text-[13px] font-semibold text-slate-200">Test Planları</h1>
        <button
          onClick={() => setShowForm(v => !v)}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-[11px] font-medium text-white hover:bg-blue-500 transition-colors"
        >
          {showForm ? "İptal" : "+ Yeni Plan"}
        </button>
      </div>

      {/* Inline create form */}
      {showForm && (
        <div className="border-b border-white/[0.06] bg-[#0d1221] px-6 py-4">
          <form onSubmit={handleCreatePlan} className="flex items-end gap-3 flex-wrap">
            <div className="flex-1 min-w-48">
              <label className="mb-1 block text-[11px] text-slate-500">Plan Adı</label>
              <input
                value={planName}
                onChange={e => setPlanName(e.target.value)}
                placeholder="örn. Q2 Release Plan"
                required
                className="w-full rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
              />
            </div>
            <div className="w-44">
              <label className="mb-1 block text-[11px] text-slate-500">Tip</label>
              <select
                value={planType}
                onChange={e => setPlanType(e.target.value)}
                className="w-full rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
              >
                <option value="release">Release</option>
                <option value="regression">Regression</option>
                <option value="sprint">Sprint</option>
                <option value="smoke">Smoke</option>
                <option value="uat">UAT</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={createPlan.isPending || !planName.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-[11px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
            >
              {createPlan.isPending ? "Oluşturuluyor…" : "Oluştur"}
            </button>
          </form>
        </div>
      )}

      {/* Plan grid */}
      <div className="p-6">
        {isLoading ? (
          <div className="animate-pulse grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-28 rounded-xl bg-white/[0.04]" />
            ))}
          </div>
        ) : (plans ?? []).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-2">
            <p className="text-[13px] text-slate-500">Henüz plan yok</p>
            <button onClick={() => setShowForm(true)}
              className="rounded-md border border-white/[0.08] px-4 py-2 text-[11px] text-slate-400 hover:border-white/[0.15] hover:text-slate-200 transition-colors">
              Yeni Plan Oluştur
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {(plans ?? []).slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((plan: TestPlan) => {
              const dot      = PLAN_TYPE_DOT[plan.plan_type] ?? "bg-slate-500";
              const cycles   = cyclesForPlan(plan.id);
              const expanded = expandedPlanId === plan.id;

              return (
                <div key={plan.id} className="rounded-xl border border-white/[0.06] bg-[#0d1221] overflow-hidden">
                  {/* Card header */}
                  <button
                    onClick={() => setExpandedPlanId(expanded ? null : plan.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.04] transition-colors"
                  >
                    <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${dot}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-medium text-slate-200 truncate">{plan.name}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {plan.plan_type} · {cycles.length} cycle ·{" "}
                        {new Date(plan.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}
                      </p>
                    </div>
                    <span className="text-[11px] text-slate-600">{expanded ? "▲" : "▼"}</span>
                  </button>

                  {/* Expanded cycles */}
                  {expanded && (
                    <div className="border-t border-white/[0.06]">
                      {cycles.length === 0 && addCycleForPlan !== plan.id ? (
                        <p className="px-6 py-4 text-[11px] text-slate-600">Bu plana ait cycle yok.</p>
                      ) : (
                        cycles.map((cycle: TestCycle) => {
                          const cDot = CYCLE_STATUS_DOT[cycle.status] ?? "bg-slate-600";
                          return (
                            <div key={cycle.id}
                              className="flex items-center gap-3 border-b border-white/[0.04] px-5 py-3 last:border-b-0 hover:bg-white/[0.03] transition-colors">
                              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${cDot}`} />
                              <div className="flex-1 min-w-0">
                                <p className="truncate text-[13px] text-slate-300">{cycle.name}</p>
                                <p className="text-[11px] text-slate-500">
                                  {cycle.environment ?? "—"}{cycle.build_version ? ` · ${cycle.build_version}` : ""}
                                </p>
                              </div>
                              <span className={`rounded-full border px-2 py-0.5 text-[10px] ${
                                cycle.status === "active"    ? "border-blue-500/20 bg-blue-500/10 text-blue-400" :
                                cycle.status === "completed" ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-400" :
                                "border-slate-700 bg-slate-800 text-slate-500"
                              }`}>{cycle.status}</span>
                              <button
                                onClick={() => { setCycleRunPlanId(cycle.id); handleStartRun(cycle); }}
                                disabled={createRun.isPending && cycleRunPlanId === cycle.id}
                                className="rounded-lg border border-blue-500/30 px-3 py-1 text-[11px] text-blue-500 hover:bg-blue-500/10 disabled:opacity-40 transition-colors"
                              >
                                {createRun.isPending && cycleRunPlanId === cycle.id ? "…" : "▶ Run"}
                              </button>
                            </div>
                          );
                        })
                      )}

                      {/* New cycle form */}
                      {addCycleForPlan === plan.id ? (
                        <div className="border-t border-white/[0.04] bg-blue-500/[0.03] px-5 py-3">
                          <p className="mb-2.5 text-[10px] font-medium uppercase tracking-widest text-slate-600">Yeni Cycle</p>
                          <div className="space-y-2">
                            <input
                              autoFocus
                              type="text"
                              value={cycleName}
                              onChange={e => setCycleName(e.target.value)}
                              onKeyDown={e => { if (e.key === "Enter") handleCreateCycle(plan.id); if (e.key === "Escape") { setAddCycleForPlan(null); setCycleName(""); }}}
                              placeholder="Cycle adı *"
                              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/40 transition-colors"
                            />
                            <div className="grid grid-cols-2 gap-2">
                              <input type="text" value={cycleEnv} onChange={e => setCycleEnv(e.target.value)}
                                placeholder="Ortam (prod/staging)"
                                className="rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/40 transition-colors"/>
                              <input type="text" value={cycleBuild} onChange={e => setCycleBuild(e.target.value)}
                                placeholder="Build (v2.1.0)"
                                className="rounded-xl border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[12px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/40 transition-colors"/>
                            </div>
                            <div className="flex gap-2">
                              <button type="button"
                                onClick={() => handleCreateCycle(plan.id)}
                                disabled={!cycleName.trim() || createCycle.isPending}
                                className="flex-1 rounded-xl bg-blue-600 py-2 text-[13px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
                                {createCycle.isPending ? "Oluşturuluyor…" : "Cycle Oluştur"}
                              </button>
                              <button type="button"
                                onClick={() => { setAddCycleForPlan(null); setCycleName(""); setCycleEnv(""); setCycleBuild(""); }}
                                className="rounded-xl border border-white/[0.08] px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300 transition-colors">
                                İptal
                              </button>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="border-t border-white/[0.04] px-5 py-2">
                          <button type="button"
                            onClick={() => { setAddCycleForPlan(plan.id); setExpandedPlanId(plan.id); }}
                            className="flex w-full items-center gap-1.5 rounded-lg py-1.5 text-[12px] text-slate-600 hover:text-slate-400 transition-colors">
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
                            </svg>
                            Yeni Cycle Ekle
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Pagination */}
            {(plans ?? []).length > PAGE_SIZE && (
              <div className="flex items-center justify-between border-t border-white/[0.06] pt-4 mt-2">
                <span className="text-[11px] text-slate-500">
                  {(plans ?? []).length} plandan {Math.min(page * PAGE_SIZE, (plans ?? []).length)} tanesi
                </span>
                <div className="flex items-center gap-2">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage(p => p - 1)}
                    className="rounded border border-white/[0.08] px-3 py-1 text-[11px] text-slate-400 hover:border-white/[0.15] disabled:opacity-30 disabled:cursor-not-allowed"
                  >← Önceki</button>
                  <span className="text-[11px] text-slate-500">{page} / {Math.ceil((plans ?? []).length / PAGE_SIZE)}</span>
                  <button
                    disabled={page >= Math.ceil((plans ?? []).length / PAGE_SIZE)}
                    onClick={() => setPage(p => p + 1)}
                    className="rounded border border-white/[0.08] px-3 py-1 text-[11px] text-slate-400 hover:border-white/[0.15] disabled:opacity-30 disabled:cursor-not-allowed"
                  >Sonraki →</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
