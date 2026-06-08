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
  useManagementEvidence,
  useUploadEvidence,
  useCaseDependencies,
  type RunCase,
  type TestRunStatus,
  type EvidenceFile,
} from "@/lib/hooks/use-management";
import { IntelligencePanel } from "../../../_components/IntelligencePanel";
import { EvidenceModal } from "../../../_components/EvidenceModal";

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
  { key: "blocked", label: "Block", cls: "border-border      text-fg-muted  hover:bg-surface-overlay",       activeCls: "bg-surface-overlay      border-border-strong      text-fg" },
  { key: "skipped", label: "Skip",  cls: "border-border      text-fg-subtle  hover:bg-surface-overlay",       activeCls: "bg-surface-overlay      border-border-strong      text-fg-muted" },
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
      aria-current={isSelected ? "true" : undefined}
      aria-label={`${caseInfo.title ?? rc.case_id}${caseInfo.case_key ? ` (${caseInfo.case_key})` : ""} — ${STATUS_LABEL[rc.status] ?? rc.status}`}
      className={cn(
        "flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left transition-all",
        isSelected ? "bg-teal-500/10 border border-teal-500/20" : "hover:bg-surface-overlay border border-transparent",
      )}>
      <span className={cn("mt-1 h-1.5 w-1.5 shrink-0 rounded-full", dot)}/>
      <div className="min-w-0 flex-1">
        {caseInfo.case_key && (
          <span className="font-mono text-[9px] text-fg-disabled">{caseInfo.case_key}</span>
        )}
        <p className={cn("text-[11px] leading-snug line-clamp-2 transition-colors",
          isSelected ? "text-teal-300" : "text-fg-muted")}>
          {caseInfo.title ?? rc.case_id}
        </p>
      </div>
    </button>
  );
}

// ─── Step Card ────────────────────────────────────────────────────────────────

function StepCard({ step, result, onChange, projectId, runCaseId, runId, onDefectRequest }: {
  step: SnapshotStep;
  result: { status: TestRunStatus; actual_result: string } | undefined;
  onChange: (status: TestRunStatus, actual: string) => void;
  projectId: string; runCaseId: string; runId: string;
  onDefectRequest?: () => void;
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
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-overlay font-mono text-[10px] font-bold text-fg-muted">
          {step.step_no}
        </span>
        {!step.is_required && (
          <span className="rounded bg-surface-overlay px-1.5 py-0.5 text-[9px] text-fg-disabled">opsiyonel</span>
        )}
        <div className="ml-auto flex items-center gap-1">
          {STEP_STATUS_BTN.map(btn => (
            <button key={btn.key} type="button"
              onClick={() => save(btn.key)}
              disabled={updateStep.isPending}
              aria-label={`Adım ${step.step_no}: ${btn.label} olarak işaretle`}
              aria-pressed={currentStatus === btn.key}
              className={cn(
                "rounded-lg border px-2 py-1 text-[10px] font-medium transition-colors disabled:opacity-40",
                currentStatus === btn.key ? btn.activeCls : btn.cls,
              )}>
              {btn.label}
            </button>
          ))}
          {currentStatus === "failed" && onDefectRequest && (
            <button
              type="button"
              onClick={onDefectRequest}
              className="flex items-center gap-1 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs text-red-400 hover:bg-red-500/20 transition-colors"
            >
              🐛 Defect Aç
            </button>
          )}
        </div>
      </div>

      {/* Action */}
      <p className="text-xs text-fg leading-relaxed">{step.action}</p>

      {/* Expected */}
      <div className="mt-2 rounded-lg border border-border bg-surface-raised px-3 py-2">
        <p className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-fg-subtle">Beklenen</p>
        <p className="text-xs text-fg">{step.expected_result}</p>
      </div>

      {/* Actual */}
      <div className="mt-2">
        <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-fg-subtle">Gerçekleşen</p>
        <textarea
          value={actual}
          onChange={e => { setActual(e.target.value); onChange(currentStatus, e.target.value); }}
          onBlur={() => { if (actual !== (result?.actual_result ?? "")) save(currentStatus); }}
          rows={2}
          aria-label={`Adım ${step.step_no} gerçekleşen sonuç`}
          placeholder="Gerçekleşen sonucu girin…"
          className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs text-white placeholder:text-fg-disabled focus:border-border-strong focus:outline-none resize-none"/>
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
    idleCls:   "border-border text-fg-muted hover:bg-surface-overlay hover:border-border-strong",
  },
  {
    key: "skipped",
    label: "Skip",
    shortcut: "S",
    activeCls: "bg-slate-500 border-border-strong text-white",
    idleCls:   "border-border text-fg-subtle hover:bg-surface-overlay hover:border-border-strong",
  },
  {
    key: "not_run",
    label: "Retest",
    shortcut: "R",
    activeCls: "bg-brand border-teal-600 text-white",
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

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/40";
  const sel = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" aria-hidden="true">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="defect-modal-title"
        className="w-full max-w-lg rounded-xl border border-border bg-[#0d1117] shadow-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="defect-modal-title" className="text-[14px] font-semibold text-fg">Defect Oluştur</h2>
          <button onClick={onClose} aria-label="Defect modalını kapat" className="rounded-lg p-1.5 text-fg-disabled hover:text-fg">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        <form onSubmit={submit} className="p-5 space-y-4">
          <div>
            <label htmlFor="defect-title" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Başlık *</label>
            <input id="defect-title" value={title} onChange={e => setTitle(e.target.value)} required aria-required="true" className={inp} />
          </div>
          <div>
            <label htmlFor="defect-ext-key" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Jira/External Key</label>
            <input id="defect-ext-key" value={extKey} onChange={e => setExtKey(e.target.value)} placeholder="JIRA-123" className={inp} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="defect-severity" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Severity</label>
              <select id="defect-severity" value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                {["blocker","critical","major","minor","trivial"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="defect-priority" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Priority</label>
              <select id="defect-priority" value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="defect-root-cause" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-disabled">Root Cause / Açıklama</label>
            <textarea id="defect-root-cause" value={rootCause} onChange={e => setRootCause(e.target.value)} rows={3} placeholder="Hata detayları, root cause…"
              className={cn(inp, "resize-none")} />
          </div>
          <div className="flex items-center justify-between pt-1">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[13px] text-fg-subtle hover:text-fg">İptal</button>
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

// ─── Evidence Section ─────────────────────────────────────────────────────────

function EvidenceSection({ projectId, runId, runCaseId, caseKey, caseTitle }: {
  projectId: string; runId: string; runCaseId: string; caseKey?: string; caseTitle?: string;
}) {
  const { data: files = [], isLoading } = useManagementEvidence(projectId, runId, runCaseId);
  const [showModal, setShowModal] = useState(false);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <p className="text-[10px] font-medium uppercase tracking-wide text-fg-subtle">Evidence</p>
        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-[10px] text-fg-muted hover:text-fg hover:bg-surface-overlay transition-colors"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/></svg>
          Evidence Ekle
        </button>
      </div>
      {isLoading ? (
        <div className="h-8 rounded-lg bg-surface-overlay animate-pulse"/>
      ) : files.length === 0 ? (
        <p className="text-[10px] text-fg-disabled italic">Henüz evidence eklenmedi.</p>
      ) : (
        <div className="space-y-1">
          {(files as EvidenceFile[]).map(f => (
            <a key={f.id} href={f.url} target="_blank" rel="noreferrer"
              className="flex items-center gap-2 rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 text-[11px] text-fg hover:text-teal-300 transition-colors truncate">
              <svg className="h-3 w-3 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"/></svg>
              <span className="truncate">{f.filename}</span>
              <span className="ml-auto shrink-0 text-[9px] text-fg-disabled">{f.content_type.split("/")[1] ?? f.content_type}</span>
            </a>
          ))}
        </div>
      )}
      {showModal && (
        <EvidenceModal
          projectId={projectId}
          runId={runId}
          runCaseId={runCaseId}
          caseKey={caseKey}
          caseTitle={caseTitle}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}

// ─── Draft key helper ─────────────────────────────────────────────────────────

const draftKey = (runId: string, caseId: string) => `execute-draft-${runId}-${caseId}`;

// ─── Case Execution Timer ─────────────────────────────────────────────────────

function CaseTimer({ rcId, status }: { rcId: string; status: string }) {
  const storageKey = `execute-timer-start-${rcId}`;
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(false);

  // Start timer when status is not_run or in_progress
  useEffect(() => {
    const isActive = status === "not_run" || status === "in_progress";
    if (!isActive) {
      setRunning(false);
      return;
    }
    const stored = localStorage.getItem(storageKey);
    const startTs = stored ? parseInt(stored, 10) : Date.now();
    if (!stored) localStorage.setItem(storageKey, String(startTs));
    setRunning(true);
    setElapsed(Math.floor((Date.now() - startTs) / 1000));
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startTs) / 1000)), 1000);
    return () => clearInterval(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rcId, status]);

  // Clear timer when case is completed
  useEffect(() => {
    if (!["not_run", "in_progress"].includes(status)) {
      localStorage.removeItem(storageKey);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const color = elapsed > 600 ? "text-red-400" : elapsed > 300 ? "text-amber-400" : "text-teal-400";

  return (
    <div className="flex items-center gap-1.5" title="Bu case üzerinde geçen süre">
      <span className={cn("flex h-1.5 w-1.5 rounded-full", running ? "bg-teal-400 animate-pulse" : "bg-fg-disabled")} />
      <span className={cn("font-mono text-[11px] tabular-nums font-medium", running ? color : "text-fg-disabled")}>
        {fmt(elapsed)}
      </span>
    </div>
  );
}

// ─── Session Timer (total elapsed for entire run session) ─────────────────────
function SessionTimer({ runId }: { runId: string }) {
  const storageKey = `execute-session-start-${runId}`;
  const [elapsed, setElapsed] = useState(() => {
    const stored = localStorage.getItem(storageKey);
    const startTs = stored ? parseInt(stored, 10) : Date.now();
    if (!stored) localStorage.setItem(storageKey, String(startTs));
    return Math.floor((Date.now() - startTs) / 1000);
  });

  useEffect(() => {
    const id = setInterval(() => {
      const stored = localStorage.getItem(storageKey);
      if (stored) setElapsed(Math.floor((Date.now() - parseInt(stored, 10)) / 1000));
    }, 1000);
    return () => clearInterval(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const h = Math.floor(elapsed / 3600);
  const m = Math.floor((elapsed % 3600) / 60);
  const s = elapsed % 60;
  const fmt = h > 0
    ? `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
    : `${m}:${s.toString().padStart(2, "0")}`;

  return (
    <div className="flex items-center justify-between text-[9px]">
      <span className="text-fg-disabled">Oturum süresi</span>
      <span className="font-mono text-fg-disabled tabular-nums">{fmt}</span>
    </div>
  );
}

// ─── Main Execution Panel ─────────────────────────────────────────────────────
function ExecutionPanel({ rc, projectId, runId, onNext, onPrev, mpid }: {
  rc: RunCase; projectId: string; runId: string; onNext: () => void; onPrev: (() => void) | null; mpid: string;
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
  const [showShortcuts,  setShowShortcuts]  = useState(false);

  // ── Load draft from localStorage on mount / case change ─────────────────────
  useEffect(() => {
    if (!runId || !rc.id) return;
    const key = draftKey(runId, rc.id);
    const saved = localStorage.getItem(key);
    if (saved) {
      try {
        const draft = JSON.parse(saved) as { notes?: string };
        // Only restore draft if case hasn't been run yet
        if (rc.status === "not_run" || !rc.status) {
          if (draft.notes !== undefined) setNotes(draft.notes);
        }
      } catch { /* ignore malformed draft */ }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, rc.id]);

  // ── Auto-save notes draft to localStorage ───────────────────────────────────
  useEffect(() => {
    if (!runId || !rc.id) return;
    const key = draftKey(runId, rc.id);
    localStorage.setItem(key, JSON.stringify({ notes, status: rc.status }));
  }, [runId, rc.id, notes, rc.status]);

  const updateCase     = useUpdateManagementRunCase(projectId, runId);
  const updateAllSteps = useUpdateManagementStepResult(projectId, rc.id, runId);

  // ── TestRail case-level result: one click → status set for whole case ─────
  const handleCaseStatus = useCallback(async (status: TestRunStatus) => {
    // Compute duration from the timer's localStorage start timestamp
    const timerKey = `execute-timer-start-${rc.id}`;
    const startTs  = localStorage.getItem(timerKey);
    const duration_seconds = startTs ? Math.floor((Date.now() - parseInt(startTs, 10)) / 1000) : null;

    await updateCase.mutateAsync({ runCaseId: rc.id, status, execution_notes: notes || null, duration_seconds });
    // Clear draft + timer once successfully saved to backend
    localStorage.removeItem(draftKey(runId, rc.id));
    localStorage.removeItem(timerKey);
    // Auto-advance to next case when marking terminal statuses (pass/fail/skip)
    if (["passed", "failed", "skipped"].includes(status)) {
      setTimeout(() => onNext(), 300);
    }
  }, [updateCase, rc.id, notes, onNext, runId]);

  // Keyboard shortcuts: P/F/B/S/R/N/← and ? (only when not typing in a textarea/input)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "?") { e.preventDefault(); setShowShortcuts(v => !v); return; }
      if (e.key === "Escape") { setShowShortcuts(false); return; }
      const map: Record<string, TestRunStatus> = { p: "passed", f: "failed", b: "blocked", s: "skipped", r: "not_run" };
      const action = map[e.key.toLowerCase()];
      if (action) { e.preventDefault(); void handleCaseStatus(action); return; }
      if (e.key.toLowerCase() === "n" || e.key === "ArrowRight") { e.preventDefault(); onNext(); return; }
      if (e.key === "ArrowLeft" || e.key === "Backspace") { e.preventDefault(); onPrev?.(); }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [handleCaseStatus, onNext, onPrev]);

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

  // ── Dependency warning ───────────────────────────────────────────────────────
  const { data: deps = [] } = useCaseDependencies(mpid || undefined, rc.case_id || undefined);
  type DepItem = { id: string; dep_type: string; depends_on_key: string };
  const blockingDeps = (deps as DepItem[]).filter((d) => d.dep_type === "blocks");

  return (
    <div className="flex h-full flex-col">
      {/* Dependency warning banner */}
      {blockingDeps.length > 0 && rc.status === "not_run" && (
        <div className="border-b border-amber-500/20 bg-amber-500/5 px-5 py-2">
          <div className="flex items-start gap-2">
            <svg className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
            </svg>
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-amber-300">Bağımlılık Uyarısı</p>
              <p className="text-[10px] text-amber-400/70 mt-0.5">
                Bu case önce tamamlanmalı:{" "}
                {blockingDeps.map((d, i) => (
                  <span key={d.id}>
                    {i > 0 && ", "}
                    <span className="font-mono">{d.depends_on_key}</span>
                  </span>
                ))}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Case header */}
      <div className="border-b border-border bg-surface-raised px-5 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {caseInfo.case_key && <span className="font-mono text-[10px] text-fg-subtle">{caseInfo.case_key}</span>}
          {caseInfo.priority && (
            <span className="inline-flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", priorityDot[caseInfo.priority] ?? "bg-slate-600")}/>
              <span className="font-mono text-[10px] text-fg-muted">{caseInfo.priority}</span>
            </span>
          )}
          {caseInfo.type && (
            <span className="rounded bg-surface-overlay px-1.5 py-0.5 text-[10px] text-fg-muted">{caseInfo.type}</span>
          )}
          <div className="ml-auto flex items-center gap-3">
            <CaseTimer rcId={rc.id} status={rc.status} />
            <span className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[rc.status] ?? STATUS_DOT.not_run)}/>
            <span className="text-[10px] text-fg-subtle">{STATUS_LABEL[rc.status] ?? rc.status}</span>
          </div>
        </div>
        <h2 className="mt-1.5 text-sm font-semibold text-white">{caseInfo.title ?? rc.case_id}</h2>

        {/* Progress bar */}
        {steps.length > 0 && (
          <div className="mt-2 flex items-center gap-3">
            <div
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Adım ilerleme: ${passedCount}/${steps.length}`}
              className="flex-1 h-1 rounded-full bg-surface-overlay overflow-hidden"
            >
              <div className="h-full rounded-full bg-teal-500/70 transition-all duration-300" style={{ width: `${progress}%` }}/>
            </div>
            <span className="text-[10px] text-fg-subtle tabular-nums" aria-hidden="true">{passedCount}/{steps.length} adım</span>
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
              aria-label={`${btn.label} olarak işaretle (kısayol: ${btn.shortcut})`}
              aria-pressed={rc.status === btn.key}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-4 py-2 text-[13px] font-semibold transition-all duration-150 disabled:opacity-40",
                rc.status === btn.key ? btn.activeCls : btn.idleCls,
              )}
            >
              {btn.label}
              <kbd className="hidden sm:inline-flex h-4 w-4 items-center justify-center rounded bg-white/10 text-[9px] font-mono opacity-60" aria-hidden="true">
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
          <span className="ml-auto flex items-center gap-2">
            <span className="text-[11px] text-fg-disabled">
              {steps.length > 0 ? `${steps.length} adım` : "adımsız"}
            </span>
            <button
              type="button"
              onClick={() => setShowShortcuts(true)}
              title="Klavye kısayollarını göster (?)"
              aria-label="Klavye kısayollarını göster"
              className="flex h-5 w-5 items-center justify-center rounded border border-border bg-surface-overlay text-[10px] font-mono text-fg-disabled hover:border-border-strong hover:text-fg transition-colors"
            >
              ?
            </button>
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

      {showShortcuts && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
          onClick={() => setShowShortcuts(false)}
          aria-hidden="true"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="shortcuts-dialog-title"
            className="bg-surface-raised rounded-xl p-6 max-w-sm w-full border border-border"
            onClick={e => e.stopPropagation()}
          >
            <h2 id="shortcuts-dialog-title" className="text-sm font-semibold mb-4">Klavye Kısayolları</h2>
            <table className="w-full text-xs text-fg-subtle">
              <tbody>
                {([
                  ["P", "Geçti (Passed)"],
                  ["F", "Başarısız (Failed)"],
                  ["B", "Engellendi (Blocked)"],
                  ["S", "Atlandı (Skipped)"],
                  ["R", "Çalıştırılmadı (Not Run)"],
                  ["N / →", "Sonraki case"],
                  ["← / Backspace", "Önceki case"],
                  ["?", "Bu menüyü aç/kapat"],
                  ["Esc", "Menüyü kapat"],
                ] as [string, string][]).map(([key, desc]) => (
                  <tr key={key}>
                    <td className="pr-4 py-1.5">
                      {key.split(" / ").map((k, i) => (
                        <span key={k}>
                          {i > 0 && <span className="mx-1 text-fg-disabled">/</span>}
                          <kbd className="inline-flex items-center justify-center rounded border border-border bg-surface-overlay px-1.5 py-0.5 font-mono text-[10px] text-fg">{k}</kbd>
                        </span>
                      ))}
                    </td>
                    <td className="py-1.5 text-fg-muted">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={() => setShowShortcuts(false)}
              className="mt-4 text-xs text-brand"
            >
              Kapat (Esc)
            </button>
          </div>
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

        {/* Objective + Preconditions */}
        {(caseInfo.objective || caseInfo.preconditions) && (
          <div className="grid gap-3 sm:grid-cols-2">
            {caseInfo.objective && (
              <div className="rounded-xl border border-border bg-surface-raised px-3 py-2.5">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-fg-subtle">Amaç</p>
                <p className="text-xs text-fg leading-relaxed">{caseInfo.objective}</p>
              </div>
            )}
            {caseInfo.preconditions && (
              <div className="rounded-xl border border-border bg-surface-raised px-3 py-2.5">
                <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-fg-subtle">Ön Koşullar</p>
                <p className="text-xs text-fg leading-relaxed">{caseInfo.preconditions}</p>
              </div>
            )}
          </div>
        )}

        {/* Steps */}
        {steps.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border py-10 text-center">
            <p className="text-xs text-fg-subtle">Bu case için adım tanımlanmamış.</p>
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
                onDefectRequest={() => setShowDefectModal(true)}
              />
            ))}
          </div>
        )}

        {/* Notes */}
        <div>
          <label htmlFor="execution-notes" className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-fg-subtle">Notlar</label>
          <textarea id="execution-notes" value={notes} onChange={e => setNotes(e.target.value)} rows={3}
            aria-label="Koşum notları ve gözlemler"
            placeholder="Koşum notları, gözlemler…"
            className="w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-xs text-white placeholder:text-fg-disabled focus:border-border-strong focus:outline-none resize-none"/>
        </div>

        {/* Evidence */}
        <EvidenceSection projectId={projectId} runId={runId} runCaseId={rc.id} caseKey={caseInfo.case_key} caseTitle={caseInfo.title} />
      </div>

      {/* Footer */}
      <div className="border-t border-border bg-surface-raised px-5 py-3">
        {/* Bulk actions */}
        <div className="mb-3 flex flex-wrap gap-2">
          <span className="self-center text-[10px] text-fg-subtle">Toplu:</span>
          {[
            { label: "Pass All",  status: "passed"  as TestRunStatus, cls: "border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10" },
            { label: "Fail All",  status: "failed"  as TestRunStatus, cls: "border-red-500/20     text-red-400    hover:bg-red-500/10" },
            { label: "Block All", status: "blocked" as TestRunStatus, cls: "border-border      text-fg-muted  hover:bg-surface-overlay" },
            { label: "Retest",    status: "not_run" as TestRunStatus, cls: "border-teal-500/20    text-teal-400   hover:brightness-105/10" },
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
          <div className="text-[10px] text-fg-disabled">
            {passedCount}/{steps.length} adım tamamlandı
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={onPrev === null || saving}
              onClick={() => onPrev?.()}
              className="px-3 py-2 rounded-lg border border-border text-sm text-fg-subtle disabled:opacity-30"
            >
              ← Önceki
            </button>
            <button type="button"
              disabled={saving || updateCase.isPending}
              onClick={async () => {
                if (notes !== (rc.execution_notes ?? "")) {
                  await updateCase.mutateAsync({ runCaseId: rc.id, status: rc.status as TestRunStatus, execution_notes: notes || null }).catch(() => {});
                }
                onNext();
              }}
              className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-xs font-semibold text-white hover:brightness-105 transition-colors shadow-lg shadow-blue-900/20 disabled:opacity-40">
              <IcSave/> Kaydet & İleri
            </button>
          </div>
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
  const [caseFilter, setCaseFilter] = useState<"all" | "not_run" | "failed" | "passed">("all");
  const [showEarlyComplete, setShowEarlyComplete] = useState(false);
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

  const activeCaseIndex = runCases.findIndex(rc => rc.id === (selectedRc?.id ?? ""));
  const prevCaseIndex   = activeCaseIndex > 0 ? activeCaseIndex - 1 : null;

  const goPrev: (() => void) | null = prevCaseIndex !== null
    ? () => { const prev = runCases[prevCaseIndex]; if (prev) setSelectedRcId(prev.id); }
    : null;

  const passed      = runCases.filter(rc => rc.status === "passed").length;
  const failed      = runCases.filter(rc => rc.status === "failed").length;
  const blocked     = runCases.filter(rc => rc.status === "blocked").length;
  const notRun      = runCases.filter(rc => rc.status === "not_run").length;
  const total       = runCases.length;
  const pct         = total > 0 ? Math.round((passed / total) * 100) : 0;
  const pendingCount = runCases.filter(rc => rc.status === "not_run" || rc.status === "in_progress").length;

  const filteredCases = useMemo(() => {
    if (caseFilter === "all")     return runCases;
    if (caseFilter === "not_run") return runCases.filter(rc => rc.status === "not_run" || rc.status === "in_progress");
    if (caseFilter === "failed")  return runCases.filter(rc => rc.status === "failed" || rc.status === "blocked");
    if (caseFilter === "passed")  return runCases.filter(rc => rc.status === "passed");
    return runCases;
  }, [runCases, caseFilter]);

  const jumpToFirstNotRun = () => {
    const first = runCases.find(rc => rc.status === "not_run");
    if (first) setSelectedRcId(first.id);
  };

  const activeCaseId = selectedRc?.id ?? "";

  // Scroll active case into view when it changes
  useEffect(() => {
    activeCaseRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeCaseId]);

  const loading = runQuery.isLoading;

  // ── Run completion summary overlay ────────────────────────────────────────
  if (run?.status === "completed" && !loading) {
    const passRate = total > 0 ? Math.round((passed / total) * 100) : 0;
    const failRate = total > 0 ? Math.round((failed / total) * 100) : 0;
    return (
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-48px)] bg-bg px-6 py-12 text-center">
        <div className={cn(
          "flex h-20 w-20 items-center justify-center rounded-full mb-6",
          passRate >= 80 ? "bg-emerald-500/15 ring-4 ring-emerald-500/20" :
          passRate >= 50 ? "bg-amber-500/15 ring-4 ring-amber-500/20" :
          "bg-red-500/15 ring-4 ring-red-500/20"
        )}>
          <span className="text-4xl">{passRate >= 80 ? "🎉" : passRate >= 50 ? "⚠️" : "❌"}</span>
        </div>
        <h1 className="text-xl font-bold text-fg">Koşum Tamamlandı</h1>
        <p className="mt-1 text-[13px] text-fg-muted max-w-sm">{run.name}</p>

        {/* Stats grid */}
        <div className="mt-8 grid grid-cols-3 gap-3 sm:grid-cols-6 w-full max-w-2xl">
          {[
            { label: "Pass Rate", value: `%${passRate}`, color: passRate >= 80 ? "text-emerald-400" : passRate >= 50 ? "text-amber-400" : "text-red-400", bg: passRate >= 80 ? "bg-emerald-500/10" : passRate >= 50 ? "bg-amber-500/10" : "bg-red-500/10" },
            { label: "Geçti",     value: passed,  color: "text-emerald-400", bg: "bg-emerald-500/10" },
            { label: "Başarısız", value: failed,  color: "text-red-400",     bg: "bg-red-500/10"     },
            { label: "Engellendi",value: blocked, color: "text-amber-400",   bg: "bg-amber-500/10"   },
            { label: "Atlandı",   value: runCases.filter(rc => rc.status === "skipped").length, color: "text-fg-muted", bg: "bg-surface-overlay" },
            { label: "Toplam",    value: total,   color: "text-fg",          bg: "bg-surface-overlay" },
          ].map(s => (
            <div key={s.label} className={cn("rounded-xl border border-border p-4", s.bg)}>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">{s.label}</p>
              <p className={cn("mt-2 text-2xl font-bold tabular-nums", s.color)}>{s.value}</p>
            </div>
          ))}
        </div>

        {/* Stacked progress bar */}
        {total > 0 && (
          <div className="mt-4 flex w-full max-w-lg h-2 overflow-hidden rounded-full gap-px">
            {passed  > 0 && <div className="bg-emerald-500" style={{ width: `${(passed  / total) * 100}%` }} />}
            {failed  > 0 && <div className="bg-red-500"     style={{ width: `${(failed  / total) * 100}%` }} />}
            {blocked > 0 && <div className="bg-amber-500"   style={{ width: `${(blocked / total) * 100}%` }} />}
            {notRun  > 0 && <div className="bg-slate-600"   style={{ width: `${(notRun  / total) * 100}%` }} />}
          </div>
        )}

        {/* Insight */}
        {failRate > 0 && (
          <p className="mt-4 max-w-sm text-[12px] text-fg-subtle">
            {failRate >= 50
              ? "Başarısızlık oranı yüksek — kritik defect'leri kontrol edin ve bir regresyon seti oluşturmayı düşünün."
              : `${failed} başarısız senaryo var. Defect oluşturup takip etmeyi unutmayın.`}
          </p>
        )}

        {/* Actions */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            href={`/p/${projectId}/management/reports`}
            className="flex items-center gap-2 rounded-xl bg-brand px-5 py-2.5 text-[13px] font-semibold text-brand-fg hover:brightness-105 transition-colors"
          >
            Rapora Git →
          </Link>
          <Link
            href={`/p/${projectId}/management/defects`}
            className="flex items-center gap-2 rounded-xl border border-border bg-surface-raised px-5 py-2.5 text-[13px] text-fg-muted hover:text-fg transition-colors"
          >
            Defect Ekle
          </Link>
          <Link
            href={`/p/${projectId}/management/runs`}
            className="flex items-center gap-2 rounded-xl border border-border bg-surface-raised px-5 py-2.5 text-[13px] text-fg-muted hover:text-fg transition-colors"
          >
            Runs Listesi
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
    <div className="flex bg-bg" style={{ height: "calc(100vh - 48px)" }}>

      {/* LEFT: Case List / AI Sidebar */}
      <aside className="hidden w-64 flex-none flex-col border-r border-border bg-surface-raised md:flex overflow-hidden">
        {/* Run info */}
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Link href={`/p/${projectId}/management/runs`}
              className="text-fg-disabled hover:text-fg transition-colors">
              <IcBack/>
            </Link>
            <p className="flex-1 min-w-0 truncate text-xs font-semibold text-fg">
              {loading ? "Yükleniyor…" : (run?.name ?? "Execute Run")}
            </p>
            {!loading && total > 0 && (
              <span className="shrink-0 rounded-md bg-surface-overlay px-1.5 py-0.5 font-mono text-[10px] text-fg-disabled tabular-nums">
                {activeCaseIndex + 1}/{total}
              </span>
            )}
          </div>
          {run?.source_ref && (
            <p className="text-[10px] text-fg-disabled">{run.source_ref}</p>
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
                : "text-fg-subtle hover:text-fg border-b-2 border-transparent",
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
                : "text-fg-subtle hover:text-fg border-b-2 border-transparent",
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
                <span className="text-[10px] text-fg-subtle">İlerleme</span>
                <span className="text-[10px] font-bold tabular-nums text-fg">
                  {progress?.progress_pct ?? pct}%
                </span>
              </div>
              <div
                role="progressbar"
                aria-valuenow={progress?.progress_pct ?? pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Koşum ilerleme: ${progress?.progress_pct ?? pct}%`}
                className="h-1 rounded-full bg-surface-overlay overflow-hidden"
              >
                <div className="h-full rounded-full bg-emerald-500/70 transition-all duration-500"
                  style={{ width: `${progress?.progress_pct ?? pct}%` }}/>
              </div>
              {progress && (
                <div className="mt-1.5 flex gap-1.5 flex-wrap text-[9px]">
                  {progress.passed  > 0 && <span className="text-emerald-400">{progress.passed} pass</span>}
                  {progress.failed  > 0 && <span className="text-red-400">{progress.failed} fail</span>}
                  {progress.blocked > 0 && <span className="text-amber-400">{progress.blocked} blk</span>}
                  <span className="text-fg-disabled">{progress.not_run} left</span>
                </div>
              )}
              {!progress && (
                <div className="mt-1.5 flex justify-between text-[9px] text-fg-disabled">
                  <span>{passed} passed</span>
                  <span>{failed > 0 ? `${failed} fail` : ""}</span>
                  <span>{notRun} left</span>
                </div>
              )}
            </div>

            {/* Case list filter tabs */}
            <div className="flex border-b border-border px-2 pt-1.5">
              {([
                { key: "all",     label: "Tümü",    count: total },
                { key: "not_run", label: "Bekliyor", count: notRun },
                { key: "failed",  label: "Hatalı",  count: failed + blocked },
                { key: "passed",  label: "Geçti",   count: passed },
              ] as { key: "all" | "not_run" | "failed" | "passed"; label: string; count: number }[]).map(f => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setCaseFilter(f.key)}
                  className={cn(
                    "flex-1 pb-1.5 text-[9px] font-medium transition-colors border-b-2",
                    caseFilter === f.key
                      ? f.key === "failed" ? "border-red-500 text-red-400"
                        : f.key === "not_run" ? "border-amber-500 text-amber-400"
                        : f.key === "passed" ? "border-emerald-500 text-emerald-400"
                        : "border-brand text-brand"
                      : "border-transparent text-fg-disabled hover:text-fg-subtle",
                  )}
                >
                  {f.label}
                  {f.count > 0 && (
                    <span className={cn(
                      "ml-1 rounded-full px-1 text-[8px] tabular-nums",
                      caseFilter === f.key ? "bg-surface-overlay" : "bg-surface-overlay opacity-70"
                    )}>{f.count}</span>
                  )}
                </button>
              ))}
            </div>

            {/* Jump to first not_run shortcut */}
            {notRun > 0 && caseFilter !== "not_run" && (
              <div className="px-2 pt-1.5 pb-0.5">
                <button
                  type="button"
                  onClick={jumpToFirstNotRun}
                  className="w-full rounded-lg border border-amber-500/20 bg-amber-500/5 py-1.5 text-[10px] text-amber-400 hover:bg-amber-500/10 transition-colors"
                >
                  → İlk bekleyene git ({notRun})
                </button>
              </div>
            )}

            {/* Case list */}
            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-10 rounded-lg bg-surface-overlay animate-pulse" style={{ opacity: Math.max(0.2, 1 - i * 0.1) }}/>
                ))
              ) : filteredCases.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 gap-2">
                  <span className="text-2xl opacity-30">
                    {caseFilter === "not_run" ? "✓" : caseFilter === "failed" ? "✓" : "○"}
                  </span>
                  <p className="text-[10px] text-fg-disabled">
                    {caseFilter === "not_run" ? "Tüm caseler tamamlandı" : caseFilter === "failed" ? "Hatalı case yok" : "Gösterilecek case yok"}
                  </p>
                </div>
              ) : filteredCases.map(rc => (
                <CaseListItem key={rc.id} rc={rc} isSelected={rc.id === activeCaseId}
                  itemRef={rc.id === activeCaseId ? activeCaseRef : undefined}
                  onClick={() => setSelectedRcId(rc.id)}/>
              ))}
            </div>

            {/* Stats footer */}
            <div className="border-t border-border px-3 py-2 space-y-2">
              <SessionTimer runId={runId} />
              <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                {[
                  { dot: "bg-emerald-500/70", label: `${passed} ok` },
                  { dot: "bg-red-500/80",     label: `${failed} fail` },
                  { dot: "bg-amber-500/60",   label: `${blocked} blk` },
                  { dot: "bg-slate-600",      label: `${notRun} bekliyor` },
                ].map(s => (
                  <span key={s.label} className="flex items-center gap-1">
                    <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", s.dot)}/>
                    <span className="text-[9px] text-fg-disabled">{s.label}</span>
                  </span>
                ))}
              </div>
              {run?.status !== "completed" && notRun === 0 && (
                <button type="button"
                  onClick={() => void completeRun.mutateAsync(runId)}
                  disabled={completeRun.isPending}
                  className="w-full rounded-lg bg-emerald-600 py-1.5 text-[11px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors">
                  {completeRun.isPending ? "Tamamlanıyor…" : "✓ Koşumu Tamamla"}
                </button>
              )}
              {run?.status !== "completed" && notRun > 0 && (passed + failed + blocked) > 0 && (
                <button type="button"
                  title={`${notRun} senaryo henüz test edilmedi — yine de tamamla`}
                  onClick={() => setShowEarlyComplete(true)}
                  disabled={completeRun.isPending}
                  className="w-full rounded-lg border border-amber-500/30 py-1.5 text-[11px] font-medium text-amber-400 hover:bg-amber-500/10 disabled:opacity-40 transition-colors">
                  {completeRun.isPending ? "Tamamlanıyor…" : `⚠ Erken Tamamla (${notRun} bekliyor)`}
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
            <h3 className="text-sm font-semibold text-fg">
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
            <ExecutionPanel rc={selectedRc} projectId={projectId} runId={runId} onNext={goNext} onPrev={goPrev} mpid={mpid}/>
          </>
        )}

        {/* Mobile sticky footer */}
        <div className="md:hidden sticky bottom-0 border-t border-border bg-surface-raised px-4 py-3">
          {pendingCount === 0 ? (
            <button
              onClick={() => {
                completeRun.mutateAsync(runId).catch((err: unknown) => {
                  console.error("[Execute] Complete run failed:", err)
                })
              }}
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
    {/* Early-complete confirmation dialog */}
    {showEarlyComplete && (
      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowEarlyComplete(false)}/>
        <div className="relative z-10 w-full max-w-sm rounded-2xl border border-amber-500/30 bg-surface-raised p-6 shadow-2xl">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500/15">
              <svg className="h-5 w-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>
            </div>
            <div className="min-w-0">
              <p className="text-[14px] font-semibold text-fg">Erken Tamamla?</p>
              <p className="mt-1 text-[12px] text-fg-muted">
                <span className="font-semibold text-amber-400">{notRun}</span> senaryo henüz test edilmedi. Koşumu erken tamamlamak istediğinizden emin misiniz?
              </p>
              <p className="mt-1.5 text-[11px] text-fg-subtle">Test edilmeyen senaryolar &quot;not_run&quot; olarak kalacak.</p>
            </div>
          </div>
          <div className="mt-5 flex gap-2 justify-end">
            <button type="button" onClick={() => setShowEarlyComplete(false)}
              className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors">
              Vazgeç
            </button>
            <button type="button"
              onClick={() => { setShowEarlyComplete(false); void completeRun.mutateAsync(runId); }}
              disabled={completeRun.isPending}
              className="rounded-xl bg-amber-600 px-5 py-2 text-[12px] font-semibold text-white hover:bg-amber-500 disabled:opacity-40 transition-colors">
              {completeRun.isPending ? "Tamamlanıyor…" : "Evet, Tamamla"}
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}
