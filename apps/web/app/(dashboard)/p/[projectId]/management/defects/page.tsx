"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  useManagementDefects,
  useUpdateManagementDefect,
  useCreateManagementDefect,
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
}

interface DefectRowProps {
  defect: DefectLink;
  onClick: () => void;
}

interface CreateDefectModalProps {
  mpid: string;
  onClose: () => void;
  onDone: () => void;
}

// ─── Stats KPI ────────────────────────────────────────────────────────────────

function StatCard({ label, value, hint, loading }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface-raised p-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">{label}</p>
      {loading ? (
        <div className="mt-2 h-7 w-14 animate-pulse rounded bg-surface-overlay"/>
      ) : (
        <p className="mt-1 text-2xl font-bold tabular-nums text-white">{value}</p>
      )}
      <p className="mt-1 text-[10px] text-slate-500">{hint}</p>
    </div>
  );
}

// ─── Create Defect Modal ──────────────────────────────────────────────────────

function CreateDefectModal({ mpid, onClose, onDone }: CreateDefectModalProps) {
  const create = useCreateManagementDefect(mpid);

  const [title,       setTitle]       = useState("");
  const [externalKey, setExternalKey] = useState("");
  const [url,         setUrl]         = useState("");
  const [severity,    setSeverity]    = useState("major");
  const [priority,    setPriority]    = useState("P2");
  const [status,      setStatus]      = useState("open");
  const [description, setDescription] = useState("");

  const inp = "w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/40 transition-colors";
  const sel = "w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/40 transition-colors";

  const handleSubmit = async () => {
    if (!title.trim()) return;
    await create.mutateAsync({
      title: title.trim(),
      external_key: externalKey.trim() || "",
      url: url.trim() || null,
      severity,
      priority,
      status,
      root_cause: description.trim() || null,
      run_case_id: "",
    });
    onDone();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-[14px] font-semibold text-slate-100">Yeni Defect Oluştur</h2>
          <button type="button" onClick={onClose}
            className="ml-2 shrink-0 rounded-lg p-1.5 text-slate-600 hover:bg-white/[0.06] hover:text-slate-300 transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Fields */}
        <div className="p-5 space-y-4">
          {/* Title */}
          <div>
            <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">
              Başlık <span className="text-red-400">*</span>
            </label>
            <input
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
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">External Key</label>
              <input
                type="text"
                value={externalKey}
                onChange={e => setExternalKey(e.target.value)}
                placeholder="JIRA-123"
                className={inp}
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">URL</label>
              <input
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
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Severity</label>
              <select value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                {["blocker","critical","major","minor","trivial"].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Status</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                {["open","in_progress","blocked"].map(v => (
                  <option key={v} value={v}>{v.replace("_", " ")}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Açıklama</label>
            <textarea
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
            className="rounded-xl border border-border px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300 transition-colors">
            İptal
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={create.isPending || !title.trim()}
            className="rounded-xl bg-teal-600 px-5 py-2 text-[13px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors"
          >
            {create.isPending ? "Oluşturuluyor…" : "Oluştur"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Defect Edit Modal ────────────────────────────────────────────────────────

function DefectEditModal({ defect, mpid, onClose }: DefectEditModalProps) {
  const update   = useUpdateManagementDefect(mpid);
  const analyze  = useAnalyzeDefectRootCause(mpid);

  const [status,       setStatus]       = useState(defect.status);
  const [severity,     setSeverity]     = useState(defect.severity);
  const [priority,     setPriority]     = useState(defect.priority);
  const [retestStatus, setRetestStatus] = useState(defect.retest_status);
  const [rootCause,    setRootCause]    = useState(defect.root_cause ?? "");
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);

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

  const inp = "w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/40 transition-colors";
  const sel = "w-full rounded-xl border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/40 transition-colors";

  const days = daysSince(defect.created_at);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", SEVERITY_DOT[defect.severity.toLowerCase()] ?? "bg-slate-600")}/>
            <span className="font-mono text-[11px] text-slate-400 shrink-0">{defect.external_key}</span>
            <span className="truncate text-[14px] font-semibold text-slate-100">{defect.title}</span>
          </div>
          <button type="button" onClick={onClose}
            className="ml-2 shrink-0 rounded-lg p-1.5 text-slate-600 hover:bg-white/[0.06] hover:text-slate-300 transition-colors">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 border-b border-border px-5 py-2.5 text-[11px]">
          {defect.url && (
            <a href={defect.url} target="_blank" rel="noreferrer"
              className="text-teal-400 hover:underline">
              {defect.url.length > 40 ? defect.url.slice(0, 40) + "…" : defect.url}
            </a>
          )}
          {days !== null && (
            <span className={cn("text-slate-500", days > 14 ? "text-red-400/70" : "")}>
              {days}g önce oluşturuldu
            </span>
          )}
        </div>

        {/* Fields */}
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Status</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                {["open","in_progress","resolved","fixed","closed","blocked","verified"].map(v => (
                  <option key={v} value={v}>{v.replace("_"," ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Retest</label>
              <select value={retestStatus} onChange={e => setRetestStatus(e.target.value)} className={sel}>
                {["pending","passed","failed","not_required","retest_failed"].map(v => (
                  <option key={v} value={v}>{v.replace(/_/g," ")}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-slate-600">Severity</label>
              <select value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                {["blocker","critical","major","minor","trivial"].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
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
            <div className="mb-1 flex items-center justify-between">
              <label className="text-[10px] uppercase tracking-widest text-slate-600">Root Cause</label>
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
            className="rounded-xl border border-border px-4 py-2 text-[13px] text-slate-500 hover:text-slate-300 transition-colors">
            İptal
          </button>
          <button type="button" onClick={save} disabled={update.isPending}
            className="rounded-xl bg-teal-600 px-5 py-2 text-[13px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors">
            {update.isPending ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Table Row ────────────────────────────────────────────────────────────────

function DefectRow({ defect, onClick }: DefectRowProps) {
  const closed     = isClosed(defect);
  const blocker    = isBlocker(defect);
  const days       = daysSince(defect.created_at);
  const sevDot     = SEVERITY_DOT[defect.severity.toLowerCase()] ?? "bg-slate-600";
  const sttDot     = statusDot(defect.status);

  const ageCls = closed                              ? "text-slate-600"
               : days !== null && days > 14          ? "text-red-400"
               : days !== null && days > 7           ? "text-slate-400"
               :                                       "text-slate-500";

  return (
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
            className="font-mono text-[10px] text-teal-400 hover:underline">{defect.external_key}</a>
        ) : (
          <span className="font-mono text-[10px] text-slate-500">{defect.external_key}</span>
        )}
      </td>
      {/* Title */}
      <td className="px-3 py-3">
        <p className="text-xs text-slate-200 line-clamp-1">{defect.title}</p>
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
          <span className="text-[10px] text-slate-400">{defect.status.replace(/_/g, " ")}</span>
        </span>
      </td>
      {/* Severity */}
      <td className="hidden w-20 px-3 py-3 md:table-cell">
        <span className="text-[10px] text-slate-400">{defect.severity}</span>
      </td>
      {/* Priority */}
      <td className="hidden w-14 px-3 py-3 md:table-cell">
        <span className="font-mono text-[10px] text-slate-500">{defect.priority}</span>
      </td>
      {/* Retest */}
      <td className="hidden w-28 px-3 py-3 lg:table-cell">
        <span className="text-[10px] text-slate-500">{defect.retest_status.replace(/_/g, " ")}</span>
      </td>
      {/* Age */}
      <td className="hidden w-16 px-3 py-3 xl:table-cell">
        <span className={cn("text-[10px] tabular-nums", ageCls)}>
          {days !== null ? `${days}g` : "—"}
        </span>
      </td>
      {/* Date */}
      <td className="hidden w-20 px-3 py-3 xl:table-cell">
        <span className="text-[10px] text-slate-600">
          {new Date(defect.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
        </span>
      </td>
    </tr>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ManagementDefectsPage() {
  const projectId = useRouteParam("projectId") ?? "";
  const mpid = useManagementProjectId(projectId || undefined);

  const defectsQuery = useManagementDefects(mpid || undefined);
  const rows         = defectsQuery.data ?? [];
  const loading      = defectsQuery.isLoading;

  const [search,       setSearch]       = useState("");
  const [severityF,    setSeverityF]    = useState("");
  const [statusF,      setStatusF]      = useState("");
  const [priorityF,    setPriorityF]    = useState("");
  const [editDefect,   setEditDefect]   = useState<DefectLink | null>(null);
  const [showCreate,   setShowCreate]   = useState(false);
  const [page,         setPage]         = useState(1);
  const PAGE_SIZE = 20;

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

  useEffect(() => { setPage(1); }, [search]);

  const hasFilter = !!(search || severityF || statusF || priorityF);
  const clearFilters = useCallback(() => { setSearch(""); setSeverityF(""); setStatusF(""); setPriorityF(""); setPage(1); }, []);

  const totalPages     = useMemo(() => Math.ceil(filtered.length / PAGE_SIZE), [filtered]);
  const paginatedItems = useMemo(
    () => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [filtered, page]
  );

  const SEL = "rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 text-[10px] text-slate-300 outline-none focus:border-border-strong transition-colors";

  return (
    <div className="min-h-screen bg-bg px-5 py-5">
      <div className="mx-auto max-w-7xl space-y-5">

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-white">Defect Management</h1>
            <p className="mt-0.5 text-xs text-slate-500">Test koşumlarından bağlanan defect&apos;ler ve retest durumu</p>
          </div>
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="rounded-xl bg-teal-600 px-4 py-2 text-[12px] font-semibold text-white hover:bg-teal-700 transition-colors"
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

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-surface-raised px-4 py-3">
          {/* Search */}
          <div className="flex w-48 items-center gap-1.5 rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 sm:w-64">
            <IcSearch/>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Ara…"
              className="flex-1 bg-transparent text-[10px] text-slate-300 placeholder-slate-600 outline-none min-w-0"/>
            {search && <button type="button" onClick={() => setSearch("")} className="text-slate-600 hover:text-slate-300"><IcClose/></button>}
          </div>

          <select value={severityF} onChange={e => setSeverityF(e.target.value)} className={SEL}>
            <option value="">Severity</option>
            {["blocker","critical","major","minor","trivial"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
          <select value={statusF} onChange={e => setStatusF(e.target.value)} className={SEL}>
            <option value="">Status</option>
            {["open","in_progress","resolved","closed","blocked"].map(v => <option key={v} value={v}>{v.replace("_", " ")}</option>)}
          </select>
          <select value={priorityF} onChange={e => setPriorityF(e.target.value)} className={SEL}>
            <option value="">Priority</option>
            {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>

          {hasFilter && (
            <button type="button" onClick={clearFilters}
              className="rounded-xl border border-red-500/20 px-2 py-1.5 text-[10px] text-red-400 hover:bg-red-500/10 transition-colors">
              Temizle
            </button>
          )}

          <span className="ml-auto text-[10px] text-slate-600">
            {hasFilter ? `${filtered.length} / ${rows.length}` : `${rows.length} defect`}
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
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 px-6 text-center gap-3">
              <IcBug/>
              <h3 className="text-sm font-semibold text-slate-400">
                {hasFilter ? "Defect bulunamadı" : "Henüz defect yok"}
              </h3>
              <p className="text-xs text-slate-600">
                {hasFilter ? "Filtre veya arama terimini değiştirin." : "Test koşumları sırasında defect bağlayabilirsiniz."}
              </p>
              {hasFilter && (
                <button type="button" onClick={clearFilters}
                  className="rounded-xl border border-border px-4 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                  Filtreleri Temizle
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="sticky top-0 z-10 bg-surface-raised border-b border-border">
                  <tr>
                    <th className="w-8 px-3 py-2.5"/>
                    {["Key","Başlık","Status","Severity","Priority","Retest","Yaş","Tarih"].map((h, i) => (
                      <th key={h} className={cn(
                        "px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-slate-600",
                        i >= 4 && "hidden md:table-cell",
                        i >= 6 && "hidden xl:table-cell",
                      )}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {paginatedItems.map(d => <DefectRow key={d.id} defect={d} onClick={() => setEditDefect(d)}/>)}
                </tbody>
              </table>
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t border-border px-4 pt-4 pb-3">
                  <span className="text-sm text-muted-foreground text-slate-500">
                    {filtered.length} sonuçtan {Math.min(page * PAGE_SIZE, filtered.length)} tanesi gösteriliyor
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={page === 1}
                      onClick={() => setPage(p => p - 1)}
                      className="rounded px-3 py-1 text-sm border border-border text-slate-300 disabled:opacity-50 hover:bg-surface-overlay transition-colors"
                    >
                      ← Önceki
                    </button>
                    <span className="px-3 py-1 text-sm text-slate-500">{page} / {totalPages}</span>
                    <button
                      disabled={page === totalPages}
                      onClick={() => setPage(p => p + 1)}
                      className="rounded px-3 py-1 text-sm border border-border text-slate-300 disabled:opacity-50 hover:bg-surface-overlay transition-colors"
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
          />
        )}

        {/* Create defect modal */}
        {showCreate && mpid && (
          <CreateDefectModal
            mpid={mpid}
            onClose={() => setShowCreate(false)}
            onDone={() => { setShowCreate(false); defectsQuery.refetch(); }}
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
                <span className="text-[10px] text-slate-500">{s.label}</span>
              </span>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
