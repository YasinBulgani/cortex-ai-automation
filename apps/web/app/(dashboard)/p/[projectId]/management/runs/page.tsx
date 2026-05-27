"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import {
  useCreateManagementRun,
  useExecutionSummary,
  useManagementCases,
  useManagementCycles,
  useManagementRuns,
  useRegressionSets,
} from "@/lib/hooks/use-management";

import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

export default function ManagementRunsPage({ params }: { params: { projectId: string } }) {
  const summary = useExecutionSummary(params.projectId);
  const runs = useManagementRuns(params.projectId);
  const cycles = useManagementCycles(params.projectId);
  const cases = useManagementCases(params.projectId);
  const regressionSets = useRegressionSets(params.projectId);
  const createRun = useCreateManagementRun(params.projectId);
  const [runName, setRunName] = useState("");
  const [cycleId, setCycleId] = useState("");
  const [regressionSetId, setRegressionSetId] = useState("");
  const data = summary.data;
  const runnableCases = useMemo(
    () => (cases.data ?? []).filter((item) => ["active", "ready"].includes(item.status) && !item.archived),
    [cases.data],
  );

  return (
    <ManagementShell projectId={params.projectId} title="Test Runs" description="Tester assignment, adım bazlı execution, actual result, evidence ve defect link akışları." active="management/runs">
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat label="Not Run" value={data ? String(data.not_run) : summary.isLoading ? "…" : "0"} note="atanmış bekliyor" />
        <ManagementStat label="Passed" value={data ? String(data.passed) : summary.isLoading ? "…" : "0"} note="son cycle" />
        <ManagementStat label="Failed" value={data ? String(data.failed) : summary.isLoading ? "…" : "0"} note="aksiyon bekliyor" />
        <ManagementStat label="Blocked" value={data ? String(data.blocked) : summary.isLoading ? "…" : "0"} note={`${runs.data?.length ?? 0} run`} />
      </div>
      <ManagementPanel title="Execution Rules">
        <div className="space-y-4">
          <form
            className="grid gap-3 rounded-lg border border-slate-800 bg-slate-950/50 p-3 md:grid-cols-[1fr_1fr_1fr_auto]"
            onSubmit={async (event) => {
              event.preventDefault();
              const selectedCycle = cycleId || cycles.data?.[0]?.id;
              const selectedSet = (regressionSets.data ?? []).find((item) => item.id === regressionSetId);
              const selectedCaseIds = selectedSet ? selectedSet.cases.map((item) => item.case_id) : runnableCases.map((item) => item.id);
              if (!runName.trim() || !selectedCycle || selectedCaseIds.length === 0) return;
              const run = await createRun.mutateAsync({
                cycle_id: selectedCycle,
                name: runName.trim(),
                case_ids: selectedCaseIds,
                source_type: selectedSet ? "regression_set" : "manual",
                source_ref: selectedSet?.id ?? null,
                scope_snapshot: selectedSet
                  ? {
                      regression_set_id: selectedSet.id,
                      regression_set_name: selectedSet.name,
                      case_count: selectedSet.cases.length,
                      cases: selectedSet.cases.map((item) => ({
                        case_id: item.case_id,
                        case_key: item.case_key,
                        case_version_no: item.case_version_no,
                        title: item.title,
                        risk_score: item.risk_score,
                      })),
                    }
                  : { source: "ready_active_cases", case_count: selectedCaseIds.length },
              });
              setRunName("");
              window.location.href = `/p/${params.projectId}/management/runs/${run.id}/execute`;
            }}
          >
            <input
              value={runName}
              onChange={(event) => setRunName(event.target.value)}
              placeholder="Run adı"
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
            />
            <select
              value={cycleId}
              onChange={(event) => setCycleId(event.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
            >
              <option value="">Cycle seç</option>
              {(cycles.data ?? []).map((cycle) => (
                <option key={cycle.id} value={cycle.id}>{cycle.name}</option>
              ))}
            </select>
            <select
              value={regressionSetId}
              onChange={(event) => setRegressionSetId(event.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-500"
            >
              <option value="">Tüm ready/active case'ler</option>
              {(regressionSets.data ?? []).map((set) => (
                <option key={set.id} value={set.id}>{set.name} ({set.cases.length})</option>
              ))}
            </select>
            <button
              disabled={createRun.isPending || !runName.trim() || !(cycleId || cycles.data?.[0]?.id) || (regressionSetId ? !((regressionSets.data ?? []).find((item) => item.id === regressionSetId)?.cases.length) : runnableCases.length === 0)}
              className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400 disabled:opacity-40"
            >
              {createRun.isPending ? "Başlatılıyor..." : `${regressionSetId ? ((regressionSets.data ?? []).find((item) => item.id === regressionSetId)?.cases.length ?? 0) : runnableCases.length} Case ile Başlat`}
            </button>
          </form>
          <ul className="space-y-2 text-sm text-slate-300">
            <li>Run case, test case'in başladığı andaki versiyonunu koşar.</li>
            <li>Failed veya blocked sonuçta actual result zorunlu olur.</li>
            <li>Evidence case'e değil run result'a bağlanır.</li>
          </ul>
          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-xs uppercase tracking-wide text-slate-500">
                <tr><th className="px-3 py-2">Run</th><th>Status</th><th>Started</th><th>Completed</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {(runs.data ?? []).slice(0, 10).map((run) => (
                  <tr key={run.id}>
                    <td className="px-3 py-2 text-slate-200">
                      <Link href={`/p/${params.projectId}/management/runs/${run.id}/execute`} className="hover:text-cyan-300">
                        {run.name}
                      </Link>
                    </td>
                    <td className="text-slate-400">{run.status}</td>
                    <td className="text-slate-500">{run.started_at ? new Date(run.started_at).toLocaleString("tr-TR") : "—"}</td>
                    <td className="text-slate-500">{run.completed_at ? new Date(run.completed_at).toLocaleString("tr-TR") : "—"}</td>
                  </tr>
                ))}
                {!runs.isLoading && (runs.data ?? []).length === 0 ? (
                  <tr><td colSpan={4} className="px-3 py-6 text-center text-slate-500">Henüz run yok.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </ManagementPanel>
    </ManagementShell>
  );
}
