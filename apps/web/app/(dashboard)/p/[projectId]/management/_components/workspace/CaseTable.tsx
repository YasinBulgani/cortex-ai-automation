"use client";

import { useMemo, useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useDraggable } from "@dnd-kit/core";
import type { TestCase } from "@/lib/hooks/use-management";
import { useCloneManagementCase, useArchiveManagementCase } from "@/lib/hooks/use-management";
import { P_DOT, S_DOT, R_DOT, IcGrip, IcPlus, IcSearch, IcPlay, TYPE_OPTIONS } from "./shared";

// ─── Context Menu ─────────────────────────────────────────────────────────────

interface ContextMenuProps {
  x: number;
  y: number;
  tc: TestCase;
  projectId: string;
  onClose: () => void;
  onClone: () => void;
  onArchive: () => void;
}

function CaseContextMenu({ x, y, tc, projectId, onClose, onClone, onArchive }: ContextMenuProps) {
  const router = useRouter();
  const menuRef = useRef<HTMLDivElement>(null);
  const [focusIdx, setFocusIdx] = useState(0);

  // Adjust position to stay within viewport
  const [pos, setPos] = useState({ x, y });
  useEffect(() => {
    const el = menuRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    setPos({
      x: x + rect.width > vw ? vw - rect.width - 8 : x,
      y: y + rect.height > vh ? vh - rect.height - 8 : y,
    });
  }, [x, y]);

  const ITEM_COUNT = 4;
  const itemsRef = useRef([
    {
      label: "Detayları Aç",
      action: () => { router.push(`/p/${projectId}/management/cases/${tc.id}`); onClose(); },
    },
    {
      label: "Klonla",
      action: () => { onClone(); onClose(); },
    },
    {
      label: "Arşivle",
      action: () => { onArchive(); onClose(); },
    },
    {
      label: "Yeni Pencerede Aç",
      action: () => { window.open(`/p/${projectId}/management/cases/${tc.id}`, "_blank"); onClose(); },
    },
  ]);
  // Keep ref in sync with latest callbacks (closures)
  itemsRef.current[0].action = () => { router.push(`/p/${projectId}/management/cases/${tc.id}`); onClose(); };
  itemsRef.current[1].action = () => { onClone(); onClose(); };
  itemsRef.current[2].action = () => { onArchive(); onClose(); };
  itemsRef.current[3].action = () => { window.open(`/p/${projectId}/management/cases/${tc.id}`, "_blank"); onClose(); };

  const items = itemsRef.current;

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key === "ArrowDown") { setFocusIdx(i => (i + 1) % ITEM_COUNT); e.preventDefault(); }
      if (e.key === "ArrowUp")   { setFocusIdx(i => (i - 1 + ITEM_COUNT) % ITEM_COUNT); e.preventDefault(); }
      if (e.key === "Enter")     { itemsRef.current[focusIdx]?.action(); e.preventDefault(); }
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [focusIdx, onClose]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      aria-label="Case işlemleri"
      className="fixed z-[9000] min-w-[160px] overflow-hidden rounded-xl border border-border bg-surface-raised py-1 shadow-elevated"
      style={{ left: pos.x, top: pos.y }}
    >
      <p className="px-3 py-1.5 text-[9px] font-semibold uppercase tracking-widest text-fg-subtle">
        {tc.case_key}
      </p>
      <div className="my-1 border-t border-border" />
      {items.map((item, idx) => (
        <button
          key={item.label}
          type="button"
          role="menuitem"
          onClick={item.action}
          onMouseEnter={() => setFocusIdx(idx)}
          className={cn(
            "flex w-full items-center gap-2 px-3 py-2 text-left text-[12px] transition-colors",
            focusIdx === idx
              ? "bg-brand-soft text-brand"
              : "text-fg-muted hover:bg-surface-overlay hover:text-fg",
          )}
        >
          {item.label}
        </button>
      ))}
    </div>,
    document.body,
  );
}

function IcCopy() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  );
}

function CaseRow({ tc, selected, onSelect, checked, onCheck, projectId, onCloned }: {
  tc: TestCase; selected: boolean; onSelect: () => void;
  checked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
  onCloned?: (newCaseId: string) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `case:${tc.id}`, data: { kind: "case", caseId: tc.id } });
  const clone   = useCloneManagementCase(projectId);
  const archive = useArchiveManagementCase(projectId);
  const [cloning, setCloning] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);

  const pd = P_DOT[tc.priority] ?? P_DOT.P3;
  const sd = S_DOT[tc.status] ?? S_DOT.draft;
  const rd = tc.last_run_status ? (R_DOT[tc.last_run_status] ?? R_DOT.not_run) : null;

  async function handleClone(e: React.MouseEvent) {
    e.stopPropagation();
    if (cloning) return;
    setCloning(true);
    try {
      const res = await clone.mutateAsync({ caseId: tc.id });
      onCloned?.(res.id);
    } finally {
      setCloning(false);
    }
  }

  function handleContextMenu(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  }

  async function handleArchive() {
    try {
      await archive.mutateAsync(tc.id);
    } catch {
      // silently ignore — parent will refetch
    }
  }

  return (
    <>
    <tr ref={setNodeRef} onClick={onSelect} onContextMenu={handleContextMenu}
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
        <div className="flex items-center gap-1.5">
          {tc.parent_id && (
            <span className="shrink-0 rounded border border-brand/20 bg-brand-soft px-1 py-0.5 text-[9px] font-medium text-brand" title="Alt senaryo">↳</span>
          )}
          <p className="line-clamp-1 text-[13px] text-fg-muted transition-colors group-hover:text-fg">{tc.title}</p>
        </div>
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
      <td className="w-20 px-2">
        <div className="invisible flex items-center gap-0.5 group-hover:visible">
          <button type="button" onClick={handleClone} disabled={cloning} title="Klonla"
            className="inline-flex rounded p-1 text-fg-subtle transition-all hover:bg-surface-overlay hover:text-fg disabled:opacity-40">
            <IcCopy />
          </button>
          <Link href={`/p/${projectId}/management/cases/${tc.id}`} onClick={e => e.stopPropagation()}
            className="inline-flex rounded p-1 text-fg-subtle transition-all hover:bg-surface-overlay hover:text-fg">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
          </Link>
        </div>
      </td>
    </tr>
    {contextMenu && (
      <CaseContextMenu
        x={contextMenu.x}
        y={contextMenu.y}
        tc={tc}
        projectId={projectId}
        onClose={() => setContextMenu(null)}
        onClone={async () => {
          setCloning(true);
          try {
            const res = await clone.mutateAsync({ caseId: tc.id });
            onCloned?.(res.id);
          } finally {
            setCloning(false);
          }
        }}
        onArchive={handleArchive}
      />
    )}
    </>
  );
}

const VISIBLE_COUNT = 50;

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
  const router    = useRouter();
  const pathname  = usePathname();
  const params    = useSearchParams();

  const [search,    setSearch]    = useState(() => params.get("q")  ?? "");
  const [statusF,   setStatusF]   = useState(() => params.get("s")  ?? "");
  const [priorityF, setPriorityF] = useState(() => params.get("p")  ?? "");
  const [typeF,     setTypeF]     = useState(() => params.get("t")  ?? "");
  const [page,      setPage]      = useState(0);
  const tableTopRef = useRef<HTMLDivElement>(null);

  // Sync filters → URL (debounced to avoid thrashing)
  useEffect(() => {
    const sp = new URLSearchParams(params.toString());
    if (search)    sp.set("q", search);    else sp.delete("q");
    if (statusF)   sp.set("s", statusF);   else sp.delete("s");
    if (priorityF) sp.set("p", priorityF); else sp.delete("p");
    if (typeF)     sp.set("t", typeF);     else sp.delete("t");
    router.replace(`${pathname}?${sp.toString()}`, { scroll: false });
  }, [search, statusF, priorityF, typeF]); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = useMemo(() => {
    let r = nodeCases;
    const q = search.trim().toLowerCase();
    if (q) r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q));
    if (statusF) r = r.filter(c => c.status === statusF);
    if (priorityF) r = r.filter(c => c.priority === priorityF);
    if (typeF) r = r.filter(c => c.type === typeF);
    return r;
  }, [nodeCases, search, statusF, priorityF, typeF]);

  // Reset page when filters change
  useEffect(() => { setPage(0); }, [search, statusF, priorityF, typeF, nodeCases]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / VISIBLE_COUNT));
  const safePage = Math.min(page, totalPages - 1);
  const paginated = filtered.slice(safePage * VISIBLE_COUNT, (safePage + 1) * VISIBLE_COUNT);

  const goToPrev = useCallback(() => {
    setPage(p => Math.max(0, p - 1));
    tableTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const goToNext = useCallback(() => {
    setPage(p => Math.min(totalPages - 1, p + 1));
    tableTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [totalPages]);

  const allChecked = filtered.length > 0 && filtered.every(c => checked.has(c.id));
  const hasFilter = !!(search || statusF || priorityF || typeF);
  const clearFilters = () => { setSearch(""); setStatusF(""); setPriorityF(""); setTypeF(""); };

  const SEL = "rounded-xl border border-border bg-surface-raised px-2.5 py-1.5 text-[11px] text-fg-muted outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";

  return (
    <div ref={tableTopRef} className="flex flex-1 flex-col min-w-0 overflow-hidden">
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
        <Button type="button" variant="primary" size="sm" onClick={onNewCase}
          className="gap-1.5 text-[13px] font-semibold">
          <IcPlus /> Yeni Senaryo
        </Button>
      </div>

      {/* Bulk bar */}
      {checked.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-b border-brand/20 bg-brand-soft px-4 py-1.5">
          <span className="text-[12px] font-semibold text-brand">{checked.size} seçili</span>
          <Button type="button" variant="outline" size="sm" onClick={onCreateRun} disabled={busy}
            className="gap-1 border-brand/25 bg-surface-raised text-[11px] text-brand hover:bg-surface-overlay">
            <IcPlay /> Seçilenlerden Run Oluştur
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={onPromote} disabled={busy}
            className="text-[11px] text-fg-muted hover:text-fg">Aktife Al</Button>
          <Button type="button" variant="ghost-danger" size="sm" onClick={onArchiveMany} disabled={busy}
            className="border border-red-500/20 px-2.5 text-[11px] text-red-400 hover:bg-red-500/10">Arşivle</Button>
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
                <Button type="button" variant="primary" onClick={onNewCase}
                  className="mt-3 gap-1.5 text-[13px] font-semibold">
                  <IcPlus /> İlk senaryoyu oluştur
                </Button></>
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
              {paginated.map(tc => (
                <CaseRow key={tc.id} tc={tc}
                  selected={selId === tc.id}
                  onSelect={() => onSelect(tc.id)}
                  checked={checked.has(tc.id)}
                  onCheck={e => { e.stopPropagation(); onCheck(tc.id); }}
                  projectId={projectId}
                  onCloned={(newId) => onSelect(newId)} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer / Pagination */}
      <div className="flex items-center justify-between border-t border-border bg-surface-raised px-4 py-1.5 gap-2">
        <span className="text-[10px] text-fg-subtle shrink-0">
          {hasFilter ? `${filtered.length} / ${nodeCases.length}` : `${filtered.length} senaryo`}
        </span>
        {filtered.length > VISIBLE_COUNT && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={goToPrev}
              disabled={safePage === 0}
              className="rounded-lg border border-border px-2 py-0.5 text-[10px] text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg disabled:opacity-30"
            >
              ← Önceki
            </button>
            <span className="text-[10px] text-fg-subtle tabular-nums">
              {safePage * VISIBLE_COUNT + 1}–{Math.min((safePage + 1) * VISIBLE_COUNT, filtered.length)} / {filtered.length} case
            </span>
            <button
              type="button"
              onClick={goToNext}
              disabled={safePage >= totalPages - 1}
              className="rounded-lg border border-border px-2 py-0.5 text-[10px] text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg disabled:opacity-30"
            >
              Sonraki →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
