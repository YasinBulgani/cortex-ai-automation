"use client";

import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { cn } from "@/lib/utils";
import {
  useManagementRun,
  useRunProgress,
  useCompleteRun,
  useUpdateManagementRunCase,
  useUpdateManagementStepResult,
  useCreateManagementDefect,
  type RunCase,
  type TestRunStatus,
} from "@/lib/hooks/use-management";
import { IntelligencePanel } from "../../../_components/IntelligencePanel";

// ─── Config ──────────────────────────────────────────────────────────────────

const STATUS_DOT: Record<string, string> = {
  passed:      "bg-emerald-500/70",
  failed:      "bg-red-500/80",
  blocked:     "bg-amber-500/60",
  skipped:     "bg-slate-500",
  in_progress: "bg-blue-500 animate-pulse",
  not_run:     "bg-slate-600",
};

const STATUS_LABEL: Record<string, string> = {
  passed:      "Passed",
  failed:      "Failed",
  blocked:     "Blocked",
  skipped:     "Skipped",
  in_progress: "Devam",
  not_run:     "Not Run",
};

const STEP_STATUS_BTN: { key: TestRunStatus; label: string; cls: string; activeCls: string }[] = [
  { key: "passed",  label: "Pass",  cls: "border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10", activeCls: "bg-emerald-500/15 border-emerald-500/40 text-emerald-300" },
  { key: "failed",  label: "Fail",  cls: "border-red-500/20     text-red-400    hover:bg-red-500/10",     activeCls: "bg-red-500/15     border-red-500/40     text-red-300" },
  { key: "blocked", label: "Block", cls: "border-border      text-slate-400  hover:bg-surface-overlay",       activeCls: "bg-surface-overlay      border-border-strong      text-slate-200" },
  { key: "skipped", label: "Skip",  cls: "border-border      text-slate-500  hover:bg-surface-overlay",       activeCls: "bg-surface-overlay      border-border-strong      text-slate-400" },
];

// ─── Types ────────────────────────────────────────────────────────────────────

interface SnapshotStep {
  id?: string;
  step_no: number;
  action: string;
  expected_result: string;
  test_data?: Record<string, unknown>;
  notes?: string | null;
  is_required?: boolean;
}

interface SnapshotCase {
  case_key?: string;
  title?: string;
  objective?: string;
  preconditions?: string;
  priority?: string;
  type?: string;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcBack()  { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/></svg>; }
function IcCheck() { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>; }
function IcSave()  { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M17 16v2a2 2 0 01-2 2H5a2 2 0 01-2-2v-7a2 2 0 012-2h2m3-4H9a2 2 0 00-2 2v7a2 2 0 002 2h10a2 2 0 002-2V7l-4-4z"/></svg>; }

// ─── Case Sidebar Item ────────────────────────────────────────────────────────

function CaseListItem({ rc, isSelected, onClick, itemRef }: {
  rc: RunCase; isSelected: boolean; onClick: () => void; itemRef?: React.Ref<HTMLButtonElement>;
}) {
  const snap     = rc.case_snapshot as { case?: SnapshotCase };
  const caseInfo = snap.case ?? {};
  const dot      = STATUS_DOT[rc.status] ?? STATUS_DOT.not_run;

  return (
    <button ref={itemRef} type="button" onClick={onClick}
      className={cn(
        "flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left transition-all",
        isSelected ? "bg-teal-500/10 border border-teal-500/20" : "hover:bg-surface-overlay border border-transparent",
      )}>
      <span className={cn("mt-1 h-1.5 w-1.5 shrink-0 rounded-full", dot)}/>
      <div className="min-w-0 flex-1">
        {caseInfo.case_key && (
          <span className="font-mono text-[9px] text-slate-600">{caseInfo.case_key}</span>
        )}
        <p className={cn("text-[11px] leading-snug line-clamp-2 transition-colors",
          isSelected ? "text-teal-300" : "text-slate-400")}>
          {caseInfo.title ?? rc.case_id}
        </p>
      </div>
    </button>
  );
}

// ─── Step Card ────────────────────────────────────────────────────────────────

function StepCard({ step, result, onChange, projectId, runCaseId, runId }: {
  step: SnapshotStep;
  result: { status: TestRunStatus; actual_result: string } | undefined;
  onChange: (status: TestRunStatus, actual: string) => void;
  projectId: string; runCaseId: string; runId: string;
}) {
  const updateStep  = useUpdateManagementStepResult(projectId, runCaseId, runId);
  const [actual, setActual] = useState(result?.actual_result ?? "");
  const currentStatus = result?.status ?? "not_run";

  const save = async (newStatus: TestRunStatus) => {
    const finalActual = actual.trim();
    onChange(newStatus, finalActual);
    await updateStep.mutateAsync({ stepNo: step.step_no, status: newStatus, actual_result: finalActual || null });
  };

  const cardBg = currentStatus === "passed"  ? "border-emerald-800/30 bg-emerald-950/10"
               : currentStatus === "failed"  ? "border-red-800/30    bg-red-950/10"
               : currentStatus === "blocked" ? "border-border     bg-surface-overlay"
               : "border-border bg-[#1a2035]/40";

  return (
    <div className={cn("rounded-xl border p-4 transition-all", cardBg)}>
      {/* Step header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-overlay font-mono text-[10px] font-bold text-slate-400">
          {step.step_no}
        </span>
        {!step.is_required && (
          <span className="rounded bg-surface-overlay px-1.5 py-0.5 text-[9px] text-slate-600">opsiyonel</span>
        )}
        <div className="ml-auto flex items-center gap-1">
          {STEP_STATUS_BTN.map(btn => (
            <button key={btn.key} type="button"
              onClick={() => save(btn.key)}
              disabled={updateStep.isPending}
              className={cn(
                "rounded-lg border px-2 py-1 text-[10px] font-medium transition-colors disabled:opacity-40",
                currentStatus === btn.key ? btn.activeCls : btn.cls,
              )}>
              {btn.label}
            </button>
          ))}
        </div>
      </div>

      {/* Action */}
      <p className="text-xs text-slate-200 leading-relaxed">{step.action}</p>

      {/* Expected */}
      <div className="mt-2 rounded-lg border border-border bg-surface-raised px-3 py-2">
        <p className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">Beklenen</p>
        <p className="text-xs text-slate-300">{step.expected_result}</p>
      </div>

      {/* Actual */}
      <div className="mt-2">
        <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-500">Gerçekleşen</p>
        <textarea
          value={actual}
          onChange={e => { setActual(e.target.value); onChange(currentStatus, e.target.value); }}
          onBlur={() => { if (actual !== (result?.actual_result ?? "")) save(currentStatus); }}
          rows={2}
          placeholder="Gerçekleşen sonucu girin…"
          className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-border-strong focus:outline-none resize-none"/>
      </div>
    </div>
  );
}

// ─── Main Execution Panel ─────────────────────────────────────────────────────

// ── TestRail-style case result buttons ──────────────────────────────────────
const CASE_RESULT_BTNS: { key: TestRunStatus; label: string; shortcut: string; activeCls: string; idleCls: string }[] = [
  {
    key: "passed",
    label: "Pass",
    shortcut: "P",
    activeCls: "bg-emerald-500 border-emerald-500 text-white shadow-lg shadow-emerald-900/30",
    idleCls:   "border-emerald-500/25 text-emerald-400 hover:bg-emerald-500/15 hover:border-emerald-500/50",
  },
  {
    key: "failed",
    label: "Fail",
    shortcut: "F",
    activeCls: "bg-red-500 border-red-500 text-white shadow-lg shadow-red-900/30",
    idleCls:   "border-red-500/25 text-red-400 hover:bg-red-500/15 hover:border-red-500/50",
  },
  {
    key: "blocked",
    label: "Block",
    shortcut: "B",
    activeCls: "bg-amber-500 border-amber-500 text-white shadow-lg shadow-amber-900/30",
    idleCls:   "border-border text-slate-400 hover:bg-surface-overlay hover:border-border-strong",
  },
  {
    key: "skipped",
    label: "Skip",
    shortcut: "S",
    activeCls: "bg-slate-500 border-slate-500 text-white",
    idleCls:   "border-border text-slate-500 hover:bg-surface-overlay hover:border-border-strong",
  },
  {
    key: "not_run",
    label: "Retest",
    shortcut: "R",
    activeCls: "bg-teal-600 border-teal-600 text-white",
    idleCls:   "border-teal-500/25 text-teal-500 hover:bg-teal-500/10 hover:border-teal-500/40",
  },
];

// ─── Quick Defect Modal ───────────────────────────────────────────────────────

function QuickDefectModal({ mpid, caseTitle, caseKey, runCaseId, onClose }: {
  mpid: string; caseTitle: string; caseKey: string; runCaseId: string; onClose: () => void;
}) {
  const create = useCreateManagementDefect(mpid);
  const [title,    setTitle]    = useState(`[${caseKey}] ${caseTitle} - Hata`);
  const [severity, setSeverity] = useState("major");
  const [priority, setPriority] = useState("P2");
  const [extKey,   setExtKey]   = useState("");
  const [rootCause, setRootCause] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create.mutateAsync({
      title: title.trim(),
      external_key: extKey.trim() || `DEF-${Date.now().toString().slice(-4)}`,
      severity,
      priority,
      status: "open",
      root_cause: rootCause.trim() || null,
      run_case_id: runCaseId,
      url: null,
      retest_status: "pending",
    });
    onClose();
  };

  const inp = "w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/40";
  const sel = "w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/40";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-[#0d1117] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-[14px] font-semibold text-slate-200">Defect Oluştur</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-600 hover:text-slate-300">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-4">
          <div>
            <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Başlık *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} required className={inp} />
          </div>
          <div>
            <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Jira/External Key</label>
            <input value={extKey} onChange={e => setExtKey(e.target.value)} placeholder="JIRA-123" className={inp} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Severity</label>
              <select value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                {["blocker","critical","major","minor","trivial"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Root Cause / Açıklama</label>
            <textarea value={rootCause} onChange={e => setRootCause(e.target.value)} rows={3} placeholder="Hata detayları, root cause…"
              className={cn(inp, "resize-none")} />
          </div>
          <div className="flex items-center justify-between pt-1">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300">İptal</button>
            <button type="submit" disabled={create.isPending}
              className="rounded-xl bg-red-600 px-5 py-2 text-[13px] font-medium text-white hover:bg-red-500 disabled:opacity-40">
              {create.isPending ? "Oluşturuluyor…" : "Defect Oluştur"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Main Execution Panel ─────────────────────────────────────────────────────
function ExecutionPanel({ rc, projectId, runId, onNext, mpid }: {
  rc: RunCase; projectId: string; runId: string; onNext: () => void; mpid: string;
}) {
  const snap     = rc.case_snapshot as { case?: SnapshotCase; steps?: SnapshotStep[] };
  const caseInfo = snap.case ?? {};
  const steps    = snap.steps ?? [];

  const [stepResults, setStepResults] = useState<Record<number, { status: TestRunStatus; actual_result: string }>>(() =>
    Object.fromEntries(rc.step_results.map(r => [r.step_no, { status: r.status as TestRunStatus, actual_result: r.actual_result ?? "" }])),
  );
  const [notes,          setNotes]          = useState(rc.execution_notes ?? "");
  const [saving,         setSaving]         = useState(false);
  const [showDefectModal,setShowDefectModal] = useState(false);

  const updateCase     = useUpdateManagementRunCase(projectId, runId);
  const updateAllSteps = useUpdateManagementStepResult(projectId, rc.id, runId);

  // ── TestRail case-level result: one click → status set for whole case ─────
  const handleCaseStatus = useCallback(async (status: TestRunStatus) => {
    await updateCase.mutateAsync({ runCaseId: rc.id, status, execution_notes: notes || null });
    // Auto-advance to next case when marking terminal statuses (pass/fail/skip)
    if (["passed", "failed", "skipped"].includes(status)) {
      setTimeout(() => onNext(), 300);
    }
  }, [updateCase, rc.id, notes, onNext]);

  // Keyboard shortcuts: P/F/B/S/R (only when not typing in a textarea/input)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const map: Record<string, TestRunStatus> = { p: "passed", f: "failed", b: "blocked", s: "skipped", r: "not_run" };
      const action = map[e.key.toLowerCase()];
      if (action) { e.preventDefault(); void handleCaseStatus(action); return; }
      if (e.key.toLowerCase() === "n") { e.preventDefault(); onNext(); }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [handleCaseStatus]);

  const handleBulkStatus = async (status: TestRunStatus) => {
    setSaving(true);
    try {
      for (const step of steps) {
        await updateAllSteps.mutateAsync({ stepNo: step.step_no, status, actual_result: stepResults[step.step_no]?.actual_result || null });
      }
      setStepResults(prev => {
        const next = { ...prev };
        steps.forEach(s => { next[s.step_no] = { ...prev[s.step_no] ?? { actual_result: "" }, status }; });
        return next;
      });
    } finally { setSaving(false); }
  };

  const passedCount = Object.values(stepResults).filter(r => r.status === "passed").length;
  const progress    = steps.length > 0 ? Math.round((passedCount / steps.length) * 100) : 0;

  const priorityDot: Record<string, string> = { P0: "bg-red-500/70", P1: "bg-orange-400/60", P2: "bg-slate-500", P3: "bg-slate-600" };

  return (
    <div className="flex h-full flex-col">
      {/* Case header */}
      <div className="border-b border-border bg-surface-raised px-5 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {caseInfo.case_key && <span className="font-mono text-[10px] text-slate-500">{caseInfo.case_key}</span>}
          {caseInfo.priority && (
            <span className="inline-flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", priorityDot[caseInfo.priority] ?? "bg-slate-600")}/>
              <span className="font-mono text-[10px] text-slate-400">{caseInfo.priority}</span>
            </span>
          )}
          {caseInfo.type && (
            <span className="rounded bg-surface-overlay px-1.5 py-0.5 text-[10px] text-slate-400">{caseInfo.type}</span>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[rc.status] ?? STATUS_DOT.not_run)}/>
            <span className="text-[10px] text-slate-500">{STATUS_LABEL[rc.status] ?? rc.status}</span>
          </div>
        </div>
        <h2 className="mt-1.5 text-sm font-semibold text-white">{caseInfo.title ?? rc.case_id}</h2>

        {/* Progress bar */}
        {steps.length > 0 && (
          <div className="mt-2 flex items-center gap-3">
            <div className="flex-1 h-1 rounded-full bg-surface-overlay overflow-hidden">
              <div className="h-full rounded-full bg-teal-500/70 transition-all duration-300" style={{ width: `${progress}%` }}/>
            </div>
            <span className="text-[10px] text-slate-500 tabular-nums">{passedCount}/{steps.length} adım</span>
          </div>
        )}
      </div>

      {/* ── TestRail-style case result bar ────────────────────────────────── */}
      <div className="border-b border-border bg-[#111827]/60 px-5 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {CASE_RESULT_BTNS.map(btn => (
            <button
              key={btn.key}
              type="button"
              onClick={() => handleCaseStatus(btn.key)}
              disabled={updateCase.isPending}
              title={`${btn.label} (${btn.shortcut})`}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-4 py-2 text-[13px] font-semibold transition-all duration-150 disabled:opacity-40",
                rc.status === btn.key ? btn.activeCls : btn.idleCls,
              )}
            >
              {btn.label}
              <kbd className="hidden sm:inline-flex h-4 w-4 items-center justify-center rounded bg-white/10 text-[9px] font-mono opacity-60">
                {btn.shortcut}
              </kbd>
            </button>
          ))}
          {rc.status === "failed" && (
            <button
              type="button"
              onClick={() => setShowDefectModal(true)}
              className="ml-2 flex items-center gap-1.5 rounded-lg border border-red-500/30 px-3 py-1.5 text-[11px] font-medium text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
              Defect Aç
            </button>
          )}
          <span className="ml-auto text-[11px] text-slate-600">
            {steps.length > 0 ? `${steps.length} adım` : "adımsız"}
          </span>
        </div>
      </div>
      {showDefectModal && (
        <QuickDefectModal
          mpid={mpid}
          caseTitle={caseInfo.title ?? rc.case_id}
          caseKey={caseInfo.case_key ?? ""}
          runCaseId={rc.id}
          onClose={() => setShowDefectModal(false)}
        />
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

        {/* Objective + Preconditions */}
        {(caseInfo.objective || caseInfo.preconditions) && (
          <div className="grid gap-3 sm:grid-cols-2">
            {caseInfo.objective && (
              <div className="rounded-xl border border-border bg-surface-raised px-3 py-2.5">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-500">Amaç</p>
                <p className="text-xs text-slate-300 leading-relaxed">{caseInfo.objective}</p>
              </div>
            )}
            {caseInfo.preconditions && (
              <div className="rounded-xl border border-border bg-surface-raised px-3 py-2.5">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-slate-500">Ön Koşullar</p>
                <p className="text-xs text-slate-300 leading-relaxed">{caseInfo.preconditions}</p>
              </div>
            )}
          </div>
        )}

        {/* Steps */}
        {steps.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border py-10 text-center">
            <p className="text-xs text-slate-500">Bu case için adım tanımlanmamış.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {steps.map(step => (
              <StepCard
                key={step.step_no}
                step={step}
                result={stepResults[step.step_no]}
                onChange={(status, actual) => {
                  setStepResults(prev => ({ ...prev, [step.step_no]: { status, actual_result: actual } }));
                }}
                projectId={projectId}
                runCaseId={rc.id}
                runId={runId}
              />
            ))}
          </div>
        )}

        {/* Notes */}
        <div>
          <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Notlar</label>
          <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
            placeholder="Koşum notları, gözlemler…"
            className="w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-border-strong focus:outline-none resize-none"/>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border bg-surface-raised px-5 py-3">
        {/* Bulk actions */}
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="self-center text-[10px] text-slate-500">Toplu:</span>
          {[
            { label: "Pass All",  status: "passed"  as TestRunStatus, cls: "border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10" },
            { label: "Fail All",  status: "failed"  as TestRunStatus, cls: "border-red-500/20     text-red-400    hover:bg-red-500/10" },
            { label: "Block All", status: "blocked" as TestRunStatus, cls: "border-border      text-slate-400  hover:bg-surface-overlay" },
            { label: "Retest",    status: "not_run" as TestRunStatus, cls: "border-teal-500/20    text-teal-400   hover:bg-teal-700/10" },
          ].map(btn => (
            <button key={btn.status} type="button"
              onClick={() => handleBulkStatus(btn.status)}
              disabled={saving || steps.length === 0}
              className={cn("rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors disabled:opacity-40", btn.cls)}>
              {btn.label}
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="text-[10px] text-slate-600">
            {passedCount}/{steps.length} adım tamamlandı
          </div>
          <button type="button" onClick={onNext}
            className="flex items-center gap-1.5 rounded-xl bg-teal-600 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-700 transition-colors shadow-lg shadow-blue-900/20">
            <IcSave/> Kaydet & İleri
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ManagementRunExecutePage() {
  const projectId = useRouteParam("projectId") ?? "";
  const runId     = useRouteParam("runId") ?? "";
  const mpid      = useManagementProjectId(projectId || undefined) ?? "";

  const runQuery    = useManagementRun(projectId || undefined, runId || undefined);
  const progressQ   = useRunProgress(mpid || undefined, runId || undefined);
  const completeRun = useCompleteRun(mpid || "");
  const run         = runQuery.data;
  const runCases    = run?.run_cases ?? [];
  const progress    = progressQ.data;

  const [selectedRcId, setSelectedRcId] = useState<string | null>(null);
  const [sidebarTab, setSidebarTab] = useState<"cases" | "ai">("cases");
  const activeCaseRef = useRef<HTMLButtonElement>(null);

  const selectedRc = useMemo(() => {
    if (selectedRcId) return runCases.find(rc => rc.id === selectedRcId) ?? null;
    return runCases[0] ?? null;
  }, [selectedRcId, runCases]);

  const goNext = () => {
    const idx = runCases.findIndex(rc => rc.id === (selectedRc?.id ?? ""));
    const next = runCases[idx + 1];
    if (next) setSelectedRcId(next.id);
  };

  const passed      = runCases.filter(rc => rc.status === "passed").length;
  const failed      = runCases.filter(rc => rc.status === "failed").length;
  const blocked     = runCases.filter(rc => rc.status === "blocked").length;
  const notRun      = runCases.filter(rc => rc.status === "not_run").length;
  const total       = runCases.length;
  const pct         = total > 0 ? Math.round((passed / total) * 100) : 0;
  const pendingCount = runCases.filter(rc => rc.status === "not_run" || rc.status === "in_progress").length;

  const activeCaseId = selectedRc?.id ?? "";

  // Scroll active case into view when it changes
  useEffect(() => {
    activeCaseRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeCaseId]);

  const loading = runQuery.isLoading;

  return (
    <div className="flex bg-bg" style={{ height: "calc(100vh - 48px)" }}>

      {/* LEFT: Case List / AI Sidebar */}
      <aside className="hidden w-64 flex-none flex-col border-r border-border bg-surface-raised md:flex overflow-hidden">
        {/* Run info */}
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Link href={`/p/${projectId}/management/runs`}
              className="text-slate-600 hover:text-slate-300 transition-colors">
              <IcBack/>
            </Link>
            <p className="flex-1 min-w-0 truncate text-xs font-semibold text-slate-200">
              {loading ? "Yükleniyor…" : (run?.name ?? "Execute Run")}
            </p>
          </div>
          {run?.source_ref && (
            <p className="text-[10px] text-slate-600">{run.source_ref}</p>
          )}
        </div>

        {/* Tab buttons */}
        <div className="flex border-b border-border">
          <button
            type="button"
            onClick={() => setSidebarTab("cases")}
            className={cn(
              "flex-1 py-2 text-[11px] font-medium transition-colors",
              sidebarTab === "cases"
                ? "border-b-2 border-teal-500 text-teal-300"
                : "text-slate-500 hover:text-slate-300 border-b-2 border-transparent",
            )}
          >
            Case Listesi
          </button>
          <button
            type="button"
            onClick={() => setSidebarTab("ai")}
            className={cn(
              "flex-1 py-2 text-[11px] font-medium transition-colors",
              sidebarTab === "ai"
                ? "border-b-2 border-teal-500 text-teal-300"
                : "text-slate-500 hover:text-slate-300 border-b-2 border-transparent",
            )}
          >
            AI Intelligence
          </button>
        </div>

        {sidebarTab === "cases" ? (
          <>
            {/* Progress */}
            <div className="border-b border-border px-4 py-2.5">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] text-slate-500">İlerleme</span>
                <span className="text-[10px] font-bold tabular-nums text-slate-300">
                  {progress?.progress_pct ?? pct}%
                </span>
              </div>
              <div className="h-1 rounded-full bg-surface-overlay overflow-hidden">
                <div className="h-full rounded-full bg-emerald-500/70 transition-all duration-500"
                  style={{ width: `${progress?.progress_pct ?? pct}%` }}/>
              </div>
              {progress && (
                <div className="mt-1.5 flex gap-1.5 flex-wrap text-[9px]">
                  {progress.passed  > 0 && <span className="text-emerald-400">{progress.passed} pass</span>}
                  {progress.failed  > 0 && <span className="text-red-400">{progress.failed} fail</span>}
                  {progress.blocked > 0 && <span className="text-amber-400">{progress.blocked} blk</span>}
                  <span className="text-slate-600">{progress.not_run} left</span>
                </div>
              )}
              {!progress && (
                <div className="mt-1.5 flex justify-between text-[9px] text-slate-600">
                  <span>{passed} passed</span>
                  <span>{failed > 0 ? `${failed} fail` : ""}</span>
                  <span>{notRun} left</span>
                </div>
              )}
            </div>

            {/* Case list */}
            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-10 rounded-lg bg-surface-overlay animate-pulse" style={{ opacity: Math.max(0.2, 1 - i * 0.1) }}/>
                ))
              ) : runCases.map(rc => (
                <CaseListItem key={rc.id} rc={rc} isSelected={rc.id === activeCaseId}
                  itemRef={rc.id === activeCaseId ? activeCaseRef : undefined}
                  onClick={() => setSelectedRcId(rc.id)}/>
              ))}
            </div>

            {/* Stats footer */}
            <div className="border-t border-border px-3 py-2 space-y-2">
              <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                {[
                  { dot: "bg-emerald-500/70", label: `${passed} ok` },
                  { dot: "bg-red-500/80",     label: `${failed} fail` },
                  { dot: "bg-amber-500/60",   label: `${blocked} blk` },
                  { dot: "bg-slate-600",      label: `${notRun} left` },
                ].map(s => (
                  <span key={s.label} className="flex items-center gap-1">
                    <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", s.dot)}/>
                    <span className="text-[9px] text-slate-600">{s.label}</span>
                  </span>
                ))}
              </div>
              {run?.status !== "completed" && notRun === 0 && (
                <button type="button"
                  onClick={() => completeRun.mutateAsync(runId)}
                  disabled={completeRun.isPending}
                  className="w-full rounded-lg bg-emerald-600 py-1.5 text-[11px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors">
                  {completeRun.isPending ? "Tamamlanıyor…" : "✓ Koşumu Tamamla"}
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {projectId && runId && (
              <IntelligencePanel projectId={projectId} runId={runId} />
            )}
          </div>
        )}
      </aside>

      {/* MAIN: Execution Panel */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-border border-t-blue-500"/>
          </div>
        ) : !selectedRc ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center p-8">
            <IcCheck/>
            <h3 className="text-sm font-semibold text-slate-300">
              {runCases.length === 0 ? "Bu run'a case eklenmemiş." : "Case seçin"}
            </h3>
            <Link href={`/p/${projectId}/management/runs`}
              className="text-xs text-teal-400 hover:underline">
              Runs listesine dön →
            </Link>
          </div>
        ) : (
          <>
            {pendingCount === 0 && (
              <div className="mx-4 mb-3 mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/8 px-4 py-3">
                <p className="text-[13px] font-semibold text-emerald-400">Tüm case&apos;ler tamamlandı!</p>
                <p className="text-[11px] text-emerald-500/70">Koşumu tamamlamak için butona tıklayın.</p>
              </div>
            )}
            <ExecutionPanel rc={selectedRc} projectId={projectId} runId={runId} onNext={goNext} mpid={mpid}/>
          </>
        )}

        {/* Mobile sticky footer */}
        <div className="md:hidden sticky bottom-0 border-t border-border bg-surface-raised px-4 py-3">
          {pendingCount === 0 ? (
            <button
              onClick={() => completeRun.mutateAsync(runId)}
              disabled={completeRun.isPending}
              className="w-full rounded-xl bg-emerald-600 py-3 text-[13px] font-semibold text-white disabled:opacity-40">
              {completeRun.isPending ? "Tamamlanıyor…" : "Koşumu Tamamla"}
            </button>
          ) : (
            <p className="text-center text-[12px] text-fg-muted">{pendingCount} case kaldı</p>
          )}
        </div>
      </div>

    </div>
  );
}
