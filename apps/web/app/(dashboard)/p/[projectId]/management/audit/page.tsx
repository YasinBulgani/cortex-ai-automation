"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useManagementAuditEvents, type ManagementAuditEvent } from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { RoleGuard } from "../_components/RoleGuard";

const ACTION_COLOR: Record<string, string> = {
  "case.created":              "bg-emerald-500/15 text-emerald-400",
  "case.updated":              "bg-blue-500/15 text-blue-400",
  "case.archived":             "bg-amber-500/15 text-amber-400",
  "case.deleted":              "bg-red-500/15 text-red-400",
  "case.sub_case_created":     "bg-teal-500/15 text-teal-400",
  "case.dependency_added":     "bg-violet-500/15 text-violet-400",
  "suite.created":             "bg-purple-500/15 text-purple-400",
  "suite.deleted":             "bg-red-500/15 text-red-400",
  "folder.created":            "bg-cyan-500/15 text-cyan-400",
  "folder.deleted":            "bg-red-500/15 text-red-400",
  "run.created":               "bg-blue-500/15 text-blue-400",
  "run.updated":               "bg-sky-500/15 text-sky-400",
  "run.deleted":               "bg-red-500/15 text-red-400",
  "run.completed":             "bg-emerald-500/15 text-emerald-400",
  "plan.created":              "bg-indigo-500/15 text-indigo-400",
  "plan.updated":              "bg-blue-500/15 text-blue-400",
  "cycle.created":             "bg-indigo-500/15 text-indigo-400",
  "cycle.updated":             "bg-blue-500/15 text-blue-400",
  "cycle.deleted":             "bg-red-500/15 text-red-400",
  "shared_step.created":       "bg-teal-500/15 text-teal-400",
  "shared_step.updated":       "bg-blue-500/15 text-blue-400",
  "shared_step.deleted":       "bg-red-500/15 text-red-400",
  "release_signoff.created":   "bg-emerald-500/15 text-emerald-400",
  "defect.created":            "bg-red-500/15 text-red-400",
  "defect_link.created":       "bg-red-500/15 text-red-400",
  "defect_link.updated":       "bg-orange-500/15 text-orange-400",
  "defect_link.deleted":       "bg-slate-500/15 text-fg-muted",
  "requirement_link.created":  "bg-emerald-500/15 text-emerald-400",
  "requirement_link.deleted":  "bg-red-500/15 text-red-400",
};

const ENTITY_ICON: Record<string, string> = {
  case:             "TC",
  suite:            "S",
  folder:           "F",
  run:              "R",
  plan:             "P",
  cycle:            "C",
  shared_step:      "⊞",
  release_signoff:  "✓",
  defect:           "!",
  defect_link:      "!",
  requirement:      "Q",
  requirement_link: "Q",
  regression_set:   "Rg",
};

function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("tr-TR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
  });
}

function fmtDateISO(iso: string) {
  return new Date(iso).toISOString().slice(0, 10);
}

function exportJSON(events: ManagementAuditEvent[]) {
  const blob = new Blob([JSON.stringify(events, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCSV(events: ManagementAuditEvent[]) {
  const header = ["id", "action", "entity_type", "entity_id", "actor_id", "created_at", "payload"];
  const rows = events.map(ev => [
    ev.id,
    ev.action,
    ev.entity_type,
    ev.entity_id ?? "",
    ev.actor_id ?? "",
    ev.created_at,
    JSON.stringify(ev.payload ?? {}),
  ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(","));
  const csv = [header.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function EventRow({ ev, userIdMap = {} }: { ev: ManagementAuditEvent; userIdMap?: Record<string, string> }) {
  const [open, setOpen] = useState(false);
  const colorCls = ACTION_COLOR[ev.action] ?? "bg-surface-accent/30 text-fg-muted";
  const icon     = ENTITY_ICON[ev.entity_type] ?? ev.entity_type?.[0]?.toUpperCase() ?? "?";
  const hasPayload = ev.payload && Object.keys(ev.payload).length > 0;
  const actorDisplay = ev.actor_id
    ? (userIdMap[ev.actor_id] ?? ev.actor_id.slice(0, 8) + "…")
    : "Sistem";

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
          <span className="text-[10px] text-fg-muted truncate max-w-[120px] block" title={ev.actor_id ?? undefined}>
            {actorDisplay}
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
  const [actorFilter,  setActorFilter]  = useState("");
  const [dateFrom,     setDateFrom]     = useState("");
  const [dateTo,       setDateTo]       = useState("");

  const { data: events, isLoading, isError, refetch } = useManagementAuditEvents(mpid || undefined, limit);

  const { data: membersData } = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () =>
      apiFetch<Array<{ user_id: string; email: string; full_name?: string }>>(
        `/api/v1/organizations/projects/${projectId}/members`
      ).then(d => (Array.isArray(d) ? d : [])),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
  const userIdMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const m of membersData ?? []) {
      map[m.user_id] = m.full_name?.trim() || m.email;
    }
    return map;
  }, [membersData]);

  const filtered = useMemo(() => (events ?? []).filter(ev => {
    if (actionFilter && !ev.action.includes(actionFilter)) return false;
    if (entityFilter && ev.entity_type !== entityFilter) return false;
    if (actorFilter && (ev.actor_id ?? "") !== actorFilter) return false;
    if (dateFrom) {
      const evDate = fmtDateISO(ev.created_at);
      if (evDate < dateFrom) return false;
    }
    if (dateTo) {
      const evDate = fmtDateISO(ev.created_at);
      if (evDate > dateTo) return false;
    }
    return true;
  }), [events, actionFilter, entityFilter, actorFilter, dateFrom, dateTo]);

  const entityTypes = useMemo(() => [...new Set((events ?? []).map(e => e.entity_type))].sort(), [events]);
  const actionTypes = useMemo(() => [...new Set((events ?? []).map(e => e.action))].sort(), [events]);
  const actorIds    = useMemo(() => [...new Set((events ?? []).filter(e => e.actor_id).map(e => e.actor_id!))].sort(), [events]);

  const hasFilter = !!(actionFilter || entityFilter || actorFilter || dateFrom || dateTo);

  function clearFilters() {
    setActionFilter("");
    setEntityFilter("");
    setActorFilter("");
    setDateFrom("");
    setDateTo("");
  }

  const SEL = "rounded-lg border border-border bg-surface-overlay px-2.5 py-1.5 text-[11px] text-fg-muted outline-none focus:border-brand transition-colors";

  return (
    <RoleGuard minRole="admin" projectId={projectId ?? ""}
      fallback={
        <div className="flex flex-col items-center justify-center min-h-full gap-4 text-center p-8">
          <div className="rounded-full bg-surface-overlay p-5">
            <svg className="h-10 w-10 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
          </div>
          <div>
            <p className="text-[14px] font-semibold text-fg-muted">Erişim Kısıtlandı</p>
            <p className="mt-1 text-[12px] text-fg-subtle max-w-xs mx-auto">Denetim kaydına erişmek için Admin veya Owner yetkisi gereklidir.</p>
          </div>
        </div>
      }>
    <div className="flex flex-col min-h-full bg-surface-base text-fg">
      {/* Header */}
      <div className="border-b border-border bg-surface-raised px-6 py-4">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-[15px] font-semibold text-fg">Denetim İzi</h1>
              <p className="mt-0.5 text-[11px] text-fg-subtle">Proje üzerindeki tüm değişikliklerin kaydı</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => filtered.length > 0 && exportJSON(filtered)}
                disabled={filtered.length === 0}
                className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[11px] font-medium text-fg-muted hover:text-fg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                JSON
              </button>
              <button
                type="button"
                onClick={() => filtered.length > 0 && exportCSV(filtered)}
                disabled={filtered.length === 0}
                className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[11px] font-medium text-fg-muted hover:text-fg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                CSV
              </button>
              <button type="button" onClick={() => refetch()}
                className="rounded-lg border border-border bg-surface-overlay px-3 py-1.5 text-[11px] font-medium text-fg-muted hover:text-fg transition-colors">
                ↺ Yenile
              </button>
            </div>
          </div>
          {/* Filters row */}
          <div className="flex flex-wrap items-center gap-2">
            <select value={actionFilter} onChange={e => setActionFilter(e.target.value)} className={SEL}>
              <option value="">Tüm İşlemler</option>
              {actionTypes.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={entityFilter} onChange={e => setEntityFilter(e.target.value)} className={SEL}>
              <option value="">Tüm Varlıklar</option>
              {entityTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={actorFilter} onChange={e => setActorFilter(e.target.value)} className={SEL}>
              <option value="">Tüm Kullanıcılar</option>
              {actorIds.map(id => (
                <option key={id} value={id}>
                  {userIdMap[id] ?? id.slice(0, 8) + "…"}
                </option>
              ))}
            </select>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              title="Başlangıç tarihi"
              className={SEL}
            />
            <span className="text-[10px] text-fg-subtle">—</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              title="Bitiş tarihi"
              className={SEL}
            />
            <select value={limit} onChange={e => setLimit(Number(e.target.value))} className={SEL}>
              {[50, 100, 200].map(n => <option key={n} value={n}>Son {n}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      {events && events.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-raised px-6 py-2 text-[11px] text-fg-subtle">
          <span className="text-fg-muted font-medium">{filtered.length} kayıt</span>
          {actionFilter && <span className="rounded-full border border-brand/20 bg-brand-soft px-2 py-0.5 text-[10px] text-brand">{actionFilter}</span>}
          {entityFilter && <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{entityFilter}</span>}
          {actorFilter && <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">Kullanıcı: {userIdMap[actorFilter] ?? actorFilter.slice(0, 8) + "…"}</span>}
          {dateFrom && <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{dateFrom} den</span>}
          {dateTo && <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted">{dateTo} e</span>}
          {hasFilter && (
            <button type="button" onClick={clearFilters}
              className="text-[10px] text-fg-subtle hover:text-danger">Temizle</button>
          )}
        </div>
      )}

      {/* Activity breakdown strip */}
      {!isLoading && !isError && filtered.length > 0 && (
        <div className="border-b border-border bg-surface-base px-6 py-2.5 overflow-x-auto">
          <div className="flex items-center gap-3 min-w-max">
            {(() => {
              const byEntity: Record<string, number> = {};
              for (const ev of filtered) {
                const e = ev.entity_type ?? "other";
                byEntity[e] = (byEntity[e] ?? 0) + 1;
              }
              const ENTITY_COLORS: Record<string, string> = {
                case:   "text-blue-400 bg-blue-500/10 border-blue-500/20",
                suite:  "text-purple-400 bg-purple-500/10 border-purple-500/20",
                run:    "text-teal-400 bg-teal-500/10 border-teal-500/20",
                plan:   "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
                defect: "text-red-400 bg-red-500/10 border-red-500/20",
                defect_link: "text-orange-400 bg-orange-500/10 border-orange-500/20",
                requirement: "text-amber-400 bg-amber-500/10 border-amber-500/20",
                shared_step: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
              };
              const ENTITY_LABELS: Record<string, string> = {
                case: "Case", suite: "Suite", folder: "Klasör", run: "Run",
                plan: "Plan", cycle: "Cycle", defect: "Defect",
                defect_link: "Defect", requirement: "Gereksinim",
                shared_step: "Adım Şablonu", release_signoff: "Onay",
              };
              return Object.entries(byEntity)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([entity, count]) => (
                  <button
                    key={entity}
                    type="button"
                    onClick={() => setEntityFilter(entityFilter === entity ? "" : entity)}
                    className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium transition-colors ${
                      ENTITY_COLORS[entity] ?? "text-fg-muted bg-surface-overlay border-border"
                    } ${entityFilter === entity ? "ring-2 ring-brand/30" : ""}`}
                  >
                    <span>{ENTITY_LABELS[entity] ?? entity}</span>
                    <span className="opacity-70 tabular-nums">{count}</span>
                  </button>
                ));
            })()}
          </div>
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
            <svg className="h-12 w-12 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
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
              {filtered.map(ev => <EventRow key={ev.id} ev={ev} userIdMap={userIdMap} />)}
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
    </RoleGuard>
  );
}
