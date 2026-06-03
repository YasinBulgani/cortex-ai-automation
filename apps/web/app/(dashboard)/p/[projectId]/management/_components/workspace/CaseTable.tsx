"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useDraggable } from "@dnd-kit/core";
import type { TestCase } from "@/lib/hooks/use-management";
import { P_DOT, S_DOT, R_DOT, IcGrip, IcPlus, IcSearch, IcPlay, TYPE_OPTIONS } from "./shared";

function CaseRow({ tc, selected, onSelect, checked, onCheck, projectId }: {
  tc: TestCase; selected: boolean; onSelect: () => void;
  checked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `case:${tc.id}`, data: { kind: "case", caseId: tc.id } });
  const pd = P_DOT[tc.priority] ?? P_DOT.P3;
  const sd = S_DOT[tc.status] ?? S_DOT.draft;
  const rd = tc.last_run_status ? (R_DOT[tc.last_run_status] ?? R_DOT.not_run) : null;

  return (
    <tr ref={setNodeRef} onClick={onSelect}
      className={cn("group border-b border-border cursor-pointer transition-colors",
        isDragging && "opacity-30",
        selected ? "border-l-2 border-l-brand bg-brand-soft" : "border-l-2 border-l-transparent hover:bg-surface-overlay")}>
      <td className="hidden w-5 pl-1.5 sm:table-cell">
        <button type="button" {...attributes} {...listeners} title="Folder'a sürükle"
          className="invisible cursor-grab touch-none text-fg-subtle hover:text-fg-muted active:cursor-grabbing group-hover:visible">
          <IcGrip />
        </button>
      </td>
      <td className="w-8 px-2">
        <button type="button" onClick={onCheck}
          className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
            checked ? "border-brand bg-brand" : "border-border hover:border-brand")}>
          {checked && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" /></svg>}
        </button>
      </td>
      <td className="w-[5.5rem] px-3 py-3">
        <span className="select-all font-mono text-[10px] text-fg-subtle">{tc.case_key}</span>
      </td>
      <td className="px-3 py-3">
        <p className="line-clamp-1 text-[13px] text-fg-muted transition-colors group-hover:text-fg">{tc.title}</p>
        {tc.tags && tc.tags.length > 0 && (
          <div className="mt-1 flex gap-1">
            {tc.tags.slice(0, 3).map(t => <span key={t} className="rounded border border-border bg-surface-overlay px-1.5 py-0.5 text-[10px] text-fg-subtle">{t}</span>)}
          </div>
        )}
      </td>
      <td className="w-16 px-3 py-3">
        <span className="flex items-center gap-1.5">
          <span className={cn("h-1.5 w-1.5 rounded-full", pd)} />
          <span className="font-mono text-[11px] text-fg-subtle">{tc.priority}</span>
        </span>
      </td>
      <td className="hidden w-24 px-3 py-3 lg:table-cell">
        <span className="rounded border border-border bg-surface-overlay px-1.5 py-0.5 text-[11px] text-fg-subtle">{tc.type}</span>
      </td>
      <td className="hidden w-20 px-3 py-3 md:table-cell">
        <span className="flex items-center gap-1.5">
          <span className={cn("h-1.5 w-1.5 rounded-full", sd.dot)} />
          <span className="text-[11px] text-fg-subtle">{sd.label}</span>
        </span>
      </td>
      <td className="hidden w-24 px-3 py-3 lg:table-cell">
        {rd ? (
          <span className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", rd.dot)} />
            <span className="text-[11px] text-fg-subtle">{rd.label}</span>
          </span>
        ) : <span className="text-[11px] text-fg-disabled">—</span>}
      </td>
      <td className="hidden w-16 px-3 py-3 text-[11px] text-fg-subtle tabular-nums xl:table-cell">
        {tc.steps?.length ?? 0}
      </td>
      <td className="hidden w-20 px-3 py-3 xl:table-cell">
        <span className="text-[11px] text-fg-subtle">
          {tc.updated_at ? new Date(tc.updated_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" }) : "—"}
        </span>
      </td>
      <td className="w-10 px-2">
        <Link href={`/p/${projectId}/management/cases/${tc.id}`} onClick={e => e.stopPropagation()}
          className="invisible inline-flex rounded p-1 text-fg-subtle transition-all hover:bg-surface-overlay hover:text-fg group-hover:visible">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
        </Link>
      </td>
    </tr>
  );
}

export function CaseTable({
  nodeName, nodeCases, loading, projectId,
  selId, onSelect, checked, onCheck, onClearChecked, onToggleAll,
  onNewCase, onCreateRun, onPromote, onArchiveMany, busy,
}: {
  nodeName: string; nodeCases: TestCase[]; loading: boolean; projectId: string;
  selId: string | null; onSelect: (id: string) => void;
  checked: Set<string>; onCheck: (id: string) => void; onClearChecked: () => void; onToggleAll: (ids: string[]) => void;
  onNewCase: () => void; onCreateRun: () => void; onPromote: () => void; onArchiveMany: () => void; busy: boolean;
}) {
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("");
  const [priorityF, setPriorityF] = useState("");
  const [typeF, setTypeF] = useState("");

  const filtered = useMemo(() => {
    let r = nodeCases;
    const q = search.trim().toLowerCase();
    if (q) r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q));
    if (statusF) r = r.filter(c => c.status === statusF);
    if (priorityF) r = r.filter(c => c.priority === priorityF);
    if (typeF) r = r.filter(c => c.type === typeF);
    return r;
  }, [nodeCases, search, statusF, priorityF, typeF]);

  const allChecked = filtered.length > 0 && filtered.every(c => checked.has(c.id));
  const hasFilter = !!(search || statusF || priorityF || typeF);
  const clearFilters = () => { setSearch(""); setStatusF(""); setPriorityF(""); setTypeF(""); };

  const SEL = "rounded-xl border border-border bg-surface-raised px-2.5 py-1.5 text-[11px] text-fg-muted outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";

  return (
    <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-raised px-4 py-2.5">
        <span className="mr-1 text-[13px] font-semibold text-fg">{nodeName}</span>
        {filtered.length > 0 && <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] text-fg-muted tabular-nums">{filtered.length}</span>}
        <div className="flex-1" />
        <div className="flex w-44 items-center gap-1.5 rounded-xl border border-border bg-surface-raised px-2.5 py-1.5 shadow-xs transition-colors focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
          <IcSearch /><input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Ara…"
            className="min-w-0 flex-1 bg-transparent text-[11px] text-fg placeholder:text-fg-subtle outline-none" />
        </div>
        <select value={statusF} onChange={e => setStatusF(e.target.value)} className={SEL}>
          <option value="">Durum</option><option value="active">Aktif</option>
          <option value="draft">Taslak</option><option value="review">Review</option>
        </select>
        <select value={priorityF} onChange={e => setPriorityF(e.target.value)} className={SEL}>
          <option value="">Priority</option>
          {["P0", "P1", "P2", "P3"].map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={typeF} onChange={e => setTypeF(e.target.value)} className={cn(SEL, "hidden lg:block")}>
          <option value="">Tür</option>
          {TYPE_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        {hasFilter && <button type="button" onClick={clearFilters}
          className="text-[11px] text-red-500/70 hover:text-red-400 transition-colors">✕ Temizle</button>}
        <button type="button" onClick={onNewCase}
          className="flex items-center gap-1.5 rounded-xl bg-brand px-3 py-1.5 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
          <IcPlus /> Yeni Senaryo
        </button>
      </div>

      {/* Bulk bar */}
      {checked.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-b border-brand/20 bg-brand-soft px-4 py-1.5">
          <span className="text-[12px] font-semibold text-brand">{checked.size} seçili</span>
          <button type="button" onClick={onCreateRun} disabled={busy}
            className="flex items-center gap-1 rounded-lg border border-brand/25 bg-surface-raised px-2.5 py-1 text-[11px] text-brand transition-colors hover:bg-surface-overlay disabled:opacity-40">
            <IcPlay /> Seçilenlerden Run Oluştur
          </button>
          <button type="button" onClick={onPromote} disabled={busy}
            className="rounded-lg border border-border px-2.5 py-1 text-[11px] text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg disabled:opacity-40">Aktife Al</button>
          <button type="button" onClick={onArchiveMany} disabled={busy}
            className="rounded-lg border border-red-500/20 px-2.5 py-1 text-[11px] text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-colors">Arşivle</button>
          <button type="button" onClick={onClearChecked} className="ml-auto text-[11px] text-fg-subtle hover:text-fg-muted">Temizle</button>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div>{Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 border-b border-border px-4 py-3">
              <div className="h-4 w-4 shrink-0 rounded bg-surface-overlay animate-pulse" />
              <div className="h-3 w-16 rounded bg-surface-overlay animate-pulse" />
              <div className="h-3 flex-1 max-w-sm rounded bg-surface-overlay animate-pulse" />
              <div className="h-4 w-8 rounded bg-surface-overlay animate-pulse" />
            </div>
          ))}</div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            {hasFilter ? (
              <><p className="text-[14px] font-medium text-fg-muted">Sonuç bulunamadı</p>
                <button type="button" onClick={clearFilters}
                  className="mt-3 text-[12px] text-brand hover:text-brand-secondary transition-colors">Filtreleri temizle</button></>
            ) : (
              <><p className="text-[14px] font-medium text-fg-muted">Henüz senaryo yok</p>
                <button type="button" onClick={onNewCase}
                  className="mt-3 flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
                  <IcPlus /> İlk senaryoyu oluştur
                </button></>
            )}
          </div>
        ) : (
          <table className="w-full">
            <thead className="sticky top-0 z-raised bg-surface-overlay backdrop-blur-sm">
              <tr className="border-b border-border">
                <th className="hidden w-5 sm:table-cell" />
                <th className="w-8 px-2 py-2.5">
                  <button type="button" onClick={() => allChecked ? onClearChecked() : onToggleAll(filtered.map(c => c.id))}
                    className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
                      allChecked ? "border-brand bg-brand" : "border-border hover:border-brand")}>
                    {allChecked && <svg className="h-2.5 w-2.5 text-brand-fg" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" /></svg>}
                  </button>
                </th>
                {["ID", "Başlık", "P", "Tür", "Durum", "Son Koşum", "Adım", "Tarih", ""].map(h => (
                  <th key={h} className={cn("px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-muted",
                    h === "Tür" && "hidden lg:table-cell", h === "Durum" && "hidden md:table-cell",
                    h === "Son Koşum" && "hidden lg:table-cell", h === "Adım" && "hidden xl:table-cell",
                    h === "Tarih" && "hidden xl:table-cell")}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(tc => (
                <CaseRow key={tc.id} tc={tc}
                  selected={selId === tc.id}
                  onSelect={() => onSelect(tc.id)}
                  checked={checked.has(tc.id)}
                  onCheck={e => { e.stopPropagation(); onCheck(tc.id); }}
                  projectId={projectId} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-border bg-surface-raised px-4 py-1.5">
        <span className="text-[10px] text-fg-subtle">
          {hasFilter ? `${filtered.length} / ${nodeCases.length}` : `${filtered.length} senaryo`}
        </span>
      </div>
    </div>
  );
}
