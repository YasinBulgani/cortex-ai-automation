"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";
import {
  useManagementCase,
  useManagementCaseVersions,
  useUpdateManagementCase,
  useArchiveManagementCase,
  useDeleteManagementCase,
  useCloneManagementCase,
  useImproveManagementCase,
  useSubmitCaseForReview,
  useApproveCaseReview,
  useRejectCaseReview,
  useCaseAttachments,
  useUploadCaseAttachment,
  useCaseDefects,
  type ImproveTestCaseResponse,
  type CaseAttachment,
} from "@/lib/hooks/use-management";

interface Member { user_id: string; email: string; full_name?: string; }
import { P_BADGE, SB_BADGE, STATUS_LABEL_TR } from "./shared";
import { CommentThread } from "../CommentThread";
import { ParameterizedCasesPanel } from "../ParameterizedCasesPanel";
import { useProfile } from "@/lib/hooks/use-profile";

type Tab = "detail" | "runs" | "defects" | "files" | "comments" | "history" | "parametric";

const SEVERITY_BADGE: Record<string, string> = {
  blocker:  "border-red-500/30 bg-red-500/10 text-red-400",
  critical: "border-orange-500/30 bg-orange-500/10 text-orange-400",
  major:    "border-amber-500/30 bg-amber-500/10 text-amber-400",
  minor:    "border-blue-500/30 bg-blue-500/10 text-blue-400",
  trivial:  "border-border-strong/20 bg-slate-500/5 text-fg-muted",
};

const DEFECT_STATUS_BADGE: Record<string, string> = {
  open:        "border-red-500/30 bg-red-500/10 text-red-400",
  in_progress: "border-amber-500/30 bg-amber-500/10 text-amber-400",
  resolved:    "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  closed:      "border-border-strong/20 bg-slate-500/5 text-fg-muted",
  reopened:    "border-orange-500/30 bg-orange-500/10 text-orange-400",
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CaseDetailDrawer({ caseId, pid, projectId, onClose }: {
  caseId: string; pid: string; projectId: string; onClose: () => void;
}) {
  const { data: tc, isLoading } = useManagementCase(pid || undefined, caseId || undefined);
  const { data: versions, isLoading: versionsLoading } = useManagementCaseVersions(pid || undefined, caseId || undefined);
  const { data: attachments, isLoading: attachLoading } = useCaseAttachments(pid || undefined, caseId || undefined);
  const { data: defects, isLoading: defectsLoading } = useCaseDefects(pid || undefined, caseId || undefined);
  const uploadAttachment = useUploadCaseAttachment(pid, caseId);

  const update       = useUpdateManagementCase(pid);
  const archive      = useArchiveManagementCase(pid);
  const del          = useDeleteManagementCase(pid);
  const clone        = useCloneManagementCase(pid);
  const improve      = useImproveManagementCase(pid);
  const submitReview = useSubmitCaseForReview(pid);
  const approveRev   = useApproveCaseReview(pid);
  const rejectRev    = useRejectCaseReview(pid);

  const [cloneSuccess,      setCloneSuccess]      = useState<string | null>(null);
  const [improveResult,     setImproveResult]     = useState<ImproveTestCaseResponse | null>(null);
  const [showImprove,       setShowImprove]       = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [reviewComment,     setReviewComment]     = useState("");
  const [showReviewPanel,   setShowReviewPanel]   = useState(false);
  const [uploadError,       setUploadError]       = useState<string | null>(null);
  const [showQuickStep,     setShowQuickStep]     = useState(false);
  const [quickStepAction,   setQuickStepAction]   = useState("");
  const [quickStepExpected, setQuickStepExpected] = useState("");
  const [quickStepSaving,   setQuickStepSaving]   = useState(false);
  const [quickStepErr,      setQuickStepErr]      = useState<string | null>(null);
  const [deleteErr,         setDeleteErr]         = useState<string | null>(null);

  const [tab, setTab] = useState<Tab>("detail");
  const [editing,      setEditing]      = useState(false);
  const [title,        setTitle]        = useState("");
  const [priority,     setPriority]     = useState("P2");
  const [status,       setStatus]       = useState("draft");
  const [type,         setType]         = useState("manual");
  const [severity,     setSeverity]     = useState("minor");
  const [objective,    setObjective]    = useState("");
  const [preconditions,setPreconditions]= useState("");
  const [tagsText,     setTagsText]     = useState("");
  const [ownerId,      setOwnerId]      = useState("");

  const { data: membersData } = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () => apiFetch<Member[]>(`/api/v1/organizations/projects/${projectId}/members`).then(d => Array.isArray(d) ? d : []),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
  const members: Member[] = membersData ?? [];
  const userIdMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const m of members) map[m.user_id] = m.full_name?.trim() || m.email;
    return map;
  }, [members]);

  const profile = useProfile();
  const currentUserId = profile.data ? String(profile.data.id) : null;

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!showDeleteConfirm) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !del.isPending) setShowDeleteConfirm(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [showDeleteConfirm, del.isPending]);

  useEffect(() => {
    if (!tc) return;
    setTitle(tc.title ?? "");
    setPriority(tc.priority ?? "P2");
    setStatus(tc.status ?? "draft");
    setType(tc.type ?? "manual");
    setSeverity(tc.severity ?? "minor");
    setObjective(tc.objective ?? "");
    setPreconditions(tc.preconditions ?? "");
    setTagsText((tc.tags ?? []).join(", "));
    setOwnerId(tc.owner_id ?? "");
    setEditing(false);
  }, [tc?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async () => {
    if (!tc) return;
    await update.mutateAsync({
      caseId: tc.id,
      title: title.trim() || tc.title,
      priority,
      status,
      type,
      severity,
      objective: objective.trim() || null,
      preconditions: preconditions.trim() || null,
      tags: tagsText.split(",").map(t => t.trim()).filter(Boolean),
      owner_id: ownerId || null,
    });
    setEditing(false);
  };

  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    try {
      await uploadAttachment.mutateAsync(file);
    } catch {
      setUploadError("Dosya yüklenemedi. Lütfen tekrar deneyin.");
    }
  };

  const inp = "w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";
  const sel = "w-full rounded-xl border border-border bg-surface-raised px-2.5 py-2 text-[13px] text-fg-muted outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";

  const tabs: { key: Tab; label: string }[] = [
    { key: "detail",   label: "Detay" },
    { key: "runs",     label: "Koşumlar" },
    { key: "defects",  label: "Defectler" },
    { key: "files",    label: "Dosyalar" },
    { key: "comments",   label: "Yorumlar" },
    { key: "parametric", label: "Parametrik" },
    { key: "history",    label: "Geçmiş" },
  ];

  return (
    <aside className="flex w-[360px] flex-none flex-col overflow-hidden border-l border-border bg-surface-raised shadow-sm">
      {/* Header */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
        {tc && <span className="font-mono text-[10px] text-fg-subtle">{tc.case_key}</span>}
        <span className="flex-1 truncate text-[12px] font-medium text-fg-muted">
          {isLoading ? "Yükleniyor…" : tc ? "Detay" : "—"}
        </span>
        <div className="flex items-center gap-0.5">
          {tc && (
            <>
              {!editing && (
                <>
                  <button
                    type="button"
                    title="Arşivle"
                    disabled={archive.isPending}
                    onClick={async () => { await archive.mutateAsync(tc.id); onClose(); }}
                    className="rounded-md p-1.5 text-amber-500/70 transition-colors hover:bg-amber-500/10 hover:text-amber-400 disabled:opacity-40"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round"
                        d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8l1 12a2 2 0 002 2h8a2 2 0 002-2L19 8M10 12v4m4-4v4" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    title="Kalıcı Sil"
                    disabled={del.isPending}
                    onClick={() => { setDeleteErr(null); setShowDeleteConfirm(true); }}
                    className="rounded-md p-1.5 text-red-400/60 transition-colors hover:bg-red-500/10 hover:text-red-400 disabled:opacity-40"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </>
              )}
              <button type="button" onClick={() => setEditing(v => !v)}
                title={editing ? "Görüntüle" : "Düzenle"}
                className={cn("rounded-md p-1.5 transition-colors",
                  editing ? "bg-brand-soft text-brand" : "text-fg-subtle hover:bg-surface-overlay hover:text-fg")}>
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round"
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <Link href={`/p/${projectId}/management/cases/${caseId}`}
                title="Tam Sayfada Aç"
                className="rounded-md p-1.5 text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </Link>
            </>
          )}
          <button type="button" onClick={onClose}
            className="rounded-md p-1.5 text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Scrollable tab bar */}
      <div className="flex shrink-0 overflow-x-auto border-b border-border scrollbar-none">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "shrink-0 px-3 py-2 text-[11px] font-medium transition-colors whitespace-nowrap",
              tab === key
                ? "border-b-2 border-brand bg-brand-soft text-brand"
                : "text-fg-subtle hover:text-fg"
            )}
          >
            {label}
            {key === "defects" && (defects?.length ?? 0) > 0 && (
              <span className="ml-1 rounded-full bg-red-500/15 px-1.5 py-0.5 text-[10px] text-red-400">
                {defects!.length}
              </span>
            )}
            {key === "files" && (attachments?.length ?? 0) > 0 && (
              <span className="ml-1 rounded-full bg-surface-overlay px-1.5 py-0.5 text-[10px] text-fg-muted">
                {attachments!.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-8 rounded-lg bg-surface-overlay animate-pulse"
                style={{ opacity: Math.max(0.15, 1 - i * 0.18) }} />
            ))}
          </div>
        ) : !tc ? (
          <div className="flex items-center justify-center p-8">
            <p className="text-[13px] text-fg-subtle">Senaryo yüklenemedi</p>
          </div>
        ) : tab === "comments" ? (
          <div className="flex-1 overflow-auto">
            <CommentThread
              entityType="case"
              entityId={caseId}
              projectId={pid}
              currentUserId={currentUserId}
              userDirectory={userIdMap}
            />
          </div>

        ) : tab === "parametric" ? (
          <div className="flex-1 overflow-auto p-4">
            <ParameterizedCasesPanel caseId={caseId} />
          </div>

        ) : tab === "history" ? (
          <div className="flex-1 overflow-auto p-4">
            <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Versiyon Geçmişi</p>
            {versionsLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-10 animate-pulse rounded-lg bg-surface-overlay" style={{ opacity: 1 - i * 0.25 }} />
                ))}
              </div>
            ) : !versions || versions.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <svg className="h-8 w-8 text-fg-subtle/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p className="text-[12px] text-fg-subtle">Henüz versiyon geçmişi yok.</p>
              </div>
            ) : (
              <div className="space-y-0">
                {[...versions].reverse().map((v, idx, arr) => {
                  const date = new Date(v.created_at);
                  const relTime = date.toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
                  const changedFields = v.changed_fields?.length > 0
                    ? v.changed_fields.join(", ")
                    : v.change_summary ?? "Güncellendi";
                  return (
                    <div key={v.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand" />
                        {idx < arr.length - 1 && (
                          <div className="mt-1 w-px flex-1 bg-border" style={{ minHeight: "28px" }} />
                        )}
                      </div>
                      <div className="pb-4 min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="rounded-md border border-border bg-surface-overlay px-1.5 py-0.5 font-mono text-[10px] font-semibold text-fg-muted">
                            v{v.version_no}
                          </span>
                          <span className="flex-1 truncate text-[12px] text-fg-muted">{changedFields}</span>
                        </div>
                        <p className="mt-0.5 text-[11px] text-fg-subtle">{relTime}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        ) : tab === "runs" ? (
          <div className="flex-1 overflow-auto p-4 space-y-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Koşum İstatistikleri</p>
            {(tc.run_count ?? 0) === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <svg className="h-8 w-8 text-fg-subtle/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z"/>
                </svg>
                <p className="text-[12px] text-fg-subtle">Bu senaryo henüz çalıştırılmadı.</p>
              </div>
            ) : (
              <>
                {/* Stats grid */}
                <div className="grid grid-cols-2 gap-3">
                  {([
                    ["Toplam Koşum", String(tc.run_count ?? 0), "text-fg"],
                    ["Geçti", String(tc.pass_count ?? 0), "text-emerald-400"],
                    ["Başarısız", String(tc.fail_count ?? 0), "text-red-400"],
                    ["Geçme Oranı", `${tc.run_count ? Math.round(((tc.pass_count ?? 0) / tc.run_count) * 100) : 0}%`, "text-brand"],
                  ] as [string, string, string][]).map(([label, val, cls]) => (
                    <div key={label} className="rounded-xl border border-border bg-surface-overlay p-3 text-center">
                      <p className={cn("text-[22px] font-bold tabular-nums", cls)}>{val}</p>
                      <p className="mt-0.5 text-[10px] text-fg-subtle">{label}</p>
                    </div>
                  ))}
                </div>

                {/* Pass rate bar */}
                {(tc.run_count ?? 0) > 0 && (() => {
                  const passRate = Math.round(((tc.pass_count ?? 0) / (tc.run_count ?? 1)) * 100);
                  const failRate = Math.round(((tc.fail_count ?? 0) / (tc.run_count ?? 1)) * 100);
                  const skipRate = 100 - passRate - failRate;
                  return (
                    <div>
                      <div className="mb-1.5 flex justify-between text-[10px] text-fg-subtle">
                        <span>Geçme/Başarısız Dağılımı</span>
                        <span>{passRate}% geçti</span>
                      </div>
                      <div className="flex h-3 overflow-hidden rounded-full bg-surface-overlay">
                        <div className="bg-emerald-500 transition-all" style={{ width: `${passRate}%` }} />
                        <div className="bg-red-500 transition-all" style={{ width: `${failRate}%` }} />
                        {skipRate > 0 && <div className="bg-surface-overlay transition-all" style={{ width: `${skipRate}%` }} />}
                      </div>
                      <div className="mt-1.5 flex gap-3 text-[10px] text-fg-subtle">
                        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />Geçti</span>
                        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500 inline-block" />Başarısız</span>
                      </div>
                    </div>
                  );
                })()}

                {/* Flakiness — only meaningful for automated cases (manual variance is human, not test flakiness) */}
                {(tc.flakiness_score ?? 0) > 0 &&
                  (tc.automation_status === "automated" || tc.automation_status === "in_progress") && (
                  <div className={cn("rounded-xl border p-3",
                    (tc.flakiness_score ?? 0) >= 0.5 ? "border-red-500/30 bg-red-500/5" :
                    (tc.flakiness_score ?? 0) >= 0.3 ? "border-amber-500/30 bg-amber-500/5" :
                    "border-border bg-surface-overlay"
                  )}>
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] font-medium text-fg-muted">Flakiness Skoru</p>
                      <span className={cn("text-[18px] font-bold tabular-nums",
                        (tc.flakiness_score ?? 0) >= 0.5 ? "text-red-400" :
                        (tc.flakiness_score ?? 0) >= 0.3 ? "text-amber-400" :
                        "text-fg-muted"
                      )}>
                        {Math.round((tc.flakiness_score ?? 0) * 100)}%
                      </span>
                    </div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-overlay">
                      <div
                        className={cn("h-full rounded-full transition-all",
                          (tc.flakiness_score ?? 0) >= 0.5 ? "bg-red-500" :
                          (tc.flakiness_score ?? 0) >= 0.3 ? "bg-amber-500" : "bg-emerald-500"
                        )}
                        style={{ width: `${Math.min(100, Math.round((tc.flakiness_score ?? 0) * 100))}%` }}
                      />
                    </div>
                    <p className="mt-1.5 text-[10px] text-fg-subtle">
                      {(tc.flakiness_score ?? 0) >= 0.5 ? "⚠ Yüksek flakiness — acil inceleme gerekiyor" :
                       (tc.flakiness_score ?? 0) >= 0.3 ? "Orta flakiness — stabil olmayan sonuçlar" :
                       "Düşük flakiness — stabil senaryo"}
                    </p>
                  </div>
                )}

                <div className="rounded-xl border border-border bg-surface-overlay p-3 text-[11px] text-fg-subtle space-y-1">
                  <p>Son koşum: <span className="text-fg-muted">{tc.last_run_status ?? "—"}</span></p>
                  <p>Versiyon: <span className="text-fg-muted">v{tc.current_version}</span></p>
                </div>
              </>
            )}
          </div>

        ) : tab === "defects" ? (
          <div className="flex-1 overflow-auto p-4 space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
              Bağlı Defectler
              {defects && defects.length > 0 && (
                <span className="ml-1.5 font-normal text-fg-muted">({defects.length})</span>
              )}
            </p>
            {defectsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-16 animate-pulse rounded-xl bg-surface-overlay" style={{ opacity: 1 - i * 0.25 }} />
                ))}
              </div>
            ) : !defects || defects.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <svg className="h-8 w-8 text-fg-subtle/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p className="text-[12px] text-fg-subtle">Bu senaryoya bağlı defect yok.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {defects.map(defect => (
                  <div key={defect.id} className="rounded-xl border border-border bg-surface-overlay p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className="font-mono text-[10px] text-fg-subtle">{defect.external_key}</span>
                          <span className={cn("rounded-full border px-1.5 py-0.5 text-[9px] font-medium",
                            DEFECT_STATUS_BADGE[defect.status] ?? DEFECT_STATUS_BADGE.open)}>
                            {defect.status}
                          </span>
                        </div>
                        <p className="text-[12px] text-fg-muted leading-snug line-clamp-2">{defect.title}</p>
                      </div>
                      <span className={cn("shrink-0 rounded-full border px-1.5 py-0.5 text-[9px] font-medium",
                        SEVERITY_BADGE[defect.severity] ?? SEVERITY_BADGE.minor)}>
                        {defect.severity}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center gap-2 text-[10px] text-fg-subtle">
                      <span>{defect.priority}</span>
                      <span>·</span>
                      <span>{new Date(defect.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}</span>
                      {defect.url && (
                        <>
                          <span>·</span>
                          <a href={defect.url} target="_blank" rel="noreferrer"
                            className="text-brand hover:underline truncate max-w-[120px]">
                            Jira/Link ↗
                          </a>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="pt-1">
              <Link
                href={`/p/${projectId}/management/defects`}
                className="block w-full rounded-xl border border-border py-2 text-center text-[12px] text-fg-muted hover:bg-surface-overlay hover:text-fg transition-colors"
              >
                Tüm defectleri görüntüle →
              </Link>
            </div>
          </div>

        ) : tab === "files" ? (
          <div className="flex-1 overflow-auto p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Dosya Ekleri</p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadAttachment.isPending}
                className="flex items-center gap-1.5 rounded-lg border border-brand/30 bg-brand-soft px-2.5 py-1 text-[11px] font-medium text-brand hover:brightness-105 disabled:opacity-40 transition-colors"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                {uploadAttachment.isPending ? "Yükleniyor…" : "Dosya Ekle"}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={e => {
                  const file = e.target.files?.[0];
                  if (file) void handleFileUpload(file);
                  e.target.value = "";
                }}
              />
            </div>

            {uploadError && (
              <p className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-[11px] text-red-400">
                {uploadError}
              </p>
            )}

            {attachLoading ? (
              <div className="space-y-2">
                {[1, 2].map(i => (
                  <div key={i} className="h-14 animate-pulse rounded-xl bg-surface-overlay" style={{ opacity: 1 - i * 0.3 }} />
                ))}
              </div>
            ) : !attachments || attachments.length === 0 ? (
              <div
                role="button"
                tabIndex={0}
                aria-label="Dosya yükle"
                className="flex flex-col items-center gap-3 rounded-xl border-2 border-dashed border-border py-8 text-center cursor-pointer hover:border-brand/40 focus:border-brand/60 focus:outline-none transition-colors"
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={e => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
              >
                <svg className="h-8 w-8 text-fg-subtle/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"/>
                </svg>
                <div>
                  <p className="text-[12px] text-fg-subtle">Henüz dosya yok</p>
                  <p className="text-[11px] text-fg-disabled">Tıklayarak dosya yükleyin (maks. 10 MB)</p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                {(attachments as CaseAttachment[]).map(att => {
                  const isImage = att.content_type.startsWith("image/");
                  const isPdf   = att.content_type === "application/pdf";
                  const ext = att.filename.split(".").pop()?.toLowerCase() ?? "";
                  return (
                    <div key={att.id} className="flex items-center gap-3 rounded-xl border border-border bg-surface-overlay px-3 py-2.5">
                      <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold uppercase",
                        isImage ? "bg-purple-500/10 text-purple-400" :
                        isPdf   ? "bg-red-500/10 text-red-400" :
                        "bg-surface-raised text-fg-subtle")}>
                        {isImage ? (
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"/>
                          </svg>
                        ) : isPdf ? (
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
                          </svg>
                        ) : ext}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-[12px] font-medium text-fg-muted">{att.filename}</p>
                        <p className="text-[10px] text-fg-subtle">{formatBytes(att.size)} · {new Date(att.created_at).toLocaleDateString("tr-TR")}</p>
                      </div>
                      <a
                        href={`/api/v1/management/projects/${pid}/cases/${caseId}/attachments/${att.id}/download`}
                        download={att.filename}
                        className="shrink-0 rounded-md p-1.5 text-fg-subtle transition-colors hover:bg-surface-raised hover:text-fg"
                        title="İndir"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"/>
                        </svg>
                      </a>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

        ) : editing ? (
          <div className="flex-1 overflow-auto p-4 space-y-3">
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Başlık</label>
              <input value={title} onChange={e => setTitle(e.target.value)} className={inp} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Priority</label>
                <select value={priority} onChange={e => setPriority(e.target.value)} className={sel}>
                  {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Durum</label>
                <select value={status} onChange={e => setStatus(e.target.value)} className={sel}>
                  {["draft","review","active","archived"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Tür</label>
                <select value={type} onChange={e => setType(e.target.value)} className={sel}>
                  {["manual","automated","exploratory","regression","smoke","functional","performance","security","usability","acceptance"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Severity</label>
                <select value={severity} onChange={e => setSeverity(e.target.value)} className={sel}>
                  {["blocker","critical","major","minor","trivial"].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Amaç</label>
              <textarea value={objective} onChange={e => setObjective(e.target.value)}
                rows={2} placeholder="Test senaryosunun amacı…"
                className={cn(inp, "resize-none text-[12px]")} />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Ön Koşullar</label>
              <textarea value={preconditions} onChange={e => setPreconditions(e.target.value)}
                rows={2} placeholder="Testin başlamadan önce sağlanması gereken koşullar…"
                className={cn(inp, "resize-none text-[12px]")} />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Etiketler</label>
              <input value={tagsText} onChange={e => setTagsText(e.target.value)}
                placeholder="smoke, regression, auth…" className={inp} />
            </div>
            {members.length > 0 && (
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Sahip</label>
                <select value={ownerId} onChange={e => setOwnerId(e.target.value)} className={sel}>
                  <option value="">— Atanmamış —</option>
                  {members.map(m => (
                    <option key={m.user_id} value={m.user_id}>{m.full_name?.trim() || m.email}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="flex gap-2 pt-1">
              <Button type="button" variant="primary" onClick={save} disabled={update.isPending}
                className="flex-1 rounded-xl">
                {update.isPending ? "Kaydediliyor…" : "Kaydet"}
              </Button>
              <Button type="button" variant="outline" onClick={() => setEditing(false)}
                className="rounded-xl">
                İptal
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-auto p-4 space-y-4">
            <h3 className="text-[15px] font-semibold leading-snug text-fg">{tc.title}</h3>

            <div className="flex flex-wrap gap-1.5">
              <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium", P_BADGE[tc.priority] ?? P_BADGE.P2)}>
                {tc.priority}
              </span>
              <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium", SB_BADGE[tc.status] ?? SB_BADGE.draft)}>
                {STATUS_LABEL_TR[tc.status] ?? tc.status}
              </span>
              <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[11px] text-fg-muted">{tc.type}</span>
              {tc.severity && (
                <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[11px] text-fg-subtle">{tc.severity}</span>
              )}
              {tc.automation_status && tc.automation_status !== "manual" && (
                <span className="rounded-full border border-purple-500/20 bg-purple-500/5 px-2 py-0.5 text-[11px] text-purple-400/80">
                  {tc.automation_status}
                </span>
              )}
            </div>

            {tc.tags && tc.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tc.tags.map(tag => (
                  <span key={tag} className="rounded-md border border-border bg-surface-overlay px-2 py-0.5 text-[11px] text-fg-muted">{tag}</span>
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 gap-y-3 rounded-xl border border-border bg-surface-overlay px-4 py-3 text-[12px]">
              {([
                ["Son Koşum", tc.last_run_status ?? "—"],
                ["Adım Sayısı", String(tc.steps?.length ?? 0)],
                ["Versiyon", `v${tc.current_version}`],
                ["Otomasyon", tc.automation_status],
                ...(tc.run_count ? [["Koşum Sayısı", String(tc.run_count)]] : []),
                // Flakiness yalnızca otomasyonlu case'lerde anlamlı
                ...(tc.run_count && (tc.automation_status === "automated" || tc.automation_status === "in_progress")
                  ? [["Flakiness", `${Math.round((tc.flakiness_score ?? 0) * 100)}%`]] : []),
              ] as [string, string][]).map(([k, v]) => (
                <div key={k}>
                  <p className="text-fg-subtle">{k}</p>
                  <p className={cn(
                    "mt-0.5 font-medium",
                    k === "Flakiness" && ((tc.flakiness_score ?? 0) >= 0.3) ? "text-amber-400" : "text-fg-muted"
                  )}>{v}</p>
                </div>
              ))}
              {tc.owner_id && (
                <div className="col-span-2">
                  <p className="text-fg-subtle">Sahip</p>
                  <p className="mt-0.5 font-medium text-fg-muted truncate" title={userIdMap[tc.owner_id] ?? tc.owner_id}>
                    {userIdMap[tc.owner_id] ?? `${tc.owner_id.slice(0, 8)}…`}
                  </p>
                </div>
              )}
            </div>

            {/* ── Review Workflow Panel ── */}
            {(() => {
              const rs = tc.review_status ?? "none";
              const REVIEW_CONFIG: Record<string, { label: string; badge: string }> = {
                none:     { label: "İnceleme Yok",       badge: "border-border-strong/30 bg-slate-500/10 text-fg-muted" },
                pending:  { label: "İnceleme Bekliyor",  badge: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
                approved: { label: "Onaylandı",           badge: "border-teal-500/30 bg-teal-500/10 text-teal-400"   },
                rejected: { label: "Reddedildi",          badge: "border-red-500/30 bg-red-500/10 text-red-400"      },
              };
              const cfg = REVIEW_CONFIG[rs] ?? REVIEW_CONFIG.none;
              return (
                <div className="rounded-xl border border-border bg-surface-overlay p-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">İnceleme</p>
                    <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium", cfg.badge)}>
                      {cfg.label}
                    </span>
                  </div>

                  {rs === "none" || rs === "rejected" ? (
                    <button
                      onClick={() => setShowReviewPanel(v => !v)}
                      className="mt-2 w-full rounded-lg border border-purple-500/30 bg-purple-500/10 py-1.5 text-[11px] font-medium text-purple-400 hover:brightness-110 transition-all"
                    >
                      {rs === "rejected" ? "Tekrar İncelemeye Gönder" : "İncelemeye Gönder"}
                    </button>
                  ) : rs === "pending" ? (
                    <div className="mt-2 flex gap-1.5">
                      <button
                        disabled={approveRev.isPending}
                        onClick={async () => {
                          await approveRev.mutateAsync({ caseId: tc.id, comment: reviewComment || undefined });
                          setReviewComment("");
                        }}
                        className="flex-1 rounded-lg border border-teal-500/30 bg-teal-500/10 py-1.5 text-[11px] font-medium text-teal-400 hover:brightness-110 disabled:opacity-50 transition-all"
                      >
                        {approveRev.isPending ? "…" : "Onayla"}
                      </button>
                      <button
                        disabled={rejectRev.isPending}
                        onClick={async () => {
                          await rejectRev.mutateAsync({ caseId: tc.id, comment: reviewComment || undefined });
                          setReviewComment("");
                        }}
                        className="flex-1 rounded-lg border border-red-500/30 bg-red-500/10 py-1.5 text-[11px] font-medium text-red-400 hover:brightness-110 disabled:opacity-50 transition-all"
                      >
                        {rejectRev.isPending ? "…" : "Reddet"}
                      </button>
                    </div>
                  ) : null}

                  {showReviewPanel && (rs === "none" || rs === "rejected") && (
                    <div className="mt-2 space-y-2">
                      <textarea
                        value={reviewComment}
                        onChange={e => setReviewComment(e.target.value)}
                        rows={2}
                        placeholder="İnceleme notu (opsiyonel)..."
                        className="w-full rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 text-[12px] text-fg-muted placeholder:text-fg-disabled outline-none resize-none focus:border-purple-500/50"
                      />
                      <div className="flex gap-1.5">
                        <Button
                          size="sm"
                          disabled={submitReview.isPending}
                          onClick={async () => {
                            await submitReview.mutateAsync({ caseId: tc.id, comment: reviewComment || undefined });
                            setReviewComment("");
                            setShowReviewPanel(false);
                          }}
                          className="flex-1 rounded-lg bg-purple-600 text-white hover:bg-purple-500"
                        >
                          {submitReview.isPending ? "Gönderiliyor…" : "İncelemeye Gönder"}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowReviewPanel(false)}
                          className="rounded-lg"
                        >
                          İptal
                        </Button>
                      </div>
                    </div>
                  )}

                  {tc.review_comment && (
                    <p className="mt-2 text-[11px] italic text-fg-subtle">
                      &ldquo;{String(tc.review_comment)}&rdquo;
                    </p>
                  )}
                </div>
              );
            })()}

            {tc.objective && (
              <div>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Amaç</p>
                <p className="text-[12px] leading-relaxed text-fg-muted">{tc.objective}</p>
              </div>
            )}

            {tc.preconditions && (
              <div>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Ön Koşullar</p>
                <p className="text-[12px] leading-relaxed text-fg-muted">{tc.preconditions}</p>
              </div>
            )}

            {(tc.steps && tc.steps.length > 0 || true) && (
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                    Test Adımları
                    {tc.steps && tc.steps.length > 0 && (
                      <span className="ml-1 text-fg-disabled normal-case">({tc.steps.length})</span>
                    )}
                  </p>
                  <button type="button" onClick={() => setShowQuickStep(v => !v)}
                    className="flex items-center gap-1 rounded-lg border border-border px-2 py-0.5 text-[10px] text-fg-muted hover:bg-surface-raised hover:text-fg transition-colors">
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 5v14M5 12h14"/>
                    </svg>
                    Adım Ekle
                  </button>
                </div>
                {tc.steps && tc.steps.length > 0 && (
                  <div className="space-y-1.5">
                    {tc.steps.map((s, i) => (
                      <div key={s.id ?? i} className="rounded-xl border border-border bg-surface-raised p-3 shadow-xs">
                        <div className="flex items-start gap-2.5">
                          <span className="mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border border-border bg-surface-overlay font-mono text-[10px] font-bold text-fg-muted">
                            {s.step_no}
                          </span>
                          <div className="flex-1 min-w-0 space-y-1">
                            <p className="text-[12px] leading-relaxed text-fg-muted">{s.action}</p>
                            {s.expected_result && (
                              <p className="text-[11px] leading-relaxed text-fg-subtle">
                                <span className="text-fg-disabled">→ </span>{s.expected_result}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {showQuickStep && (
                  <div className="mt-2 rounded-xl border border-brand/20 bg-brand/5 p-3 space-y-2">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-brand/70">Yeni Adım</p>
                    <div>
                      <label className="mb-1 block text-[10px] text-fg-subtle">Aksiyon *</label>
                      <input
                        autoFocus
                        value={quickStepAction}
                        onChange={e => setQuickStepAction(e.target.value)}
                        placeholder="Bu adımda ne yapılacak?"
                        className="w-full rounded-lg border border-border bg-surface-overlay px-2.5 py-1.5 text-[12px] text-fg placeholder-fg-subtle outline-none focus:border-brand/50"
                      />
                    </div>
                    <div>
                      <label className="mb-1 block text-[10px] text-fg-subtle">Beklenen Sonuç</label>
                      <input
                        value={quickStepExpected}
                        onChange={e => setQuickStepExpected(e.target.value)}
                        placeholder="Ne olması bekleniyor?"
                        className="w-full rounded-lg border border-border bg-surface-overlay px-2.5 py-1.5 text-[12px] text-fg placeholder-fg-subtle outline-none focus:border-brand/50"
                      />
                    </div>
                    <div className="flex items-center gap-2 pt-1">
                      <Button
                        type="button"
                        size="sm"
                        disabled={!quickStepAction.trim() || quickStepSaving}
                        onClick={async () => {
                          if (!quickStepAction.trim()) return;
                          setQuickStepSaving(true);
                          setQuickStepErr(null);
                          try {
                            const existingSteps = (tc.steps ?? []).map(s => ({
                              step_no: s.step_no,
                              action: s.action,
                              expected_result: s.expected_result ?? "",
                              test_data: s.test_data ?? undefined,
                              notes: s.notes ?? undefined,
                            }));
                            const nextNo = existingSteps.length > 0 ? Math.max(...existingSteps.map(s => s.step_no)) + 1 : 1;
                            await update.mutateAsync({
                              caseId: tc.id,
                              steps: [
                                ...existingSteps,
                                { step_no: nextNo, action: quickStepAction.trim(), expected_result: quickStepExpected.trim() },
                              ],
                            });
                            setQuickStepAction("");
                            setQuickStepExpected("");
                            setShowQuickStep(false);
                          } catch {
                            setQuickStepErr("Adım kaydedilemedi. Lütfen tekrar deneyin.");
                          } finally {
                            setQuickStepSaving(false);
                          }
                        }}
                        className="flex-1 rounded-lg"
                      >
                        {quickStepSaving ? "Kaydediliyor…" : "Adımı Kaydet"}
                      </Button>
                      <Button type="button" variant="outline" size="sm" onClick={() => { setShowQuickStep(false); setQuickStepAction(""); setQuickStepExpected(""); setQuickStepErr(null); }}
                        className="rounded-lg">
                        İptal
                      </Button>
                    </div>
                    {quickStepErr && (
                      <p className="text-[11px] text-danger" role="alert">{quickStepErr}</p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* AI İyileştir */}
            <div className="border-t border-border pt-3">
              <Button type="button" variant="outline"
                onClick={async () => {
                  setShowImprove(true);
                  const res = await improve.mutateAsync({ caseId: tc.id, focus: "all" });
                  setImproveResult(res);
                }}
                disabled={improve.isPending}
                className="w-full rounded-xl border-purple-500/20 bg-purple-500/5 text-purple-400 hover:bg-purple-500/10">
                {improve.isPending ? "✦ AI İyileştiriyor…" : "✦ AI İyileştir"}
              </Button>

              {showImprove && improveResult && (
                <div className="mt-2 rounded-xl border border-purple-500/20 bg-purple-500/5 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-purple-400">AI Önerileri</p>
                    <button type="button" onClick={() => { setShowImprove(false); setImproveResult(null); }}
                      className="text-[10px] text-fg-subtle hover:text-fg">✕</button>
                  </div>
                  {improveResult.suggestions.length > 0 && (
                    <ul className="space-y-1">
                      {improveResult.suggestions.map((s, i) => (
                        <li key={i} className="text-[11px] text-fg-muted">• {s}</li>
                      ))}
                    </ul>
                  )}
                  {(improveResult.title || improveResult.objective) && (
                    <Button type="button" size="sm"
                      onClick={async () => {
                        await update.mutateAsync({
                          caseId: tc.id,
                          ...(improveResult.title ? { title: improveResult.title } : {}),
                          ...(improveResult.objective ? { objective: improveResult.objective } : {}),
                          ...(improveResult.preconditions ? { preconditions: improveResult.preconditions } : {}),
                        });
                        setShowImprove(false); setImproveResult(null);
                      }}
                      disabled={update.isPending}
                      className="w-full rounded-lg bg-purple-600 text-white hover:bg-purple-500">
                      {update.isPending ? "Uygulanıyor…" : "Önerileri Uygula"}
                    </Button>
                  )}
                </div>
              )}
            </div>

            <div className="pt-1 space-y-2">
              {cloneSuccess && (
                <p className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-[11px] text-emerald-400">
                  Kopyalandı: {cloneSuccess}
                </p>
              )}
              <Button type="button" variant="outline" disabled={clone.isPending}
                onClick={async () => {
                  const cloned = await clone.mutateAsync({ caseId: tc.id });
                  setCloneSuccess(cloned.case_key ?? cloned.title);
                  setTimeout(() => setCloneSuccess(null), 3000);
                }}
                className="w-full rounded-xl">
                {clone.isPending ? "Kopyalanıyor…" : "Kopyala (Clone)"}
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* ── Kalıcı Silme Onay Diyaloğu ──────────────────────────────────── */}
      {showDeleteConfirm && tc && (
        <div
          className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="case-delete-title"
          onClick={() => !del.isPending && setShowDeleteConfirm(false)}
        >
          <div className="w-full max-w-sm rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
                </svg>
              </div>
              <div>
                <h3 id="case-delete-title" className="text-[14px] font-semibold text-fg">Senaryoyu Kalıcı Sil</h3>
                <p className="text-[11px] text-fg-subtle">{tc.case_key}</p>
              </div>
            </div>
            <p className="mb-5 text-[13px] text-fg-muted">
              <span className="font-medium text-fg">{tc.title}</span> senaryosu kalıcı olarak silinecek.
              Bu işlem geri alınamaz. Run geçmişindeki bu senaryoya ait tüm veriler de silinir.
            </p>
            {deleteErr && (
              <p className="mb-3 text-[12px] text-danger" role="alert">{deleteErr}</p>
            )}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="destructive"
                disabled={del.isPending}
                onClick={async () => {
                  try {
                    await del.mutateAsync(tc.id);
                    setShowDeleteConfirm(false);
                    onClose();
                  } catch {
                    setDeleteErr("Senaryo silinemedi. Lütfen tekrar deneyin.");
                  }
                }}
                className="flex-1 rounded-xl"
              >
                {del.isPending ? "Siliniyor…" : "Evet, Kalıcı Sil"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-xl"
              >
                İptal
              </Button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
