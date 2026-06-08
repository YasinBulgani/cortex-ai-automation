"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import Link from "next/link";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";
import { RoleGuard } from "../_components/RoleGuard";
import {
  useManagementDefects,
  useUpdateManagementDefect,
  useCreateManagementDefect,
  useDeleteManagementDefect,
  useAnalyzeDefectRootCause,
  useCreateManagementRun,
  useManagementCycles,
  type DefectLink,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useToast } from "@/lib/useToast";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";
import { useProfile } from "@/lib/hooks/use-profile";

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

interface Member { user_id: string; email: string; full_name?: string; }

interface DefectEditModalProps {
  defect: DefectLink;
  mpid: string;
  onClose: () => void;
  onDeleted: (id: string) => void;
  onAnalysisResult?: (defectId: string, result: string) => void;
  members?: Member[];
  userIdMap?: Record<string, string>;
}

interface DefectRowProps {
  defect: DefectLink;
  mpid: string;
  onClick: () => void;
  onDeleted: (id: string) => void;
  analysisResult?: string;
  userIdMap?: Record<string, string>;
}

interface CreateDefectModalProps {
  mpid: string;
  onClose: () => void;
  onDone: () => void;
  existingTitles?: string[];
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
        <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-muted">Açık Defekt Trendi</p>
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

// ─── Defect Analytics Panel ───────────────────────────────────────────────────

function DefectAnalyticsPanel({ defects, loading }: { defects: DefectLink[]; loading: boolean }) {
  const open   = defects.filter(d => !isClosed(d));
  const closed = defects.filter(d => isClosed(d));

  // MTTR: average days from created_at to closed (for closed defects)
  const mttrDays = useMemo(() => {
    const closedWithDates = closed.filter(d => d.created_at && d.updated_at);
    if (!closedWithDates.length) return null;
    const totalMs = closedWithDates.reduce((sum, d) => {
      const diff = new Date(d.updated_at ?? d.created_at).getTime() - new Date(d.created_at).getTime();
      return sum + Math.max(0, diff);
    }, 0);
    return Math.round(totalMs / closedWithDates.length / 86_400_000);
  }, [closed]);

  // Oldest open defect age
  const oldestOpenDays = useMemo(() => {
    if (!open.length) return null;
    const oldest = open.reduce((min, d) =>
      new Date(d.created_at).getTime() < new Date(min.created_at).getTime() ? d : min, open[0]);
    return daysSince(oldest.created_at);
  }, [open]);

  // Severity breakdown
  const severityMap = useMemo(() => {
    const m: Record<string, number> = {};
    for (const d of defects) {
      const s = (d.severity ?? "").toLowerCase() || "unknown";
      m[s] = (m[s] ?? 0) + 1;
    }
    return m;
  }, [defects]);

  const sevOrder = ["blocker", "critical", "major", "minor", "trivial"];
  const sevColors: Record<string, string> = {
    blocker: "bg-red-600",
    critical: "bg-red-400",
    major: "bg-orange-400",
    minor: "bg-amber-400",
    trivial: "bg-slate-500",
  };

  const totalForSev = Object.values(severityMap).reduce((a, b) => a + b, 0) || 1;

  // CSV export
  function exportDefectsCSV() {
    const headers = ["ID", "Başlık", "Önem", "Öncelik", "Durum", "Oluşturulma", "Yaş (gün)"];
    const rows = defects.map(d => [
      d.external_key ?? d.id,
      d.title,
      d.severity,
      d.priority,
      d.status,
      d.created_at ? new Date(d.created_at).toLocaleDateString("tr-TR") : "",
      daysSince(d.created_at) ?? "",
    ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(";"));
    const csv = "﻿" + [headers.join(";"), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "defektler.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return <div className="h-24 rounded-xl border border-border bg-surface-raised animate-pulse" />;
  }

  if (!defects.length) return null;

  return (
    <div className="rounded-xl border border-border bg-surface-raised overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <p className="text-[11px] font-semibold text-fg">Defekt Analizi</p>
        <button
          type="button"
          onClick={exportDefectsCSV}
          className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1 text-[10px] font-medium text-fg-muted hover:text-fg hover:border-border-strong transition-colors"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          CSV İndir
        </button>
      </div>

      <div className="grid grid-cols-2 gap-0 divide-x divide-border sm:grid-cols-4">
        {/* MTTR */}
        <div className="px-4 py-3">
          <p className="text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">MTTR</p>
          <p className="mt-1 text-xl font-bold tabular-nums text-fg">
            {mttrDays !== null ? `${mttrDays}g` : "—"}
          </p>
          <p className="text-[10px] text-fg-muted">Ort. kapatma süresi</p>
        </div>

        {/* Oldest open */}
        <div className="px-4 py-3">
          <p className="text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">En Yaşlı Açık</p>
          <p className={cn(
            "mt-1 text-xl font-bold tabular-nums",
            oldestOpenDays !== null && oldestOpenDays > 30 ? "text-red-400" :
            oldestOpenDays !== null && oldestOpenDays > 14 ? "text-amber-400" : "text-fg",
          )}>
            {oldestOpenDays !== null ? `${oldestOpenDays}g` : "—"}
          </p>
          <p className="text-[10px] text-fg-muted">Açık kalan en eski</p>
        </div>

        {/* Resolution rate */}
        <div className="px-4 py-3">
          <p className="text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">Kapatma Oranı</p>
          <p className={cn(
            "mt-1 text-xl font-bold tabular-nums",
            defects.length > 0 && (closed.length / defects.length) >= 0.7 ? "text-emerald-400" : "text-fg",
          )}>
            {defects.length > 0 ? `${Math.round((closed.length / defects.length) * 100)}%` : "—"}
          </p>
          <p className="text-[10px] text-fg-muted">{closed.length}/{defects.length} kapatıldı</p>
        </div>

        {/* Open count */}
        <div className="px-4 py-3">
          <p className="text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">Açık Defekt</p>
          <p className={cn(
            "mt-1 text-xl font-bold tabular-nums",
            open.length > 10 ? "text-red-400" : open.length > 5 ? "text-amber-400" : "text-fg",
          )}>
            {open.length}
          </p>
          <p className="text-[10px] text-fg-muted">Kapatılmamış</p>
        </div>
      </div>

      {/* Severity breakdown bar */}
      {totalForSev > 0 && (
        <div className="border-t border-border px-4 py-3">
          <p className="mb-2 text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">Önem Dağılımı</p>
          <div className="flex h-2 w-full overflow-hidden rounded-full">
            {sevOrder
              .filter(s => (severityMap[s] ?? 0) > 0)
              .map(s => (
                <div
                  key={s}
                  className={cn("h-full transition-all", sevColors[s] ?? "bg-slate-500")}
                  style={{ width: `${((severityMap[s] ?? 0) / totalForSev) * 100}%` }}
                  title={`${s}: ${severityMap[s]}`}
                />
              ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-3">
            {sevOrder
              .filter(s => (severityMap[s] ?? 0) > 0)
              .map(s => (
                <div key={s} className="flex items-center gap-1.5">
                  <span className={cn("h-2 w-2 rounded-full", sevColors[s] ?? "bg-slate-500")} />
                  <span className="text-[10px] text-fg-muted capitalize">{s}: {severityMap[s]}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Risk Matrix: Severity × Priority */}
      {open.length > 0 && (
        <div className="border-t border-border px-4 py-3">
          <p className="mb-3 text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">Risk Matrisi (Açık Defektler)</p>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[10px]">
              <thead>
                <tr>
                  <th className="pb-1 pr-2 text-left text-fg-disabled font-normal">Sev \ Önc</th>
                  {["P0","P1","P2","P3"].map(p => (
                    <th key={p} className="pb-1 px-1 text-center font-semibold text-fg-muted">{p}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {["blocker","critical","major","minor","trivial"].map(sev => (
                  <tr key={sev}>
                    <td className="py-0.5 pr-2 capitalize text-fg-muted">{sev}</td>
                    {["P0","P1","P2","P3"].map(pri => {
                      const count = open.filter(d =>
                        (d.severity ?? "").toLowerCase() === sev &&
                        (d.priority ?? "") === pri
                      ).length;
                      const risk = (sev === "blocker" || sev === "critical") && (pri === "P0" || pri === "P1") ? "high" :
                                   (sev === "major" && pri === "P0") || ((sev === "blocker" || sev === "critical") && pri === "P2") ? "medium" : "low";
                      return (
                        <td key={pri} className="px-1 py-0.5 text-center">
                          {count > 0 ? (
                            <span className={cn(
                              "inline-flex h-6 w-6 items-center justify-center rounded font-bold tabular-nums",
                              risk === "high"   ? "bg-red-500/20 text-red-400" :
                              risk === "medium" ? "bg-amber-500/20 text-amber-400" :
                              "bg-slate-500/20 text-fg-muted"
                            )}>
                              {count}
                            </span>
                          ) : (
                            <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-surface-overlay text-fg-disabled">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 flex gap-4 text-[10px] text-fg-disabled">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-red-500/50"/> Yüksek Risk</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-amber-500/50"/> Orta Risk</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-slate-500/50"/> Düşük Risk</span>
          </div>
        </div>
      )}
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
            <h3 className="text-[14px] font-semibold text-fg">Defekt Silinecek</h3>
          </div>
          <p className="text-[12px] text-fg-muted leading-relaxed">
            Bu defekt kalıcı olarak silinecek. Onaylıyor musunuz?
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isPending}
            className="text-[12px] text-fg-muted hover:text-fg"
          >
            İptal
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={onConfirm}
            disabled={isPending}
            className="text-[12px]"
          >
            {isPending ? "Siliniyor…" : "Evet, Sil"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Create Defect Modal ──────────────────────────────────────────────────────

function CreateDefectModal({ mpid, onClose, onDone, existingTitles = [] }: CreateDefectModalProps) {
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
  const [submitErr,   setSubmitErr]   = useState<string | null>(null);

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/40 transition-colors";
  const sel = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg outline-none focus:border-teal-500/40 transition-colors";

  const potentialDuplicates = useMemo(() => {
    if (!title.trim() || title.trim().length < 5) return [];
    const q = title.trim().toLowerCase();
    return existingTitles.filter(t => t.toLowerCase().includes(q) || q.includes(t.toLowerCase()));
  }, [title, existingTitles]);

  const handleSubmit = async () => {
    if (!title.trim()) return;
    setSubmitErr(null);
    const payload: Parameters<typeof create.mutateAsync>[0] = {
      title: title.trim(),
      external_key: externalKey.trim() || "",
      url: url.trim() || null,
      severity,
      priority,
      status,
      root_cause: description.trim() || null,
    };
    try {
      await create.mutateAsync(payload);
      onDone();
    } catch {
      setSubmitErr("Defekt oluşturulamadı. Lütfen tekrar deneyin.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-border bg-surface-raised shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-[14px] font-semibold text-fg">Yeni Defekt Oluştur</h2>
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
              placeholder="Defekt başlığı…"
              className={inp}
            />
            {potentialDuplicates.length > 0 && (
              <div className="mt-1.5 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
                <p className="text-[10px] font-semibold text-amber-400 mb-1">⚠ Olası Tekrar Defektler</p>
                <ul className="space-y-0.5">
                  {potentialDuplicates.slice(0, 3).map((t, i) => (
                    <li key={i} className="text-[11px] text-fg-muted truncate">• {t}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* External Key & URL */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="create-defect-key" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Harici Anahtar</label>
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
              <label htmlFor="create-defect-priority" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Öncelik</label>
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
              placeholder="Defekt açıklaması…"
              className={cn(inp, "resize-none")}
            />
          </div>
        </div>

        {/* Footer */}
        {submitErr && (
          <div className="border-t border-danger/30 bg-danger-subtle px-5 py-2.5 text-[12px] text-danger">
            {submitErr}
          </div>
        )}
        <div className="flex items-center justify-between border-t border-border px-5 py-4">
          <Button type="button" variant="outline" onClick={onClose}
            className="text-[13px] text-fg-muted hover:text-fg">
            İptal
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={handleSubmit}
            disabled={create.isPending || !title.trim()}
            className="px-5 text-[13px]"
          >
            {create.isPending ? "Oluşturuluyor…" : "Oluştur"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Defect Edit Modal ────────────────────────────────────────────────────────

function DefectEditModal({ defect, mpid, onClose, onDeleted, onAnalysisResult, members = [], userIdMap = {} }: DefectEditModalProps) {
  const update     = useUpdateManagementDefect(mpid);
  const del        = useDeleteManagementDefect(mpid);
  const analyze    = useAnalyzeDefectRootCause(mpid);
  const createRun   = useCreateManagementRun(mpid);
  const cyclesQuery = useManagementCycles(mpid || undefined);
  const toastCtx   = useToast();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const [status,        setStatus]       = useState(defect.status);
  const [severity,      setSeverity]     = useState(defect.severity);
  const [priority,      setPriority]     = useState(defect.priority);
  const [retestStatus,  setRetestStatus] = useState(defect.retest_status);
  const [assigneeId,    setAssigneeId]   = useState(defect.assignee_id ?? "");
  const [rootCause,     setRootCause]    = useState(defect.root_cause ?? "");
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [retestRunCreated, setRetestRunCreated] = useState(false);
  const [retestRunPending, setRetestRunPending] = useState(false);

  const RETEST_STATUSES = new Set(["resolved", "fixed"]);
  const showRetestBanner = RETEST_STATUSES.has(status.toLowerCase()) && !retestRunCreated;

  const cycles   = cyclesQuery.data ?? [];
  const firstCycleId = cycles[0]?.id ?? "";

  const handleCreateRetestRun = async () => {
    if (!firstCycleId) {
      toastCtx.error("Retest run için önce bir test döngüsü (cycle) oluşturun.");
      return;
    }
    setRetestRunPending(true);
    try {
      await createRun.mutateAsync({
        cycle_id: firstCycleId,
        name: `Retest: ${defect.title.slice(0, 80)}`,
        case_ids: [],
        source_type: "defect_retest",
        source_ref: defect.id,
      });
      setRetestStatus("pending");
      setRetestRunCreated(true);
      toastCtx.success("Retest koşumu oluşturuldu. Runs sekmesinden takip edebilirsiniz.");
    } catch {
      toastCtx.error("Retest run oluşturulamadı.");
    } finally {
      setRetestRunPending(false);
    }
  };

  const save = async () => {
    await update.mutateAsync({
      defectId: defect.id,
      status,
      severity,
      priority,
      retest_status: retestStatus,
      assignee_id: assigneeId.trim() || null,
      root_cause: rootCause.trim() || null,
    });
    onClose();
  };

  const handleDelete = async () => {
    try {
      await del.mutateAsync(defect.id);
      setShowConfirmDelete(false);
      onDeleted(defect.id);
    } catch {
      toastCtx.error("Defect silinirken bir hata oluştu.");
    }
  };

  const inp = "w-full rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[13px] text-fg placeholder:text-fg-disabled outline-none focus:border-teal-500/40 transition-colors";
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
                disabled={del.isPending}
                aria-label="Defect'i sil"
                title="Defect'i sil"
                className="rounded-lg p-1.5 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 disabled:opacity-40 transition-colors"
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
            {defect.url && /^https?:\/\//i.test(defect.url) && (
              <a href={defect.url} target="_blank" rel="noreferrer noopener"
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
                <label htmlFor="edit-defect-status" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Status</label>
                <select id="edit-defect-status" value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                  {ALL_STATUSES.map(v => (
                    <option key={v} value={v}>{v.replace(/_/g," ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="edit-defect-retest" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Retest</label>
                <select id="edit-defect-retest" value={retestStatus} onChange={e => setRetestStatus(e.target.value)} className={sel}>
                  {["pending","passed","failed","not_required","retest_failed"].map(v => (
                    <option key={v} value={v}>{v.replace(/_/g," ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="edit-defect-severity" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Severity</label>
                <select id="edit-defect-severity" value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                  {["blocker","critical","major","minor","trivial"].map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="edit-defect-priority" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Öncelik</label>
                <select id="edit-defect-priority" value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                  {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="edit-defect-assignee" className="mb-1 block text-[10px] uppercase tracking-widest text-fg-subtle">Atanan Kişi</label>
              {members.length > 0 ? (
                <select
                  id="edit-defect-assignee"
                  value={assigneeId}
                  onChange={e => setAssigneeId(e.target.value)}
                  className={sel}
                >
                  <option value="">— Atanmamış —</option>
                  {members.map(m => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.full_name?.trim() || m.email}
                    </option>
                  ))}
                </select>
              ) : (
                <input id="edit-defect-assignee" value={assigneeId} onChange={e => setAssigneeId(e.target.value)}
                  placeholder="kullanici@sirket.com veya kullanıcı adı"
                  className={inp} />
              )}
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between">
                <label htmlFor="edit-defect-root-cause" className="text-[10px] uppercase tracking-widest text-fg-subtle">Kök Neden</label>
                <button type="button"
                  disabled={analyze.isPending}
                  onClick={async () => {
                    try {
                      const res = await analyze.mutateAsync({ defect_title: defect.title, defect_status: status });
                      if (!rootCause) setRootCause(res.root_cause);
                      setAiSuggestions(res.suggestions);
                      const analysisText = res.root_cause || (res as unknown as Record<string, string>).analysis;
                      if (analysisText && onAnalysisResult) {
                        onAnalysisResult(defect.id, analysisText);
                      }
                    } catch {
                      toastCtx.error("AI analiz sırasında bir hata oluştu.");
                    }
                  }}
                  className="flex items-center gap-1 text-[10px] text-teal-400 hover:text-teal-300 disabled:opacity-40 transition-colors">
                  {analyze.isPending ? "Analiz ediliyor…" : "✦ AI Analiz"}
                </button>
              </div>
              <textarea id="edit-defect-root-cause" value={rootCause} onChange={e => setRootCause(e.target.value)}
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

          {/* Retest banner */}
          {showRetestBanner && (
            <div className="mx-5 mb-2 flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/8 px-4 py-3">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-emerald-400">Retest Önerilir</p>
                <p className="text-[11px] text-fg-muted">
                  Defekt çözüldü olarak işaretlendi. Doğrulamak için bir retest koşumu oluşturun.
                </p>
              </div>
              <button
                type="button"
                onClick={() => { void handleCreateRetestRun(); }}
                disabled={retestRunPending || !firstCycleId}
                title={!firstCycleId ? "Önce bir test döngüsü oluşturun" : "Retest run başlat"}
                className="ml-4 shrink-0 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-[11px] font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-40 transition-colors"
              >
                {retestRunPending ? "Oluşturuluyor…" : "Retest Run Oluştur"}
              </button>
            </div>
          )}
          {retestRunCreated && (
            <div className="mx-5 mb-2 rounded-xl border border-teal-500/30 bg-teal-500/8 px-4 py-2.5">
              <p className="text-[11px] text-teal-400">
                ✓ Retest koşumu oluşturuldu. <span className="text-fg-muted">Runs sekmesinden takip edin.</span>
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-border px-5 py-4">
            <Button type="button" variant="outline" onClick={onClose}
              className="text-[13px] text-fg-muted hover:text-fg">
              İptal
            </Button>
            <Button type="button" variant="primary" onClick={save} disabled={update.isPending}
              className="px-5 text-[13px]">
              {update.isPending ? "Kaydediliyor…" : "Kaydet"}
            </Button>
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

const SLA_DAYS: Record<string, number> = {
  blocker: 2, critical: 2, major: 5, minor: 14, trivial: 30,
};

function DefectRow({ defect, mpid, onClick, onDeleted, analysisResult, userIdMap = {} }: DefectRowProps) {
  const del = useDeleteManagementDefect(mpid);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  const closed  = isClosed(defect);
  const blocker = isBlocker(defect);
  const days    = daysSince(defect.created_at);
  const sevDot  = SEVERITY_DOT[defect.severity.toLowerCase()] ?? "bg-slate-600";
  const sttDot  = statusDot(defect.status);

  const sev      = defect.severity.toLowerCase();
  const slaDays  = SLA_DAYS[sev] ?? 14;
  const slaBreached = !closed && days !== null && days > slaDays;
  const slaWarning  = !closed && !slaBreached && days !== null && days > Math.floor(slaDays * 0.6);

  const ageCls = closed        ? "text-fg-subtle"
    : slaBreached              ? "text-red-400 font-semibold"
    : slaWarning               ? "text-amber-400"
    :                            "text-fg-muted";

  const handleDeleteConfirm = async () => {
    try {
      await del.mutateAsync(defect.id);
      setShowConfirmDelete(false);
      onDeleted(defect.id);
    } catch {
      setShowConfirmDelete(false);
    }
  };

  return (
    <>
      <tr onClick={onClick}
        className={cn("cursor-pointer border-b border-border hover:bg-surface-overlay transition-colors", blocker && "bg-red-500/3", analysisResult && "border-b-0")}>
        {/* Severity dot */}
        <td className="w-8 px-3 py-3">
          <span className={cn("h-1.5 w-1.5 rounded-full inline-block", sevDot)}/>
        </td>
        {/* Key */}
        <td className="w-28 px-3 py-3">
          {defect.url && /^https?:\/\//i.test(defect.url) ? (
            <a href={defect.url} target="_blank" rel="noreferrer noopener"
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
          {slaBreached && !blocker && (
            <span className="mt-0.5 inline-flex items-center gap-1">
              <span className="text-[9px] text-red-400 font-medium">⏱ SLA aşıldı ({days}g)</span>
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
        {/* Assignee */}
        <td className="hidden w-28 px-3 py-3 lg:table-cell">
          {defect.assignee_id ? (
            <span className="text-[10px] text-fg-muted truncate max-w-[7rem] block" title={userIdMap[defect.assignee_id] ?? defect.assignee_id}>
              {userIdMap[defect.assignee_id] ?? `…${defect.assignee_id.slice(-8)}`}
            </span>
          ) : (
            <span className="text-[10px] text-fg-disabled">—</span>
          )}
        </td>
        {/* Retest */}
        <td className="hidden w-28 px-3 py-3 md:table-cell">
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
            disabled={del.isPending}
            onClick={e => { e.stopPropagation(); setShowConfirmDelete(true); }}
            className="rounded-lg p-1 text-fg-subtle hover:bg-red-500/10 hover:text-red-400 disabled:opacity-40 transition-colors"
          >
            <IcTrash/>
          </button>
        </td>
      </tr>
      {analysisResult && (
        <tr className="border-b border-border">
          <td colSpan={10} className="px-3 pb-3 pt-0">
            <div className="rounded-lg bg-surface-overlay border border-border p-3 text-xs text-fg-subtle">
              <span className="text-brand font-medium">✦ AI Analiz: </span>
              {analysisResult}
            </div>
          </td>
        </tr>
      )}
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
  const toastCtx = useToast();

  const defectsQuery = useManagementDefects(mpid || undefined);
  const rows = defectsQuery.data ?? [];
  const loading = defectsQuery.isLoading;
  const profile = useProfile();

  const { data: membersData } = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () =>
      apiFetch<Member[]>(`/api/v1/organizations/projects/${projectId}/members`)
        .then(d => (Array.isArray(d) ? d : [])),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
  const members: Member[] = membersData ?? [];
  const userIdMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const m of members) {
      map[m.user_id] = m.full_name?.trim() || m.email;
    }
    return map;
  }, [members]);

  const searchParams = useSearchParams();
  const router       = useRouter();
  const pathname     = usePathname();

  const [search,       setSearch]       = useState(searchParams.get("q") ?? "");
  const [severityF,    setSeverityF]    = useState(searchParams.get("severity") ?? "");
  const [statusF,      setStatusF]      = useState(searchParams.get("status") ?? "");
  const [priorityF,    setPriorityF]    = useState(searchParams.get("priority") ?? "");
  const [assigneeF,    setAssigneeF]    = useState(searchParams.get("assignee") ?? "");
  const [myDefects,    setMyDefects]    = useState(false);
  const [editDefect,      setEditDefect]      = useState<DefectLink | null>(null);
  const [showCreate,      setShowCreate]      = useState(false);
  const [analysisResults, setAnalysisResults] = useState<Record<string, string>>({});
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
  const handleAssigneeChange = (v: string) => { setAssigneeF(v); updateUrl({ assignee: v }); };

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
    if (assigneeF) {
      const isExactId = members.some(m => m.user_id === assigneeF);
      if (isExactId) {
        r = r.filter(d => d.assignee_id === assigneeF);
      } else {
        const af = assigneeF.toLowerCase();
        r = r.filter(d => {
          const rawId = d.assignee_id ?? "";
          const displayName = rawId ? (userIdMap[rawId] ?? rawId) : "";
          return displayName.toLowerCase().includes(af) || rawId.toLowerCase().includes(af);
        });
      }
    }
    if (myDefects && profile.data) {
      const myId = String(profile.data.id);
      r = r.filter(d => (d.assignee_id ?? "") === myId);
    }
    return r;
  }, [rows, search, severityF, statusF, priorityF, assigneeF, myDefects, profile.data, userIdMap, members]);

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
  useEffect(() => { setPage(1); }, [search, severityF, statusF, priorityF, assigneeF, myDefects]);

  const hasFilter = !!(search || severityF || statusF || priorityF || assigneeF || myDefects);
  const clearFilters = useCallback(() => {
    setSearch(""); setSeverityF(""); setStatusF(""); setPriorityF(""); setAssigneeF(""); setMyDefects(false); setPage(1);
    const sp = new URLSearchParams(searchParams.toString());
    sp.delete("q"); sp.delete("severity"); sp.delete("status"); sp.delete("priority"); sp.delete("assignee");
    router.replace(pathname + (sp.toString() ? "?" + sp.toString() : ""), { scroll: false });
  }, [searchParams, router, pathname]);

  const totalPages     = useMemo(() => Math.ceil(sorted.length / PAGE_SIZE), [sorted]);
  const paginatedItems = useMemo(
    () => sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [sorted, page]
  );

  const SEL = "rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 text-[10px] text-fg outline-none focus:border-border-strong transition-colors";

  return (
    <PageErrorBoundary>
    <div className="min-h-screen bg-surface-base px-5 py-5">
      <div className="mx-auto max-w-7xl space-y-5">

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold text-fg">Defekt Yönetimi</h1>
            <p className="mt-0.5 text-xs text-fg-muted">Test koşumlarından bağlanan defektler ve retest durumu</p>
          </div>
          <RoleGuard minRole="member" projectId={projectId || undefined}>
            <Button
              type="button"
              variant="primary"
              onClick={() => setShowCreate(true)}
              aria-label="Yeni defekt oluştur"
              className="text-[12px]"
            >
              + Yeni Defekt
            </Button>
          </RoleGuard>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Toplam Defekt"   value={loading ? "—" : rows.length}     hint="bağlı defekt"      loading={loading}/>
          <StatCard label="Açık"           value={loading ? "—" : open.length}     hint="kapatılmamış"     loading={loading}/>
          <StatCard label="Engelleyici"    value={loading ? "—" : critical.length} hint="sürümü engelleyen" loading={loading}/>
          <StatCard label="Yeniden Açılan" value={loading ? "—" : reopened.length} hint="tekrar açıldı"    loading={loading}/>
        </div>

        {/* SLA breach banner — critical/blocker open > 7 days */}
        {!loading && (() => {
          const breached = rows.filter(d => {
            if (isClosed(d)) return false;
            const isPriority = ["P0","P1"].includes(d.priority) || ["blocker","critical"].includes(d.severity.toLowerCase());
            const age = daysSince(d.created_at);
            return isPriority && age !== null && age >= 7;
          });
          if (!breached.length) return null;
          return (
            <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/8 px-4 py-3">
              <svg className="mt-0.5 h-4 w-4 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
              </svg>
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-red-300">
                  SLA Aşımı — {breached.length} kritik defect 7+ gün açık
                </p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {breached.slice(0, 5).map(d => {
                    const age = daysSince(d.created_at);
                    return (
                      <button
                        key={d.id}
                        type="button"
                        onClick={() => setEditDefect(d)}
                        className="flex items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/10 px-2 py-1 text-[10px] text-red-400 hover:bg-red-500/20 transition-colors"
                      >
                        <span className="font-mono">{d.external_key}</span>
                        <span className="text-red-300/70">{age}g</span>
                      </button>
                    );
                  })}
                  {breached.length > 5 && (
                    <span className="self-center text-[10px] text-red-400/70">+{breached.length - 5} daha</span>
                  )}
                </div>
              </div>
            </div>
          );
        })()}

        {/* Bug fix 3: Açık defect trendi sparkline */}
        {!loading && rows.length > 0 && <OpenDefectSparkline defects={rows}/>}

        {/* Analytics panel: MTTR, oldest open, severity breakdown, CSV export */}
        <DefectAnalyticsPanel defects={rows} loading={loading} />

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 rounded-xl border border-border bg-surface-raised px-4 py-3">
          {/* Search */}
          <div className="flex w-full sm:w-48 items-center gap-1.5 rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 sm:w-64">
            <IcSearch/>
            <input type="text" value={search} onChange={e => handleSearchChange(e.target.value)} placeholder="Ara…"
              aria-label="Defect ara"
              className="flex-1 bg-transparent text-[10px] text-fg placeholder:text-fg-disabled outline-none min-w-0"/>
            {search && <button type="button" onClick={() => handleSearchChange("")} aria-label="Aramayı temizle" className="text-fg-subtle hover:text-fg"><IcClose/></button>}
          </div>

          <label htmlFor="defect-severity-filter" className="sr-only">Önem derecesi filtresi</label>
          <select id="defect-severity-filter" value={severityF} onChange={e => handleSeverityChange(e.target.value)} className={SEL}>
            <option value="">Önem Derecesi</option>
            {["blocker","critical","major","minor","trivial"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
          <label htmlFor="defect-status-filter" className="sr-only">Durum filtresi</label>
          <select id="defect-status-filter" value={statusF} onChange={e => handleStatusChange(e.target.value)} className={SEL}>
            <option value="">Durum</option>
            {ALL_STATUSES.map(v => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
          </select>
          <label htmlFor="defect-priority-filter" className="sr-only">Öncelik filtresi</label>
          <select id="defect-priority-filter" value={priorityF} onChange={e => handlePriorityChange(e.target.value)} className={SEL}>
            <option value="">Öncelik</option>
            {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>

          {/* Assigned to filter */}
          <label htmlFor="defect-assignee-filter" className="sr-only">Atanan kişi filtresi</label>
          {members.length > 0 ? (
            <select
              id="defect-assignee-filter"
              value={assigneeF}
              onChange={e => handleAssigneeChange(e.target.value)}
              className="rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 text-[10px] text-fg outline-none focus:border-border-strong transition-colors"
            >
              <option value="">Tüm atamalar</option>
              {members.map(m => (
                <option key={m.user_id} value={m.user_id}>
                  {m.full_name?.trim() || m.email}
                </option>
              ))}
            </select>
          ) : (
            <input
              id="defect-assignee-filter"
              type="text"
              value={assigneeF}
              onChange={e => handleAssigneeChange(e.target.value)}
              placeholder="Atanan kişi…"
              className="rounded-xl border border-border bg-surface-overlay px-2.5 py-1.5 text-[10px] text-fg placeholder:text-fg-disabled outline-none focus:border-border-strong transition-colors"
            />
          )}

          {/* My defects quick toggle */}
          <button
            type="button"
            onClick={() => setMyDefects(v => !v)}
            className={cn(
              "rounded-xl border px-2.5 py-1.5 text-[10px] font-medium transition-colors",
              myDefects
                ? "border-brand/40 bg-brand/10 text-brand"
                : "border-border text-fg-muted hover:text-fg",
            )}
          >
            Benim Defect&apos;lerim
          </button>

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
                {hasFilter ? "Defekt bulunamadı" : "Henüz defekt yok"}
              </h3>
              <p className="text-xs text-fg-subtle">
                {hasFilter ? "Filtre veya arama terimini değiştirin." : (
                  <>
                    Test koşumları sırasında defekt bağlayabilirsiniz.
                    <Link href={`/p/${projectId}/management/runs`} className="ml-1 text-brand underline text-[12px]">
                      Koşum başlat →
                    </Link>
                  </>
                )}
              </p>
              {hasFilter && (
                <Button type="button" variant="outline" onClick={clearFilters}
                  className="text-xs text-fg-muted hover:text-fg">
                  Filtreleri Temizle
                </Button>
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
                    <SortTh col="severity" label="Önem" className="hidden md:table-cell"/>
                    <SortTh col="priority" label="Öncelik" className="hidden md:table-cell"/>
                    <th scope="col" className="hidden px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle lg:table-cell">Atanan</th>
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
                      onDeleted={(_id: string) => {
                        toastCtx.success("Defect silindi");
                        void defectsQuery.refetch();
                      }}
                      analysisResult={analysisResults[d.id]}
                      userIdMap={userIdMap}
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
            onDeleted={(_id: string) => {
              setEditDefect(null);
              toastCtx.success("Defect silindi");
              void defectsQuery.refetch();
            }}
            onAnalysisResult={(defectId, result) => {
              setAnalysisResults(prev => ({ ...prev, [defectId]: result }));
            }}
            members={members}
            userIdMap={userIdMap}
          />
        )}

        {/* Create defect modal */}
        {showCreate && mpid && (
          <CreateDefectModal
            mpid={mpid}
            existingTitles={rows.map(d => d.title)}
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
    </PageErrorBoundary>
  );
}
