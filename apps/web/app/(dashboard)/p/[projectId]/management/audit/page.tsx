"use client";

import { useState } from "react";
import { useManagementAuditEvents, type ManagementAuditEvent } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";

const ACTION_COLOR: Record<string, string> = {
  "case.created":            "bg-emerald-500/15 text-emerald-400",
  "case.updated":            "bg-blue-500/15 text-blue-400",
  "case.archived":           "bg-amber-500/15 text-amber-400",
  "case.deleted":            "bg-red-500/15 text-red-400",
  "suite.created":           "bg-purple-500/15 text-purple-400",
  "suite.deleted":           "bg-red-500/15 text-red-400",
  "folder.created":          "bg-cyan-500/15 text-cyan-400",
  "folder.deleted":          "bg-red-500/15 text-red-400",
  "run.created":             "bg-blue-500/15 text-blue-400",
  "run.completed":           "bg-emerald-500/15 text-emerald-400",
  "release_signoff.created": "bg-emerald-500/15 text-emerald-400",
  "defect.created":          "bg-red-500/15 text-red-400",
};

const ENTITY_ICON: Record<string, string> = {
  case:            "TC",
  suite:           "S",
  folder:          "F",
  run:             "R",
  plan:            "P",
  release_signoff: "✓",
  defect:          "!",
  requirement:     "Q",
  regression_set:  "Rg",
};

function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("tr-TR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
  });
}

function EventRow({ ev }: { ev: ManagementAuditEvent }) {
  const [open, setOpen] = useState(false);
  const colorCls = ACTION_COLOR[ev.action] ?? "bg-slate-700/30 text-slate-400";
  const icon     = ENTITY_ICON[ev.entity_type] ?? ev.entity_type?.[0]?.toUpperCase() ?? "?";
  const hasPayload = ev.payload && Object.keys(ev.payload).length > 0;

  return (
    <>
      <tr
        onClick={() => hasPayload && setOpen(v => !v)}
        className={cn(
          "border-b border-border/50 transition-colors",
          hasPayload ? "cursor-pointer hover:bg-surface-overlay" : "",
        )}
      >
        <td className="px-4 py-3 w-10">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-overlay font-mono text-[9px] font-bold text-fg-subtle">
            {icon}
          </span>
        </td>
        <td className="px-4 py-3">
          <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold", colorCls)}>
            {ev.action}
          </span>
        </td>
        <td className="px-4 py-3 hidden md:table-cell">
          <span className="text-[12px] text-fg-muted">{ev.entity_type}</span>
        </td>
        <td className="px-4 py-3 hidden lg:table-cell">
          <span className="font-mono text-[10px] text-fg-subtle truncate max-w-[120px] block">
            {ev.entity_id ? ev.entity_id.slice(0, 8) + "…" : "—"}
          </span>
        </td>
        <td className="px-4 py-3 hidden md:table-cell">
          <span className="font-mono text-[10px] text-fg-subtle truncate max-w-[80px] block">
            {ev.actor_id ? ev.actor_id.slice(0, 8) + "…" : "Sistem"}
          </span>
        </td>
        <td className="px-4 py-3 text-[11px] text-fg-subtle tabular-nums whitespace-nowrap">
          {fmtTime(ev.created_at)}
        </td>
        {hasPayload && (
          <td className="px-3 py-3 w-8 text-fg-subtle">
            <svg className={cn("h-3 w-3 transition-transform", open && "rotate-90")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/>
            </svg>
          </td>
        )}
      </tr>
      {open && hasPayload && (
        <tr className="border-b border-border/30 bg-surface-overlay">
          <td colSpan={7} className="px-4 py-3">
            <pre className="text-[11px] text-fg-muted font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
              {JSON.stringify(ev.payload, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  );
}

export default function ManagementAuditPage() {
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);

  const [limit,        setLimit]        = useState(100);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");

  const { data: events, isLoading, isError, refetch } = useManagementAuditEvents(mpid || undefined, limit);

  const filtered = (events ?? []).filter(ev => {
    if (actionFilter && !ev.action.includes(actionFilter)) return false;
    if (entityFilter && ev.entity_type !== entityFilter) return false;
    return true;
  });

  const entityTypes = [...new Set((events ?? []).map(e => e.entity_type))].sort();
  const actionTypes = [...new Set((events ?? []).map(e => e.action))].sort();

  const SEL = "rounded-lg border border-border bg-surface-overlay px-2.5 py-1.5 text-[11px] text-fg-muted outline-none focus:border-brand transition-colors";

  return (
    <div className="flex flex-col min-h-full bg-bg text-slate-200">
      {/* Header */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-[15px] font-semibold text-fg">Denetim İzi</h1>
            <p className="mt-0.5 text-[11px] text-fg-subtle">Proje üzerindeki tüm değişikliklerin kaydı</p>
          </div>
          <div className="flex items-center gap-2">
            <select value={actionFilter} onChange={e => setActionFilter(e.target.value)} className={SEL}>
              <option value="">Tüm İşlemler</option>
              {actionTypes.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={entityFilter} onChange={e => setEntityFilter(e.target.value)} className={SEL}>
              <option value="">Tüm Varlıklar</option>
              {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={limit} onChange={e => setLimit(Number(e.target.value))} className={SEL}>
              {[50, 100, 200].map(n => <option key={n} value={n}>Son {n}</option>)}
            </select>
            <button type="button" onClick={() => refetch()}
              className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[11px] font-medium text-fg-muted hover:text-fg transition-colors">
              ↺ Yenile
            </button>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      {events && events.length > 0 && (
        <div className="flex items-center gap-4 border-b border-border bg-surface-raised px-6 py-2 text-[11px] text-fg-subtle">
          <span className="text-fg-muted font-medium">{filtered.length} kayıt</span>
          {actionFilter && <span className="rounded-full border border-brand/20 bg-brand-soft px-2 py-0.5 text-[10px] text-brand">{actionFilter}</span>}
          {entityFilter && <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{entityFilter}</span>}
          {(actionFilter || entityFilter) && (
            <button type="button" onClick={() => { setActionFilter(""); setEntityFilter(""); }}
              className="text-[10px] text-fg-subtle hover:text-danger">Temizle</button>
          )}
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="space-y-px pt-1 px-2">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg border border-border/30 px-4 py-3 animate-pulse"
                style={{ opacity: Math.max(0.15, 1 - i * 0.08) }}>
                <div className="h-7 w-7 rounded-lg bg-surface-overlay" />
                <div className="h-4 w-32 rounded bg-surface-overlay" />
                <div className="h-3 w-16 rounded bg-surface-overlay" />
                <div className="ml-auto h-3 w-24 rounded bg-surface-overlay" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <p className="text-[13px] font-medium text-fg-muted">Veri yüklenemedi</p>
            <button type="button" onClick={() => refetch()}
              className="rounded-xl border border-border px-4 py-2 text-[12px] text-fg-muted hover:text-fg transition-colors">
              Tekrar Dene
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <svg className="h-12 w-12 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
            <p className="text-[13px] font-medium text-fg-muted">Henüz kayıt yok</p>
            <p className="text-[11px] text-fg-subtle">Proje üzerinde işlem yapıldıkça burası dolacak</p>
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-10 border-b border-border bg-surface-raised">
              <tr>
                <th className="w-10 px-4 py-2.5" />
                <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">İşlem</th>
                <th className="hidden px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle md:table-cell">Tür</th>
                <th className="hidden px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle lg:table-cell">Varlık ID</th>
                <th className="hidden px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle md:table-cell">Kullanıcı</th>
                <th className="px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Zaman</th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody>
              {filtered.map(ev => <EventRow key={ev.id} ev={ev} />)}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer */}
      {events && events.length > 0 && (
        <div className="border-t border-border px-6 py-2 text-[10px] text-fg-subtle flex items-center justify-between">
          <span>{filtered.length} / {events.length} kayıt gösteriliyor</span>
          {events.length >= limit && (
            <button type="button" onClick={() => setLimit(l => l + 100)}
              className="text-brand hover:underline">Daha fazla yükle</button>
          )}
        </div>
      )}
    </div>
  );
}
