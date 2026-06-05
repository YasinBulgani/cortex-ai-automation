"use client";

import { useMemo, useState, useRef, useCallback, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  useManagementRuns,
  useUpdateManagementRun,
  useDeleteManagementRun,
  type TestRun,
} from "@/lib/hooks/use-management";
import { RUN_STATUS_DOT, RUN_STATUS_LABEL, IcPlus } from "./shared";

function fmtShortDate(iso?: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "2-digit", month: "short", year: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/* Kebab menu                                                           */
/* ------------------------------------------------------------------ */
interface KebabMenuProps {
  run: TestRun;
  pid: string;
  onRenameStart: () => void;
  onDeleted?: () => void;
}

function KebabMenu({ run, pid, onRenameStart, onDeleted }: KebabMenuProps) {
  const [open, setOpen] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const updateRun = useUpdateManagementRun(pid);
  const deleteRun = useDeleteManagementRun(pid);

  useEffect(() => {
    if (!open) return;
    function handle(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [open]);

  const handleReopen = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setOpen(false);
      updateRun.mutate({ id: run.id, status: "not_started" });
    },
    [run.id, updateRun],
  );

  const handleRename = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setOpen(false);
      onRenameStart();
    },
    [onRenameStart],
  );

  const handleDelete = useCallback(
    async (e: React.MouseEvent) => {
      e.stopPropagation();
      if (confirmDeleteId !== run.id) {
        setConfirmDeleteId(run.id);
        return;
      }
      setConfirmDeleteId(null);
      setOpen(false);
      await deleteRun.mutateAsync(run.id);
      onDeleted?.();
    },
    [run.id, confirmDeleteId, deleteRun, onDeleted],
  );

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={e => { e.stopPropagation(); setOpen(v => !v); }}
        className="flex h-5 w-5 items-center justify-center rounded opacity-0 group-hover:opacity-100 hover:bg-surface-overlay text-fg-subtle transition-opacity"
        title="İşlemler"
      >
        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
          <circle cx="8" cy="2" r="1.5" />
          <circle cx="8" cy="8" r="1.5" />
          <circle cx="8" cy="14" r="1.5" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-6 z-50 min-w-[148px] rounded-xl border border-border bg-surface-raised py-1 shadow-xl">
          <button
            type="button"
            onClick={handleReopen}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-[12px] text-fg-muted hover:bg-surface-overlay"
          >
            Yeniden Aç
          </button>
          <button
            type="button"
            onClick={handleRename}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-[12px] text-fg-muted hover:bg-surface-overlay"
          >
            Yeniden Adlandır
          </button>
          <div className="my-1 border-t border-border-subtle" />
          {confirmDeleteId === run.id ? (
            <div className="flex items-center gap-1 px-3 py-1.5">
              <span className="flex-1 text-[11px] text-red-400">Emin misin?</span>
              <button
                type="button"
                onClick={handleDelete}
                className="rounded px-2 py-0.5 text-[11px] font-semibold text-red-400 hover:bg-red-500/10"
              >
                Evet
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                className="rounded px-2 py-0.5 text-[11px] text-fg-muted hover:bg-surface-overlay"
              >
                Hayır
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleDelete}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-[12px] text-red-400 hover:bg-red-500/10"
            >
              Sil
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* RunItem                                                              */
/* ------------------------------------------------------------------ */
interface RunItemProps {
  run: TestRun;
  selected: boolean;
  onSelect: () => void;
  pid: string;
  onDeleted?: () => void;
}

function RunItem({ run, selected, onSelect, pid, onDeleted }: RunItemProps) {
  const status = run.status || "not_started";
  const updateRun = useUpdateManagementRun(pid);

  const [renaming, setRenaming] = useState(false);
  const [renameVal, setRenameVal] = useState(run.name);
  const inputRef = useRef<HTMLInputElement>(null);

  const startRename = useCallback(() => {
    setRenameVal(run.name);
    setRenaming(true);
    setTimeout(() => inputRef.current?.select(), 0);
  }, [run.name]);

  const commitRename = useCallback(() => {
    const trimmed = renameVal.trim();
    if (trimmed && trimmed !== run.name) {
      updateRun.mutate({ id: run.id, name: trimmed });
    }
    setRenaming(false);
  }, [run, renameVal, updateRun]);

  const handleRenameKey = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") commitRename();
      if (e.key === "Escape") setRenaming(false);
    },
    [commitRename],
  );

  return (
    <div
      className={cn(
        "group flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left transition-colors cursor-pointer",
        selected ? "bg-brand-soft text-brand shadow-xs" : "text-fg-muted hover:bg-surface-overlay hover:text-fg",
      )}
      onClick={onSelect}
    >
      <span className={cn("mt-1 h-1.5 w-1.5 shrink-0 rounded-full", RUN_STATUS_DOT[status] ?? "bg-slate-600")} />
      <div className="min-w-0 flex-1">
        {renaming ? (
          <input
            ref={inputRef}
            value={renameVal}
            onChange={e => setRenameVal(e.target.value)}
            onBlur={commitRename}
            onKeyDown={handleRenameKey}
            onClick={e => e.stopPropagation()}
            className="w-full rounded border border-brand bg-surface px-1.5 py-0 text-[12px] font-medium text-fg outline-none"
          />
        ) : (
          <p className="truncate text-[12px] leading-snug">{run.name}</p>
        )}
        <p className="text-[10px] text-fg-subtle">
          {RUN_STATUS_LABEL[status] ?? status}
          {run.environment ? ` · ${run.environment}` : ""}
          {run.created_at ? ` · ${fmtShortDate(run.created_at)}` : ""}
        </p>
      </div>
      <KebabMenu run={run} pid={pid} onRenameStart={startRename} onDeleted={onDeleted} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* RunList                                                              */
/* ------------------------------------------------------------------ */
export function RunList({
  pid,
  selectedRunId,
  onSelect,
  onNewRun,
  onDeleted,
  filteredRunIds,
}: {
  pid: string;
  selectedRunId: string | null;
  onSelect: (id: string) => void;
  onNewRun: () => void;
  onDeleted?: () => void;
  filteredRunIds?: Set<string>;
}) {
  const { data: runs, isLoading } = useManagementRuns(pid || undefined);
  const allRaw = useMemo(() => runs ?? [], [runs]);
  const all = useMemo(
    () => filteredRunIds ? allRaw.filter(r => filteredRunIds.has(r.id)) : allRaw,
    [allRaw, filteredRunIds],
  );

  const groups = useMemo(() => {
    const active = all.filter(r => r.status === "in_progress");
    const pending = all.filter(r => r.status === "not_started" || !r.status);
    const done = all.filter(r => r.status === "completed" || r.status === "failed");
    return [
      { key: "active", label: "Devam Eden", items: active },
      { key: "pending", label: "Bekleyen", items: pending },
      { key: "done", label: "Tamamlanan", items: done },
    ].filter(g => g.items.length > 0);
  }, [all]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
        <span className="text-[12px] font-semibold text-fg">Test Runs</span>
        <button
          type="button"
          onClick={onNewRun}
          className="flex items-center gap-1 rounded-lg bg-brand px-2 py-1 text-[11px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
        >
          <IcPlus /> Yeni
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-10 rounded-lg bg-surface-overlay animate-pulse"
              style={{ opacity: Math.max(0.2, 1 - i * 0.12) }}
            />
          ))
        ) : all.length === 0 ? (
          <div className="px-2 py-8 text-center">
            <p className="text-[12px] font-medium text-fg-muted">Henüz run yok</p>
            <button
              type="button"
              onClick={onNewRun}
              className="mt-2 text-[11px] font-medium text-brand hover:text-brand-secondary"
            >
              İlk run'ı oluştur →
            </button>
          </div>
        ) : (
          groups.map(g => (
            <div key={g.key}>
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                {g.label} <span className="text-fg-disabled">({g.items.length})</span>
              </p>
              <div className="space-y-0.5">
                {g.items.map(run => (
                  <RunItem
                    key={run.id}
                    run={run}
                    selected={selectedRunId === run.id}
                    onSelect={() => onSelect(run.id)}
                    pid={pid}
                    onDeleted={onDeleted}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="border-t border-border px-4 py-2 text-[10px] text-fg-subtle">
        {filteredRunIds && filteredRunIds.size !== allRaw.length
          ? `${all.length} / ${allRaw.length} run`
          : `${all.length} run`}
      </div>
    </div>
  );
}
