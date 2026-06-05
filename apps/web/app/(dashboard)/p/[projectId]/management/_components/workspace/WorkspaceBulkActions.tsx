"use client";

import { useState } from "react";
import { type TestSuite, type TestFolder } from "@/lib/hooks/use-management";

export interface WorkspaceBulkActionsProps {
  checkedSize: number;
  checkedIds: string[];
  checkedArchivedCount: number;
  busy: boolean;
  suites: TestSuite[];
  folders: TestFolder[];
  cloneProgress?: { done: number; total: number } | null;
  onToggleAll: (ids: string[]) => void;
  nodeCaseIds: string[];
  onCreateRun: () => void;
  onPromote: () => void;
  onArchiveMany: () => void;
  onUnarchiveMany: () => void;
  onBulkMove: (caseId: string, suiteId: string, folderId: string | null) => Promise<void>;
  onBulkUpdate: (payload: {
    case_ids: string[];
    priority?: string;
    type?: string;
    status?: string;
    tags_add?: string[];
  }) => Promise<void>;
  onBulkClone: (caseIds: string[]) => Promise<void>;
  onClearChecked: () => void;
}

export function WorkspaceBulkActions({
  checkedSize,
  checkedIds,
  checkedArchivedCount,
  busy,
  suites,
  folders,
  cloneProgress,
  onToggleAll,
  nodeCaseIds,
  onCreateRun,
  onPromote,
  onArchiveMany,
  onUnarchiveMany,
  onBulkMove,
  onBulkUpdate,
  onBulkClone,
  onClearChecked,
}: WorkspaceBulkActionsProps) {
  const [tagInput, setTagInput] = useState("");
  const [showTagInput, setShowTagInput] = useState(false);
  const [localCloneProgress, setLocalCloneProgress] = useState<{ done: number; total: number } | null>(null);

  const activeCloneProgress = cloneProgress ?? localCloneProgress;

  const handleBulkClone = async () => {
    if (!checkedIds.length) return;
    setLocalCloneProgress({ done: 0, total: checkedIds.length });
    await onBulkClone(checkedIds);
    setLocalCloneProgress(null);
    onClearChecked();
  };

  if (checkedSize === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-brand/20 bg-brand-soft px-4 py-2">
      {/* Counter + select all */}
      <span className="text-[11px] font-semibold text-brand">
        {checkedSize} senaryo seçili
      </span>
      <button
        type="button"
        onClick={() => onToggleAll(nodeCaseIds)}
        className="rounded border border-brand/25 px-1.5 py-0.5 text-[10px] text-brand hover:bg-brand/10 transition-colors"
      >
        Tümünü Seç
      </button>
      <span className="text-[10px] text-fg-disabled">|</span>
      <button
        type="button"
        onClick={onCreateRun}
        disabled={busy}
        className="rounded-md border border-brand/25 bg-surface-raised px-2.5 py-1 text-[11px] font-medium text-brand transition-colors hover:bg-surface-overlay disabled:opacity-40"
      >
        ▶ Run Oluştur
      </button>
      <button
        type="button"
        onClick={onPromote}
        disabled={busy}
        className="rounded border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-40 transition-colors"
      >
        Aktife Al
      </button>

      {/* Bulk priority */}
      <select
        disabled={busy}
        onChange={async e => {
          if (!e.target.value) return;
          await onBulkUpdate({ case_ids: checkedIds, priority: e.target.value });
          onClearChecked();
          e.target.value = "";
        }}
        className="rounded border border-border bg-surface-raised px-2 py-1 text-[11px] text-fg-muted disabled:opacity-40 outline-none cursor-pointer"
      >
        <option value="">Öncelik Değiştir →</option>
        {["P0", "P1", "P2", "P3"].map(p => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Bulk move: suite picker */}
      <select
        disabled={busy}
        onChange={async e => {
          if (!e.target.value) return;
          const [suiteId, folderId] = e.target.value.split("|");
          for (const id of checkedIds) {
            await onBulkMove(id, suiteId, folderId || null);
          }
          onClearChecked();
          e.target.value = "";
        }}
        className="rounded border border-border bg-surface-raised px-2 py-1 text-[11px] text-fg-muted disabled:opacity-40 outline-none cursor-pointer"
      >
        <option value="">Suite/Folder Taşı →</option>
        {suites.map(s => (
          <optgroup key={s.id} label={s.name}>
            <option value={`${s.id}|`}>{s.name} (kök)</option>
            {folders
              .filter(f => f.suite_id === s.id && !f.parent_id)
              .map(f => (
                <option key={f.id} value={`${s.id}|${f.id}`}>
                  &nbsp;&nbsp;{f.name}
                </option>
              ))}
          </optgroup>
        ))}
      </select>

      {/* Etiket Ekle */}
      {showTagInput ? (
        <form
          className="flex items-center gap-1"
          onSubmit={async e => {
            e.preventDefault();
            const newTags = tagInput.split(",").map(t => t.trim()).filter(Boolean);
            if (!newTags.length) { setShowTagInput(false); return; }
            await onBulkUpdate({ case_ids: checkedIds, tags_add: newTags });
            setTagInput("");
            setShowTagInput(false);
            onClearChecked();
          }}
        >
          <input
            autoFocus
            value={tagInput}
            onChange={e => setTagInput(e.target.value)}
            placeholder="tag1, tag2"
            className="rounded border border-brand/30 bg-surface-raised px-2 py-1 text-[11px] text-fg outline-none focus:border-brand w-32"
            onKeyDown={e => {
              if (e.key === "Escape") { setShowTagInput(false); setTagInput(""); }
            }}
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded border border-brand/30 bg-brand/10 px-2 py-1 text-[11px] text-brand hover:bg-brand/20 disabled:opacity-40 transition-colors"
          >
            Ekle
          </button>
          <button
            type="button"
            onClick={() => { setShowTagInput(false); setTagInput(""); }}
            className="text-[11px] text-fg-subtle hover:text-fg px-1"
          >
            ✕
          </button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setShowTagInput(true)}
          disabled={busy}
          className="rounded border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-40 transition-colors"
        >
          🏷 Etiket Ekle
        </button>
      )}

      {/* Bulk Clone */}
      <button
        type="button"
        onClick={() => void handleBulkClone()}
        disabled={busy || activeCloneProgress !== null}
        className="rounded border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-40 transition-colors"
      >
        {activeCloneProgress
          ? `${activeCloneProgress.done}/${activeCloneProgress.total} kopyalandı`
          : "Klonla"}
      </button>

      {/* Arşiv'den Çıkar — only when archived cases are selected */}
      {checkedArchivedCount > 0 && (
        <button
          type="button"
          onClick={onUnarchiveMany}
          disabled={busy}
          className="rounded border border-emerald-500/25 px-2.5 py-1 text-[11px] text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-40 transition-colors"
        >
          Arşiv&apos;den Çıkar ({checkedArchivedCount})
        </button>
      )}

      <button
        type="button"
        onClick={onArchiveMany}
        disabled={busy}
        className="rounded border border-red-500/20 px-2.5 py-1 text-[11px] text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-colors"
      >
        Arşivle
      </button>
      <button
        type="button"
        onClick={() => { onClearChecked(); setShowTagInput(false); setTagInput(""); }}
        className="ml-auto text-[11px] text-fg-subtle hover:text-fg-muted"
      >
        Temizle
      </button>
    </div>
  );
}
