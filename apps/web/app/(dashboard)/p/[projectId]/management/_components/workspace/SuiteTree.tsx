"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  useCreateManagementSuite,
  useCreateManagementFolder,
  useUpdateManagementSuite,
  useUpdateManagementFolder,
  useDeleteManagementSuite,
  useDeleteManagementFolder,
  type TestCase, type TestFolder, type TestSuite,
} from "@/lib/hooks/use-management";
import {
  IcChev, IcPlus, IcFolder, IcGrip, IcTrash, IcPencil, IcSearch, IcClose,
  type WsNode, slugify,
} from "./shared";

export type DragKind = "case" | "suite" | "folder" | null;

function IcCheckMini() {
  return (
    <svg className="h-3 w-3" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={2.2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.25 4.75 8.5l5-5" />
    </svg>
  );
}

function TreeEditorRow({
  value,
  setValue,
  placeholder,
  marker,
  onSave,
  onCancel,
  size = "sm",
}: {
  value: string;
  setValue: (value: string) => void;
  placeholder: string;
  marker: string;
  onSave: () => void;
  onCancel: () => void;
  size?: "xs" | "sm";
}) {
  return (
    <div className="min-w-0 rounded-lg border border-brand/25 bg-brand-soft/70 p-2 shadow-xs ring-1 ring-brand/10">
      <div className="flex min-w-0 items-center gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-brand/20 bg-surface-raised text-[9px] font-bold text-brand">
          {marker}
        </span>
        <input
          autoFocus
          type="text"
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder={placeholder}
          onKeyDown={e => {
            if (e.key === "Enter") onSave();
            if (e.key === "Escape") onCancel();
          }}
          className={cn(
            "min-w-0 flex-1 rounded-md border border-border bg-surface-raised px-2 py-1 text-fg shadow-xs placeholder:text-fg-subtle outline-none transition-colors focus:border-brand focus:ring-2 focus:ring-brand/15",
            size === "xs" ? "text-[12px]" : "text-[13px]",
          )}
        />
      </div>
      <div className="mt-2 flex items-center justify-end gap-1.5">
        <button
          type="button"
          onClick={onSave}
          aria-label="Kaydet"
          className="inline-flex h-7 items-center gap-1 rounded-md bg-brand px-2 text-[11px] font-semibold text-brand-fg shadow-xs transition-colors hover:brightness-105"
        >
          <IcCheckMini />
          Kaydet
        </button>
        <button
          type="button"
          onClick={onCancel}
          aria-label="İptal"
          className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-surface-raised px-2 text-[11px] font-medium text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg"
        >
          <IcClose />
          İptal
        </button>
      </div>
    </div>
  );
}

function CodeTreeBackdrop() {
  const rows = [
    "repo.root()",
    "  .suite('checkout')",
    "    .folder('login')",
    "      .case('NX-104')",
    "    .folder('payment')",
    "      .case('NX-118')",
    "  .suite('api')",
    "    .folder('contracts')",
  ];

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl opacity-70">
      <div className="absolute inset-y-10 left-5 w-px bg-gradient-to-b from-emerald-400/0 via-emerald-400/25 to-emerald-400/0" />
      <div className="absolute inset-y-20 left-12 w-px bg-gradient-to-b from-teal-400/0 via-teal-400/20 to-teal-400/0" />
      <div className="absolute right-[-42px] top-8 rotate-[-10deg] font-mono text-[10px] leading-5 text-emerald-300/10">
        {rows.map((row) => (
          <div key={row} className="whitespace-pre">{row}</div>
        ))}
      </div>
      <div className="absolute bottom-16 left-10 h-24 w-24 rounded-full border border-emerald-400/10" />
      <div className="absolute bottom-24 left-14 h-10 w-px bg-emerald-400/15" />
      <div className="absolute bottom-28 left-14 h-px w-12 bg-emerald-400/15" />
      <div className="absolute bottom-20 left-14 h-px w-20 bg-emerald-400/10" />
    </div>
  );
}

function TreeBranchGuide({ depth }: { depth: number }) {
  if (depth <= 0) return null;
  return (
    <div className="pointer-events-none absolute inset-y-0 left-0 flex">
      {Array.from({ length: depth }).map((_, index) => (
        <span key={index} className="ml-[18px] w-px bg-gradient-to-b from-transparent via-emerald-500/10 to-transparent" />
      ))}
    </div>
  );
}

// ─── Folder node (recursive) ────────────────────────────────────────────────────

function FolderNode({
  folder, suiteId, allFolders, cases, depth,
  node, onNode, expanded, toggle, dragKind,
  onAddSub, onRename, onDelete, addingUnder, draftName, setDraftName, onCommitAdd, onCancelAdd,
}: {
  folder: TestFolder; suiteId: string; allFolders: TestFolder[]; cases: TestCase[]; depth: number;
  node: WsNode; onNode: (n: WsNode) => void;
  expanded: Set<string>; toggle: (id: string) => void; dragKind: DragKind;
  onAddSub: (parentId: string) => void;
  onRename: (folderId: string, name: string) => void;
  onDelete: (folderId: string) => void;
  addingUnder: string | null; draftName: string; setDraftName: (v: string) => void;
  onCommitAdd: (suiteId: string, parentId: string) => void; onCancelAdd: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging, isOver } =
    useSortable({ id: `folder:${folder.id}`, data: { kind: "folder", folderId: folder.id, suiteId, parentId: folder.parent_id ?? null } });

  const [renaming, setRenaming] = useState(false);
  const [renameVal, setRenameVal] = useState(folder.name);

  const children = allFolders.filter(f => f.parent_id === folder.id);
  const exp = expanded.has(folder.id);
  const fc = cases.filter(c => c.folder_id === folder.id && !c.archived).length;
  const sel = node.type === "folder" && node.id === folder.id;
  const dropActive = dragKind === "case" && isOver;

  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 }} className="relative">
      <TreeBranchGuide depth={depth} />
      <div className={cn("group flex items-center gap-0.5 rounded-lg",
        dropActive && "ring-1 ring-teal-500/50 bg-teal-500/10")}>
        <button type="button" onClick={() => toggle(folder.id)}
          title={children.length > 0 ? (exp ? "Daralt" : "Genişlet") : "Alt folder yok"}
          className="z-10 flex h-5 w-4 shrink-0 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-emerald-500/10 hover:text-emerald-500">
          {children.length > 0 ? <IcChev open={exp} /> : <span className="h-1 w-1 rounded-full bg-fg-disabled" />}
        </button>
        {renaming ? (
          <div className="min-w-0 flex-1">
            <TreeEditorRow
              value={renameVal}
              setValue={setRenameVal}
              placeholder="Folder adı"
              marker="F"
              size="xs"
              onSave={() => { onRename(folder.id, renameVal.trim() || folder.name); setRenaming(false); }}
              onCancel={() => { setRenameVal(folder.name); setRenaming(false); }}
            />
          </div>
        ) : (
          <button type="button" onClick={() => onNode({ type: "folder", id: folder.id, suiteId })}
            className={cn("flex flex-1 min-w-0 items-center gap-2 rounded-lg px-1.5 py-1 text-[12px] transition-colors",
              sel ? "bg-emerald-500/12 text-emerald-700 shadow-xs ring-1 ring-emerald-500/20 dark:text-emerald-300" : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
            <IcFolder />
            <span className="flex-1 truncate text-left">{folder.name}</span>
            {fc > 0 && <span className="text-[10px] text-fg-subtle tabular-nums">{fc}</span>}
          </button>
        )}
        <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
          <button type="button" {...attributes} {...listeners} title="Sürükle"
            className="flex h-5 w-4 cursor-grab touch-none items-center justify-center text-fg-disabled hover:text-fg-muted active:cursor-grabbing"><IcGrip /></button>
          <button type="button" onClick={() => onAddSub(folder.id)} title="Alt folder"
            className="flex h-5 w-4 items-center justify-center text-fg-disabled hover:text-fg-muted"><IcPlus /></button>
          <button type="button" onClick={() => { setRenameVal(folder.name); setRenaming(true); }} title="Yeniden adlandır"
            className="flex h-5 w-4 items-center justify-center text-fg-disabled hover:text-fg-muted"><IcPencil /></button>
          <button type="button" onClick={() => onDelete(folder.id)} title="Sil"
            className="flex h-5 w-4 items-center justify-center text-fg-disabled hover:text-danger"><IcTrash /></button>
        </div>
      </div>

      {exp && (children.length > 0 || addingUnder === folder.id) && (
        <div className="ml-3 border-l border-emerald-500/20 pl-1.5 mt-0.5 space-y-0.5">
          <SortableContext items={children.map(c => `folder:${c.id}`)} strategy={verticalListSortingStrategy}>
            {children.map(child => (
              <FolderNode key={child.id} folder={child} suiteId={suiteId} allFolders={allFolders} cases={cases} depth={depth + 1}
                node={node} onNode={onNode} expanded={expanded} toggle={toggle} dragKind={dragKind}
                onAddSub={onAddSub} onRename={onRename} onDelete={onDelete}
                addingUnder={addingUnder} draftName={draftName} setDraftName={setDraftName}
                onCommitAdd={onCommitAdd} onCancelAdd={onCancelAdd} />
            ))}
          </SortableContext>
          {addingUnder === folder.id && (
            <TreeEditorRow
              value={draftName}
              setValue={setDraftName}
              placeholder="Alt folder adı"
              marker="F"
              size="xs"
              onSave={() => onCommitAdd(suiteId, folder.id)}
              onCancel={onCancelAdd}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ─── Suite node ─────────────────────────────────────────────────────────────────

function SuiteNode({
  suite, folders, cases, node, onNode, expanded, toggle, dragKind,
  onAddFolder, onRenameSuite, onDeleteSuite,
  onAddSubFolder, onRenameFolder, onDeleteFolder,
  addingUnder, draftName, setDraftName, onCommitAdd, onCancelAdd,
}: {
  suite: TestSuite; folders: TestFolder[]; cases: TestCase[];
  node: WsNode; onNode: (n: WsNode) => void; expanded: Set<string>; toggle: (id: string) => void; dragKind: DragKind;
  onAddFolder: (suiteId: string) => void;
  onRenameSuite: (suiteId: string, name: string) => void;
  onDeleteSuite: (suiteId: string) => void;
  onAddSubFolder: (parentId: string) => void;
  onRenameFolder: (folderId: string, name: string) => void;
  onDeleteFolder: (folderId: string) => void;
  addingUnder: string | null; draftName: string; setDraftName: (v: string) => void;
  onCommitAdd: (suiteId: string, parentId: string | null) => void; onCancelAdd: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging, isOver } =
    useSortable({ id: `suite:${suite.id}`, data: { kind: "suite", suiteId: suite.id } });

  const [renaming, setRenaming] = useState(false);
  const [renameVal, setRenameVal] = useState(suite.name);

  const topFolders = folders.filter(f => f.suite_id === suite.id && !f.parent_id);
  const sc = cases.filter(c => c.suite_id === suite.id && !c.archived).length;
  const exp = expanded.has(suite.id);
  const sel = node.type === "suite" && node.id === suite.id;
  const dropActive = dragKind === "case" && isOver;

  return (
    <div ref={setNodeRef} style={{ transform: CSS.Transform.toString(transform), transition, opacity: isDragging ? 0.4 : 1 }} className="relative">
      <div className={cn("group flex items-center gap-0.5 rounded-lg",
        dropActive && "ring-1 ring-teal-500/50 bg-teal-500/10")}>
        <button type="button" onClick={() => toggle(suite.id)}
          title={exp ? "Daralt" : "Genişlet"}
          className="z-10 flex h-5 w-5 shrink-0 items-center justify-center rounded text-fg-subtle transition-colors hover:bg-emerald-500/10 hover:text-emerald-500">
          <IcChev open={exp} />
        </button>
        {renaming ? (
          <div className="min-w-0 flex-1">
            <TreeEditorRow
              value={renameVal}
              setValue={setRenameVal}
              placeholder="Suite adı"
              marker="S"
              onSave={() => { onRenameSuite(suite.id, renameVal.trim() || suite.name); setRenaming(false); }}
              onCancel={() => { setRenameVal(suite.name); setRenaming(false); }}
            />
          </div>
        ) : (
          <button type="button" onClick={() => onNode({ type: "suite", id: suite.id })}
            className={cn("flex flex-1 min-w-0 items-center gap-2 rounded-lg px-2 py-1.5 text-[13px] transition-colors",
              sel ? "bg-emerald-500/12 text-emerald-700 shadow-xs ring-1 ring-emerald-500/20 dark:text-emerald-300" : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
            <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded border border-emerald-500/20 bg-emerald-500/10 text-[9px] font-bold text-emerald-600 dark:text-emerald-300">S</span>
            <span className="flex-1 truncate text-left font-medium">{suite.name}</span>
            {sc > 0 && <span className="text-[11px] text-fg-subtle tabular-nums">{sc}</span>}
          </button>
        )}
        <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
          <button type="button" {...attributes} {...listeners} title="Sürükle"
            className="flex h-5 w-4 cursor-grab touch-none items-center justify-center text-fg-disabled hover:text-fg-muted active:cursor-grabbing"><IcGrip /></button>
          <button type="button" onClick={() => { onAddFolder(suite.id); }} title="Folder ekle"
            className="flex h-5 w-4 items-center justify-center text-fg-disabled hover:text-fg-muted"><IcPlus /></button>
          <button type="button" onClick={() => { setRenameVal(suite.name); setRenaming(true); }} title="Yeniden adlandır"
            className="flex h-5 w-4 items-center justify-center text-fg-disabled hover:text-fg-muted"><IcPencil /></button>
          <button type="button" onClick={() => onDeleteSuite(suite.id)} title="Sil"
            className="flex h-5 w-4 items-center justify-center text-fg-disabled hover:text-danger"><IcTrash /></button>
        </div>
      </div>

      {exp && (
        <div className="ml-5 border-l border-emerald-500/20 pl-2 mt-0.5 space-y-0.5">
          <SortableContext items={topFolders.map(f => `folder:${f.id}`)} strategy={verticalListSortingStrategy}>
            {topFolders.map(folder => (
              <FolderNode key={folder.id} folder={folder} suiteId={suite.id} allFolders={folders} cases={cases} depth={0}
                node={node} onNode={onNode} expanded={expanded} toggle={toggle} dragKind={dragKind}
                onAddSub={onAddSubFolder} onRename={onRenameFolder} onDelete={onDeleteFolder}
                addingUnder={addingUnder} draftName={draftName} setDraftName={setDraftName}
                onCommitAdd={(sid, pid) => onCommitAdd(sid, pid)} onCancelAdd={onCancelAdd} />
            ))}
          </SortableContext>

          {addingUnder === suite.id ? (
            <TreeEditorRow
              value={draftName}
              setValue={setDraftName}
              placeholder="Folder adı"
              marker="F"
              size="xs"
              onSave={() => onCommitAdd(suite.id, null)}
              onCancel={onCancelAdd}
            />
          ) : (
            <button type="button" onClick={() => onAddFolder(suite.id)}
              className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg-muted">
              <IcPlus /> Folder ekle
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── All-cases drop node ────────────────────────────────────────────────────────

function AllNode({ count, selected, onSelect, dragKind }: {
  count: number; selected: boolean; onSelect: () => void; dragKind: DragKind;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: "all", data: { kind: "allDrop" } });
  const dropActive = dragKind === "case" && isOver;
  return (
    <button type="button" ref={setNodeRef} onClick={onSelect}
      className={cn("flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors",
        dropActive && "ring-1 ring-teal-500/50 bg-teal-500/10",
        selected ? "bg-brand-soft text-brand shadow-xs" : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
      <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded border border-border bg-surface-overlay text-[9px] font-bold text-fg-muted">∑</span>
      <span className="flex-1 text-left font-medium">Tüm Senaryolar</span>
      <span className="text-[11px] text-fg-subtle tabular-nums">{count}</span>
    </button>
  );
}

// ─── SuiteTree (exported) ───────────────────────────────────────────────────────

export function SuiteTree({ suites, folders, cases, node, onNode, pid, dragKind }: {
  suites: TestSuite[]; folders: TestFolder[]; cases: TestCase[];
  node: WsNode; onNode: (n: WsNode) => void; pid: string; dragKind: DragKind;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(suites.slice(0, 3).map(s => s.id)));
  const [search, setSearch] = useState("");
  const [addSuite, setAddSuite] = useState(false);
  const [suiteName, setSuiteName] = useState("");
  const [addFolder, setAddFolder] = useState(false);
  const [folderSuiteId, setFolderSuiteId] = useState<string>("");
  const [folderName, setFolderName] = useState("");
  const [addingUnder, setAddingUnder] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [deleteConfirmSuiteId, setDeleteConfirmSuiteId] = useState<string | null>(null);

  const createSuite = useCreateManagementSuite(pid);
  const createFolder = useCreateManagementFolder(pid);
  const updateSuite = useUpdateManagementSuite(pid);
  const updateFolder = useUpdateManagementFolder(pid);
  const deleteSuite = useDeleteManagementSuite(pid);
  const deleteFolder = useDeleteManagementFolder(pid);

  const toggle = (id: string) => setExpanded(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const q = search.trim().toLowerCase();
  const visibleSuites = q ? suites.filter(s => s.name.toLowerCase().includes(q)) : suites;
  const total = cases.filter(c => !c.archived).length;
  const allNodeIds = [
    ...suites.map(s => s.id),
    ...folders.map(f => f.id),
  ];
  const expandAll = () => setExpanded(new Set(allNodeIds));
  const collapseAll = () => setExpanded(new Set());

  const saveFolder = async () => {
    if (!folderName.trim() || !folderSuiteId) return;
    const s = await createFolder.mutateAsync({
      suite_id: folderSuiteId, parent_id: null, name: folderName.trim(),
      path: slugify(folderName.trim()),
      order_index: folders.filter(f => f.suite_id === folderSuiteId && !f.parent_id).length,
    });
    setExpanded(p => new Set([...p, folderSuiteId]));
    setFolderName(""); setFolderSuiteId(""); setAddFolder(false);
  };

  const saveSuite = async () => {
    if (!suiteName.trim()) return;
    const s = await createSuite.mutateAsync({ name: suiteName.trim(), order_index: suites.length });
    setExpanded(p => new Set([...p, s.id]));
    setSuiteName(""); setAddSuite(false);
  };

  const commitAddFolder = async (suiteId: string, parentId: string | null) => {
    if (!draftName.trim()) return;
    await createFolder.mutateAsync({
      suite_id: suiteId, parent_id: parentId, name: draftName.trim(),
      path: slugify(draftName.trim()),
      order_index: folders.filter(f => f.suite_id === suiteId && (f.parent_id ?? null) === parentId).length,
    });
    setDraftName(""); setAddingUnder(null);
  };

  const onAddFolder = (suiteId: string) => { setExpanded(p => new Set([...p, suiteId])); setAddingUnder(suiteId); setDraftName(""); };
  const onAddSubFolder = (parentId: string) => { setExpanded(p => new Set([...p, parentId])); setAddingUnder(parentId); setDraftName(""); };
  const onCancelAdd = () => { setAddingUnder(null); setDraftName(""); };

  const onRenameSuite = (suiteId: string, name: string) => { void updateSuite.mutateAsync({ suiteId, name }); };
  const onRenameFolder = (folderId: string, name: string) => { void updateFolder.mutateAsync({ folderId, name }); };

  const onDeleteSuite = (suiteId: string) => {
    setDeleteConfirmSuiteId(suiteId);
  };

  const confirmDeleteSuite = () => {
    if (!deleteConfirmSuiteId) return;
    void deleteSuite.mutateAsync(deleteConfirmSuiteId);
    setDeleteConfirmSuiteId(null);
  };
  const onDeleteFolder = (folderId: string) => {
    if (typeof window !== "undefined" && !window.confirm("Folder silinsin mi?")) return;
    void deleteFolder.mutateAsync(folderId);
  };

  return (
    <div className="relative flex h-full flex-col overflow-hidden">
      <CodeTreeBackdrop />
      <div className="relative border-b border-border px-3 py-2.5">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-600 dark:text-emerald-300">
            Test Repository
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={expandAll}
              className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-700 transition-colors hover:bg-emerald-500/15 dark:text-emerald-200"
            >
              Aç
            </button>
            <button
              type="button"
              onClick={collapseAll}
              className="rounded-md border border-border bg-surface-raised px-2 py-1 text-[10px] font-medium text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg"
            >
              Kapat
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-raised/90 px-2.5 py-1.5 shadow-xs backdrop-blur transition-colors focus-within:border-emerald-500/50 focus-within:ring-2 focus-within:ring-emerald-500/15">
          <IcSearch />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Suite ara..."
            className="flex-1 bg-transparent text-[12px] text-fg placeholder:text-fg-subtle outline-none" />
        </div>
      </div>

      <div className="relative px-2 pt-2">
        <AllNode count={total} selected={node.type === "all"} onSelect={() => onNode({ type: "all" })} dragKind={dragKind} />
      </div>

      <div className="relative flex-1 overflow-y-auto space-y-0.5 px-2 pb-2 pt-1">
        <SortableContext items={visibleSuites.map(s => `suite:${s.id}`)} strategy={verticalListSortingStrategy}>
          {visibleSuites.map(suite => (
            <SuiteNode key={suite.id} suite={suite} folders={folders} cases={cases}
              node={node} onNode={onNode} expanded={expanded} toggle={toggle} dragKind={dragKind}
              onAddFolder={onAddFolder} onRenameSuite={onRenameSuite} onDeleteSuite={onDeleteSuite}
              onAddSubFolder={onAddSubFolder} onRenameFolder={onRenameFolder} onDeleteFolder={onDeleteFolder}
              addingUnder={addingUnder} draftName={draftName} setDraftName={setDraftName}
              onCommitAdd={commitAddFolder} onCancelAdd={onCancelAdd} />
          ))}
        </SortableContext>

        {addSuite ? (
          <TreeEditorRow
            value={suiteName}
            setValue={setSuiteName}
            placeholder="Suite adı"
            marker="S"
            onSave={saveSuite}
            onCancel={() => { setAddSuite(false); setSuiteName(""); }}
          />
        ) : (
          <button type="button" onClick={() => setAddSuite(true)}
            className="mt-1 flex w-full items-center gap-1.5 rounded-lg border border-dashed border-border px-2 py-1.5 text-[11px] text-fg-subtle transition-colors hover:border-brand/35 hover:bg-brand-soft hover:text-brand">
            <IcPlus /> Yeni Suite
          </button>
        )}

        {suites.length > 0 && (
          addFolder ? (
            <div className="mt-1 min-w-0 rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-2 shadow-xs ring-1 ring-emerald-500/10">
              <div className="flex min-w-0 items-center gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border border-emerald-500/20 bg-surface-raised text-[9px] font-bold text-emerald-600">F</span>
                <input
                  autoFocus
                  type="text"
                  value={folderName}
                  onChange={e => setFolderName(e.target.value)}
                  placeholder="Folder adı"
                  onKeyDown={e => { if (e.key === "Enter") void saveFolder(); if (e.key === "Escape") { setAddFolder(false); setFolderName(""); setFolderSuiteId(""); } }}
                  className="min-w-0 flex-1 rounded-md border border-border bg-surface-raised px-2 py-1 text-[12px] text-fg shadow-xs placeholder:text-fg-subtle outline-none transition-colors focus:border-emerald-500/50 focus:ring-2 focus:ring-emerald-500/15"
                />
              </div>
              <div className="mt-1.5">
                <select
                  value={folderSuiteId}
                  onChange={e => setFolderSuiteId(e.target.value)}
                  className="w-full rounded-md border border-border bg-surface-raised px-2 py-1 text-[11px] text-fg shadow-xs outline-none focus:border-emerald-500/50"
                >
                  <option value="">Suite seç…</option>
                  {suites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div className="mt-2 flex items-center justify-end gap-1.5">
                <button type="button" onClick={() => void saveFolder()}
                  className="inline-flex h-7 items-center gap-1 rounded-md bg-emerald-600 px-2 text-[11px] font-semibold text-white shadow-xs transition-colors hover:brightness-105">
                  <IcCheckMini />Kaydet
                </button>
                <button type="button" onClick={() => { setAddFolder(false); setFolderName(""); setFolderSuiteId(""); }}
                  className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-surface-raised px-2 text-[11px] font-medium text-fg-subtle transition-colors hover:bg-surface-overlay hover:text-fg">
                  <IcClose />İptal
                </button>
              </div>
            </div>
          ) : (
            <button type="button" onClick={() => { setAddFolder(true); setFolderSuiteId(suites[0]?.id ?? ""); }}
              className="mt-1 flex w-full items-center gap-1.5 rounded-lg border border-dashed border-emerald-500/20 px-2 py-1.5 text-[11px] text-fg-subtle transition-colors hover:border-emerald-500/40 hover:bg-emerald-500/5 hover:text-emerald-700 dark:hover:text-emerald-300">
              <IcFolder /> Yeni Folder
            </button>
          )
        )}
      </div>

      <div className="relative border-t border-border bg-surface-raised/75 px-4 py-2 backdrop-blur">
        <div className="flex items-center justify-between text-[10px] text-fg-subtle">
          <span>{suites.length} suite</span>
          <span>{folders.length} folder</span>
          <span>{total} case</span>
        </div>
      </div>

      {/* ── Suite delete confirm modal ─────────────────────────────────────── */}
      {deleteConfirmSuiteId && (() => {
        const suiteToDelete = suites.find(s => s.id === deleteConfirmSuiteId);
        const caseCount = cases.filter(c => c.suite_id === deleteConfirmSuiteId).length;
        const folderCount = folders.filter(f => f.suite_id === deleteConfirmSuiteId).length;
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div className="w-full max-w-sm rounded-xl border border-border bg-surface-raised p-5 shadow-elevated">
              <h3 className="text-sm font-semibold text-fg">Suite silinsin mi?</h3>
              <p className="mt-2 text-xs text-fg-muted">
                <span className="font-medium text-fg">{suiteToDelete?.name ?? "Suite"}</span> kalıcı olarak silinecek.
              </p>
              {(caseCount > 0 || folderCount > 0) && (
                <div className="mt-3 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2">
                  {folderCount > 0 && (
                    <p className="text-xs text-amber-400">
                      Bu suite içinde {folderCount} folder var. Silinince folder'lar da kaldırılacak.
                    </p>
                  )}
                  {caseCount > 0 && (
                    <p className="text-amber-400 text-xs mt-1">
                      ⚠️ Bu suite içinde {caseCount} case var. Silince bu case'lerin suite bağlantısı kaldırılacak.
                    </p>
                  )}
                </div>
              )}
              <div className="mt-4 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setDeleteConfirmSuiteId(null)}
                  className="rounded-lg border border-border px-4 py-1.5 text-xs text-fg-subtle hover:bg-surface-overlay"
                >
                  İptal
                </button>
                <button
                  type="button"
                  onClick={confirmDeleteSuite}
                  className="rounded-lg bg-red-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-red-500"
                >
                  Sil
                </button>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
