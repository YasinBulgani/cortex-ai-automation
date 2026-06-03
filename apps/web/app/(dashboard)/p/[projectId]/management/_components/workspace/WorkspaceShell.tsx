"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
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
  useBulkUpdateCases,
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
import { type WsNode, R_DOT, P_DOT, TYPE_COLOR, AUTO_DOT, RUN_STATUS_DOT, RUN_STATUS_LABEL } from "./shared";

type DragData =
  | { kind: "case"; caseId: string }
  | { kind: "suite"; suiteId: string }
  | { kind: "folder"; folderId: string; suiteId: string; parentId: string | null }
  | { kind: "allDrop" };

// ─── Minimal Icons ────────────────────────────────────────────────────────────

function IcCheck() {
  return <svg className="h-2.5 w-2.5" fill="none" viewBox="0 0 10 10" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M1.5 5l2.5 2.5 4.5-4.5" /></svg>;
}
function IcSearch() {
  return <svg className="h-3.5 w-3.5 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>;
}
function IcGrip() {
  return <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 16 16"><circle cx="5" cy="4" r="1.2" /><circle cx="11" cy="4" r="1.2" /><circle cx="5" cy="8" r="1.2" /><circle cx="11" cy="8" r="1.2" /><circle cx="5" cy="12" r="1.2" /><circle cx="11" cy="12" r="1.2" /></svg>;
}
function IcEdit() {
  return <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>;
}

// ─── Case Row ─────────────────────────────────────────────────────────────────

function CaseRow({ tc, selected, onSelect, checked, onCheck, projectId }: {
  tc: TestCase; selected: boolean; onSelect: () => void;
  checked: boolean; onCheck: (e: React.MouseEvent) => void; projectId: string;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable(tc.id);
  const rd  = tc.last_run_status ? (R_DOT[tc.last_run_status] ?? null) : null;
  const ad  = AUTO_DOT[tc.automation_status] ?? AUTO_DOT.not_automated;

  return (
    <tr
      ref={setNodeRef}
      onClick={onSelect}
      className={cn(
        "group border-b border-border/40 cursor-pointer select-none",
        isDragging  && "opacity-30",
        selected    && "bg-brand-soft",
        !selected   && "hover:bg-surface-overlay",
      )}
    >
      {/* Grip */}
      <td className="hidden w-5 pl-1.5 sm:table-cell">
        <button type="button" {...attributes} {...listeners}
          className="invisible group-hover:visible cursor-grab active:cursor-grabbing touch-none text-fg-subtle hover:text-fg p-0.5">
          <IcGrip />
        </button>
      </td>

      {/* Checkbox */}
      <td className="w-8 px-2">
        <button type="button" onClick={onCheck}
          className={cn("flex h-4 w-4 items-center justify-center rounded border transition-colors",
            checked ? "border-brand bg-brand text-brand-fg" : "border-border-strong bg-surface-raised hover:border-brand")}>
          {checked && <IcCheck />}
        </button>
      </td>

      {/* ID — TestRail-style colored badge */}
      <td className="w-24 px-3 py-2.5">
        <Link
          href={`/p/${projectId}/management/cases/${tc.id}`}
          onClick={e => e.stopPropagation()}
          className="inline-flex items-center rounded-md border border-brand/20 bg-brand-soft px-1.5 py-0.5 font-mono text-[10px] font-semibold text-brand transition-colors hover:border-brand/35 hover:bg-surface-accent"
        >
          {tc.case_key}
        </Link>
      </td>

      {/* Title */}
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", ad.dot)} title={ad.label} />
          <span className="text-[13px] text-fg line-clamp-1 transition-colors">
            {tc.title}
          </span>
        </div>
        {tc.tags && tc.tags.length > 0 && (
          <div className="mt-1 flex gap-1">
            {tc.tags.slice(0, 3).map(t => (
              <span key={t} className="rounded bg-surface-accent px-1.5 py-0.5 text-[10px] text-fg-subtle">{t}</span>
            ))}
          </div>
        )}
      </td>

      {/* Priority */}
      <td className="w-14 px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className={cn("h-1.5 w-1.5 rounded-full", P_DOT[tc.priority] ?? P_DOT.P3)} />
          <span className="text-[11px] text-fg-subtle font-mono">{tc.priority}</span>
        </div>
      </td>

      {/* Type */}
      <td className="hidden w-24 px-3 py-2.5 lg:table-cell">
        <span className={cn("rounded-md px-1.5 py-0.5 text-[10px]",
          TYPE_COLOR[tc.type] ?? "bg-slate-500/15 text-fg-subtle")}>
          {tc.type}
        </span>
      </td>

      {/* Last Run */}
      <td className="hidden w-24 px-3 py-2.5 md:table-cell">
        {rd ? (
          <div className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", rd.dot)} />
            <span className="text-[11px] text-fg-subtle">{rd.label}</span>
          </div>
        ) : (
          <span className="text-[11px] text-fg-subtle">—</span>
        )}
      </td>

      {/* Steps */}
      <td className="hidden w-12 px-3 py-2.5 text-[11px] text-fg-subtle tabular-nums xl:table-cell">
        {tc.steps?.length ?? 0}
      </td>

      {/* Edit link */}
      <td className="w-10 px-2">
        <Link href={`/p/${projectId}/management/cases/${tc.id}`}
          onClick={e => e.stopPropagation()}
          className="invisible group-hover:visible inline-flex rounded p-1 text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-all">
          <IcEdit />
        </Link>
      </td>
    </tr>
  );
}

function useDraggable(id: string) {
  const { useDraggable: dnd } = require("@dnd-kit/core");
  return dnd({ id: `case:${id}`, data: { kind: "case", caseId: id } });
}

// ─── Case Table (ultra-clean TestRail style) ──────────────────────────────────

const SEL_CLS = "h-8 rounded-lg border border-border bg-surface-raised px-2.5 text-[11px] font-medium text-fg-muted outline-none transition-colors cursor-pointer hover:border-border-strong focus:border-brand focus:ring-2 focus:ring-brand/15";

function CaseTable({
  nodeName, nodeCases, loading, projectId,
  selId, onSelect, checked, onCheck, onClearChecked, onToggleAll,
  onNewCase, onCreateRun, onPromote, onArchiveMany, onBulkMove, onBulkUpdate, busy,
  suites, folders,
}: {
  nodeName: string; nodeCases: TestCase[]; loading: boolean; projectId: string;
  selId: string | null; onSelect: (id: string) => void;
  checked: Set<string>; onCheck: (id: string) => void;
  onClearChecked: () => void; onToggleAll: (ids: string[]) => void;
  onNewCase: () => void; onCreateRun: () => void;
  onPromote: () => void; onArchiveMany: () => void;
  onBulkMove: (caseId: string, suiteId: string, folderId: string | null) => Promise<void>;
  onBulkUpdate: (payload: { case_ids: string[]; priority?: string; type?: string; status?: string }) => Promise<void>;
  busy: boolean;
  suites: TestSuite[];
  folders: TestFolder[];
}) {
  const [search,    setSearch]    = useState("");
  const [priority,  setPriority]  = useState("");
  const [type,      setType]      = useState("");
  const [status,    setStatus]    = useState("");

  const filtered = useMemo(() => {
    let r = nodeCases;
    const q = search.trim().toLowerCase();
    if (q)        r = r.filter(c => c.title.toLowerCase().includes(q) || c.case_key.toLowerCase().includes(q));
    if (priority) r = r.filter(c => c.priority === priority);
    if (type)     r = r.filter(c => c.type === type);
    if (status)   r = r.filter(c => c.last_run_status === status);
    return r;
  }, [nodeCases, search, priority, type, status]);

  const allChecked = filtered.length > 0 && filtered.every(c => checked.has(c.id));
  const hasFilter  = !!(search || priority || type || status);
  const clearAll   = () => { setSearch(""); setPriority(""); setType(""); setStatus(""); };

  return (
    <div className="flex flex-1 flex-col min-w-0 overflow-hidden">

      {/* ── Toolbar ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-raised px-4 py-3 shadow-xs">
        {/* Section name + count */}
        <span className="mr-1 text-[14px] font-semibold text-fg">{nodeName}</span>
        <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] font-medium tabular-nums text-fg-muted">
          {filtered.length}{hasFilter && `/${nodeCases.length}`}
        </span>
        {/* Quick filters */}
        {nodeCases.some(c => c.last_run_status === "failed") && (
          <button type="button"
            onClick={() => setStatus(status === "failed" ? "" : "failed")}
            className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
              status === "failed" ? "bg-red-500/15 border-red-500/30 text-red-400" : "border-red-500/20 text-red-500/60 hover:text-red-400")}>
            {nodeCases.filter(c => c.last_run_status === "failed").length} fail
          </button>
        )}
        {nodeCases.some(c => c.last_run_status === "blocked") && (
          <button type="button"
            onClick={() => setStatus(status === "blocked" ? "" : "blocked")}
            className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
              status === "blocked" ? "bg-amber-500/15 border-amber-500/30 text-amber-400" : "border-amber-500/20 text-amber-500/60 hover:text-amber-400")}>
            {nodeCases.filter(c => c.last_run_status === "blocked").length} blk
          </button>
        )}

        <div className="flex-1" />

        {/* Search */}
        <div className="flex w-44 items-center gap-1.5 rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 shadow-xs transition-colors focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
          <IcSearch />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Ara…"
            className="flex-1 bg-transparent text-[11px] text-fg placeholder:text-fg-subtle outline-none min-w-0"
          />
        </div>

        {/* Filters */}
        <select value={priority} onChange={e => setPriority(e.target.value)} className={SEL_CLS}>
          <option value="">Öncelik</option>
          {["P0","P1","P2","P3"].map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={type} onChange={e => setType(e.target.value)} className={cn(SEL_CLS, "hidden lg:block")}>
          <option value="">Tür</option>
          {["manual","smoke","regression","uat","exploratory","api","e2e"].map(v =>
            <option key={v} value={v}>{v}</option>
          )}
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)} className={SEL_CLS}>
          <option value="">Koşum</option>
          {["passed","failed","blocked","skipped"].map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        {hasFilter && (
          <button type="button" onClick={clearAll}
            className="text-[11px] text-fg-subtle transition-colors hover:text-danger">Temizle</button>
        )}

        {/* Add case */}
        <button type="button" onClick={onNewCase}
          className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
          + Senaryo
        </button>
      </div>

      {/* ── Bulk action bar ─────────────────────────────────────────────────── */}
      {checked.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-b border-brand/20 bg-brand-soft px-4 py-2">
          <span className="text-[11px] font-semibold text-brand">{checked.size} seçili</span>
          <button type="button" onClick={onCreateRun} disabled={busy}
            className="rounded-md border border-brand/25 bg-surface-raised px-2.5 py-1 text-[11px] font-medium text-brand transition-colors hover:bg-surface-overlay disabled:opacity-40">
            ▶ Run Oluştur
          </button>
          <button type="button" onClick={onPromote} disabled={busy}
            className="rounded border border-border px-2.5 py-1 text-[11px] text-fg-muted hover:text-fg disabled:opacity-40 transition-colors">
            Aktife Al
          </button>
          {/* Bulk priority */}
          <select disabled={busy} onChange={async e => {
            if (!e.target.value) return;
            await onBulkUpdate({ case_ids: [...checked], priority: e.target.value });
            onClearChecked();
            e.target.value = "";
          }}
            className="rounded border border-border bg-surface-raised px-2 py-1 text-[11px] text-fg-muted disabled:opacity-40 outline-none">
            <option value="">Öncelik →</option>
            {["P0","P1","P2","P3"].map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          {/* Bulk move: suite picker */}
          <select disabled={busy} onChange={async e => {
            if (!e.target.value) return;
            const [suiteId, folderId] = e.target.value.split("|");
            const ids = [...checked];
            for (const id of ids) {
              await onBulkMove(id, suiteId, folderId || null);
            }
            onClearChecked();
            e.target.value = "";
          }}
            className="rounded border border-border bg-surface-raised px-2 py-1 text-[11px] text-fg-muted disabled:opacity-40 outline-none">
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
          <button type="button" onClick={onArchiveMany} disabled={busy}
            className="rounded border border-red-500/20 px-2.5 py-1 text-[11px] text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-colors">
            Arşivle
          </button>
          <button type="button" onClick={onClearChecked}
            className="ml-auto text-[11px] text-fg-subtle hover:text-fg-muted">Seçimi Temizle</button>
        </div>
      )}

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
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            {hasFilter ? (
              <>
                <p className="text-[13px] font-medium text-fg-muted">Sonuç bulunamadı</p>
                <button type="button" onClick={clearAll}
                  className="text-[12px] font-medium text-brand transition-colors hover:text-brand-secondary">
                  Filtreleri temizle
                </button>
              </>
            ) : (
              <>
                <p className="text-[13px] font-medium text-fg-muted">Bu bölümde senaryo yok</p>
                <button type="button" onClick={onNewCase}
                  className="rounded-lg bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
                  + İlk senaryoyu ekle
                </button>
              </>
            )}
          </div>
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
                  { label: "ID",       cls: "w-20"                       },
                  { label: "Başlık",   cls: ""                           },
                  { label: "P",        cls: "w-14"                       },
                  { label: "Tür",      cls: "hidden w-24 lg:table-cell"  },
                  { label: "Son Koşum",cls: "hidden w-24 md:table-cell"  },
                  { label: "Adım",     cls: "hidden w-12 xl:table-cell"  },
                  { label: "",         cls: "w-10"                       },
                ].map(({ label, cls }) => (
                  <th key={label}
                    className={cn("px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-muted", cls)}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(tc => (
                <CaseRow
                  key={tc.id} tc={tc}
                  selected={selId === tc.id}
                  onSelect={() => onSelect(tc.id)}
                  checked={checked.has(tc.id)}
                  onCheck={e => { e.stopPropagation(); onCheck(tc.id); }}
                  projectId={projectId}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Footer ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between border-t border-border bg-surface-raised px-4 py-2">
        <span className="text-[10px] text-fg-muted">
          {hasFilter ? `${filtered.length} / ${nodeCases.length} senaryo` : `${nodeCases.length} senaryo`}
        </span>
        {checked.size > 0 && (
          <span className="text-[10px] font-medium text-brand">{checked.size} seçili</span>
        )}
      </div>
    </div>
  );
}

// ─── Run Tab mini header ──────────────────────────────────────────────────────

function RunTabHeader({ onNewRun }: { onNewRun: () => void }) {
  return (
    <div className="flex items-center gap-2 border-b border-border bg-surface-raised px-4 py-3 shadow-xs">
      <span className="text-[14px] font-semibold text-fg">Test Koşumları</span>
      <div className="flex-1" />
      <button type="button" onClick={onNewRun}
        className="rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
        + Yeni Run
      </button>
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
  const allCases= useMemo(() => repoQ.data?.cases ?? [], [repoQ.data]);
  const active  = useMemo(() => allCases.filter(c => !c.archived), [allCases]);
  const runs    = runsQ.data ?? [];

  const moveCase     = useMoveManagementCase(mpid || "");
  const updateSuite  = useUpdateManagementSuite(mpid || "");
  const updateFolder = useUpdateManagementFolder(mpid || "");
  const promote      = usePromoteCases(mpid || "");
  const archive      = useArchiveManagementCase(mpid || "");
  const bulkUpdate   = useBulkUpdateCases(mpid || "");

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

  const nodeName = node.type === "all" ? "Tüm Senaryolar"
    : node.type === "suite"  ? (suites.find(s => s.id === node.id)?.name ?? "Suite")
    : (folders.find(f => f.id === node.id)?.name ?? "Folder");

  const draggingCase   = draggingCaseId ? active.find(c => c.id === draggingCaseId) : null;
  const checkedIds     = useMemo(() => [...checked], [checked]);
  const activeRunCount = runs.filter(r => r.status === "in_progress").length;

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
    try { for (const id of checkedIds) await archive.mutateAsync(id); setChecked(new Set()); }
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
              nodeName={nodeName} nodeCases={nodeCases}
              loading={repoQ.isLoading} projectId={projectId}
              selId={selId} onSelect={id => setSelId(selId === id ? null : id)}
              checked={checked}
              onCheck={id => setChecked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; })}
              onClearChecked={() => setChecked(new Set())}
              onToggleAll={ids => setChecked(new Set(ids))}
              onNewCase={() => setShowNewCase(true)}
              onCreateRun={openNewRun}
              onPromote={onPromote}
              onArchiveMany={onArchiveMany}
              onBulkMove={async (caseId, suiteId, folderId) => {
                await moveCase.mutateAsync({ caseId, suite_id: suiteId, folder_id: folderId });
              }}
              onBulkUpdate={async payload => {
                await bulkUpdate.mutateAsync(payload);
              }}
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
          <RunTabHeader onNewRun={openNewRun} />
          <div className="flex flex-1 min-h-0">
            <aside className="hidden w-[224px] flex-none overflow-hidden border-r border-border bg-surface-raised md:block">
              <RunList
                pid={mpid || ""} selectedRunId={selectedRunId}
                onSelect={setSelectedRunId}
                onNewRun={openNewRun}
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
