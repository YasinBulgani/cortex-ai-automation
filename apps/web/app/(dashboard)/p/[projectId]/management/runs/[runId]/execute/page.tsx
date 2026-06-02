"use client";

import { useState } from "react";
import {
  useCreateManagementDefect,
  useManagementEvidence,
  useManagementRun,
  useUpdateManagementStepResult,
  type RunCase,
} from "@/lib/hooks/use-management";
import { apiFetch } from "@/lib/api-client";
import { ManagementPanel, ManagementShell, ManagementStat } from "../../../_components/ManagementShell";
import { EvidenceModal } from "../../../_components/EvidenceModal";
  const dotClass = STATUS_DOT[runCase.status] ?? "bg-slate-600";
  const bulkMutation = useUpdateManagementStepResult(projectId, runCase.id, runId);

  // Map step_results to a lookup by step_no for quick access.
  const resultsByStepNo: Record<number, { status: StepStatus; actual_result?: string | null }> =
    Object.fromEntries(
      runCase.step_results.map((r) => [
        r.step_no,
        { status: r.status as StepStatus, actual_result: r.actual_result },
      ]),
    );

  const snapshot = runCase.case_snapshot as {
    case?: SnapshotCase;
    steps?: Array<Omit<ExecutionStep, "id"> & { id?: string }>;
  };
  const snapshotCase = snapshot.case ?? {};
  const steps: ExecutionStep[] = (snapshot.steps ?? []).map((step) => ({
    id: step.id ?? `${runCase.id}-${step.step_no}`,
    step_no: step.step_no,
    action: step.action,
    expected_result: step.expected_result,
    test_data: step.test_data,
    notes: step.notes,
    is_required: step.is_required,
  }));
  const completedSteps = steps.filter((step) =>
    ["passed", "skipped"].includes(resultsByStepNo[step.step_no]?.status ?? ""),
  ).length;

  const markCasePassed = async () => {
    for (const step of steps) {
      await bulkMutation.mutateAsync({
        stepNo: step.step_no,
        status: "passed",
        actual_result: resultsByStepNo[step.step_no]?.actual_result ?? "Beklenen sonuç gözlendi.",
      });
    }
    setBulkSaved(true);
    setTimeout(() => setBulkSaved(false), 2000);
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50">
      {/* Case header */}
      <div
        className="flex cursor-pointer items-center gap-3 p-4"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={`h-3 w-3 flex-shrink-0 rounded-full ${dotClass}`} />
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-medium text-white">
            {snapshotCase.case_key ? <span className="mr-2 font-mono text-xs text-slate-500">{snapshotCase.case_key}</span> : null}
            {snapshotCase.title ?? runCase.case_id}
          </p>
          <p className="text-xs text-slate-500">
            {runCase.step_results.length}/{steps.length} adım kaydedildi ·{" "}
            {runCase.status.replace("_", " ")}
          </p>
        </div>
        <div className="hidden shrink-0 items-center gap-2 md:flex">
          <span className="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-400">
            {completedSteps}/{steps.length} ok
          </span>
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              void markCasePassed();
            }}
            disabled={bulkMutation.isPending || steps.length === 0}
            className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-40"
          >
            {bulkMutation.isPending ? "İşleniyor..." : bulkSaved ? "Kaydedildi" : "Case Pass"}
          </button>
          <button
            type="button"
            onClick={(event) => { event.stopPropagation(); setShowEvidenceModal(true); }}
            className="rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/10"
          >
            Case Fail + Evidence
          </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementRunExecutePage({
  params,
}: {
  params: { projectId: string; runId: string };
}) {
  const { projectId, runId } = params;
  const runQuery   = useManagementRun(projectId, runId);
  const [statusFilter, setStatusFilter] = useState("all");

  const run   = runQuery.data;

  // Stats derived from run_cases.
  const runCases   = run?.run_cases ?? [];
  const total      = runCases.length;
  const done       = runCases.filter((rc) => ["passed", "failed", "blocked", "skipped"].includes(rc.status)).length;
  const failed     = runCases.filter((rc) => rc.status === "failed").length;
  const notRun     = runCases.filter((rc) => rc.status === "not_run").length;
  const filteredRunCases = statusFilter === "all"
    ? runCases
    : runCases.filter((rc) => rc.status === statusFilter);

  const loading = runQuery.isLoading;

  return (
    <ManagementShell
      projectId={projectId}
      title={run ? `Execute: ${run.name}` : "Execute Run"}
      description="Tester odaklı adım adım koşum — actual result, step status ve defect linkleme."
      active="management/runs"
    >
      {/* ── Stats ── */}
      <div className="grid gap-4 md:grid-cols-4">
        <ManagementStat
          label="Total Cases"
          value={loading ? "…" : String(total)}
          note="bu run'da"
        />
        <ManagementStat
          label="Done"
          value={loading ? "…" : String(done)}
          note={`${total > 0 ? ((done / total) * 100).toFixed(0) : 0}% tamamlandı`}
        />
        <ManagementStat
          label="Failed"
          value={loading ? "…" : String(failed)}
          note="defect bekliyor"
        />
        <ManagementStat
          label="Not Run"
          value={loading ? "…" : String(notRun)}
          note="bekleyen case"
        />
      </div>

      {/* ── Case list ── */}
      <div className="mt-6 space-y-3">
        <ManagementPanel title="Koşum Filtreleri">
          <div className="flex flex-wrap gap-2">
            {[
              ["all", `Tümü (${runCases.length})`],
              ["not_run", `Not Run (${notRun})`],
              ["in_progress", `In Progress (${runCases.filter((rc) => rc.status === "in_progress").length})`],
              ["passed", `Passed (${runCases.filter((rc) => rc.status === "passed").length})`],
              ["failed", `Failed (${failed})`],
              ["blocked", `Blocked (${runCases.filter((rc) => rc.status === "blocked").length})`],
            ].map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setStatusFilter(value)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
                  statusFilter === value
                    ? "bg-teal-500 text-slate-950"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </ManagementPanel>
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
          </div>
        ) : runCases.length === 0 ? (
          <ManagementPanel title="Koşum Case'leri">
            <p className="text-sm text-slate-500">Bu run'a henüz case eklenmemiş.</p>
          </ManagementPanel>
        ) : filteredRunCases.length === 0 ? (
          <ManagementPanel title="Koşum Case'leri">
            <p className="text-sm text-slate-500">Bu filtrede case yok.</p>
          </ManagementPanel>
        ) : (
          filteredRunCases.map((rc) => (
            <CasePanel
              key={rc.id}
              runCase={rc}
              projectId={projectId}
              runId={runId}
            />
          ))
        )}
      </div>
    </ManagementShell>
  );
}
