"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  useManagementDefects,
  useUpdateManagementDefect,
  useCreateManagementDefect,
  useDeleteManagementDefect,
  useAnalyzeDefectRootCause,
  type DefectLink,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const CLOSED_STATUSES = new Set(["closed","done","resolved","fixed","verified"]);
const BLOCKER_PATTERN = /blocker|critical|p0|sev0|sev1|release|prod|production|security|data loss/i;

function isClosed(d: DefectLink)       { return CLOSED_STATUSES.has(d.status.trim().toLowerCase()); }
function isBlocker(d: DefectLink)      { return !isClosed(d) && (BLOCKER_PATTERN.test(`${d.title} ${d.status} ${d.external_key}`) || ["blocker","critical"].includes(d.severity.toLowerCase()) || ["P0","P1"].includes(d.priority)); }
function daysSince(v?: string | null)  { if (!v) return null; const t = new Date(v).getTime(); return Number.isNaN(t) ? null : Math.max(0, Math.floor((Date.now() - t) / 86_400_000)); }

// ─── Status dot config ────────────────────────────────────────────────────────

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-red-500/70",
  major:    "bg-orange-400/60",
  minor:    "bg-slate-500",
  trivial:  "bg-slate-600",
  blocker:  "bg-red-500/80",
};

const STATUS_DOT_MAP: Record<string, string> = {
  open:        "bg-red-500/70",
  in_progress: "bg-blue-500 animate-pulse",
  resolved:    "bg-emerald-500/70",
  fixed:       "bg-emerald-500/70",
  closed:      "bg-slate-600",
  verified:    "bg-emerald-400",
  done:        "bg-emerald-400",
  blocked:     "bg-slate-500",
};

function statusDot(s: string) {
  const norm = s.trim().toLowerCase().replace(/\s+/g, "_");
  if (CLOSED_STATUSES.has(norm)) return "bg-emerald-500/70";
  if (norm.includes("progress"))  return "bg-teal-500";
  return STATUS_DOT_MAP[norm] ?? "bg-slate-500";
}

// ─── All statuses ─────────────────────────────────────────────────────────────

const ALL_STATUSES = [
  "open", "in_progress", "blocked", "resolved", "fixed",
  "closed", "verified", "deferred", "rejected", "reopened",
];

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcSearch() { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>; }
function IcClose()  { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>; }
function IcBug()    { return (
  <svg width="80" height="80" viewBox="0 0 80 80" className="opacity-[0.07]" fill="none">
    <circle cx="40" cy="36" r="18" stroke="#94a3b8" strokeWidth="2"/>
    <path d="M26 18l-8-8M54 18l8-8M22 36H10M70 36H58M26 54l-8 8M54 54l8 8M40 54v12" stroke="#64748b" strokeWidth="1.5" strokeLinecap="round"/>
    <circle cx="33" cy="32" r="3" fill="#64748b" fillOpacity=".5"/>
    <circle cx="47" cy="32" r="3" fill="#64748b" fillOpacity=".5"/>
  </svg>
); }
function IcTrash()  { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>; }
function IcLink()   { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path strokeLinecap="round" strokeLinejoin="round" d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>; }

// ─── Prop interfaces ──────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  hint: string;
  loading?: boolean;
}

interface DefectEditModalProps {
  defect: DefectLink;
  mpid: string;
  onClose: () => void;
  onDeleted: () => void;
}

interface DefectRowProps {
  defect: DefectLink;
  mpid: string;
  onClick: () => void;
  onDeleted: () => void;
}

interface CreateDefectModalProps {
  mpid: string;
  onClose: () => void;
  onDone: () => void;
}

interface ConfirmDeleteDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
  isPending: boolean;
}

// ─── Sparkline ────────────────────────────────────────────────────────────────

interface SparklineProps {
  defects: DefectLink[];
}

function OpenDefectSparkline({ defects }: SparklineProps) {
  const points = useMemo(() => {
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    return Array.from({ length: 7 }, (_, i) => {
      const dayEnd = new Date(today);
      dayEnd.setDate(today.getDate() - (6 - i));
      const count = defects.filter(d => {
        const created = new Date(d.created_at).getTime();
        return created <= dayEnd.getTime() && !isClosed(d);
      }).length;
      return count;
    });
  }, [defects]);

  const max = Math.max(...points, 1);
  const W = 140;
  const H = 32;
  const pad = 2;

  const coords = points.map((v, i) => {
    const x = pad + (i / (points.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v / max) * (H - pad * 2));
    return `${x},${y}`;
  }).join(" ");

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface-raised px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-muted">Açık Defect Trendi</p>
        <p className="text-[10px] text-fg-subtle mt-0.5">Son 7 gün</p>
      </div>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="shrink-0">
        <polyline
          points={coords}
          fill="none"
          stroke="#f87171"
          strokeWidth="1.5"
          strokeLinejoin="round"
          strokeLinecap="round"
          opacity="0.7"
        />
        {points.map((v, i) => {
          const x = pad + (i / (points.length - 1)) * (W - pad * 2);
          const y = H - pad - ((v / max) * (H - pad * 2));
          return (
            <circle key={i} cx={x} cy={y} r="2" fill="#f87171" opacity="0.9"/>
          );
        })}
      </svg>
      <div className="shrink-0 text-right">
        <p className="text-lg font-bold tabular-nums text-fg">{points[6]}</p>
        <p className="text-[9px] text-fg-subtle">bugün</p>
      </div>
    </div>
  );
}

// ─── Stats KPI ────────────────────────────────────────────────────────────────

function StatCard({ label, value, hint, loading }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-muted">{label}</p>
      {loading ? (
        <div className="mt-2 h-7 w-14 animate-pulse rounded bg-surface-overlay"/>
      ) : (
        <p className="mt-1 text-2xl font-bold tabular-nums text-fg">{value}</p>
      )}
      <p className="mt-1 text-[10px] text-fg-muted">{hint}</p>
    </div>
  );
}

// ─── Confirm Delete Dialog ────────────────────────────────────────────────────

function ConfirmDeleteDialog({ onConfirm, onCancel, isPending }: ConfirmDeleteDialogProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-sm rounded-xl border border-red-500/30 bg-surface-raised shadow-2xl overflow-hidden">
        <div className="p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-500/10">
              <IcTrash/>
            </div>
            <h3 className="text-[14px] font-semibold text-fg">Defect Silinecek</h3>
          </div>
          <p className="text-[12px] text-fg-muted leading-relaxed">
            Bu defect kalıcı olarak silinecek. Onaylıyor musunuz?
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg disabled:opacity-40 transition-colors"
          >
            İptal
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="rounded-xl bg-red-600 px-4 py-2 text-[12px] font-medium text-white hover:bg-red-700 disabled:opacity-40 transition-colors"
          >
            {isPending ? "Siliniyor…" : "Evet, Sil"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Create Defect Modal ──────────────────────────────────────────────────────

function CreateDefectModal({ mpid, onClose, onDone }: CreateDefectModalProps) {
  const create = useCreateManagementDefect(mpid);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const [title,       setTitle]       = useState("");
  const [externalKey, setExternalKey] = useState("");
  const [url,         setUrl]         = useState("");
  const [severity,    setSeverity]    = useState("major");
  const [priority,    setPriority]    = useState("P2");
  const [status,      setStatus]      = useState("open");
  const [description, setDescription] = useState("");

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/40 transition-colors";
  const sel = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40 transition-colors";

  const handleSubmit = async () => {
    if (!title.trim()) return;
    const payload: Parameters<typeof create.mutateAsync>[0] = {
      title: title.trim(),
      external_key: externalKey.trim() || "",
      url: url.trim() || null,
      severity,
      priority,
      status,
      root_cause: description.trim() || null,
    };
    await create.mutateAsync(payload);
    onDone();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-[14px] font-semibold text-fg">Yeni Defect Oluştur</h2>
          <button type="button" onClick={onClose} aria-label="Modalı kapat"
            className="ml-2 shrink-0 rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Fields */}
        <div className="p-5 space-y-4">
          {/* Title */}
          <div>
            <label htmlFor="create-defect-title" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">
              Başlık <span className="text-red-400">*</span>
            </label>
            <input
              id="create-defect-title"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Defect başlığı…"
              className={inp}
            />
          </div>

          {/* External Key & URL */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="create-defect-key" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">External Key</label>
              <input
                id="create-defect-key"
                type="text"
                value={externalKey}
                onChange={e => setExternalKey(e.target.value)}
                placeholder="JIRA-123"
                className={inp}
              />
            </div>
            <div>
              <label htmlFor="create-defect-url" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">URL</label>
              <input
                id="create-defect-url"
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://…"
                className={inp}
              />
            </div>
          </div>

          {/* Severity / Priority / Status */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label htmlFor="create-defect-severity" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Severity</label>
              <select id="create-defect-severity" value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                {["blocker","critical","major","minor","trivial"].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="create-defect-priority" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Priority</label>
              <select id="create-defect-priority" value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="create-defect-status" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Status</label>
              <select id="create-defect-status" value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                {ALL_STATUSES.map(v => (
                  <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="create-defect-desc" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Açıklama</label>
            <textarea
              id="create-defect-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              placeholder="Defect açıklaması…"
              className={cn(inp, "resize-none")}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border px-5 py-4">
          <button type="button" onClick={onClose}
            className="rounded-xl border border-border px-4 py-2 text-[13px] text-fg-muted hover:text-fg transition-colors">
            İptal
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={create.isPending || !title.trim()}
            className="rounded-xl bg-brand px-5 py-2 text-[13px] font-medium text-brand-fg hover:brightness-105 disabled:opacity-40 transition-colors"
          >
            {create.isPending ? "Oluşturuluyor…" : "Oluştur"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Defect Edit Modal ────────────────────────────────────────────────────────

function DefectEditModal({ defect, mpid, onClose, onDeleted }: DefectEditModalProps) {
  const update   = useUpdateManagementDefect(mpid);
  const del      = useDeleteManagementDefect(mpid);
  const analyze  = useAnalyzeDefectRootCause(mpid);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const [status,        setStatus]       = useState(defect.status);
  const [severity,      setSeverity]     = useState(defect.severity);
  const [priority,      setPriority]     = useState(defect.priority);
  const [retestStatus,  setRetestStatus] = useState(defect.retest_status);
  const [rootCause,     setRootCause]    = useState(defect.root_cause ?? "");
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const save = async () => {
    await update.mutateAsync({
      defectId: defect.id,
      status,
      severity,
      priority,
      retest_status: retestStatus,
      root_cause: rootCause.trim() || null,
    });
    onClose();
  };

  const handleDelete = async () => {
    await del.mutateAsync(defect.id);
    setShowConfirmDelete(false);
    onDeleted();
  };

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder-slate-600 outline-none focus:border-teal-500/40 transition-colors";
  const sel = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40 transition-colors";

  const days = daysSince(defect.created_at);
  const hasRunLink = !!defect.run_case_id && defect.run_case_id !== "";

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
        <div className="w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div className="flex items-center gap-2.5 min-w-0">
              <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", SEVERITY_DOT[defect.severity.toLowerCase()] ?? "bg-slate-600")}/>
              <span className="font-mono text-[11px] text-fg-muted shrink-0">{defect.external_key}</span>
              <span className="truncate text-[14px] font-semibold text-fg">{defect.title}</span>
            </div>
            <div className="ml-2 flex shrink-0 items-center gap-1">
              {/* Delete button */}
              <button
                type="button"
                onClick={() => setShowConfirmDelete(true)}
                aria-label="Defect'i sil"
                title="Defect'i sil"
                className="rounded-lg p-1.5 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 transition-colors"
              >
                <IcTrash/>
              </button>
              <button type="button" onClick={onClose} aria-label="Modalı kapat"
                className="rounded-lg p-1.5 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          {/* Meta row — external URL + linked run case + age */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-border px-5 py-2.5 text-[11px]">
            {defect.url && (
              <a href={defect.url} target="_blank" rel="noreferrer"
                className="flex items-center gap-1 text-teal-400 hover:underline">
                <IcLink/>
                {defect.url.length > 40 ? defect.url.slice(0, 40) + "…" : defect.url}
              </a>
            )}
            {hasRunLink && (
              <span className="flex items-center gap-1 text-fg-muted">
                <span className="text-fg-subtle">Bağlı Run Case:</span>
                <span className="font-mono text-fg-muted">{defect.run_case_id.slice(0, 8)}…</span>
              </span>
            )}
            {days !== null && (
              <span className={cn("text-fg-muted", days > 14 ? "text-red-400/70" : "")}>
                {days}g önce oluşturuldu
              </span>
            )}
          </div>

          {/* Fields */}
          <div className="p-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Status</label>
                <select value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                  {ALL_STATUSES.map(v => (
                    <option key={v} value={v}>{v.replace(/_/g," ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Retest</label>
                <select value={retestStatus} onChange={e => setRetestStatus(e.target.value)} className={sel}>
                  {["pending","passed","failed","not_required","retest_failed"].map(v => (
                    <option key={v} value={v}>{v.replace(/_/g," ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Severity</label>
                <select value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                  {["blocker","critical","major","minor","trivial"].map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Priority</label>
                <select value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                  {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <label className="text-[10px] uppercase tracking-widest text-fg-subtle">Root Cause</label>
                <button type="button"
                  disabled={analyze.isPending}
                  onClick={async () => {
                    const res = await analyze.mutateAsync({ defect_title: defect.title, defect_status: status });
                    if (!rootCause) setRootCause(res.root_cause);
                    setAiSuggestions(res.suggestions);
                  }}
                  className="flex items-center gap-1 text-[10px] text-teal-400 hover:text-teal-300 disabled:opacity-40 transition-colors">
                  {analyze.isPending ? "Analiz ediliyor…" : "✦ AI Analiz"}
                </button>
              </div>
              <textarea value={rootCause} onChange={e => setRootCause(e.target.value)}
                rows={3} placeholder="Hatanın temel nedeni…"
                className={cn(inp, "resize-none")}/>
              {aiSuggestions.length > 0 && (
                <div className="mt-2 space-y-1 rounded-lg border border-teal-500/20 bg-teal-500/5 px-3 py-2">
                  {aiSuggestions.map((s, i) => (
                    <p key={i} className="text-[11px] text-teal-300/80">• {s}</p>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-border px-5 py-4">
            <button type="button" onClick={onClose}
              className="rounded-xl border border-border px-4 py-2 text-[13px] text-fg-muted hover:text-fg transition-colors">
              İptal
            </button>
            <button type="button" onClick={save} disabled={update.isPending}
              className="rounded-xl bg-brand px-5 py-2 text-[13px] font-medium text-brand-fg hover:brightness-105 disabled:opacity-40 transition-colors">
              {update.isPending ? "Kaydediliyor…" : "Kaydet"}
            </button>
          </div>
        </div>
      </div>

      {/* Confirm delete overlay */}
      {showConfirmDelete && (
        <ConfirmDeleteDialog
          onConfirm={handleDelete}
          onCancel={() => setShowConfirmDelete(false)}
          isPending={del.isPending}
        />
      )}
    </>
  );
}

// ─── Table Row ────────────────────────────────────────────────────────────────

function DefectRow({ defect, mpid, onClick, onDeleted }: DefectRowProps) {
  const del = useDeleteManagementDefect(mpid);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const closed  = isClosed(defect);
  const blocker = isBlocker(defect);
  const days    = daysSince(defect.created_at);
  const sevDot  = SEVERITY_DOT[defect.severity.toLowerCase()] ?? "bg-slate-600";
  const sttDot  = statusDot(defect.status);

  const ageCls = closed                              ? "text-fg-subtle"
               : days !== null && days > 14          ? "text-red-400"
               : days !== null && days > 7           ? "text-fg-muted"
               :                                       "text-fg-muted";

  const handleDeleteConfirm = async () => {
    await del.mutateAsync(defect.id);
    setShowConfirmDelete(false);
    onDeleted();
  };

  return (
    <>
      <tr onClick={onClick}
        className={cn("cursor-pointer border-b border-border hover:bg-surface-overlay transition-colors", blocker && "bg-red-500/3")}>
        {/* Severity dot */}
        <td className="w-8 px-3 py-3">
          <span className={cn("h-1.5 w-1.5 rounded-full inline-block", sevDot)}/>
        </td>
        {/* Key */}
        <td className="w-28 px-3 py-3">
          {defect.url ? (
            <a href={defect.url} target="_blank" rel="noreferrer"
              onClick={e => e.stopPropagation()}
              className="font-mono text-[10px] text-teal-400 hover:underline">{defect.external_key}</a>
          ) : (
            <span className="font-mono text-[10px] text-fg-muted">{defect.external_key}</span>
          )}
        </td>
        {/* Title */}
        <td className="px-3 py-3">
          <p className="text-xs text-fg line-clamp-1">{defect.title}</p>
          {blocker && (
            <span className="mt-0.5 inline-flex items-center gap-1">
              <span className="h-1 w-1 rounded-full bg-red-500 inline-block"/>
              <span className="text-[9px] text-red-400 uppercase tracking-wide">blocker</span>
            </span>
          )}
        </td>
        {/* Status */}
        <td className="w-28 px-3 py-3">
          <span className="inline-flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", sttDot)}/>
            <span className="text-[10px] text-fg-muted">{defect.status.replace(/_/g, " ")}</span>
          </span>
        </td>
        {/* Severity */}
        <td className="hidden w-20 px-3 py-3 md:table-cell">
          <span className="text-[10px] text-fg-muted">{defect.severity}</span>
        </td>
        {/* Priority */}
        <td className="hidden w-14 px-3 py-3 md:table-cell">
          <span className="font-mono text-[10px] text-fg-muted">{defect.priority}</span>
        </td>
        {/* Retest */}
        <td className="hidden w-28 px-3 py-3 lg:table-cell">
          <span className="text-[10px] text-fg-muted">{defect.retest_status.replace(/_/g, " ")}</span>
        </td>
        {/* Age */}
        <td className="hidden w-16 px-3 py-3 xl:table-cell">
          <span className={cn("text-[10px] tabular-nums", ageCls)}>
            {days !== null ? `${days}g` : "—"}
          </span>
        </td>
        {/* Date */}
        <td className="hidden w-20 px-3 py-3 xl:table-cell">
          <span className="text-[10px] text-fg-subtle">
            {new Date(defect.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
          </span>
        </td>
        {/* Delete */}
        <td className="w-10 px-2 py-3">
          <button
            type="button"
            aria-label="Defect'i sil"
            title="Defect'i sil"
            onClick={e => { e.stopPropagation(); setShowConfirmDelete(true); }}
            className="rounded-lg p-1 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 transition-colors"
          >
            <IcTrash/>
          </button>
        </td>
      </tr>
      {showConfirmDelete && (
        <ConfirmDeleteDialog
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowConfirmDelete(false)}
          isPending={del.isPending}
        />
      )}
    </>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ManagementDefectsPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);

  const defectsQuery = useManagementDefects(mpid || undefined);
  const rows         = defectsQuery.data ?? [];
  const loading      = defectsQuery.isLoading;

  const searchParams = useSearchParams();
  const router       = useRouter();
  const pathname     = usePathname();

  const [search,       setSearch]       = useState(searchParams.get("q") ?? "");
  const [severityF,    setSeverityF]    = useState(searchParams.get("severity") ?? "");
  const [statusF,      setStatusF]      = useState(searchParams.get("status") ?? "");
  const [priorityF,    setPriorityF]    = useState(searchParams.get("priority") ?? "");
  const [editDefect,   setEditDefect]   = useState<DefectLink | null>(null);
  const [showCreate,   setShowCreate]   = useState(false);
  const [page,         setPage]         = useState(1);
  const [sortCol,      setSortCol]      = useState<string>("created_at");
  const [sortDir,      setSortDir]      = useState<"asc" | "desc">("desc");
  const PAGE_SIZE = 20;

  const updateUrl = (params: Record<string, string>) => {
    const sp = new URLSearchParams(searchParams.toString());
    Object.entries(params).forEach(([k, v]) => { if (v) sp.set(k, v); else sp.delete(k); });
    router.replace(pathname + "?" + sp.toString(), { scroll: false });
  };

  const handleSearchChange   = (v: string) => { setSearch(v);    updateUrl({ q: v }); };
  const handleSeverityChange = (v: string) => { setSeverityF(v); updateUrl({ severity: v }); };
  const handleStatusChange   = (v: string) => { setStatusF(v);   updateUrl({ status: v }); };
  const handlePriorityChange = (v: string) => { setPriorityF(v); updateUrl({ priority: v }); };

  const open      = rows.filter(d => !isClosed(d));
  const critical  = rows.filter(d => isBlocker(d));
  const reopened  = rows.filter(d => d.retest_status === "failed" || d.retest_status === "retest_failed");

  const filtered = useMemo(() => {
    let r = rows;
    const q = search.trim().toLowerCase();
    if (q)        r = r.filter(d => d.title.toLowerCase().includes(q) || d.external_key.toLowerCase().includes(q));
    if (severityF) r = r.filter(d => d.severity.toLowerCase() === severityF);
    if (statusF)   r = r.filter(d => d.status.toLowerCase().includes(statusF));
    if (priorityF) r = r.filter(d => d.priority === priorityF);
    return r;
  }, [rows, search, severityF, statusF, priorityF]);

  const sorted = useMemo(() => {
    const PRIO_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };
    const SEV_ORDER: Record<string, number> = { critical: 0, major: 1, minor: 2, trivial: 3 };
    return [...filtered].sort((a, b) => {
      let va: string | number = "";
      let vb: string | number = "";
      if (sortCol === "priority") { va = PRIO_ORDER[a.priority] ?? 9; vb = PRIO_ORDER[b.priority] ?? 9; }
      else if (sortCol === "severity") { va = SEV_ORDER[a.severity] ?? 9; vb = SEV_ORDER[b.severity] ?? 9; }
      else { va = String((a as unknown as Record<string, unknown>)[sortCol] ?? ""); vb = String((b as unknown as Record<string, unknown>)[sortCol] ?? ""); }
      if (typeof va === "number" && typeof vb === "number") return sortDir === "asc" ? va - vb : vb - va;
      const sa = String(va); const sb = String(vb);
      return sortDir === "asc" ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
  }, [filtered, sortCol, sortDir]);

  function SortTh({ col, label, className }: { col: string; label: string; className?: string }) {
    const active = sortCol === col;
    return (
      <th onClick={() => { setSortDir(active && sortDir === "desc" ? "asc" : "desc"); setSortCol(col); }}
        className={cn("cursor-pointer select-none px-4 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle hover:text-fg", className)}>
        {label}{active ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
      </th>
    );
  }

  // Bug fix 1: tüm filtre değişkenlerini bağımlılık listesine ekle
  useEffect(() => { setPage(1); }, [search, severityF, statusF, priorityF]);

  const hasFilter = !!(search || severityF || statusF || priorityF);
  const clearFilters = useCallback(() => {
    setSearch(""); setSeverityF(""); setStatusF(""); setPriorityF(""); setPage(1);
    const sp = new URLSearchParams(searchParams.toString());
    sp.delete("q"); sp.delete("severity"); sp.delete("status"); sp.delete("priority");
    router.replace(pathname + (sp.toString() ? "?" + sp.toString() : ""), { scroll: false });
  }, [searchParams, router, pathname]);

  const totalPages     = useMemo(() => Math.ceil(sorted.length / PAGE_SIZE), [sorted]);
  const paginatedItems = useMemo(
    () => sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [sorted, page]
  );

  const SEL = "rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 text-[10px] text-fg outline-none focus:border-border-strong transition-colors";

  return (
    <div className="min-h-screen bg-bg px-5 py-5">
      <div className="mx-auto max-w-7xl space-y-5">

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-fg">Defect Management</h1>
            <p className="mt-0.5 text-xs text-fg-muted">Test koşumlarından bağlanan defect&apos;ler ve retest durumu</p>
          </div>
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            aria-label="Yeni defect oluştur"
            className="rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg hover:brightness-105 transition-colors"
          >
            + Yeni Defect
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Toplam Defect"  value={loading ? "—" : rows.length}     hint="bağlı defect"    loading={loading}/>
          <StatCard label="Açık"           value={loading ? "—" : open.length}     hint="kapatılmamış"   loading={loading}/>
          <StatCard label="Blocker"        value={loading ? "—" : critical.length} hint="release blocker" loading={loading}/>
          <StatCard label="Reopen"         value={loading ? "—" : reopened.length} hint="yeniden açılan"  loading={loading}/>
        </div>

        {/* Bug fix 3: Açık defect trendi sparkline */}
        {!loading && rows.length > 0 && <OpenDefectSparkline defects={rows}/>}

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 rounded-xl border border-border bg-surface-raised px-4 py-3">
          {/* Search */}
          <div className="flex w-full sm:w-48 items-center gap-1.5 rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 sm:w-64">
            <IcSearch/>
            <input type="text" value={search} onChange={e => handleSearchChange(e.target.value)} placeholder="Ara…"
              aria-label="Defect ara"
              className="flex-1 bg-transparent text-[10px] text-fg placeholder-slate-600 outline-none min-w-0"/>
            {search && <button type="button" onClick={() => handleSearchChange("")} aria-label="Aramayı temizle" className="text-fg-subtle hover:text-fg"><IcClose/></button>}
          </div>

          <label htmlFor="defect-severity-filter" className="sr-only">Severity filtresi</label>
          <select id="defect-severity-filter" value={severityF} onChange={e => handleSeverityChange(e.target.value)} className={SEL}>
            <option value="">Severity</option>
            {["blocker","critical","major","minor","trivial"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
          <label htmlFor="defect-status-filter" className="sr-only">Status filtresi</label>
          <select id="defect-status-filter" value={statusF} onChange={e => handleStatusChange(e.target.value)} className={SEL}>
            <option value="">Status</option>
            {ALL_STATUSES.map(v => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
          <label htmlFor="defect-priority-filter" className="sr-only">Priority filtresi</label>
          <select id="defect-priority-filter" value={priorityF} onChange={e => handlePriorityChange(e.target.value)} className={SEL}>
            <option value="">Priority</option>
            {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>

          {hasFilter && (
            <button type="button" onClick={clearFilters}
              className="rounded-xl border border-red-500/20 px-2 py-1.5 text-[10px] text-red-400 hover:bg-red-500/10 transition-colors">
              Temizle
            </button>
          )}

          <span className="ml-auto text-[10px] text-fg-subtle">
            {hasFilter ? `${sorted.length} / ${rows.length}` : `${rows.length} defect`}
          </span>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
          {loading ? (
            <div className="space-y-px">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 border-b border-border px-4 py-3"
                  style={{ opacity: Math.max(0.2, 1 - i * 0.15) }}>
                  <div className="h-3 w-20 animate-pulse rounded bg-surface-overlay"/>
                  <div className="h-3 flex-1 animate-pulse rounded bg-surface-overlay"/>
                  <div className="h-5 w-16 animate-pulse rounded bg-surface-overlay"/>
                </div>
              ))}
            </div>
          ) : defectsQuery.isError ? (
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <p className="text-[13px] text-red-400">Defect&apos;ler yüklenemedi.</p>
              <button onClick={() => void defectsQuery.refetch()} className="text-[12px] text-teal-400 hover:underline">
                Tekrar dene
              </button>
            </div>
          ) : sorted.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center gap-3">
              <IcBug/>
              <h3 className="text-sm font-semibold text-fg-muted">
                {hasFilter ? "Defect bulunamadı" : "Henüz defect yok"}
              </h3>
              <p className="text-xs text-fg-subtle">
                {hasFilter ? "Filtre veya arama terimini değiştirin." : (
                  <>
                    Test koşumları sırasında defect bağlayabilirsiniz.
                    <Link href={`/p/${projectId}/management/runs`} className="ml-1 text-brand underline text-[12px]">
                      Run başlat →
                    </Link>
                  </>
                )}
              </p>
              {hasFilter && (
                <button type="button" onClick={clearFilters}
                  className="rounded-xl border border-border px-4 py-2 text-xs text-fg-muted hover:text-fg transition-colors">
                  Filtreleri Temizle
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="sticky top-0 z-10 bg-surface-raised border-b border-border">
                  <tr>
                    <th scope="col" className="w-8 px-3 py-2.5"/>
                    <th scope="col" className="px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">Key</th>
                    <SortTh col="title" label="Başlık"/>
                    <SortTh col="status" label="Durum"/>
                    <SortTh col="severity" label="Severity" className="hidden md:table-cell"/>
                    <SortTh col="priority" label="Priority" className="hidden md:table-cell"/>
                    <th scope="col" className="hidden px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle md:table-cell">Retest</th>
                    <th scope="col" className="hidden px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle xl:table-cell">Yaş</th>
                    <SortTh col="created_at" label="Tarih" className="hidden xl:table-cell"/>
                    <th scope="col" className="w-10 px-2 py-2.5"/>
                  </tr>
                </thead>
                <tbody>
                  {paginatedItems.map(d => (
                    <DefectRow
                      key={d.id}
                      defect={d}
                      mpid={mpid ?? ""}
                      onClick={() => setEditDefect(d)}
                      onDeleted={() => void defectsQuery.refetch()}
                    />
                  ))}
                </tbody>
              </table>
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-border px-4 pt-4 pb-3">
                  <span className="text-sm text-muted-foreground text-fg-muted">
                    {sorted.length} sonuçtan {Math.min(page * PAGE_SIZE, sorted.length)} tanesi gösteriliyor
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={page === 1}
                      onClick={() => setPage(p => p - 1)}
                      className="rounded px-3 py-1 text-sm border border-border text-fg disabled:opacity-50 hover:bg-surface-overlay transition-colors"
                    >
                      ← Önceki
                    </button>
                    <span className="px-3 py-1 text-sm text-fg-muted">{page} / {totalPages}</span>
                    <button
                      disabled={page === totalPages}
                      onClick={() => setPage(p => p + 1)}
                      className="rounded px-3 py-1 text-sm border border-border text-fg disabled:opacity-50 hover:bg-surface-overlay transition-colors"
                    >
                      Sonraki →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Defect edit modal */}
        {editDefect && mpid && (
          <DefectEditModal
            defect={editDefect}
            mpid={mpid}
            onClose={() => setEditDefect(null)}
            onDeleted={() => { setEditDefect(null); void defectsQuery.refetch(); }}
          />
        )}

        {/* Create defect modal */}
        {showCreate && mpid && (
          <CreateDefectModal
            mpid={mpid}
            onClose={() => setShowCreate(false)}
            onDone={() => { setShowCreate(false); void defectsQuery.refetch(); }}
          />
        )}

        {/* Footer summary */}
        {!loading && rows.length > 0 && (
          <div className="flex flex-wrap gap-4 rounded-xl border border-border bg-surface-raised px-4 py-3">
            {[
              { dot: "bg-red-500/70",     label: `${open.length} açık` },
              { dot: "bg-emerald-500/70", label: `${rows.length - open.length} kapalı` },
              { dot: "bg-red-500/80",     label: `${critical.length} blocker` },
              { dot: "bg-slate-500",      label: `${reopened.length} reopen` },
            ].map(s => (
              <span key={s.label} className="flex items-center gap-1.5">
                <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", s.dot)}/>
                <span className="text-[10px] text-fg-muted">{s.label}</span>
              </span>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
