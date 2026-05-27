"use client";

import { useMemo, useState } from "react";

import {
  useCreateManagementCycle,
  useCreateManagementPlan,
  useManagementCycles,
  useManagementPlans,
  useManagementRepository,
  useRegressionSets,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementPlansPage({ params }: { params: { projectId: string } }) {
  const plans = useManagementPlans(params.projectId);
  const cycles = useManagementCycles(params.projectId);
  const repository = useManagementRepository(params.projectId);
  const regressionSets = useRegressionSets(params.projectId);
  const createPlan = useCreateManagementPlan(params.projectId);
  const createCycle = useCreateManagementCycle(params.projectId);
  const [planName, setPlanName] = useState("");
  const [planType, setPlanType] = useState("regression");
  const [releaseName, setReleaseName] = useState("");
  const [regressionSetId, setRegressionSetId] = useState("");
  const [scopeObjective, setScopeObjective] = useState("");
  const [scopeAreas, setScopeAreas] = useState("");
  const [scopeExclusions, setScopeExclusions] = useState("");
  const [scopeNotes, setScopeNotes] = useState("");
  const [cycleName, setCycleName] = useState("");
  const [cyclePlanId, setCyclePlanId] = useState("");
  const [environment, setEnvironment] = useState("");
  const [buildVersion, setBuildVersion] = useState("");
  const activePlans = plans.data?.filter((plan) => plan.status !== "archived").length ?? 0;
  const caseCount = repository.data?.cases.length ?? 0;
  const readyCases = repository.data?.cases.filter((item) => ["ready", "active"].includes(item.status)).length ?? 0;
  const readyPct = caseCount ? Math.round((readyCases / caseCount) * 100) : 0;
  const selectedSet = useMemo(
    () => (regressionSets.data ?? []).find((item) => item.id === regressionSetId),
    [regressionSetId, regressionSets.data],
  );
  const selectedSetCaseCount = selectedSet?.cases.length ?? 0;
  const selectedSetRiskTotal = selectedSet?.cases.reduce((sum, item) => sum + (item.risk_score ?? 0), 0) ?? 0;
  const scopeSummary = useMemo(() => {
    const rows = [
      `Regression set: ${selectedSet ? `${selectedSet.name} (${selectedSet.cases.length} case, risk ${selectedSetRiskTotal})` : "Seçilmedi"}`,
      scopeObjective.trim() ? `Amaç: ${scopeObjective.trim()}` : "",
      scopeAreas.trim() ? `Kapsam: ${scopeAreas.trim()}` : "",
      scopeExclusions.trim() ? `Hariç: ${scopeExclusions.trim()}` : "",
      scopeNotes.trim() ? `Notlar: ${scopeNotes.trim()}` : "",
    ].filter(Boolean);

    return rows.join("\n");
  }, [scopeAreas, scopeExclusions, scopeNotes, scopeObjective, selectedSet, selectedSetRiskTotal]);

  return (
    <ManagementShell projectId={params.projectId} title="Test Plans" description="Release, sprint, regression ve UAT planları için case seçimi, cycle ve kapsam yönetimi." active="management/plans">
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat label="Active Plans" value={plans.isLoading ? "…" : String(activePlans)} note={`${cycles.data?.length ?? 0} cycle`} />
        <ManagementStat label="Repository Cases" value={repository.isLoading ? "…" : String(caseCount)} note="plan kapsamına seçilebilir" />
        <ManagementStat label="Ready to Run" value={repository.isLoading ? "…" : `${readyPct}%`} note="ready/active case oranı" />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <ManagementPanel title="Create Plan">
          <form
            className="space-y-3"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!planName.trim()) return;
              await createPlan.mutateAsync({
                name: planName.trim(),
                plan_type: planType,
                release_name: releaseName.trim() || null,
                scope_summary: scopeSummary || null,
              });
              setPlanName("");
              setReleaseName("");
              setRegressionSetId("");
              setScopeObjective("");
              setScopeAreas("");
              setScopeExclusions("");
              setScopeNotes("");
            }}
          >
            <input
              value={planName}
              onChange={(event) => setPlanName(event.target.value)}
              placeholder="Plan adı"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
            />
            <div className="grid gap-3 md:grid-cols-2">
              <select
                value={planType}
                onChange={(event) => setPlanType(event.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
              >
                <option value="regression">Regression</option>
                <option value="release">Release</option>
                <option value="sprint">Sprint</option>
                <option value="uat">UAT</option>
                <option value="smoke">Smoke</option>
              </select>
              <input
                value={releaseName}
                onChange={(event) => setReleaseName(event.target.value)}
                placeholder="Release / Sprint"
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
              />
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
              <div className="mb-3 grid gap-3 md:grid-cols-[1fr_auto_auto]">
                <select
                  value={regressionSetId}
                  onChange={(event) => setRegressionSetId(event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                >
                  <option value="">Kayıtlı regression set seç</option>
                  {(regressionSets.data ?? []).map((set) => (
                    <option key={set.id} value={set.id}>{set.name} ({set.cases.length})</option>
                  ))}
                </select>
                <div className="rounded-lg border border-slate-800 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Cases</p>
                  <p className="text-sm font-semibold text-slate-100">{regressionSets.isLoading ? "..." : selectedSetCaseCount}</p>
                </div>
                <div className="rounded-lg border border-slate-800 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Risk</p>
                  <p className="text-sm font-semibold text-amber-300">{regressionSets.isLoading ? "..." : selectedSetRiskTotal}</p>
                </div>
              </div>
              <div className="grid gap-3">
                <textarea
                  value={scopeObjective}
                  onChange={(event) => setScopeObjective(event.target.value)}
                  rows={2}
                  placeholder="Plan amacı: release riskleri, kritik akışlar, müşteri taahhüdü..."
                  className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                />
                <textarea
                  value={scopeAreas}
                  onChange={(event) => setScopeAreas(event.target.value)}
                  rows={2}
                  placeholder="Kapsam: modüller, tag'ler, priority/severity kararları, platformlar..."
                  className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                />
                <div className="grid gap-3 md:grid-cols-2">
                  <textarea
                    value={scopeExclusions}
                    onChange={(event) => setScopeExclusions(event.target.value)}
                    rows={2}
                    placeholder="Hariç tutulanlar"
                    className="resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                  />
                  <textarea
                    value={scopeNotes}
                    onChange={(event) => setScopeNotes(event.target.value)}
                    rows={2}
                    placeholder="Kabul kriteri / özel notlar"
                    className="resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Scope Summary Preview</p>
                  <pre className="whitespace-pre-wrap text-xs leading-5 text-slate-300">{scopeSummary || "Regression set ve kapsam alanları dolduruldukça plan özeti burada oluşur."}</pre>
                </div>
              </div>
            </div>
            <button
              disabled={createPlan.isPending || !planName.trim()}
              className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
            >
              {createPlan.isPending ? "Oluşturuluyor..." : "Plan Oluştur"}
            </button>
          </form>
        </ManagementPanel>

        <ManagementPanel title="Create Cycle">
          <form
            className="space-y-3"
            onSubmit={async (event) => {
              event.preventDefault();
              const selectedPlan = cyclePlanId || plans.data?.[0]?.id;
              if (!cycleName.trim() || !selectedPlan) return;
              await createCycle.mutateAsync({
                plan_id: selectedPlan,
                name: cycleName.trim(),
                environment: environment.trim() || null,
                build_version: buildVersion.trim() || null,
              });
              setCycleName("");
              setEnvironment("");
              setBuildVersion("");
            }}
          >
            <select
              value={cyclePlanId}
              onChange={(event) => setCyclePlanId(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
            >
              <option value="">Plan seç</option>
              {(plans.data ?? []).map((plan) => (
                <option key={plan.id} value={plan.id}>{plan.name}</option>
              ))}
            </select>
            <input
              value={cycleName}
              onChange={(event) => setCycleName(event.target.value)}
              placeholder="Cycle adı"
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
            />
            <div className="grid gap-3 md:grid-cols-2">
              <input
                value={environment}
                onChange={(event) => setEnvironment(event.target.value)}
                placeholder="Environment"
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
              />
              <input
                value={buildVersion}
                onChange={(event) => setBuildVersion(event.target.value)}
                placeholder="Build"
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
              />
            </div>
            <button
              disabled={createCycle.isPending || !cycleName.trim() || !(cyclePlanId || plans.data?.[0]?.id)}
              className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
            >
              {createCycle.isPending ? "Oluşturuluyor..." : "Cycle Oluştur"}
            </button>
          </form>
        </ManagementPanel>
      </div>

      <ManagementPanel title="Plan Builder Contract">
        <div className="space-y-3 text-sm leading-6 text-slate-300">
          <p>
            Plan oluşturma akışı repository filtrelerinden case seçer, cycle bilgisiyle ortam/build snapshot'ı alır ve run oluştururken her case için `case_version_no` değerini sabitler.
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-xs uppercase tracking-wide text-slate-500">
                <tr><th className="px-3 py-2">Plan</th><th>Type</th><th>Status</th><th>Release</th><th>Scope Summary</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {(plans.data ?? []).slice(0, 10).map((plan) => (
                  <tr key={plan.id}>
                    <td className="px-3 py-2 text-slate-200">{plan.name}</td>
                    <td className="text-slate-400">{plan.plan_type}</td>
                    <td className="text-slate-400">{plan.status}</td>
                    <td className="text-slate-500">{plan.release_name ?? "—"}</td>
                    <td className="max-w-lg whitespace-pre-wrap px-3 py-2 text-xs leading-5 text-slate-400">{plan.scope_summary ?? "—"}</td>
                  </tr>
                ))}
                {!plans.isLoading && (plans.data ?? []).length === 0 ? (
                  <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-500">Henüz plan yok.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
