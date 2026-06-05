"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  DndContext, DragOverlay, PointerSensor, KeyboardSensor,
  useSensor, useSensors, closestCenter,
  type DragStartEvent, type DragEndEvent,
} from "@dnd-kit/core";
import { arrayMove, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import {
  useManagementRepository,
  useManagementRuns,
  useMoveManagementCase,
  useUpdateManagementSuite,
  useUpdateManagementFolder,
  usePromoteCases,
  useArchiveManagementCase,
  useUnarchiveManagementCase,
  useBulkUpdateCases,
  useCloneManagementCase,
  useQualityScan,
  type QualityScanResult,
  type TestCase, type TestSuite, type TestFolder,
} from "@/lib/hooks/use-management";
import { SuiteTree, type DragKind } from "./SuiteTree";
import { CaseDetailDrawer } from "./CaseDetailDrawer";
import { NewCaseModal } from "./NewCaseModal";
import { RunList } from "./RunList";
import { RunDetailPane } from "./RunDetailPane";
import { NewRunModal } from "./NewRunModal";
import { type WsNode } from "./shared";
import { CaseRow, ArchivedCaseRow } from "./CaseRow";
import { RunTabHeader, type RunFilters } from "./RunTabHeader";
import { WorkspaceFilterBar } from "./WorkspaceFilterBar";
import { WorkspaceBulkActions } from "./WorkspaceBulkActions";
import { WorkspaceEmptyState } from "./WorkspaceEmptyState";

type DragData =
  | { kind: "case"; caseId: string }
  | { kind: "suite"; suiteId: string }
  | { kind: "folder"; folderId: string; suiteId: string; parentId: string | null }
  | { kind: "allDrop" };

// ─── Local Icons (used only in CaseTable) ─────────────────────────────────────

function IcCheck() {
  return <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" /></svg>;
}

// ─── Case Table (ultra-clean TestRail style) ──────────────────────────────────

function CaseTable({
  nodeName, nodeCases, archivedCases, loading, projectId,
  selId, onSelect, checked, onCheck, onClearChecked, onToggleAll,
  onNewCase, onCreateRun, onPromote, onArchiveMany, onUnarchiveMany,
  onBulkMove, onBulkUpdate, onBulkClone, onCloneCase, onUnarchivedSingle,
  busy, suites, folders,
}: {
  nodeName: string; nodeCases: TestCase[]; archivedCases: TestCase[]; loading: boolean; projectId: string;
  selId: string | null; onSelect: (id: string) => void;
  checked: Set<string>; onCheck: (id: string) => void;
  onClearChecked: () => void; onToggleAll: (ids: string[]) => void;
  onNewCase: () => void; onCreateRun: () => void;
  onPromote: () => void; onArchiveMany: () => void; onUnarchiveMany: () => void;
  onBulkMove: (caseId: string, suiteId: string, folderId: string | null) => Promise<void>;
  onBulkUpdate: (payload: { case_ids: string[]; priority?: string; type?: string; status?: string; tags_add?: string[] }) => Promise<void>;
  onBulkClone: (caseIds: string[]) => Promise<void>;
  onCloneCase: (caseId: string) => Promise<void>;
  onUnarchivedSingle: (caseId: string) => Promise<void>;
  busy: boolean;
  suites: TestSuite[];
  folders: TestFolder[];
}) {
  const [search,       setSearch]       = useState("");
  const [priority,     setPriority]     = useState("");
  const [type,         setType]         = useState("");
  const [status,       setStatus]       = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [cloningId,    setCloningId]    = useState<string | null>(null);
  const [unarchivedId, setUnarchivedId] = useState<string | null>(null);
  const [sortCol, setSortCol] = useState<string>("updated_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const searchTimer = useRef<ReturnType<typeof setTimeout>>();
  const [debouncedSearch, setDebouncedSearch] = useState(search);

  useEffect(() => {
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setDebouncedSearch(search), 250);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  const filtered = useMemo(() => {
    let r = nodeCases;
    const q = debouncedSearch.trim().toLowerCase();
    if (q)        r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q));
    if (priority) r = r.filter(c => c.priority === priority);
    if (type)     r = r.filter(c => c.type === type);
    if (status)   r = r.filter(c => c.last_run_status === status);
    return r;
  }, [nodeCases, debouncedSearch, priority, type, status]);

  const sorted = useMemo(() => {
    const PRIO = { P0: 0, P1: 1, P2: 2, P3: 3 } as Record<string, number>;
    return [...filtered].sort((a, b) => {
      if (sortCol === "priority") {
        const pa = PRIO[a.priority] ?? 9; const pb = PRIO[b.priority] ?? 9;
        return sortDir === "asc" ? pa - pb : pb - pa;
      }
      const va = String((a as unknown as Record<string, unknown>)[sortCol] ?? "");
      const vb = String((b as unknown as Record<string, unknown>)[sortCol] ?? "");
      return sortDir === "asc" ? va.localeCompare(vb) : vb.localeCompare(va);
    });
  }, [filtered, sortCol, sortDir]);

  const activeFilterCount = [priority, type, status].filter(Boolean).length + (debouncedSearch ? 1 : 0);

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortCol(col); setSortDir("asc"); }
  };

  const allChecked = filtered.length > 0 && filtered.every(c => checked.has(c.id));
  const hasFilter  = !!(debouncedSearch || priority || type || status);
  const clearAll   = () => { setSearch(""); setPriority(""); setType(""); setStatus(""); };
  const checkedIds = [...checked];

  const checkedArchivedCount = useMemo(
    () => checkedIds.filter(id => archivedCases.some(c => c.id === id)).length,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [checked, archivedCases],
  );

  const handleCloneRow = async (caseId: string) => {
    setCloningId(caseId);
    try { await onCloneCase(caseId); }
    finally { setCloningId(null); }
  };

  const handleUnarchiveRow = async (caseId: string) => {
    setUnarchivedId(caseId);
    try { await onUnarchivedSingle(caseId); }
    finally { setUnarchivedId(null); }
  };

  return (
    <div className="flex flex-1 flex-col min-w-0 overflow-hidden">

      {/* ── Toolbar ─────────────────────────────────────────────────────────── */}
      <WorkspaceFilterBar
        nodeName={nodeName}
        totalCount={nodeCases.length}
        filteredCount={filtered.length}
        hasFilter={hasFilter}
        search={search}
        priority={priority}
        type={type}
        status={status}
        activeFilterCount={activeFilterCount}
        showArchived={showArchived}
        archivedCount={archivedCases.length}
        failedCount={nodeCases.filter(c => c.last_run_status === "failed").length}
        blockedCount={nodeCases.filter(c => c.last_run_status === "blocked").length}
        onSearchChange={setSearch}
        onPriorityChange={setPriority}
        onTypeChange={setType}
        onStatusChange={setStatus}
        onToggleArchived={() => setShowArchived(v => !v)}
        onClearAll={clearAll}
        onNewCase={onNewCase}
      />

      {/* ── Bulk action bar ─────────────────────────────────────────────────── */}
      <WorkspaceBulkActions
        checkedSize={checked.size}
        checkedIds={checkedIds}
        checkedArchivedCount={checkedArchivedCount}
        busy={busy}
        suites={suites}
        folders={folders}
        onToggleAll={onToggleAll}
        nodeCaseIds={nodeCases.map(c => c.id)}
        onCreateRun={onCreateRun}
        onPromote={onPromote}
        onArchiveMany={onArchiveMany}
        onUnarchiveMany={onUnarchiveMany}
        onBulkMove={onBulkMove}
        onBulkUpdate={onBulkUpdate}
        onBulkClone={onBulkClone}
        onClearChecked={onClearChecked}
      />

      {/* ── Table ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div>
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 border-b border-border/40 px-4 py-2.5">
                <div className="h-3 w-16 rounded bg-surface-accent animate-pulse" />
                <div className="h-3 flex-1 max-w-md rounded bg-surface-accent animate-pulse" />
                <div className="h-3 w-8 rounded bg-surface-accent animate-pulse" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 && !showArchived ? (
          <WorkspaceEmptyState
            hasFilter={hasFilter}
            onClearFilters={clearAll}
            onNewCase={onNewCase}
          />
        ) : (
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-10 border-b border-border bg-surface-overlay">
              <tr>
                <th className="hidden w-5 sm:table-cell" />
                <th className="w-8 px-2 py-2">
                  <button type="button"
                    onClick={() => allChecked ? onClearChecked() : onToggleAll(filtered.map(c => c.id))}
                    className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
                      allChecked ? "border-brand bg-brand text-brand-fg" : "border-border-strong bg-surface-raised hover:border-brand")}>
                    {allChecked && <IcCheck />}
                  </button>
                </th>
                {[
                  { label: "ID",        col: null,         cls: "w-20"                       },
                  { label: "Başlık",    col: "title",      cls: ""                           },
                  { label: "Öncelik",   col: "priority",   cls: "w-14"                       },
                  { label: "Tür",       col: "type",       cls: "hidden w-24 lg:table-cell"  },
                  { label: "Güncelleme",col: "updated_at", cls: "hidden w-24 md:table-cell"  },
                  { label: "Adım",      col: null,         cls: "hidden w-12 xl:table-cell"  },
                  { label: "",          col: null,         cls: "w-16"                       },
                ].map(({ label, col, cls }) => (
                  <th key={label}
                    className={cn("px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-muted", cls, col && "cursor-pointer select-none hover:text-fg")}
                    onClick={col ? () => toggleSort(col) : undefined}>
                    {label}
                    {col && sortCol === col && (
                      <span className="ml-1 text-brand">{sortDir === "asc" ? "↑" : "↓"}</span>
                    )}
                    {col && sortCol !== col && (
                      <span className="ml-1 opacity-30">↕</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map(tc => (
                <CaseRow
                  key={tc.id} tc={tc}
                  selected={selId === tc.id}
                  onSelect={() => onSelect(tc.id)}
                  checked={checked.has(tc.id)}
                  onCheck={e => { e.stopPropagation(); onCheck(tc.id); }}
                  projectId={projectId}
                  onClone={() => void handleCloneRow(tc.id)}
                  cloning={cloningId === tc.id}
                />
              ))}
              {/* ── Archived section ────────────────────────────────── */}
              {showArchived && archivedCases.length > 0 && (
                <>
                  <tr>
                    <td colSpan={9} className="px-4 py-2 bg-surface-overlay border-y border-border/60">
                      <span className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                        Arşivlendi ({archivedCases.length})
                      </span>
                    </td>
                  </tr>
                  {archivedCases.map(tc => (
                    <ArchivedCaseRow
                      key={tc.id} tc={tc}
                      checked={checked.has(tc.id)}
                      onCheck={e => { e.stopPropagation(); onCheck(tc.id); }}
                      projectId={projectId}
                      onUnarchive={() => void handleUnarchiveRow(tc.id)}
                      unarchiving={unarchivedId === tc.id}
                    />
                  ))}
                </>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-t border-border bg-surface-raised px-4 py-2">
        <span className="text-[10px] text-fg-muted">
          {hasFilter ? `${filtered.length} / ${nodeCases.length} senaryo` : `${nodeCases.length} senaryo`}
          {archivedCases.length > 0 && (
            <span className="ml-2 text-fg-subtle">· {archivedCases.length} arşivde</span>
          )}
        </span>
        {checked.size > 0 && (
          <span className="text-[10px] font-medium text-brand">{checked.size} seçili</span>
        )}
      </div>
    </div>
  );
}

// ─── Run Timeline ─────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  completed:   "bg-emerald-500",
  passed:      "bg-emerald-500",
  failed:      "bg-red-500",
  in_progress: "bg-blue-500",
  not_started: "bg-slate-500",
};

const STATUS_LABEL_SHORT: Record<string, string> = {
  completed:   "pass",
  passed:      "pass",
  failed:      "fail",
  in_progress: "active",
  not_started: "pending",
};

function fmtTimelineDate(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
}

function RunTimeline({
  runs,
  selectedRunId,
  onSelect,
}: {
  runs: Array<{ id: string; name: string; status: string; created_at: string }>;
  selectedRunId: string | null;
  onSelect: (id: string) => void;
}) {
  const sorted = useMemo(
    () => [...runs]
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .slice(-10),
    [runs],
  );

  if (sorted.length === 0) return null;

  return (
    <div className="border-b border-border bg-surface-raised px-4 py-3 overflow-x-auto">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
        Son Run Geçmişi
      </p>
      <div className="flex items-end gap-0 min-w-max">
        {sorted.map((run, idx) => {
          const status = run.status || "not_started";
          const dotColor = STATUS_COLORS[status] ?? "bg-slate-500";
          const shortLabel = STATUS_LABEL_SHORT[status] ?? status;
          const isActive = status === "in_progress";
          const isSelected = selectedRunId === run.id;

          return (
            <div key={run.id} className="flex items-center">
              {/* Node */}
              <button
                type="button"
                onClick={() => onSelect(run.id)}
                className="flex flex-col items-center gap-1 group"
                title={run.name}
              >
                {/* Date */}
                <span className={cn(
                  "text-[9px] tabular-nums transition-colors",
                  isSelected ? "text-brand font-semibold" : "text-fg-disabled group-hover:text-fg-subtle",
                )}>
                  {fmtTimelineDate(run.created_at)}
                </span>
                {/* Dot */}
                <div className={cn(
                  "relative flex h-5 w-5 items-center justify-center rounded-full border-2 transition-all",
                  isSelected
                    ? "border-brand scale-125 shadow-sm shadow-brand/30"
                    : "border-border group-hover:scale-110",
                  dotColor,
                )}>
                  {isActive && (
                    <span className="absolute inset-0 rounded-full animate-ping opacity-40" style={{ backgroundColor: "rgb(59 130 246)" }} />
                  )}
                </div>
                {/* Status label */}
                <span className={cn(
                  "text-[9px] font-medium transition-colors max-w-[52px] truncate text-center",
                  isSelected ? "text-brand" : "text-fg-disabled group-hover:text-fg-subtle",
                )}>
                  {shortLabel}
                </span>
              </button>
              {/* Connector line */}
              {idx < sorted.length - 1 && (
                <div className="h-px w-6 flex-none bg-border mx-0.5 mb-3" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main Shell ───────────────────────────────────────────────────────────────

export function WorkspaceShell({
  projectId,
  mpid,
  initialMode = "cases",
}: {
  projectId: string;
  mpid: string;
  initialMode?: "cases" | "runs";
}) {
  const repoQ = useManagementRepository(mpid || undefined);
  const runsQ = useManagementRuns(mpid || undefined);

  const suites  = useMemo<TestSuite[]>(() => repoQ.data?.suites ?? [], [repoQ.data]);
  const folders = useMemo<TestFolder[]>(() => repoQ.data?.folders ?? [], [repoQ.data]);
  const allCases  = useMemo(() => repoQ.data?.cases ?? [], [repoQ.data]);
  const active    = useMemo(() => allCases.filter(c => !c.archived), [allCases]);
  const archived  = useMemo(() => allCases.filter(c => c.archived), [allCases]);
  const runs      = runsQ.data ?? [];

  const moveCase     = useMoveManagementCase(mpid || "");
  const updateSuite  = useUpdateManagementSuite(mpid || "");
  const updateFolder = useUpdateManagementFolder(mpid || "");
  const promote      = usePromoteCases(mpid || "");
  const archiveMut   = useArchiveManagementCase(mpid || "");
  const unarchiveMut = useUnarchiveManagementCase(mpid || "");
  const bulkUpdate   = useBulkUpdateCases(mpid || "");
  const cloneMut     = useCloneManagementCase(mpid || "");

  const router = useRouter();

  const [mode,           setMode]           = useState<"cases" | "runs">(initialMode);
  const [node,           setNode]           = useState<WsNode>({ type: "all" });
  const [showQualityScan, setShowQualityScan] = useState(false);
  const qualityScan = useQualityScan(mpid || undefined);
  const [selId,          setSelId]          = useState<string | null>(null);
  const [checked,        setChecked]        = useState<Set<string>>(new Set());
  const [showNewCase,    setShowNewCase]    = useState(false);
  const [showNewRun,     setShowNewRun]     = useState(false);
  const [runInitCaseIds, setRunInitCaseIds] = useState<string[]>([]);
  const [selectedRunId,  setSelectedRunId]  = useState<string | null>(null);
  const [busy,           setBusy]           = useState(false);
  const [dragKind,       setDragKind]       = useState<DragKind>(null);
  const [draggingCaseId, setDraggingCaseId] = useState<string | null>(null);
  const [runFilters,     setRunFilters]     = useState<RunFilters>({ search: "", status: "", dateRange: "" });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const nodeCases = useMemo(() => {
    switch (node.type) {
      case "suite":  return active.filter(c => c.suite_id === node.id);
      case "folder": return active.filter(c => c.folder_id === node.id);
      default:       return active;
    }
  }, [active, node]);

  const nodeArchivedCases = useMemo(() => {
    switch (node.type) {
      case "suite":  return archived.filter(c => c.suite_id === node.id);
      case "folder": return archived.filter(c => c.folder_id === node.id);
      default:       return archived;
    }
  }, [archived, node]);

  const nodeName = node.type === "all" ? "Tüm Senaryolar"
    : node.type === "suite"  ? (suites.find(s => s.id === node.id)?.name ?? "Suite")
    : (folders.find(f => f.id === node.id)?.name ?? "Folder");

  const draggingCase   = draggingCaseId ? active.find(c => c.id === draggingCaseId) : null;
  const checkedIds     = useMemo(() => [...checked], [checked]);
  const activeRunCount = runs.filter(r => r.status === "in_progress").length;

  const filteredRuns = useMemo(() => {
    let r = runs;
    const q = runFilters.search.trim().toLowerCase();
    if (q) r = r.filter(run => run.name.toLowerCase().includes(q));
    if (runFilters.status) r = r.filter(run => (run.status || "not_started") === runFilters.status);
    if (runFilters.dateRange) {
      const now = Date.now();
      const cutoff: Record<string, number> = {
        today: 1,
        week:  7,
        month: 30,
      };
      const days = cutoff[runFilters.dateRange] ?? 0;
      const ms   = days * 24 * 60 * 60 * 1000;
      r = r.filter(run => {
        const dateStr = (run as unknown as Record<string, unknown>).created_at as string | undefined ?? run.started_at;
        if (!dateStr) return true;
        return now - new Date(dateStr).getTime() <= ms;
      });
    }
    return r;
  }, [runs, runFilters]);

  const onDragStart = (e: DragStartEvent) => {
    const d = e.active.data.current as DragData | undefined;
    if (!d) return;
    setDragKind(d.kind === "allDrop" ? null : d.kind);
    if (d.kind === "case") setDraggingCaseId(d.caseId);
  };

  const reorder = async (
    items: Array<{ id: string; order_index: number }>,
    activeId: string, overId: string,
    patch: (id: string, i: number) => Promise<unknown>,
  ) => {
    const sorted = [...items].sort((a, b) => a.order_index - b.order_index);
    const oi = sorted.findIndex(x => x.id === activeId);
    const ni = sorted.findIndex(x => x.id === overId);
    if (oi < 0 || ni < 0 || oi === ni) return;
    const next = arrayMove(sorted, oi, ni);
    await Promise.all(next.map((x, i) => x.order_index === i ? null : patch(x.id, i)).filter(Boolean) as Promise<unknown>[]);
  };

  const onDragEnd = async (e: DragEndEvent) => {
    const a = e.active.data.current as DragData | undefined;
    const o = e.over?.data.current as DragData | undefined;
    setDragKind(null); setDraggingCaseId(null);
    if (!a || !o) return;
    if (a.kind === "case") {
      if (o.kind === "allDrop") await moveCase.mutateAsync({ caseId: a.caseId, suite_id: null, folder_id: null });
      else if (o.kind === "suite")  await moveCase.mutateAsync({ caseId: a.caseId, suite_id: o.suiteId, folder_id: null });
      else if (o.kind === "folder") await moveCase.mutateAsync({ caseId: a.caseId, suite_id: o.suiteId, folder_id: o.folderId });
      return;
    }
    if (a.kind === "suite" && o.kind === "suite") {
      await reorder(suites, a.suiteId, o.suiteId, (id, i) => updateSuite.mutateAsync({ suiteId: id, order_index: i }));
      return;
    }
    if (a.kind === "folder" && o.kind === "folder" && a.suiteId === o.suiteId && a.parentId === o.parentId) {
      const siblings = folders.filter(f => f.suite_id === a.suiteId && (f.parent_id ?? null) === a.parentId);
      await reorder(siblings, a.folderId, o.folderId, (id, i) => updateFolder.mutateAsync({ folderId: id, order_index: i }));
    }
  };

  const onPromote = async () => {
    if (!checkedIds.length) return;
    setBusy(true);
    try { await promote.mutateAsync({ case_ids: checkedIds, target_status: "active" }); setChecked(new Set()); }
    finally { setBusy(false); }
  };
  const onArchiveMany = async () => {
    if (!checkedIds.length) return;
    setBusy(true);
    try {
      await Promise.all([...checkedIds].map(id => archiveMut.mutateAsync(id)));
      setChecked(new Set());
    } catch (err: unknown) {
      console.error("[WorkspaceShell] Bulk operation partial failure:", err);
    } finally { setBusy(false); }
  };

  const onUnarchiveMany = async () => {
    const archivedChecked = checkedIds.filter(id => archived.some(c => c.id === id));
    if (!archivedChecked.length) return;
    setBusy(true);
    try {
      await Promise.all([...archivedChecked].map(id => unarchiveMut.mutateAsync(id)));
      setChecked(new Set());
    } catch (err: unknown) {
      console.error("[WorkspaceShell] Bulk operation partial failure:", err);
    } finally { setBusy(false); }
  };

  const onBulkClone = async (caseIds: string[]) => {
    setBusy(true);
    try {
      await Promise.all([...caseIds].map(id => cloneMut.mutateAsync({ caseId: id })));
    } catch (err: unknown) {
      console.error("[WorkspaceShell] Bulk operation partial failure:", err);
    } finally { setBusy(false); }
  };

  // Single-row clone: navigate to new case
  const onCloneCase = async (caseId: string) => {
    const newCase = await cloneMut.mutateAsync({ caseId });
    if (newCase?.id) router.push(`/p/${projectId}/management/cases/${newCase.id}`);
  };

  // Single-row unarchive
  const onUnarchivedSingle = async (caseId: string) => {
    setBusy(true);
    try { await unarchiveMut.mutateAsync(caseId); }
    finally { setBusy(false); }
  };

  const openNewRun = () => { setRunInitCaseIds(checkedIds); setShowNewRun(true); };
  const onRunCreated = (runId: string) => {
    setShowNewRun(false); setChecked(new Set());
    setMode("runs"); setSelectedRunId(runId);
  };

  return (
    <div className="flex h-full flex-col bg-surface-base">

      {/* ── Top bar (TestRail ana tab çubuğu) ────────────────────────────── */}
      <div className="flex items-center border-b border-border bg-surface-raised px-2 shadow-xs">
        {[
          { id: "cases" as const, label: `Senaryolar`, badge: active.length },
          { id: "runs"  as const, label: "Test Koşumları", badge: runs.length },
        ].map(({ id, label, badge }) => (
          <button key={id} type="button" onClick={() => setMode(id)}
            className={cn(
              "flex items-center gap-2 rounded-t-lg border-b-2 px-4 py-3 text-[13px] font-semibold transition-colors",
              mode === id
                ? "border-brand bg-brand-soft text-brand"
                : "border-transparent text-fg-subtle hover:text-fg hover:bg-surface-overlay",
            )}>
            {label}
            {badge > 0 && (
              <span className={cn(
                "rounded-full px-1.5 py-0.5 text-[10px] tabular-nums",
                mode === id ? "bg-brand-soft text-brand" : "bg-surface-accent text-fg-subtle",
              )}>
                {badge}
              </span>
            )}
          </button>
        ))}

        <div className="flex-1" />

        {/* Active run indicator */}
        {activeRunCount > 0 && (
          <div className="flex items-center gap-1.5 mr-2 rounded-full bg-blue-500/10 border border-blue-500/20 px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
            <span className="text-[11px] text-blue-400">{activeRunCount} aktif</span>
          </div>
        )}

        {/* Quality scan button */}
        <button type="button" onClick={() => setShowQualityScan(v => !v)}
          className={cn(
            "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition-colors mr-2",
            showQualityScan
              ? "border-purple-500/30 bg-purple-500/10 text-purple-400"
              : "border-border text-fg-subtle hover:border-purple-500/20 hover:text-purple-400",
          )}>
          ✦ Kalite
          {qualityScan.data && qualityScan.data.issues_found > 0 && (
            <span className="rounded-full bg-amber-500/20 px-1.5 py-0.5 text-[9px] text-amber-400">
              {qualityScan.data.issues_found}
            </span>
          )}
        </button>
      </div>

      {/* ── Quality Scan Panel ───────────────────────────────────────────────── */}
      {showQualityScan && (
        <div className="border-b border-border bg-surface-overlay px-4 py-3 space-y-2 max-h-64 overflow-y-auto">
          <div className="flex items-center justify-between mb-1">
            <p className="text-[11px] font-semibold text-fg">
              Kalite Taraması
              {qualityScan.data && <span className="ml-2 text-fg-subtle">· {qualityScan.data.issues_found}/{qualityScan.data.total} sorunlu</span>}
            </p>
            <button type="button" onClick={() => void qualityScan.refetch()}
              className="text-[10px] text-fg-subtle hover:text-fg">↺</button>
          </div>
          {qualityScan.isLoading ? (
            <div className="space-y-1">
              {[1,2,3].map(i => <div key={i} className="h-8 rounded bg-surface-accent animate-pulse" />)}
            </div>
          ) : qualityScan.data?.results.length === 0 ? (
            <p className="text-[12px] text-emerald-400 py-2">✓ Tüm case'ler kalite standartlarını karşılıyor</p>
          ) : (
            <div className="space-y-1.5">
              {(qualityScan.data?.results ?? []).map((r: QualityScanResult) => (
                <div key={r.case_id} className="flex items-start gap-2.5 rounded-lg border border-border px-3 py-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-fg-subtle">{r.case_key}</span>
                      <span className="truncate text-[12px] text-fg">{r.title}</span>
                    </div>
                    <p className="text-[10px] text-amber-400">{r.issues.slice(0,2).join(" · ")}</p>
                  </div>
                  <span className={cn("shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold",
                    r.score < 40 ? "bg-red-500/20 text-red-400" :
                    r.score < 70 ? "bg-amber-500/20 text-amber-400" :
                    "bg-emerald-500/20 text-emerald-400"
                  )}>
                    {r.score}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Content ──────────────────────────────────────────────────────────── */}
      {mode === "cases" ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter}
          onDragStart={onDragStart} onDragEnd={onDragEnd}
          onDragCancel={() => { setDragKind(null); setDraggingCaseId(null); }}>
          <div className="flex flex-1 min-h-0">

            {/* ── Left: Suite tree (TestRail sol panel) ──────────────────── */}
            <aside className="hidden w-[292px] flex-none flex-col overflow-hidden border-r border-border bg-surface-raised md:flex">
              <SuiteTree
                suites={suites} folders={folders} cases={active}
                node={node} onNode={setNode}
                pid={mpid || ""} dragKind={dragKind}
              />
            </aside>

            {/* ── Right: Case table ───────────────────────────────────────── */}
            <CaseTable
              nodeName={nodeName}
              nodeCases={nodeCases}
              archivedCases={nodeArchivedCases}
              loading={repoQ.isLoading}
              projectId={projectId}
              selId={selId}
              onSelect={id => setSelId(selId === id ? null : id)}
              checked={checked}
              onCheck={id => setChecked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; })}
              onClearChecked={() => setChecked(new Set())}
              onToggleAll={ids => setChecked(new Set(ids))}
              onNewCase={() => setShowNewCase(true)}
              onCreateRun={openNewRun}
              onPromote={onPromote}
              onArchiveMany={onArchiveMany}
              onUnarchiveMany={onUnarchiveMany}
              onBulkMove={async (caseId, suiteId, folderId) => {
                await moveCase.mutateAsync({ caseId, suite_id: suiteId, folder_id: folderId });
              }}
              onBulkUpdate={async payload => {
                await bulkUpdate.mutateAsync(payload);
              }}
              onBulkClone={onBulkClone}
              onCloneCase={onCloneCase}
              onUnarchivedSingle={onUnarchivedSingle}
              busy={busy}
              suites={suites}
              folders={folders}
            />

            {/* ── Far right: Case detail drawer ──────────────────────────── */}
            {selId && (
              <CaseDetailDrawer
                caseId={selId} pid={mpid || ""} projectId={projectId}
                onClose={() => setSelId(null)}
              />
            )}
          </div>

          <DragOverlay>
            {draggingCase && (
              <div className="flex items-center gap-2 rounded-lg border border-brand/30 bg-surface-raised px-3 py-2 shadow-elevated">
                <span className="font-mono text-[10px] text-fg-subtle">{draggingCase.case_key}</span>
                <span className="text-[13px] text-fg max-w-xs truncate">{draggingCase.title}</span>
              </div>
            )}
          </DragOverlay>
        </DndContext>
      ) : (
        <div className="flex flex-1 min-h-0 flex-col">
          <RunTabHeader
            onNewRun={openNewRun}
            filters={runFilters}
            onFiltersChange={setRunFilters}
            totalCount={runs.length}
            filteredCount={filteredRuns.length}
          />
          <RunTimeline
            runs={runs}
            selectedRunId={selectedRunId}
            onSelect={setSelectedRunId}
          />
          <div className="flex flex-1 min-h-0">
            <aside className="hidden w-[224px] flex-none overflow-hidden border-r border-border bg-surface-raised md:block">
              <RunList
                pid={mpid || ""} selectedRunId={selectedRunId}
                onSelect={setSelectedRunId}
                onNewRun={openNewRun}
                filteredRunIds={
                  (runFilters.search || runFilters.status || runFilters.dateRange)
                    ? new Set(filteredRuns.map(r => r.id))
                    : undefined
                }
              />
            </aside>
            <RunDetailPane pid={mpid || ""} projectId={projectId} runId={selectedRunId} />
          </div>
        </div>
      )}

      {/* ── Modals ─────────────────────────────────────────────────────────── */}
      {showNewCase && (
        <NewCaseModal
          pid={mpid || ""} suites={suites} folders={folders}
          defSuiteId={node.type === "suite" ? node.id : node.type === "folder" ? node.suiteId : undefined}
          defFolderId={node.type === "folder" ? node.id : undefined}
          onClose={() => setShowNewCase(false)}
          onDone={tc => { setShowNewCase(false); setSelId(tc.id); }}
        />
      )}
      {showNewRun && (
        <NewRunModal
          pid={mpid || ""} cases={active} initialCaseIds={runInitCaseIds}
          onClose={() => setShowNewRun(false)} onDone={onRunCreated}
        />
      )}
    </div>
  );
}
