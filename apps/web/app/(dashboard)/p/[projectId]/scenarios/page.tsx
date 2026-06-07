"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { cn } from "@/lib/utils";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCenter,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useManagementRepository,
  useCreateManagementCase,
  useCreateManagementSuite,
  useCreateManagementFolder,
  useUpdateManagementSuite,
  useDeleteManagementSuite,
  useUpdateManagementFolder,
  useDeleteManagementFolder,
  useEnsureManagementProject,
  useManagementRequirements,
  useManagementCaseVersions,
  useGenerateTestCases,
  useCloneManagementCase,
  useImproveManagementCase,
  useMoveManagementCase,
  useBulkUpdateCases,
  type GeneratedCase,
  type ImproveTestCaseResponse,
  type TestCase,
  type TestFolder,
  type TestSuite,
} from "@/lib/hooks/use-management";

// ─── Config ──────────────────────────────────────────────────────────────────

const PRIORITY_CFG = {
  P0: { label: "P0", dot: "bg-red-500/70",    text: "text-slate-300" },
  P1: { label: "P1", dot: "bg-orange-400/60", text: "text-slate-400" },
  P2: { label: "P2", dot: "bg-slate-500",     text: "text-slate-500" },
  P3: { label: "P3", dot: "bg-slate-600",     text: "text-slate-600" },
} as const;

const STATUS_CFG = {
  active:   { label: "Aktif",  dot: "bg-emerald-500/70", text: "text-slate-400" },
  draft:    { label: "Taslak", dot: "bg-slate-600",      text: "text-slate-500" },
  archived: { label: "Arşiv",  dot: "bg-slate-700",      text: "text-slate-600" },
  review:   { label: "Review", dot: "bg-blue-500/70",    text: "text-slate-400" },
} as const;

const RUN_CFG = {
  passed:  { label: "Passed",  dot: "bg-emerald-500/70", text: "text-slate-300" },
  failed:  { label: "Failed",  dot: "bg-red-500/80",     text: "text-slate-300" },
  blocked: { label: "Blocked", dot: "bg-amber-500/60",   text: "text-slate-400" },
  not_run: { label: "—",       dot: "bg-slate-700",      text: "text-slate-600" },
  retest:  { label: "Retest",  dot: "bg-blue-500/60",    text: "text-slate-400" },
  skipped: { label: "Skip",    dot: "bg-slate-600",      text: "text-slate-500" },
} as const;

const TYPE_OPTIONS = [
  "manual","smoke","regression","uat","exploratory",
  "integration","performance","security","accessibility","api","e2e",
] as const;

const SEVERITY_OPTIONS = ["critical","major","minor","trivial"] as const;

// ─── Types ────────────────────────────────────────────────────────────────────

type SelectedNode =
  | { type: "all" }
  | { type: "suite";  id: string }
  | { type: "folder"; id: string; suiteId: string };

type DetailTab = "overview" | "steps" | "history" | "requirements";

type DraftStep = {
  id: string;
  action: string;
  expected_result: string;
  test_data: string;
  is_required: boolean;
};

// ─── Utils ────────────────────────────────────────────────────────────────────

function makeStep(o?: Partial<DraftStep>): DraftStep {
  return { id: `s-${Math.random().toString(36).slice(2, 9)}`, action: "", expected_result: "", test_data: "", is_required: true, ...o };
}

function slugify(s: string) {
  return `/${s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || s}`;
}

// ─── Icons ────────────────────────────────────────────────────────────────────

function IcSearch()  { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>; }
function IcPlus()    { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/></svg>; }
function IcClose()   { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>; }
function IcChevron({ open }: { open: boolean }) { return <svg className={cn("h-2.5 w-2.5 shrink-0 transition-transform duration-150", open && "rotate-90")} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7"/></svg>; }
function IcGrip()    { return <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 16 16"><circle cx="5" cy="4" r="1.2"/><circle cx="11" cy="4" r="1.2"/><circle cx="5" cy="8" r="1.2"/><circle cx="11" cy="8" r="1.2"/><circle cx="5" cy="12" r="1.2"/><circle cx="11" cy="12" r="1.2"/></svg>; }
function IcSparkle() { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>; }
function IcEdit()    { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>; }
function IcCopy()    { return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>; }
function IcRepo()    { return <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 10V7"/></svg>; }
function IcFolder()     { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>; }
function IcFolderOpen() { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"/></svg>; }
function IcDots()       { return <svg className="h-3 w-3 shrink-0" fill="currentColor" viewBox="0 0 20 20"><circle cx="4" cy="10" r="1.5"/><circle cx="10" cy="10" r="1.5"/><circle cx="16" cy="10" r="1.5"/></svg>; }
function IcTrash()      { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>; }
function IcPencil()     { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>; }
function IcMove()       { return <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>; }

function RepositoryEditorRow({
  value,
  setValue,
  placeholder,
  marker,
  onSave,
  onCancel,
}: {
  value: string;
  setValue: (value: string) => void;
  placeholder: string;
  marker: string;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="rounded-lg border border-brand/25 bg-brand-soft/70 p-2 shadow-xs ring-1 ring-brand/10">
      <div className="flex min-w-0 items-center gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-brand/20 bg-surface-raised text-[9px] font-bold text-brand">
          {marker}
        </span>
        <input
          autoFocus
          type="text"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter") onSave();
            if (e.key === "Escape") onCancel();
          }}
          placeholder={placeholder}
          className="min-w-0 flex-1 rounded-md border border-border bg-surface-raised px-2 py-1 text-xs text-fg shadow-xs placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15"
        />
      </div>
      <div className="mt-2 flex items-center justify-end gap-1.5">
        <button
          type="button"
          onClick={onSave}
          className="inline-flex h-7 items-center rounded-md bg-brand px-2 text-[11px] font-semibold text-brand-fg shadow-xs transition-colors hover:brightness-105"
        >
          Kaydet
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex h-7 items-center rounded-md border border-border bg-surface-raised px-2 text-[11px] font-medium text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg"
        >
          İptal
        </button>
      </div>
    </div>
  );
}

// ─── Badges ───────────────────────────────────────────────────────────────────

function PBadge({ p }: { p: string }) {
  const c = PRIORITY_CFG[p as keyof typeof PRIORITY_CFG] ?? PRIORITY_CFG.P3;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", c.dot)}/>
      <span className={cn("font-mono text-[10px] font-medium", c.text)}>{c.label}</span>
    </span>
  );
}

function SDot({ s }: { s: string }) {
  const c = STATUS_CFG[s as keyof typeof STATUS_CFG] ?? STATUS_CFG.draft;
  return (
    <span className="flex items-center gap-1.5">
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", c.dot)}/>
      <span className={cn("text-[10px]", c.text)}>{c.label}</span>
    </span>
  );
}

function RunBadge({ s }: { s: string }) {
  const c = RUN_CFG[s as keyof typeof RUN_CFG] ?? RUN_CFG.not_run;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", c.dot)}/>
      <span className={cn("text-[10px]", c.text)}>{c.label}</span>
    </span>
  );
}

// ─── Suite Tree ───────────────────────────────────────────────────────────────

type AddFolderTarget = { suiteId: string; parentFolderId?: string };
type RenameTarget    = { type: "suite" | "folder"; id: string; name: string };
type DeleteTarget    = { type: "suite" | "folder"; id: string; name: string };
type MoveFolderState = { folder: TestFolder };

function FolderNode({
  folder, depth, allFolders, cases, suites, selected, onSelect,
  addTarget, setAddTarget, onRename, onDelete, onMove,
  folderName, setFolderName, onSaveFolder,
}: {
  folder: TestFolder; depth: number;
  allFolders: TestFolder[]; cases: TestCase[]; suites: TestSuite[];
  selected: SelectedNode; onSelect: (n: SelectedNode) => void;
  addTarget: AddFolderTarget | null; setAddTarget: (v: AddFolderTarget | null) => void;
  onRename: (t: RenameTarget) => void;
  onDelete: (t: DeleteTarget) => void;
  onMove: (t: MoveFolderState) => void;
  folderName: string; setFolderName: (v: string) => void;
  onSaveFolder: (suiteId: string, parentFolderId?: string) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const children = allFolders.filter(f => f.parent_id === folder.id);
  const fc       = cases.filter(c => c.folder_id === folder.id && !c.archived).length;
  const isSel    = selected.type === "folder" && selected.id === folder.id;
  const isAdding = addTarget?.suiteId === folder.suite_id && addTarget.parentFolderId === folder.id;

  return (
    <div>
      <div className="group flex items-center gap-0.5" style={{ paddingLeft: depth * 12 }}>
        {children.length > 0 ? (
          <button type="button" onClick={() => setOpen(p => !p)}
            className="flex h-5 w-4 shrink-0 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
            <IcChevron open={open}/>
          </button>
        ) : (
          <span className="w-4 shrink-0"/>
        )}
        <button type="button" onClick={() => onSelect({ type: "folder", id: folder.id, suiteId: folder.suite_id })}
          className={cn("flex flex-1 min-w-0 items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs transition-colors",
            isSel ? "border border-brand/20 bg-brand-soft text-brand shadow-xs"
                  : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
          {open && children.length > 0 ? <IcFolderOpen/> : <IcFolder/>}
          <span className="flex-1 truncate text-left">{folder.name}</span>
          <span className="shrink-0 rounded bg-surface-overlay px-1 py-0.5 text-[10px] font-medium text-fg-subtle">{fc}</span>
        </button>
        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0 transition-all">
          <button type="button" title="Alt klasör ekle"
            onClick={() => { setAddTarget({ suiteId: folder.suite_id, parentFolderId: folder.id }); setOpen(true); }}
            className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-brand">
            <IcPlus/>
          </button>
          <button type="button" title="Yeniden adlandır"
            onClick={() => onRename({ type: "folder", id: folder.id, name: folder.name })}
            className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
            <IcPencil/>
          </button>
          <button type="button" title="Taşı"
            onClick={() => onMove({ folder })}
            className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-brand">
            <IcMove/>
          </button>
          <button type="button" title="Sil"
            onClick={() => onDelete({ type: "folder", id: folder.id, name: folder.name })}
            className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-danger-subtle hover:text-danger">
            <IcTrash/>
          </button>
        </div>
      </div>

      {open && (
        <div>
          {children.map(child => (
            <FolderNode key={child.id} folder={child} depth={depth + 1}
              allFolders={allFolders} cases={cases} suites={suites}
              selected={selected} onSelect={onSelect}
              addTarget={addTarget} setAddTarget={setAddTarget}
              onRename={onRename} onDelete={onDelete} onMove={onMove}
              folderName={folderName} setFolderName={setFolderName}
              onSaveFolder={onSaveFolder}/>
          ))}
          {isAdding && (
            <div style={{ marginLeft: (depth + 1) * 12 + 4 }}>
              <RepositoryEditorRow
                value={folderName}
                setValue={setFolderName}
                placeholder="Klasör adı"
                marker="F"
                onSave={() => { void onSaveFolder(folder.suite_id, folder.id); }}
                onCancel={() => { setAddTarget(null); setFolderName(""); }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SuiteTree({ suites, folders, cases, selected, onSelect, projectId }: {
  suites: TestSuite[]; folders: TestFolder[]; cases: TestCase[];
  selected: SelectedNode; onSelect: (n: SelectedNode) => void; projectId: string;
}) {
  const [expanded,       setExpanded]       = useState<Set<string>>(() => new Set(suites.map(s => s.id)));
  const [showSuiteInput, setShowSuiteInput] = useState(false);
  const [suiteName,      setSuiteName]      = useState("");
  const [addTarget,      setAddTarget]      = useState<AddFolderTarget | null>(null);
  const [folderName,     setFolderName]     = useState("");
  const [treeSearch,     setTreeSearch]     = useState("");
  const [renaming,       setRenaming]       = useState<RenameTarget | null>(null);
  const [renameDraft,    setRenameDraft]    = useState("");
  const [confirmDelete,  setConfirmDelete]  = useState<DeleteTarget | null>(null);
  const [moveFolder,     setMoveFolder]     = useState<MoveFolderState | null>(null);
  const [moveSuiteId,    setMoveSuiteId]    = useState("");

  const createSuite  = useCreateManagementSuite(projectId);
  const createFolder = useCreateManagementFolder(projectId);
  const updateSuite  = useUpdateManagementSuite(projectId);
  const deleteSuite  = useDeleteManagementSuite(projectId);
  const updateFolder = useUpdateManagementFolder(projectId);
  const deleteFolder = useDeleteManagementFolder(projectId);
  const totalActive  = cases.filter(c => !c.archived).length;

  const toggle = (id: string) => setExpanded(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const saveSuite = async () => {
    if (!suiteName.trim()) return;
    await createSuite.mutateAsync({ name: suiteName.trim() });
    setSuiteName(""); setShowSuiteInput(false);
  };

  const saveFolder = async (suiteId: string, parentFolderId?: string) => {
    if (!folderName.trim()) return;
    await createFolder.mutateAsync({
      suite_id: suiteId, name: folderName.trim(),
      path: slugify(folderName.trim()),
      ...(parentFolderId ? { parent_id: parentFolderId } : {}),
    } as Parameters<typeof createFolder.mutateAsync>[0]);
    setFolderName(""); setAddTarget(null);
  };

  const openRename = (target: RenameTarget) => { setRenaming(target); setRenameDraft(target.name); };

  const commitRename = async () => {
    if (!renaming || !renameDraft.trim()) return;
    if (renaming.type === "suite") {
      await updateSuite.mutateAsync({ suiteId: renaming.id, name: renameDraft.trim() });
    } else {
      await updateFolder.mutateAsync({ folderId: renaming.id, name: renameDraft.trim() });
    }
    setRenaming(null); setRenameDraft("");
  };

  const commitDelete = async () => {
    if (!confirmDelete) return;
    if (confirmDelete.type === "suite") {
      await deleteSuite.mutateAsync(confirmDelete.id);
      if (selected.type === "suite" && selected.id === confirmDelete.id) onSelect({ type: "all" });
    } else {
      await deleteFolder.mutateAsync(confirmDelete.id);
      if (selected.type === "folder" && selected.id === confirmDelete.id) onSelect({ type: "all" });
    }
    setConfirmDelete(null);
  };

  const commitMove = async () => {
    if (!moveFolder || !moveSuiteId) return;
    await updateFolder.mutateAsync({ folderId: moveFolder.folder.id, suite_id: moveSuiteId, parent_id: null } as Parameters<typeof updateFolder.mutateAsync>[0]);
    setMoveFolder(null); setMoveSuiteId("");
  };

  const visibleSuites = treeSearch
    ? suites.filter(s => s.name.toLowerCase().includes(treeSearch.toLowerCase()))
    : suites;

  return (
    <div className="flex h-full flex-col text-sm">
      {/* Search */}
      <div className="border-b border-border/70 px-3 py-2">
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 text-fg-muted shadow-xs">
          <IcSearch/>
          <input type="text" value={treeSearch} onChange={e => setTreeSearch(e.target.value)}
            placeholder="Suite ara…" className="flex-1 bg-transparent text-xs font-medium text-fg placeholder:text-fg-subtle outline-none"/>
          {treeSearch && <button type="button" onClick={() => setTreeSearch("")} className="text-fg-subtle transition-colors hover:text-fg"><IcClose/></button>}
        </div>
      </div>

      {/* All Cases */}
      <div className="px-2 pt-2">
        <button type="button" onClick={() => onSelect({ type: "all" })}
          className={cn("flex w-full items-center gap-2.5 rounded-xl px-3 py-2 transition-colors",
            selected.type === "all"
              ? "border border-brand/20 bg-brand-soft text-brand shadow-xs"
              : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
          <IcRepo/>
          <span className="flex-1 text-left text-xs font-semibold">Tüm Senaryolar</span>
          <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
            selected.type === "all" ? "bg-surface-raised text-brand" : "bg-surface-overlay text-fg-muted")}>{totalActive}</span>
        </button>
      </div>

      {/* Suites */}
      <div className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-2 pt-1">
        {visibleSuites.length === 0 && (
          <div className="px-3 py-8 text-center text-xs text-fg-muted">
            {treeSearch ? "Arama sonucu bulunamadı." : "Henüz test suite yok. \"+ Suite\" ile başlayın."}
          </div>
        )}
        {visibleSuites.map(suite => {
          const rootFolders  = folders.filter(f => f.suite_id === suite.id && !f.parent_id);
          const sc           = cases.filter(c => c.suite_id === suite.id && !c.archived).length;
          const isExp        = expanded.has(suite.id);
          const isSel        = selected.type === "suite" && selected.id === suite.id;
          const isAddingHere = addTarget?.suiteId === suite.id && !addTarget.parentFolderId;

          return (
            <div key={suite.id}>
              {/* Suite row */}
              <div className="group flex items-center gap-0.5">
                <button type="button" onClick={() => toggle(suite.id)}
                  className="flex h-6 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
                  <IcChevron open={isExp}/>
                </button>
                <button type="button" onClick={() => onSelect({ type: "suite", id: suite.id })}
                  className={cn("flex flex-1 min-w-0 items-center gap-2 rounded-xl px-2 py-1.5 transition-colors",
                    isSel ? "border border-brand/20 bg-brand-soft text-brand shadow-xs"
                           : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
                  <span className={cn("flex h-5 w-5 shrink-0 items-center justify-center rounded-md text-[9px] font-bold",
                    isSel ? "border border-brand/20 bg-surface-raised text-brand" : "bg-surface-overlay text-fg-muted")}>S</span>
                  <span className="flex-1 truncate text-left text-xs font-semibold">{suite.name}</span>
                  <span className="shrink-0 rounded bg-surface-overlay px-1 py-0.5 text-[10px] font-medium text-fg-subtle">{sc}</span>
                </button>
                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0 transition-all">
                  <button type="button" title="Klasör ekle"
                    onClick={() => { setAddTarget({ suiteId: suite.id }); setExpanded(p => new Set([...p, suite.id])); }}
                    className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-brand">
                    <IcPlus/>
                  </button>
                  <button type="button" title="Yeniden adlandır"
                    onClick={() => openRename({ type: "suite", id: suite.id, name: suite.name })}
                    className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
                    <IcPencil/>
                  </button>
                  <button type="button" title="Sil"
                    onClick={() => setConfirmDelete({ type: "suite", id: suite.id, name: suite.name })}
                    className="flex h-5 w-5 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-danger-subtle hover:text-danger">
                    <IcTrash/>
                  </button>
                </div>
              </div>

              {/* Folders tree */}
              {isExp && (
                <div className="ml-5 mt-0.5 space-y-0.5">
                  {rootFolders.map(folder => (
                    <FolderNode key={folder.id} folder={folder} depth={0}
                      allFolders={folders} cases={cases} suites={suites}
                      selected={selected} onSelect={onSelect}
                      addTarget={addTarget} setAddTarget={setAddTarget}
                      onRename={openRename}
                      onDelete={setConfirmDelete}
                      onMove={f => { setMoveFolder(f); setMoveSuiteId(f.folder.suite_id); }}
                      folderName={folderName} setFolderName={setFolderName}
                      onSaveFolder={saveFolder}/>
                  ))}
                  {isAddingHere && (
                    <RepositoryEditorRow
                      value={folderName}
                      setValue={setFolderName}
                      placeholder="Klasör adı"
                      marker="F"
                      onSave={() => { void saveFolder(suite.id); }}
                      onCancel={() => { setAddTarget(null); setFolderName(""); }}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}

        {showSuiteInput ? (
          <RepositoryEditorRow
            value={suiteName} setValue={setSuiteName} placeholder="Suite adı" marker="S"
            onSave={saveSuite} onCancel={() => { setShowSuiteInput(false); setSuiteName(""); }}/>
        ) : (
          <button type="button" onClick={() => setShowSuiteInput(true)}
            className="mt-1 flex w-full items-center gap-2 rounded-xl border border-dashed border-border bg-surface-raised/60 px-3 py-2 text-xs font-medium text-fg-muted transition-colors hover:border-brand/35 hover:bg-brand-soft/60 hover:text-brand">
            <IcPlus/> Yeni Suite
          </button>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-border/70 px-3 py-2">
        <div className="flex justify-between text-[10px] font-medium text-fg-subtle">
          <span>{suites.length} suite</span>
          <span>{folders.length} klasör</span>
          <span>{totalActive} case</span>
        </div>
      </div>

      {/* ── Rename Modal ── */}
      {renaming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setRenaming(null)}/>
          <div className="relative z-10 w-full max-w-sm rounded-2xl border border-slate-700/80 bg-slate-900 p-5 shadow-2xl">
            <h3 className="mb-3 text-sm font-semibold text-white">
              {renaming.type === "suite" ? "Suite" : "Klasör"} Yeniden Adlandır
            </h3>
            <input autoFocus type="text" value={renameDraft} onChange={e => setRenameDraft(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") commitRename(); if (e.key === "Escape") setRenaming(null); }}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-slate-600 transition-colors"/>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setRenaming(null)}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                İptal
              </button>
              <button type="button" onClick={commitRename}
                disabled={!renameDraft.trim() || updateSuite.isPending || updateFolder.isPending}
                className="rounded-xl bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
                Kaydet
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete Confirm Modal ── */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setConfirmDelete(null)}/>
          <div className="relative z-10 w-full max-w-sm rounded-2xl border border-slate-700/80 bg-slate-900 p-5 shadow-2xl">
            <h3 className="mb-1 text-sm font-semibold text-white">
              {confirmDelete.type === "suite" ? "Suite" : "Klasör"} Sil
            </h3>
            <p className="mb-4 text-xs text-slate-400">
              <span className="font-semibold text-white">"{confirmDelete.name}"</span>
              {confirmDelete.type === "suite"
                ? " suite'ini ve içindeki tüm klasörleri silmek istediğinize emin misiniz?"
                : " klasörünü silmek istediğinize emin misiniz?"}
            </p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setConfirmDelete(null)}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                İptal
              </button>
              <button type="button" onClick={commitDelete}
                disabled={deleteSuite.isPending || deleteFolder.isPending}
                className="rounded-xl bg-red-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-40 transition-colors">
                {deleteSuite.isPending || deleteFolder.isPending ? "Siliniyor…" : "Sil"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Move Folder Modal ── */}
      {moveFolder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMoveFolder(null)}/>
          <div className="relative z-10 w-full max-w-sm rounded-2xl border border-slate-700/80 bg-slate-900 p-5 shadow-2xl">
            <h3 className="mb-1 text-sm font-semibold text-white">Klasörü Taşı</h3>
            <p className="mb-3 text-xs text-slate-400">
              <span className="font-semibold text-white">"{moveFolder.folder.name}"</span> klasörünü hangi suite&apos;e taşımak istiyorsunuz?
            </p>
            <div className="max-h-48 overflow-y-auto space-y-1.5">
              {suites.filter(s => s.id !== moveFolder.folder.suite_id).map(s => (
                <button key={s.id} type="button" onClick={() => setMoveSuiteId(s.id)}
                  className={cn("flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs transition-colors border",
                    moveSuiteId === s.id
                      ? "bg-blue-500/10 text-blue-300 border-blue-500/20"
                      : "text-slate-300 hover:bg-slate-800 border-transparent")}>
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-slate-700 text-[9px] font-bold">S</span>
                  {s.name}
                </button>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={() => setMoveFolder(null)}
                className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors">
                İptal
              </button>
              <button type="button" onClick={commitMove}
                disabled={!moveSuiteId || updateFolder.isPending}
                className="rounded-xl bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
                {updateFolder.isPending ? "Taşınıyor…" : "Taşı"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Step Row (modal) ─────────────────────────────────────────────────────────

function StepRow({ step, index, onChange, onRemove }: {
  step: DraftStep; index: number;
  onChange: (n: DraftStep) => void; onRemove: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: step.id });
  return (
    <div ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.35 : 1 }}
      className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex items-center gap-2 mb-2">
        <button type="button" {...attributes} {...listeners}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-800 font-mono text-[10px] font-bold text-slate-400 cursor-grab active:cursor-grabbing touch-none">
          {index + 1}
        </button>
        <label className="ml-auto flex items-center gap-1.5 text-[10px] text-slate-500">
          <input type="checkbox" checked={step.is_required} onChange={e => onChange({ ...step, is_required: e.target.checked })} className="h-3 w-3 accent-blue-500 rounded"/>
          Zorunlu
        </label>
        <button type="button" onClick={onRemove} className="text-slate-700 hover:text-red-400 transition-colors"><IcClose/></button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <textarea value={step.action} onChange={e => onChange({ ...step, action: e.target.value })}
          placeholder="Aksiyon: Kullanıcı…" rows={2}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-slate-600 focus:outline-none resize-none"/>
        <textarea value={step.expected_result} onChange={e => onChange({ ...step, expected_result: e.target.value })}
          placeholder="Beklenen sonuç…" rows={2}
          className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-slate-600 focus:outline-none resize-none"/>
      </div>
      <input type="text" value={step.test_data} onChange={e => onChange({ ...step, test_data: e.target.value })}
        placeholder="Test data (opsiyonel)…"
        className="mt-2 w-full rounded-lg border border-slate-800/80 bg-slate-900/40 px-3 py-1.5 text-[11px] text-slate-400 placeholder-slate-700 focus:border-slate-700 focus:outline-none"/>
    </div>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

function DetailPanel({ tc, suites, folders, onClose, projectId, mgmtProjectId }: {
  tc: TestCase; suites: TestSuite[]; folders: TestFolder[];
  onClose: () => void; projectId: string; mgmtProjectId: string;
}) {
  const [tab, setTab] = useState<DetailTab>("overview");
  const [cloneMsg,      setCloneMsg]      = useState<string | null>(null);
  const [improveResult, setImproveResult] = useState<ImproveTestCaseResponse | null>(null);
  const clone   = useCloneManagementCase(mgmtProjectId);
  const improve = useImproveManagementCase(mgmtProjectId);

  const suite  = suites.find(s => s.id === tc.suite_id);
  const folder = folders.find(f => f.id === tc.folder_id);

  const versionsQuery     = useManagementCaseVersions(
    tab === "history"      ? mgmtProjectId : undefined,
    tab === "history"      ? tc.id : undefined,
  );
  const requirementsQuery = useManagementRequirements(
    tab === "requirements" ? mgmtProjectId : undefined,
  );

  const versions = versionsQuery.data ?? [];
  const caseReqs = (requirementsQuery.data ?? []).filter(r => r.case_id === tc.id);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-start gap-3 border-b border-slate-800 px-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[10px] text-slate-500 select-all">{tc.case_key}</span>
            <PBadge p={tc.priority}/>
            <SDot s={tc.status}/>
            {tc.last_run_status && <RunBadge s={tc.last_run_status}/>}
          </div>
          <h2 className="mt-1.5 text-sm font-semibold text-white leading-snug">{tc.title}</h2>
        </div>
        <button type="button" onClick={onClose}
          className="shrink-0 rounded-lg p-1.5 text-slate-600 hover:bg-slate-800 hover:text-slate-200 transition-colors">
          <IcClose/>
        </button>
      </div>

      {/* Actions */}
      <div className="flex flex-wrap gap-1.5 border-b border-slate-800 px-4 py-2">
        <Link href={`/p/${projectId}/management/cases/${tc.id}`}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white transition-colors">
          <IcEdit/> Düzenle
        </Link>
        <button type="button" disabled={clone.isPending}
          onClick={async () => {
            const cloned = await clone.mutateAsync({ caseId: tc.id });
            setCloneMsg(cloned.case_key ?? cloned.title);
            setTimeout(() => setCloneMsg(null), 3000);
          }}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-40 transition-colors">
          <IcCopy/> {clone.isPending ? "Kopyalanıyor…" : "Kopyala"}
        </button>
        {cloneMsg && (
          <span className="text-[10px] text-emerald-400">✓ {cloneMsg}</span>
        )}
        <button type="button" disabled={improve.isPending}
          onClick={async () => {
            const res = await improve.mutateAsync({ caseId: tc.id, focus: "all" });
            setImproveResult(res);
          }}
          className="ml-auto flex items-center gap-1.5 rounded-lg border border-blue-500/20 bg-slate-800/60 px-2.5 py-1.5 text-xs text-blue-400 hover:bg-blue-500/8 disabled:opacity-40 transition-colors">
          <IcSparkle/> {improve.isPending ? "İyileştiriliyor…" : "AI İyileştir"}
        </button>
      </div>

      {/* AI Improve result */}
      {improveResult && (
        <div className="border-b border-slate-800 bg-blue-500/5 px-4 py-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-400">AI Önerileri</p>
            <button type="button" onClick={() => setImproveResult(null)} className="text-[10px] text-slate-600 hover:text-slate-300">✕</button>
          </div>
          {improveResult.suggestions.length > 0 && (
            <ul className="space-y-0.5">
              {improveResult.suggestions.map((s, i) => (
                <li key={i} className="text-[11px] text-slate-400">• {s}</li>
              ))}
            </ul>
          )}
          {improveResult.title && (
            <p className="text-[11px] text-slate-300"><span className="text-slate-500">Önerilen başlık:</span> {improveResult.title}</p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 px-2 overflow-x-auto">
        {([
          { key: "overview"      as const, label: "Genel" },
          { key: "steps"         as const, label: `Adımlar (${tc.steps?.length ?? 0})` },
          { key: "history"       as const, label: "Geçmiş" },
          { key: "requirements"  as const, label: `Gereksinimler (${caseReqs.length})` },
        ]).map(t => (
          <button key={t.key} type="button" onClick={() => setTab(t.key)}
            className={cn("shrink-0 px-3 py-2.5 text-xs font-medium border-b-2 -mb-px transition-colors",
              tab === t.key ? "border-blue-500 text-blue-400" : "border-transparent text-slate-500 hover:text-slate-300")}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* OVERVIEW */}
        {tab === "overview" && (
          <>
            <div className="grid grid-cols-2 gap-2">
              {([
                ["Suite",     suite?.name ?? "—"],
                ["Folder",    folder?.name ?? "—"],
                ["Tür",       tc.type],
                ["Severity",  tc.severity],
                ["Otomasyon", tc.automation_status],
                ["Versiyon",  `v${tc.current_version}`],
              ] as [string, string][]).map(([k, v]) => (
                <div key={k} className="rounded-lg bg-slate-800/40 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wide text-slate-500">{k}</p>
                  <p className="mt-0.5 truncate text-xs font-medium text-slate-200">{v}</p>
                </div>
              ))}
            </div>
            {tc.objective && (
              <div>
                <p className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Amaç</p>
                <p className="text-xs text-slate-300 leading-relaxed">{tc.objective}</p>
              </div>
            )}
            {tc.preconditions && (
              <div>
                <p className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Ön Koşullar</p>
                <div className="rounded-lg border border-slate-700/60 bg-slate-800/40 px-3 py-2">
                  <p className="text-xs text-slate-300 leading-relaxed">{tc.preconditions}</p>
                </div>
              </div>
            )}
            {tc.tags && tc.tags.length > 0 && (
              <div>
                <p className="mb-1.5 text-[10px] uppercase tracking-wide text-slate-500">Etiketler</p>
                <div className="flex flex-wrap gap-1.5">
                  {tc.tags.map(t => (
                    <span key={t} className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-[10px] text-slate-300">{t}</span>
                  ))}
                </div>
              </div>
            )}
            {tc.last_run_at && (
              <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/30 px-3 py-2">
                {tc.last_run_status && <RunBadge s={tc.last_run_status}/>}
                <span className="text-[10px] text-slate-400">{new Date(tc.last_run_at).toLocaleString("tr-TR")}</span>
              </div>
            )}
          </>
        )}

        {/* STEPS */}
        {tab === "steps" && (
          <div className="space-y-2">
            {!tc.steps?.length ? (
              <div className="rounded-xl border border-dashed border-slate-700 py-10 text-center">
                <p className="text-xs text-slate-500">Henüz adım eklenmemiş.</p>
                <Link href={`/p/${projectId}/management/cases/${tc.id}`} className="mt-2 inline-block text-xs text-blue-400 hover:underline">Adım ekle →</Link>
              </div>
            ) : tc.steps.map(step => (
              <div key={step.id} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-800 font-mono text-[10px] font-bold text-slate-400">{step.step_no}</span>
                  {!step.is_required && <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500">opsiyonel</span>}
                </div>
                <p className="text-xs text-slate-200 leading-relaxed">{step.action}</p>
                <div className="mt-2 rounded-lg border border-slate-800 bg-slate-800/40 px-2.5 py-1.5">
                  <p className="mb-0.5 text-[10px] font-medium text-slate-300">Beklenen</p>
                  <p className="text-xs text-slate-300">{step.expected_result}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* HISTORY */}
        {tab === "history" && (
          <div className="space-y-2">
            {versionsQuery.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-12 rounded-lg bg-slate-800/60 animate-pulse"/>)
            ) : versions.length === 0 ? (
              <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-500/8 font-mono text-[10px] font-bold text-blue-400">v{tc.current_version}</span>
                <div>
                  <p className="text-xs font-medium text-slate-200">Güncel versiyon</p>
                  <p className="text-[10px] text-slate-500">{tc.updated_at ? new Date(tc.updated_at).toLocaleString("tr-TR") : "—"}</p>
                </div>
              </div>
            ) : versions.map(v => (
              <div key={v.id} className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-800 font-mono text-[10px] font-bold text-slate-400">v{v.version_no}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-slate-200">{v.change_summary ?? "Güncellendi"}</p>
                  {v.changed_fields.length > 0 && <p className="text-[10px] text-slate-500">{v.changed_fields.join(", ")} değişti</p>}
                  <p className="text-[10px] text-slate-600">{new Date(v.created_at).toLocaleString("tr-TR")}</p>
                </div>
              </div>
            ))}
            <Link href={`/p/${projectId}/management/cases/${tc.id}`}
              className="block py-2 text-center text-xs text-blue-400 hover:underline">
              Tüm versiyonları gör →
            </Link>
          </div>
        )}

        {/* REQUIREMENTS */}
        {tab === "requirements" && (
          <div className="space-y-2">
            {requirementsQuery.isLoading ? (
              Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-10 rounded-lg bg-slate-800/60 animate-pulse"/>)
            ) : caseReqs.length === 0 ? (
              <div className="flex flex-col items-center rounded-xl border border-dashed border-slate-700 py-10 text-center gap-2">
                <svg className="h-8 w-8 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
                <p className="text-xs text-slate-500">Bu case için bağlı gereksinim yok.</p>
                <Link href={`/p/${projectId}/management/requirements`} className="text-xs text-blue-400 hover:underline">Gereksinim bağla →</Link>
              </div>
            ) : caseReqs.map(req => (
              <div key={req.id} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2.5">
                <span className="font-mono text-[10px] text-slate-500 shrink-0">{req.external_key}</span>
                <p className="flex-1 min-w-0 truncate text-xs text-slate-200">{req.title_snapshot}</p>
                <span className={cn("shrink-0 text-[10px]", req.coverage_status === "covered" ? "text-emerald-400" : "text-slate-500")}>
                  {req.coverage_status}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── New Case Modal ───────────────────────────────────────────────────────────

function NewCaseModal({ projectId, suites, folders, defSuiteId, defFolderId, onClose, onDone }: {
  projectId: string; suites: TestSuite[]; folders: TestFolder[];
  defSuiteId?: string; defFolderId?: string;
  onClose: () => void; onDone: (tc: TestCase) => void;
}) {
  const createCase  = useCreateManagementCase(projectId);
  const generateAI  = useGenerateTestCases(projectId);
  const [title,         setTitle]         = useState("");
  const [objective,     setObjective]     = useState("");
  const [preconditions, setPreconditions] = useState("");
  const [suiteId,       setSuiteId]       = useState(defSuiteId ?? "");
  const [folderId,      setFolderId]      = useState(defFolderId ?? "");
  const [priority,      setPriority]      = useState("P1");
  const [severity,      setSeverity]      = useState("major");
  const [type,          setType]          = useState("manual");
  const [status,        setStatus]        = useState("draft");
  const [tagsText,      setTagsText]      = useState("");
  const [steps,         setSteps]         = useState<DraftStep[]>([makeStep(), makeStep()]);
  const [err,           setErr]           = useState("");
  const [showAI,        setShowAI]        = useState(false);
  const [aiPrompt,      setAiPrompt]      = useState("");
  const [aiResults,     setAiResults]     = useState<GeneratedCase[]>([]);

  const avFolders = folders.filter(f => !suiteId || f.suite_id === suiteId);
  const sensors   = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const onStepDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    setSteps(c => { const oi = c.findIndex(s => s.id === active.id), ni = c.findIndex(s => s.id === over.id); return arrayMove(c, oi, ni); });
  };

  const save = async () => {
    if (!title.trim()) { setErr("Başlık zorunlu."); return; }
    setErr("");
    try {
      const tc = await createCase.mutateAsync({
        title: title.trim(), objective: objective.trim() || null,
        preconditions: preconditions.trim() || null,
        suite_id: suiteId || null, folder_id: folderId || null,
        priority, severity, type, status, source_type: "manual",
        tags: tagsText.split(",").map(t => t.trim()).filter(Boolean),
        steps: steps.filter(s => s.action.trim() || s.expected_result.trim()).map((s, i) => ({
          step_no: i + 1, action: s.action.trim(), expected_result: s.expected_result.trim(),
          test_data: s.test_data.trim() ? { value: s.test_data.trim() } : {},
          is_required: s.is_required,
        })),
      });
      onDone(tc);
    } catch { setErr("Kaydedilemedi. Alanları kontrol edin."); }
  };

  const SEL = "w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-white focus:border-slate-600 focus:outline-none transition-colors";
  const TXT = "w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-slate-600 focus:outline-none resize-none transition-colors";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose}/>
      <div className="relative z-10 flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-700/80 bg-slate-900 shadow-2xl shadow-black/60">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold text-white">Yeni Test Senaryosu</h2>
            <p className="mt-0.5 text-[10px] text-slate-500">Manuel test case oluştur</p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setShowAI(v => !v)}
              className={cn("flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs transition-colors",
                showAI
                  ? "border-blue-500/40 bg-blue-500/10 text-blue-400"
                  : "border-blue-500/20 bg-slate-800/60 text-blue-400 hover:bg-blue-500/8")}>
              <IcSparkle/> AI ile Üret
            </button>
            <button type="button" onClick={onClose}
              className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-800 hover:text-slate-200 transition-colors">
              <IcClose/>
            </button>
          </div>
        </div>

        {/* AI Panel */}
        {showAI && (
          <div className="border-b border-slate-800 bg-slate-900/60 px-6 py-4 space-y-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-400">AI Test Üretimi</p>
            <textarea
              autoFocus
              value={aiPrompt}
              onChange={e => setAiPrompt(e.target.value)}
              rows={2}
              placeholder="Ne test etmek istiyorsunuz? (ör: Kullanıcı girişi, ödeme akışı, şifre sıfırlama…)"
              className="w-full resize-none rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-slate-600 focus:outline-none"
            />
            <div className="flex items-center gap-2">
              <button type="button"
                onClick={async () => {
                  if (!aiPrompt.trim()) return;
                  const res = await generateAI.mutateAsync({ prompt: aiPrompt.trim(), count: 3, suite_id: suiteId || null, folder_id: folderId || null, save: false });
                  setAiResults(res.cases);
                }}
                disabled={!aiPrompt.trim() || generateAI.isPending}
                className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-1.5 text-[10px] font-semibold text-white hover:bg-blue-500 disabled:opacity-40">
                {generateAI.isPending ? "Üretiliyor…" : <><IcSparkle/> Üret (3 senaryo)</>}
              </button>
            </div>
            {aiResults.length > 0 && (
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {aiResults.map((gc, i) => (
                  <button key={i} type="button"
                    onClick={() => {
                      if (!title) setTitle(gc.title);
                      if (!objective) setObjective(gc.objective);
                      setPriority(gc.priority);
                      if (gc.tags.length) setTagsText(gc.tags.join(", "));
                      if (gc.steps.length) setSteps(gc.steps.map(s => makeStep({ action: s.action, expected_result: s.expected_result, is_required: s.is_required })));
                      setShowAI(false);
                    }}
                    className="flex w-full items-start gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-left hover:border-blue-500/30 transition-colors">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-700 text-[9px] font-bold text-slate-300">{i+1}</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-slate-200 line-clamp-1">{gc.title}</p>
                      <p className="text-[10px] text-slate-500">{gc.steps.length} adım · {gc.priority}</p>
                    </div>
                    <span className="shrink-0 text-[10px] text-blue-400">Uygula →</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          <input autoFocus={!showAI} type="text" value={title} onChange={e => setTitle(e.target.value)}
            placeholder="Senaryo başlığı *"
            className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-slate-600 focus:outline-none transition-colors"/>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className={SEL}>
                {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Severity</label>
              <select value={severity} onChange={e => setSeverity(e.target.value)} className={SEL}>
                {SEVERITY_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Tür</label>
              <select value={type} onChange={e => setType(e.target.value)} className={SEL}>
                {TYPE_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Durum</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className={SEL}>
                <option value="draft">Taslak</option>
                <option value="active">Aktif</option>
                <option value="review">Review</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Suite</label>
              <select value={suiteId} onChange={e => { setSuiteId(e.target.value); setFolderId(""); }} className={SEL}>
                <option value="">Suite seç</option>
                {suites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Folder</label>
              <select value={folderId} onChange={e => setFolderId(e.target.value)} className={SEL}>
                <option value="">Folder seç</option>
                {avFolders.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Amaç</label>
              <textarea value={objective} onChange={e => setObjective(e.target.value)} rows={3} placeholder="Bu senaryonun amacı…" className={TXT}/>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Ön Koşullar</label>
              <textarea value={preconditions} onChange={e => setPreconditions(e.target.value)} rows={3} placeholder="Testin başlaması için gerekli koşullar…" className={TXT}/>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wide text-slate-500">Etiketler <span className="normal-case text-slate-600">(virgülle ayır)</span></label>
            <input type="text" value={tagsText} onChange={e => setTagsText(e.target.value)}
              placeholder="smoke, regression, login…"
              className="w-full rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs text-white placeholder-slate-600 focus:border-slate-600 focus:outline-none"/>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-[10px] font-medium uppercase tracking-wide text-slate-500">Test Adımları</label>
              <button type="button" onClick={() => setSteps(s => [...s, makeStep()])}
                className="flex items-center gap-1 rounded-lg border border-slate-700 px-2 py-1 text-[10px] text-slate-400 hover:text-slate-300 transition-colors">
                <IcPlus/> Adım Ekle
              </button>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onStepDragEnd}>
              <SortableContext items={steps.map(s => s.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-2">
                  {steps.map((step, i) => (
                    <StepRow key={step.id} step={step} index={i}
                      onChange={n => setSteps(c => c.map(s => s.id === step.id ? n : s))}
                      onRemove={() => setSteps(c => c.length > 1 ? c.filter(s => s.id !== step.id) : c)}/>
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          </div>

          {err && <p className="text-xs text-red-400">{err}</p>}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 px-6 py-4">
          <button type="button" onClick={onClose}
            className="rounded-xl border border-slate-700 px-4 py-2 text-xs text-slate-400 hover:border-slate-600 hover:text-slate-200 transition-colors">
            İptal
          </button>
          <button type="button" onClick={save} disabled={!title.trim() || createCase.isPending}
            className="rounded-xl bg-blue-600 px-5 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:opacity-40 transition-colors">
            {createCase.isPending ? "Kaydediliyor…" : "Kaydet"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Case Table Row ───────────────────────────────────────────────────────────

function CaseTableRow({ tc, isSelected, onSelect, isChecked, onCheck, projectId }: {
  tc: TestCase; isSelected: boolean; onSelect: () => void;
  isChecked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tc.id });

  return (
    <tr ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.3 : 1 }}
      onClick={onSelect}
      className={cn(
        "group border-b border-slate-800/50 cursor-pointer transition-all duration-100",
        isSelected
          ? "bg-blue-500/5 border-l-2 border-l-blue-500/50"
          : "hover:bg-slate-800/30 border-l-2 border-l-transparent",
      )}>
      <td className="hidden w-5 pl-1 sm:table-cell">
        <button type="button" {...attributes} {...listeners}
          className="invisible group-hover:visible cursor-grab active:cursor-grabbing touch-none text-slate-700 hover:text-slate-500">
          <IcGrip/>
        </button>
      </td>
      <td className="w-8 px-2">
        <button type="button" onClick={onCheck}
          className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
            isChecked ? "bg-blue-600 border-blue-600" : "border-slate-700 hover:border-slate-500")}>
          {isChecked && <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
        </button>
      </td>
      <td className="w-[5.5rem] px-3 py-3">
        <span className="select-all font-mono text-[10px] text-slate-500">{tc.case_key}</span>
      </td>
      <td className="px-3 py-3">
        <p className="text-xs font-medium text-slate-200 line-clamp-1 group-hover:text-white transition-colors">{tc.title}</p>
        {tc.tags && tc.tags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {tc.tags.slice(0, 3).map(t => <span key={t} className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500">{t}</span>)}
            {tc.tags.length > 3 && <span className="text-[10px] text-slate-600">+{tc.tags.length - 3}</span>}
          </div>
        )}
      </td>
      <td className="w-16 px-3 py-3"><PBadge p={tc.priority}/></td>
      <td className="hidden w-24 px-3 py-3 lg:table-cell">
        <span className="rounded bg-slate-800/70 px-1.5 py-0.5 text-[10px] text-slate-400">{tc.type}</span>
      </td>
      <td className="hidden w-20 px-3 py-3 md:table-cell"><SDot s={tc.status}/></td>
      <td className="hidden w-24 px-3 py-3 lg:table-cell">
        {tc.last_run_status ? <RunBadge s={tc.last_run_status}/> : <span className="text-[10px] text-slate-700">—</span>}
      </td>
      <td className="hidden w-14 px-3 py-3 text-[10px] tabular-nums text-slate-600 xl:table-cell">
        {tc.steps?.length ?? 0} adım
      </td>
      <td className="hidden w-20 px-3 py-3 xl:table-cell">
        <span className="text-[10px] text-slate-600">
          {tc.updated_at ? new Date(tc.updated_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" }) : "—"}
        </span>
      </td>
      <td className="w-12 px-2">
        <Link href={`/p/${projectId}/management/cases/${tc.id}`} onClick={e => e.stopPropagation()}
          className="invisible group-hover:visible rounded-lg p-1.5 text-slate-600 hover:bg-slate-700 hover:text-slate-200 transition-all inline-flex">
          <IcEdit/>
        </Link>
      </td>
    </tr>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <div className="space-y-px pt-1">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-slate-800/40 px-4 py-3"
          style={{ opacity: Math.max(0.15, 1 - i * 0.12) }}>
          <div className="h-4 w-4 shrink-0 rounded bg-slate-800 animate-pulse"/>
          <div className="h-3 w-16 rounded bg-slate-800 animate-pulse"/>
          <div className="h-3 flex-1 max-w-sm rounded bg-slate-800 animate-pulse"/>
          <div className="h-5 w-8 rounded bg-slate-800 animate-pulse"/>
          <div className="h-5 w-16 rounded bg-slate-800 animate-pulse"/>
        </div>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ScenariosPage() {
  const projectId = useRouteParam("projectId") ?? "";

  const ensureProject = useEnsureManagementProject(projectId || undefined);
  const [mgmtProjectId, setMgmtProjectId] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    ensureProject.mutateAsync()
      .then(p => { setMgmtProjectId(p.id); })
      .catch(() => setMgmtProjectId(projectId));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const effectivePid = mgmtProjectId ?? projectId;
  const repoQuery    = useManagementRepository(effectivePid || undefined);
  const moveCase      = useMoveManagementCase(effectivePid || "");
  const bulkUpdateCases = useBulkUpdateCases(effectivePid || "");

  const suites   = repoQuery.data?.suites  ?? [];
  const folders  = repoQuery.data?.folders ?? [];
  const allCases = repoQuery.data?.cases   ?? [];
  const active   = allCases.filter(c => !c.archived);

  const [selectedNode,   setSelectedNode]   = useState<SelectedNode>({ type: "all" });
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [checkedIds,     setCheckedIds]     = useState<Set<string>>(new Set());
  const [showModal,      setShowModal]      = useState(false);
  const [search,         setSearch]         = useState("");
  const [statusF,        setStatusF]        = useState("");
  const [priorityF,      setPriorityF]      = useState("");
  const [typeF,          setTypeF]          = useState("");
  const [runF,           setRunF]           = useState("");
  const [tagF,           setTagF]           = useState("");
  const [sortF,          setSortF]          = useState<"title" | "updated_at" | "last_run_at" | "priority">("title");
  const [sortDir,        setSortDir]        = useState<"asc" | "desc">("asc");
  const [draggingId,     setDraggingId]     = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const nodeCases = useMemo(() => {
    switch (selectedNode.type) {
      case "suite":  return active.filter(c => c.suite_id === selectedNode.id);
      case "folder": return active.filter(c => c.folder_id === selectedNode.id);
      default:       return active;
    }
  }, [active, selectedNode]);

  // Collect all unique tags from cases for the tag dropdown
  const allTags = useMemo(() => {
    const set = new Set<string>();
    nodeCases.forEach(c => (c.tags ?? []).forEach(t => set.add(t)));
    return [...set].sort();
  }, [nodeCases]);

  const PRIORITY_ORDER: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3 };

  const filtered = useMemo(() => {
    let r = nodeCases;
    const q = search.trim().toLowerCase();
    if (q) r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q) || (c.tags ?? []).some(t => t.toLowerCase().includes(q)));
    if (statusF)   r = r.filter(c => c.status === statusF);
    if (priorityF) r = r.filter(c => c.priority === priorityF);
    if (typeF)     r = r.filter(c => c.type === typeF);
    if (runF)      r = r.filter(c => (c.last_run_status ?? "not_run") === runF);
    if (tagF)      r = r.filter(c => (c.tags ?? []).includes(tagF));

    // Sort
    r = [...r].sort((a, b) => {
      let cmp = 0;
      if (sortF === "title") {
        cmp = a.title.localeCompare(b.title, "tr");
      } else if (sortF === "updated_at") {
        cmp = (a.updated_at ?? "").localeCompare(b.updated_at ?? "");
      } else if (sortF === "last_run_at") {
        cmp = (a.last_run_at ?? "").localeCompare(b.last_run_at ?? "");
      } else if (sortF === "priority") {
        cmp = (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return r;
  }, [nodeCases, search, statusF, priorityF, typeF, runF, tagF, sortF, sortDir]);

  const hasFilter    = !!(search || statusF || priorityF || typeF || runF || tagF);
  const selectedCase = selectedCaseId ? active.find(c => c.id === selectedCaseId) : null;
  const allChecked   = filtered.length > 0 && filtered.every(c => checkedIds.has(c.id));
  const toggleAll    = () => allChecked ? setCheckedIds(new Set()) : setCheckedIds(new Set(filtered.map(c => c.id)));
  const toggleOne    = (e: React.MouseEvent, id: string) => { e.stopPropagation(); setCheckedIds(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; }); };
  const clearFilters = () => { setSearch(""); setStatusF(""); setPriorityF(""); setTypeF(""); setRunF(""); setTagF(""); setSortF("title"); setSortDir("asc"); };

  const stats = useMemo(() => ({
    total:   nodeCases.length,
    failed:  nodeCases.filter(c => c.last_run_status === "failed").length,
    blocked: nodeCases.filter(c => c.last_run_status === "blocked").length,
    passed:  nodeCases.filter(c => c.last_run_status === "passed").length,
  }), [nodeCases]);

  const defSuiteId  = selectedNode.type === "suite"  ? selectedNode.id : selectedNode.type === "folder" ? selectedNode.suiteId : undefined;
  const defFolderId = selectedNode.type === "folder" ? selectedNode.id : undefined;

  const handleDragEnd = (e: DragEndEvent) => {
    setDraggingId(null);
    // DnD reorder is visual only — move API not available in this version
    const { active: drag, over } = e;
    if (!over || drag.id === over.id) return;
    // No-op: maintain local order without mutating server
  };

  const loading  = repoQuery.isLoading || (!mgmtProjectId && !repoQuery.data);
  const SEL      = "rounded-xl border border-border bg-surface-raised px-2.5 py-1.5 text-[10px] font-medium text-fg-muted outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15";
  const nodeName = selectedNode.type === "all"    ? "Tüm Senaryolar"
                 : selectedNode.type === "suite"  ? (suites.find(s => s.id === selectedNode.id)?.name ?? "Suite")
                 : (folders.find(f => f.id === selectedNode.id)?.name ?? "Folder");

  return (
    <div className="flex bg-surface-base" style={{ height: "calc(100vh - 48px)" }}>

      {/* LEFT: Suite Tree */}
      <aside className="hidden w-56 flex-none flex-col overflow-hidden border-r border-border bg-surface-raised md:flex">
        <div className="border-b border-border/70 px-4 py-2.5">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Test Repository</span>
        </div>
        {loading ? (
          <div className="flex-1 space-y-1 p-3">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="h-7 animate-pulse rounded-lg bg-surface-overlay" style={{ opacity: Math.max(0.25, 1 - i * 0.12) }}/>
            ))}
          </div>
        ) : (
          <SuiteTree suites={suites} folders={folders} cases={active} selected={selectedNode} onSelect={setSelectedNode} projectId={effectivePid}/>
        )}
      </aside>

      {/* CENTER: Case Table */}
      <div className={cn("flex flex-col flex-1 min-w-0 overflow-hidden", selectedCase ? "hidden xl:flex" : "flex")}>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-raised px-4 py-2.5 shadow-xs">
          <div className="flex items-center gap-2 min-w-0">
            <span className="truncate text-xs font-semibold text-fg">{nodeName}</span>
            <div className="hidden items-center gap-1.5 sm:flex">
              {stats.total   > 0 && <span className="rounded-full bg-surface-overlay px-2 py-0.5 text-[10px] font-semibold text-fg-muted">{stats.total}</span>}
              {stats.failed  > 0 && <span className="rounded-full bg-danger-subtle px-2 py-0.5 text-[10px] font-semibold text-danger">{stats.failed} fail</span>}
              {stats.blocked > 0 && <span className="rounded-full bg-warning-subtle px-2 py-0.5 text-[10px] font-semibold text-warning">{stats.blocked} blocked</span>}
              {stats.passed  > 0 && <span className="rounded-full bg-success-subtle px-2 py-0.5 text-[10px] font-semibold text-success">{stats.passed} passed</span>}
            </div>
          </div>
          <div className="flex-1"/>
          <div className="flex w-40 items-center gap-1.5 rounded-xl border border-border bg-surface-raised px-2.5 py-1.5 text-fg-muted shadow-xs sm:w-56">
            <IcSearch/>
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Ara…"
              className="min-w-0 flex-1 bg-transparent text-[10px] font-medium text-fg placeholder:text-fg-subtle outline-none"/>
            {search && <button type="button" onClick={() => setSearch("")} className="text-fg-subtle hover:text-fg"><IcClose/></button>}
          </div>
          <select value={statusF}   onChange={e => setStatusF(e.target.value)}   className={SEL}>
            <option value="">Durum</option><option value="active">Aktif</option>
            <option value="draft">Taslak</option><option value="review">Review</option>
          </select>
          <select value={priorityF} onChange={e => setPriorityF(e.target.value)} className={SEL}>
            <option value="">Priority</option>
            {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
          <select value={typeF} onChange={e => setTypeF(e.target.value)} className={cn(SEL, "hidden lg:block")}>
            <option value="">Tür</option>
            {TYPE_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
          <select value={runF} onChange={e => setRunF(e.target.value)} className={cn(SEL, "hidden lg:block")}>
            <option value="">Koşum</option>
            {Object.entries(RUN_CFG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          {allTags.length > 0 && (
            <select value={tagF} onChange={e => setTagF(e.target.value)} className={cn(SEL, "hidden xl:block")}>
              <option value="">Etiket</option>
              {allTags.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          <div className="hidden items-center gap-0.5 xl:flex">
            <select
              value={sortF}
              onChange={e => setSortF(e.target.value as typeof sortF)}
              className={SEL}
            >
              <option value="title">Ad</option>
              <option value="updated_at">Tarih</option>
              <option value="last_run_at">Son Koşum</option>
              <option value="priority">Öncelik</option>
            </select>
            <button
              type="button"
              title={sortDir === "asc" ? "Artan sıralama" : "Azalan sıralama"}
              onClick={() => setSortDir(d => d === "asc" ? "desc" : "asc")}
              className="flex h-[30px] w-[30px] items-center justify-center rounded-xl border border-border bg-surface-raised text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg"
            >
              {sortDir === "asc" ? (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12"/></svg>
              ) : (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4"/></svg>
              )}
            </button>
          </div>
          {hasFilter && (
            <button type="button" onClick={clearFilters}
              className="rounded-xl border border-danger/20 px-2 py-1.5 text-[10px] font-semibold text-danger transition-colors hover:bg-danger-subtle">
              Temizle
            </button>
          )}
          <button type="button" onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 rounded-xl bg-brand px-3 py-1.5 text-xs font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
            <IcPlus/> Yeni Senaryo
          </button>
        </div>

        {/* Bulk actions */}
        {checkedIds.size > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-b border-brand/15 bg-brand-soft/70 px-4 py-1.5">
            <span className="text-[10px] font-semibold text-brand">{checkedIds.size} seçili</span>
            {["Aktife Al","Arşivle"].map(lbl => (
              <button key={lbl} type="button"
                className={cn("rounded-lg border px-2.5 py-1 text-[10px] transition-colors",
                  lbl === "Arşivle" ? "border-danger/20 text-danger hover:bg-danger-subtle"
                                   : "border-border bg-surface-raised text-fg-muted hover:border-brand/25 hover:text-fg")}>
                {lbl}
              </button>
            ))}
            {/* Bulk priority */}
            <select onChange={async e => {
              if (!e.target.value) return;
              await bulkUpdateCases.mutateAsync({ case_ids: [...checkedIds], priority: e.target.value });
              setCheckedIds(new Set());
              e.target.value = "";
            }} className="rounded-lg border border-border bg-surface-raised px-2 py-1 text-[10px] text-fg-muted outline-none">
              <option value="">Öncelik →</option>
              {["P0","P1","P2","P3"].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            {/* Bulk move */}
            <select onChange={async e => {
              if (!e.target.value) return;
              const [suiteId, folderId] = e.target.value.split("|");
              for (const id of checkedIds) {
                await moveCase.mutateAsync({ caseId: id, suite_id: suiteId || null, folder_id: folderId || null });
              }
              setCheckedIds(new Set());
              e.target.value = "";
            }} className="rounded-lg border border-border bg-surface-raised px-2 py-1 text-[10px] text-fg-muted outline-none">
              <option value="">Taşı →</option>
              {suites.map(s => (
                <optgroup key={s.id} label={s.name}>
                  <option value={`${s.id}|`}>{s.name} (kök)</option>
                  {folders.filter(f => f.suite_id === s.id && !f.parent_id).map(f => (
                    <option key={f.id} value={`${s.id}|${f.id}`}>&nbsp;&nbsp;{f.name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
            <button type="button" onClick={() => setCheckedIds(new Set())} className="ml-auto text-[10px] font-medium text-fg-subtle hover:text-fg">Temizle</button>
          </div>
        )}

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? <TableSkeleton/> : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
              {hasFilter ? (
                <>
                  <svg className="mb-4 h-14 w-14 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}><circle cx="11" cy="11" r="8"/><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35"/></svg>
                  <h3 className="text-sm font-semibold text-fg">Senaryo bulunamadı</h3>
                  <p className="mt-1 text-xs text-fg-muted">Filtre veya arama terimini değiştirin</p>
                  <button type="button" onClick={clearFilters} className="mt-4 rounded-xl border border-border bg-surface-raised px-4 py-2 text-xs font-medium text-fg-muted transition-colors hover:bg-surface-overlay hover:text-fg">Filtreleri Temizle</button>
                </>
              ) : (
                <>
                  <div className="relative mb-6 flex items-center justify-center">
                    <svg width="200" height="140" viewBox="0 0 200 140" className="opacity-[0.06]" fill="none">
                      <circle cx="100" cy="20" r="10" stroke="#94a3b8" strokeWidth="1.5"/>
                      <line x1="100" y1="30" x2="60" y2="55" stroke="#94a3b8" strokeWidth="1"/>
                      <line x1="100" y1="30" x2="100" y2="55" stroke="#94a3b8" strokeWidth="1"/>
                      <line x1="100" y1="30" x2="140" y2="55" stroke="#94a3b8" strokeWidth="1"/>
                      <circle cx="60" cy="65" r="8" stroke="#64748b" strokeWidth="1.5"/>
                      <circle cx="100" cy="65" r="8" stroke="#64748b" strokeWidth="1.5"/>
                      <circle cx="140" cy="65" r="8" stroke="#64748b" strokeWidth="1.5"/>
                      <line x1="60" y1="73" x2="40" y2="95" stroke="#64748b" strokeWidth="1"/>
                      <line x1="60" y1="73" x2="80" y2="95" stroke="#64748b" strokeWidth="1"/>
                      <line x1="140" y1="73" x2="120" y2="95" stroke="#64748b" strokeWidth="1"/>
                      <line x1="140" y1="73" x2="160" y2="95" stroke="#64748b" strokeWidth="1"/>
                      <circle cx="40" cy="105" r="6" stroke="#475569" strokeWidth="1"/>
                      <circle cx="80" cy="105" r="6" stroke="#475569" strokeWidth="1"/>
                      <circle cx="120" cy="105" r="6" stroke="#475569" strokeWidth="1"/>
                      <circle cx="160" cy="105" r="6" stroke="#475569" strokeWidth="1"/>
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <svg className="h-10 w-10 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                      </svg>
                    </div>
                  </div>
                  <h3 className="text-sm font-semibold text-fg">Test senaryosu yok</h3>
                  <p className="mt-1 max-w-xs text-xs text-fg-muted">Suite ve folder oluşturun, ardından ilk test senaryonuzu ekleyin</p>
                  <button type="button" onClick={() => setShowModal(true)}
                    className="mt-5 flex items-center gap-1.5 rounded-xl bg-brand px-5 py-2.5 text-xs font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
                    <IcPlus/> İlk Senaryoyu Oluştur
                  </button>
                </>
              )}
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter}
              onDragStart={e => setDraggingId(String(e.active.id))}
              onDragEnd={handleDragEnd}>
              <table className="w-full">
                <thead className="sticky top-0 z-10 bg-surface-raised/95 backdrop-blur-sm">
                  <tr className="border-b border-border">
                    <th className="hidden w-5 sm:table-cell"/>
                    <th className="w-8 px-2 py-2.5">
                      <button type="button" onClick={toggleAll}
                        className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
                          allChecked ? "border-brand bg-brand" : "border-border hover:border-brand/45")}>
                        {allChecked && <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5"/></svg>}
                      </button>
                    </th>
                    {["ID","Başlık","P","Tür","Durum","Son Koşum","Adım","Güncelleme",""].map(h => (
                      <th key={h} className={cn(
                        "px-3 py-2.5 text-left text-[9px] font-semibold uppercase tracking-widest text-fg-subtle",
                        h === "Tür"        && "hidden lg:table-cell",
                        h === "Durum"      && "hidden md:table-cell",
                        h === "Son Koşum"  && "hidden lg:table-cell",
                        h === "Adım"       && "hidden xl:table-cell",
                        h === "Güncelleme" && "hidden xl:table-cell",
                      )}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <SortableContext items={filtered.map(c => c.id)} strategy={verticalListSortingStrategy}>
                  <tbody>
                    {filtered.map(tc => (
                      <CaseTableRow key={tc.id} tc={tc}
                        isSelected={selectedCaseId === tc.id}
                        onSelect={() => setSelectedCaseId(selectedCaseId === tc.id ? null : tc.id)}
                        isChecked={checkedIds.has(tc.id)}
                        onCheck={e => toggleOne(e, tc.id)}
                        projectId={effectivePid}/>
                    ))}
                  </tbody>
                </SortableContext>
              </table>
              <DragOverlay>
                {draggingId && (() => {
                  const tc = filtered.find(c => c.id === draggingId);
                  return tc ? (
                    <div className="flex items-center gap-3 rounded-xl border border-brand/20 bg-surface-raised px-4 py-2.5 shadow-lg">
                      <span className="font-mono text-[10px] text-fg-subtle">{tc.case_key}</span>
                      <span className="max-w-xs truncate text-xs font-medium text-fg">{tc.title}</span>
                    </div>
                  ) : null;
                })()}
              </DragOverlay>
            </DndContext>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-border bg-surface-raised px-4 py-1.5">
          <span className="text-[10px] font-medium text-fg-subtle">
            {hasFilter ? `${filtered.length} / ${nodeCases.length}` : `${filtered.length} senaryo`}
          </span>
          <div className="flex items-center gap-3">
            <Link href={`/p/${projectId}/management/repository`} className="text-[10px] font-medium text-fg-subtle transition-colors hover:text-brand">Repository →</Link>
            <Link href={`/p/${projectId}/management/runs`}       className="text-[10px] font-medium text-fg-subtle transition-colors hover:text-brand">Test Runs →</Link>
          </div>
        </div>
      </div>

      {/* RIGHT: Detail Panel */}
      {selectedCase && (
        <aside className="flex w-full flex-none flex-col overflow-hidden border-l border-border bg-surface-raised xl:w-96">
          <DetailPanel
            tc={selectedCase}
            suites={suites}
            folders={folders}
            onClose={() => setSelectedCaseId(null)}
            projectId={projectId}
            mgmtProjectId={effectivePid}
          />
        </aside>
      )}

      {/* New Case Modal */}
      {showModal && (
        <NewCaseModal
          projectId={effectivePid}
          suites={suites}
          folders={folders}
          defSuiteId={defSuiteId}
          defFolderId={defFolderId}
          onClose={() => setShowModal(false)}
          onDone={tc => { setShowModal(false); setSelectedCaseId(tc.id); }}
        />
      )}
    </div>
  );
}
