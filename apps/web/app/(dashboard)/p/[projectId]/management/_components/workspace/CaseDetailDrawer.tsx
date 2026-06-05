"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  useManagementCase,
  useManagementCaseVersions,
  useUpdateManagementCase,
  useArchiveManagementCase,
  useDeleteManagementCase,
  useCloneManagementCase,
  useImproveManagementCase,
  type ImproveTestCaseResponse,
} from "@/lib/hooks/use-management";
import { P_BADGE, SB_BADGE, STATUS_LABEL_TR } from "./shared";
import { CommentThread } from "../CommentThread";

type Tab = "detail" | "comments" | "history";

export function CaseDetailDrawer({ caseId, pid, projectId, onClose }: {
  caseId: string; pid: string; projectId: string; onClose: () => void;
}) {
  const { data: tc, isLoading } = useManagementCase(pid || undefined, caseId || undefined);
  const { data: versions, isLoading: versionsLoading } = useManagementCaseVersions(pid || undefined, caseId || undefined);
  const update  = useUpdateManagementCase(pid);
  const archive = useArchiveManagementCase(pid);
  const del     = useDeleteManagementCase(pid);
  const clone   = useCloneManagementCase(pid);
  const improve = useImproveManagementCase(pid);
  const [cloneSuccess,      setCloneSuccess]      = useState<string | null>(null);
  const [improveResult,     setImproveResult]     = useState<ImproveTestCaseResponse | null>(null);
  const [showImprove,       setShowImprove]       = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

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
    });
    setEditing(false);
  };

  const inp = "w-full rounded-xl border border-border bg-surface-raised px-3 py-2 text-[13px] text-fg placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";
  const sel = "w-full rounded-xl border border-border bg-surface-raised px-2.5 py-2 text-[13px] text-fg-muted outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";

  const tabs: { key: Tab; label: string }[] = [
    { key: "detail",   label: "Detay" },
    { key: "comments", label: "Yorumlar" },
    { key: "history",  label: "Geçmiş" },
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
                  {/* Arşivle */}
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
                  {/* Kalıcı Sil */}
                  <button
                    type="button"
                    title="Kalıcı Sil"
                    disabled={del.isPending}
                    onClick={() => setShowDeleteConfirm(true)}
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

      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-border">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              "flex-1 py-2 text-[12px] font-medium transition-colors",
              tab === key
                ? "border-b-2 border-brand bg-brand-soft text-brand"
                : "text-fg-subtle hover:text-fg"
            )}
          >
            {label}
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
            />
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
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={save} disabled={update.isPending}
                className="flex-1 rounded-xl bg-brand py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105 disabled:opacity-40">
                {update.isPending ? "Kaydediliyor…" : "Kaydet"}
              </button>
              <button type="button" onClick={() => setEditing(false)}
                className="rounded-xl border border-border px-4 py-2 text-[13px] font-medium text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg">
                İptal
              </button>
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
              ] as [string, string][]).map(([k, v]) => (
                <div key={k}>
                  <p className="text-fg-subtle">{k}</p>
                  <p className="mt-0.5 font-medium text-fg-muted">{v}</p>
                </div>
              ))}
            </div>

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

            {tc.steps && tc.steps.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                  Test Adımları
                  <span className="ml-1 text-fg-disabled normal-case">({tc.steps.length})</span>
                </p>
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
              </div>
            )}

            {/* AI İyileştir */}
            <div className="border-t border-border pt-3">
              <button type="button"
                onClick={async () => {
                  setShowImprove(true);
                  const res = await improve.mutateAsync({ caseId: tc.id, focus: "all" });
                  setImproveResult(res);
                }}
                disabled={improve.isPending}
                className="w-full rounded-xl border border-purple-500/20 bg-purple-500/5 py-2 text-[12px] text-purple-400 hover:bg-purple-500/10 disabled:opacity-40 transition-colors">
                {improve.isPending ? "✦ AI İyileştiriyor…" : "✦ AI İyileştir"}
              </button>

              {/* AI Improve sonuçları */}
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
                    <button type="button"
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
                      className="w-full rounded-lg bg-purple-600 py-1.5 text-[11px] font-semibold text-white hover:bg-purple-500 disabled:opacity-40 transition-colors">
                      {update.isPending ? "Uygulanıyor…" : "Önerileri Uygula"}
                    </button>
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
              <button type="button" disabled={clone.isPending}
                onClick={async () => {
                  const cloned = await clone.mutateAsync({ caseId: tc.id });
                  setCloneSuccess(cloned.case_key ?? cloned.title);
                  setTimeout(() => setCloneSuccess(null), 3000);
                }}
                className="w-full rounded-xl border border-border py-2 text-[12px] text-fg-muted hover:bg-surface-overlay hover:text-fg disabled:opacity-40 transition-colors">
                {clone.isPending ? "Kopyalanıyor…" : "Kopyala (Clone)"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Kalıcı Silme Onay Diyaloğu ──────────────────────────────────── */}
      {showDeleteConfirm && tc && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl border border-border bg-surface-raised p-6 shadow-2xl">
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-500/10">
                <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
                </svg>
              </div>
              <div>
                <h3 className="text-[14px] font-semibold text-fg">Senaryoyu Kalıcı Sil</h3>
                <p className="text-[11px] text-fg-subtle">{tc.case_key}</p>
              </div>
            </div>
            <p className="mb-5 text-[13px] text-fg-muted">
              <span className="font-medium text-fg">{tc.title}</span> senaryosu kalıcı olarak silinecek.
              Bu işlem geri alınamaz. Run geçmişindeki bu senaryoya ait tüm veriler de silinir.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={del.isPending}
                onClick={async () => {
                  await del.mutateAsync(tc.id);
                  setShowDeleteConfirm(false);
                  onClose();
                }}
                className="flex-1 rounded-xl bg-red-600 py-2 text-[13px] font-semibold text-white hover:bg-red-500 disabled:opacity-40 transition-colors"
              >
                {del.isPending ? "Siliniyor…" : "Evet, Kalıcı Sil"}
              </button>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="rounded-xl border border-border px-4 py-2 text-[13px] text-fg-muted hover:text-fg transition-colors"
              >
                İptal
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
