"use client";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  DndContext, DragEndEvent, DragOverlay, DragStartEvent,
  closestCorners, KeyboardSensor, PointerSensor, useSensor, useSensors,
} from "@dnd-kit/core";
import {
  SortableContext, sortableKeyboardCoordinates,
  verticalListSortingStrategy, useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useDroppable } from "@dnd-kit/core";
import {
  PageHeader,
  StatCard,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";

type Approval = {
  id: string;
  source_text: string;
  draft_payload: Record<string, unknown> | null;
  status: string;
  decision: string | null;
};

type ColumnId = "pending" | "approved" | "rejected";

const COLUMNS: { id: ColumnId; title: string; dot: string; countColor: string }[] = [
  { id: "pending",  title: "Bekleyen",   dot: "bg-amber-400",  countColor: "text-amber-400" },
  { id: "approved", title: "Onaylanan",  dot: "bg-emerald-400", countColor: "text-emerald-400" },
  { id: "rejected", title: "Reddedilen", dot: "bg-red-400",    countColor: "text-red-400" },
];

function mapStatusToColumn(_status: string, decision: string | null): ColumnId {
  if (decision === "approved") return "approved";
  if (decision === "rejected") return "rejected";
  return "pending";
}

/* ── Kanban Column ────────────────────────────────────────────────────────── */
function KanbanColumn({
  id, title, dot, countColor, count, children,
}: { id: string; title: string; dot: string; countColor: string; count: number; children: React.ReactNode }) {
  const { isOver, setNodeRef } = useDroppable({ id });
  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col rounded-xl border transition-all ${
        isOver ? "border-blue-500/40 bg-blue-500/5" : "border-slate-700 bg-slate-900/40"
      }`}
      style={{ minHeight: 400 }}
      data-testid={`kanban-column-${id}`}
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <span className={`ml-auto text-sm font-bold ${countColor}`}>{count}</span>
      </div>
      <div className="flex-1 space-y-2 overflow-auto p-3">{children}</div>
    </div>
  );
}

/* ── Sortable Card ────────────────────────────────────────────────────────── */
function SortableCard({
  approval, isActive, onSelect,
}: { approval: Approval; isActive: boolean; onSelect: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: approval.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={onSelect}
      className={`group cursor-grab rounded-xl border p-3 transition-all active:cursor-grabbing ${
        isActive
          ? "border-blue-500/40 bg-blue-500/5 shadow-md"
          : "border-slate-700 bg-slate-800/40 hover:border-slate-600 hover:bg-slate-800/60"
      }`}
      data-testid={`approvals-card-${approval.id}`}
      {...attributes}
      {...listeners}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-slate-500">{approval.id.slice(0, 8)}...</span>
        <svg className="w-3 h-3 text-slate-600 group-hover:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </div>
      <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">
        {approval.source_text?.slice(0, 120) || "Kaynak metin yok"}
        {(approval.source_text?.length ?? 0) > 120 ? "..." : ""}
      </p>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function ApprovalsPage() {
  const projectId = useRouteParam("projectId");
  const [rows, setRows] = useState<Approval[]>([]);
  const [active, setActive] = useState<Approval | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [deciding, setDeciding] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const load = useCallback(() => {
    apiFetch<Approval[]>(`/api/v1/tspm/projects/${projectId}/approvals`).then(setRows).catch(() => {});
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const columnData = COLUMNS.map(col => ({
    ...col,
    items: rows.filter(r => mapStatusToColumn(r.status, r.decision) === col.id),
  }));

  async function decide(approvalId: string, decision: "approved" | "rejected" | "edited") {
    setDeciding(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/approvals/${approvalId}/decide`, {
        method: "POST", json: { decision, notes: "" },
      });
      setActive(null); load();
    } finally { setDeciding(false); }
  }

  async function batchApprove() {
    const pending = rows.filter(r => mapStatusToColumn(r.status, r.decision) === "pending");
    for (const p of pending) {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/approvals/${p.id}/decide`, {
        method: "POST", json: { decision: "approved", notes: "" },
      });
    }
    load();
  }

  function findColumnForItem(itemId: string): ColumnId | undefined {
    const item = rows.find(r => r.id === itemId);
    if (!item) return undefined;
    return mapStatusToColumn(item.status, item.decision);
  }

  function handleDragStart(e: DragStartEvent) { setActiveId(e.active.id as string); }

  async function handleDragEnd(e: DragEndEvent) {
    const { active: dragActive, over } = e;
    setActiveId(null);
    if (!over) return;
    const itemId = dragActive.id as string;
    const sourceCol = findColumnForItem(itemId);
    const targetCol = (COLUMNS.find(c => c.id === over.id)?.id ?? findColumnForItem(over.id as string)) as ColumnId | undefined;
    if (!sourceCol || !targetCol || sourceCol === targetCol) return;
    if (targetCol === "approved") await decide(itemId, "approved");
    else if (targetCol === "rejected") await decide(itemId, "rejected");
  }

  const dragItem = activeId ? rows.find(r => r.id === activeId) : null;
  const pendingCount = columnData.find(c => c.id === "pending")?.items.length ?? 0;
  const approvedCount = columnData.find(c => c.id === "approved")?.items.length ?? 0;
  const rejectedCount = columnData.find(c => c.id === "rejected")?.items.length ?? 0;

  return (
    <div className="flex min-h-screen flex-col gap-4 bg-slate-950 p-6" data-testid="approvals-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        }
        title="Onay Kuyruğu"
        description="Kartları sürükleyerek onaylayın veya reddedin"
        right={
          <ToolbarActions>
            {pendingCount > 0 && (
              <button
                onClick={batchApprove}
                className="flex items-center gap-2 rounded-lg border border-emerald-500/30 px-3 py-1.5 text-sm font-medium text-emerald-300 transition-all hover:bg-emerald-500/10"
                data-testid="approvals-btn-batch"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Tümünü Onayla ({pendingCount})
              </button>
            )}
          </ToolbarActions>
        }
      />

      {/* Stats */}
      <MetricRow cols={3}>
        <StatCard label="Bekleyen" value={pendingCount} color={pendingCount > 0 ? "amber" : "slate"} />
        <StatCard label="Onaylanan" value={approvedCount} color="emerald" />
        <StatCard label="Reddedilen" value={rejectedCount} color={rejectedCount > 0 ? "red" : "slate"} />
      </MetricRow>

      {/* Kanban board */}
      <div className="grid gap-4 flex-1" style={{ gridTemplateColumns: active ? "1fr 1fr 1fr" : "repeat(3, 1fr)" }}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          {columnData.map(col => (
            <SortableContext key={col.id} items={col.items.map(i => i.id)} strategy={verticalListSortingStrategy}>
              <KanbanColumn id={col.id} title={col.title} dot={col.dot} countColor={col.countColor} count={col.items.length}>
                {col.items.map(item => (
                  <SortableCard
                    key={item.id}
                    approval={item}
                    isActive={active?.id === item.id}
                    onSelect={() => setActive(active?.id === item.id ? null : item)}
                  />
                ))}
                {col.items.length === 0 && (
                  <div className="py-8 text-center text-xs text-slate-600 border-2 border-dashed border-slate-800 rounded-xl mt-2">
                    Buraya sürükleyin
                  </div>
                )}
              </KanbanColumn>
            </SortableContext>
          ))}

          <DragOverlay>
            {dragItem && (
              <div className="w-64 rounded-xl border border-blue-500/30 bg-slate-800 p-3 shadow-xl">
                <span className="font-mono text-xs text-slate-500">{dragItem.id.slice(0, 8)}...</span>
                <p className="mt-1 text-xs text-slate-300 line-clamp-2">{dragItem.source_text?.slice(0, 80) || "—"}</p>
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Detail panel */}
      {active && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
          <div className="grid gap-4 md:grid-cols-2 mb-4">
            <div>
              <h3 className="text-xs font-medium text-slate-400 mb-2">Kaynak Metin</h3>
              <pre className="text-xs text-slate-300 whitespace-pre-wrap overflow-auto max-h-40 bg-slate-950 rounded-lg p-3 border border-slate-800">
                {active.source_text || "—"}
              </pre>
            </div>
            <div>
              <h3 className="text-xs font-medium text-slate-400 mb-2">AI Taslağı</h3>
              <pre className="text-xs text-slate-300 overflow-auto max-h-40 bg-slate-950 rounded-lg p-3 border border-slate-800">
                {JSON.stringify(active.draft_payload, null, 2) || "—"}
              </pre>
            </div>
          </div>

          {active.status === "pending" && !active.decision && (
            <div className="flex gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => decide(active.id, "approved")}
                disabled={deciding}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 rounded-xl transition-colors disabled:opacity-50"
                data-testid="approvals-btn-approve"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Onayla
              </button>
              <button
                onClick={() => decide(active.id, "rejected")}
                disabled={deciding}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-red-300 border border-red-500/30 hover:bg-red-500/10 rounded-xl transition-colors disabled:opacity-50"
                data-testid="approvals-btn-reject"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Reddet
              </button>
              <button
                onClick={() => setActive(null)}
                className="px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors ml-auto"
              >
                Kapat
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
