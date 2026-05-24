"use client";

import { useState } from "react";
import {
  useManagementRun,
  useManagementCases,
  useUpdateManagementStepResult,
  type RunCase,
  type TestCase,
  type TestCaseStep,
} from "@/lib/hooks/use-management";
import { ManagementPanel, ManagementShell, ManagementStat } from "../../../_components/ManagementShell";

// ── Types ─────────────────────────────────────────────────────────────────────

type StepStatus = "not_run" | "passed" | "failed" | "blocked" | "skipped";

const STEP_STATUSES: { value: StepStatus; label: string; color: string; bg: string }[] = [
  { value: "not_run",  label: "Not Run",  color: "text-slate-400",   bg: "bg-slate-700" },
  { value: "passed",   label: "Pass",     color: "text-emerald-400", bg: "bg-emerald-600" },
  { value: "failed",   label: "Fail",     color: "text-rose-400",    bg: "bg-rose-600" },
  { value: "blocked",  label: "Blocked",  color: "text-amber-400",   bg: "bg-amber-600" },
  { value: "skipped",  label: "Skip",     color: "text-slate-400",   bg: "bg-slate-600" },
];

const STATUS_DOT: Record<string, string> = {
  not_run: "bg-slate-600",
  passed:  "bg-emerald-500",
  failed:  "bg-rose-500",
  blocked: "bg-amber-500",
  skipped: "bg-slate-500",
};

// ── Step row ──────────────────────────────────────────────────────────────────

function StepRow({
  step,
  runCaseId,
  projectId,
  existingStatus,
  existingActual,
}: {
  step: TestCaseStep;
  runCaseId: string;
  projectId: string;
  existingStatus: StepStatus;
  existingActual?: string | null;
}) {
  const [status, setStatus] = useState<StepStatus>(existingStatus);
  const [actual, setActual] = useState(existingActual ?? "");
  const [expanded, setExpanded] = useState(false);
  const [saved, setSaved] = useState(false);
  const mutation = useUpdateManagementStepResult(projectId, runCaseId);

  const handleSave = async () => {
    await mutation.mutateAsync({ stepNo: step.step_no, status, actual_result: actual || null });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const dotClass = STATUS_DOT[status] ?? "bg-slate-600";

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900">
      {/* ── Header row ── */}
      <div
        className="flex cursor-pointer items-center gap-3 px-4 py-3"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className={`h-2.5 w-2.5 flex-shrink-0 rounded-full ${dotClass}`} />
        <span className="w-6 flex-shrink-0 text-center text-xs font-mono text-slate-500">
          {step.step_no}
        </span>
        <span className="flex-1 text-sm text-slate-200 line-clamp-1">{step.action}</span>
        <span
          className={`flex-shrink-0 rounded px-2 py-0.5 text-xs font-medium ${
            STEP_STATUSES.find((s) => s.value === status)?.color ?? "text-slate-400"
          }`}
        >
          {STEP_STATUSES.find((s) => s.value === status)?.label ?? status}
        </span>
        <svg
          className={`h-4 w-4 flex-shrink-0 text-slate-500 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* ── Expanded detail ── */}
      {expanded && (
        <div className="border-t border-slate-800 px-4 pb-4 pt-3 space-y-3">
          <div className="grid gap-3 text-sm md:grid-cols-2">
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Action</p>
              <p className="text-slate-300">{step.action}</p>
            </div>
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Expected Result</p>
              <p className="text-slate-300">{step.expected_result}</p>
            </div>
          </div>

          {/* Status picker */}
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Step Status</p>
            <div className="flex flex-wrap gap-2">
              {STEP_STATUSES.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setStatus(s.value)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    status === s.value
                      ? `${s.bg} text-white ring-2 ring-offset-1 ring-offset-slate-900 ring-white/30`
                      : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Actual result */}
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">Actual Result</p>
            <textarea
              value={actual}
              onChange={(e) => setActual(e.target.value)}
              rows={2}
              placeholder="Gözlemlenen davranışı girin…"
              className="w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500/50 focus:outline-none"
            />
          </div>

          {/* Save button */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={mutation.isPending}
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:opacity-40"
            >
              {mutation.isPending ? "Kaydediliyor…" : saved ? "✓ Kaydedildi" : "Kaydet"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Case panel ────────────────────────────────────────────────────────────────

function CasePanel({
  runCase,
  caseData,
  projectId,
}: {
  runCase: RunCase;
  caseData?: TestCase;
  projectId: string;
}) {
  const [open, setOpen] = useState(false);
  const dotClass = STATUS_DOT[runCase.status] ?? "bg-slate-600";

  // Map step_results to a lookup by step_no for quick access.
  const resultsByStepNo: Record<number, { status: StepStatus; actual_result?: string | null }> =
    Object.fromEntries(
      runCase.step_results.map((r) => [
        r.step_no,
        { status: r.status as StepStatus, actual_result: r.actual_result },
      ]),
    );

  const steps: TestCaseStep[] = caseData?.steps ?? [];

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50">
      {/* Case header */}
      <div
        className="flex cursor-pointer items-center gap-3 p-4"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={`h-3 w-3 flex-shrink-0 rounded-full ${dotClass}`} />
        <div className="flex-1 min-w-0">
          <p className="truncate text-sm font-medium text-white">
            {caseData?.case_key ? <span className="mr-2 font-mono text-xs text-slate-500">{caseData.case_key}</span> : null}
            {caseData?.title ?? runCase.case_id}
          </p>
          <p className="text-xs text-slate-500">
            {runCase.step_results.length}/{steps.length} adım kaydedildi ·{" "}
            {runCase.status.replace("_", " ")}
          </p>
        </div>
        <svg
          className={`h-4 w-4 flex-shrink-0 text-slate-500 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {open && (
        <div className="border-t border-slate-800 p-4 space-y-2">
          {steps.length === 0 ? (
            <p className="text-sm text-slate-500">Bu case için adım tanımı yok.</p>
          ) : (
            steps.map((step) => (
              <StepRow
                key={step.id}
                step={step}
                runCaseId={runCase.id}
                projectId={projectId}
                existingStatus={(resultsByStepNo[step.step_no]?.status as StepStatus) ?? "not_run"}
                existingActual={resultsByStepNo[step.step_no]?.actual_result}
              />
            ))
          )}
        </div>
      )}
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
  const casesQuery = useManagementCases(projectId);

  const run   = runQuery.data;
  const cases = casesQuery.data ?? [];

  // Build a lookup from case_id → TestCase for rendering step definitions.
  const caseById = Object.fromEntries(cases.map((c) => [c.id, c]));

  // Stats derived from run_cases.
  const runCases   = run?.run_cases ?? [];
  const total      = runCases.length;
  const done       = runCases.filter((rc) => ["passed", "failed", "blocked", "skipped"].includes(rc.status)).length;
  const failed     = runCases.filter((rc) => rc.status === "failed").length;
  const notRun     = runCases.filter((rc) => rc.status === "not_run").length;

  const loading = runQuery.isLoading || casesQuery.isLoading;

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
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
          </div>
        ) : runCases.length === 0 ? (
          <ManagementPanel title="Koşum Case'leri">
            <p className="text-sm text-slate-500">Bu run'a henüz case eklenmemiş.</p>
          </ManagementPanel>
        ) : (
          runCases.map((rc) => (
            <CasePanel
              key={rc.id}
              runCase={rc}
              caseData={caseById[rc.case_id]}
              projectId={projectId}
            />
          ))
        )}
      </div>
    </ManagementShell>
  );
}
