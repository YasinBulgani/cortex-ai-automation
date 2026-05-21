"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors, DragEndEvent, DragStartEvent, DragOverlay,
} from "@dnd-kit/core";
import {
  arrayMove, SortableContext, sortableKeyboardCoordinates,
  verticalListSortingStrategy, useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  PageHeader,
  SectionCard,
  ProgressBar,
  EmptyState,
  StatCard,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";

type SetRow = {
  id: string;
  name: string;
  description: string;
  scenario_count: number;
  item_count: number;
  created_at: string | null;
  coverage_pct?: number;
};

type SuggestedSet = {
  name: string;
  description: string;
  scenario_ids: string[];
  priority: string;
};

const PRIORITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 border-red-500/20 text-red-400",
  high:     "bg-orange-500/10 border-orange-500/20 text-orange-400",
  medium:   "bg-blue-500/10 border-blue-500/20 text-blue-400",
  low:      "bg-slate-800 border-slate-700 text-slate-400",
};
const PRIORITY_LABELS: Record<string, string> = {
  critical: "Kritik", high: "Yüksek", medium: "Orta", low: "Düşük",
};

/* ── Sortable Row ─────────────────────────────────────────────────────────── */
function SortableSetRow({ row, projectId }: { row: SetRow; projectId: string }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: row.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };
  const count = row.scenario_count ?? row.item_count ?? 0;
  const coverage = row.coverage_pct ?? Math.min(100, count * 8);

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className="group border-b border-slate-800 transition-colors hover:bg-slate-800/40"
    >
      <td className="w-8 pl-2">
        <button
          type="button"
          aria-label="Sürükle"
          className="cursor-grab touch-none rounded p-1 text-slate-600 transition-colors hover:text-slate-400"
          {...attributes}
          {...listeners}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
            <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 5A.75.75 0 012.75 9h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 9.75zm0 5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z" clipRule="evenodd" />
          </svg>
        </button>
      </td>
      <td className="px-4 py-3">
        <Link
          href={`/p/${projectId}/regression/${row.id}`}
          className="text-sm font-medium text-white transition-colors hover:text-blue-400"
        >
          {row.name}
        </Link>
        {row.description && (
          <p className="mt-0.5 max-w-64 truncate text-xs text-slate-500">{row.description}</p>
        )}
      </td>
      <td className="px-4 py-3">
        <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-300">
          {count} senaryo
        </span>
      </td>
      <td className="min-w-36 px-4 py-3">
        <ProgressBar value={coverage} color="emerald" height="sm" />
        <div className="mt-1 text-xs text-slate-500">{coverage.toFixed(0)}% kapsam</div>
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {row.created_at
          ? new Date(row.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })
          : "—"}
      </td>
      <td className="px-4 py-3">
        <Link
          href={`/p/${projectId}/regression/${row.id}`}
          className="inline-flex rounded-lg px-2 py-1 text-xs text-slate-400 opacity-0 transition-all hover:bg-slate-700 hover:text-white group-hover:opacity-100"
        >
          Düzenle →
        </Link>
      </td>
    </tr>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function RegressionSetsPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const [rows, setRows] = useState<SetRow[]>([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [sortMode, setSortMode] = useState(false);
  const [activeItem, setActiveItem] = useState<SetRow | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestedSet[] | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [accepting, setAccepting] = useState(false);
  const [extraInstructions, setExtraInstructions] = useState("");

  const load = useCallback(() => {
    apiFetch<SetRow[]>(`/api/v1/tspm/projects/${projectId}/regression-sets`).then(setRows).catch(() => {});
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragStart(event: DragStartEvent) {
    const found = rows.find(r => r.id === event.active.id);
    setActiveItem(found ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveItem(null);
    if (!over || active.id === over.id) return;
    setRows(prev => {
      const oldIdx = prev.findIndex(r => r.id === active.id);
      const newIdx = prev.findIndex(r => r.id === over.id);
      return arrayMove(prev, oldIdx, newIdx);
    });
  }

  async function handleSuggest() {
    setSuggesting(true);
    try {
      const result = await apiFetch<SuggestedSet[]>(
        `/api/v1/tspm/projects/${projectId}/regression-sets/suggest`,
        { method: "POST", json: { extra: extraInstructions } },
      );
      setSuggestions(result);
      setSelected(new Set());
    } catch {
      // silent
    } finally {
      setSuggesting(false);
    }
  }

  async function acceptSelected() {
    if (!suggestions) return;
    setAccepting(true);
    try {
      const chosen = suggestions.filter((_, i) => selected.has(i));
      await Promise.all(
        chosen.map(s =>
          apiFetch(`/api/v1/tspm/projects/${projectId}/regression-sets`, {
            method: "POST",
            json: { name: s.name, description: s.description },
          }),
        ),
      );
      setSuggestions(null);
      setSelected(new Set());
      load();
    } catch {
      // silent
    } finally {
      setAccepting(false);
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const rs = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/regression-sets`, {
        method: "POST",
        json: { name: name.trim() || "Regresyon seti" },
      });
      setName("");
      router.push(`/p/${projectId}/regression/${rs.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    }
  }

  const totalScenarios = rows.reduce((a, r) => a + (r.scenario_count ?? r.item_count ?? 0), 0);

  /* Stats */
  const totalSets = rows.length;
  const totalScenariosInSets = rows.reduce((acc, r) => acc + (r.scenario_count ?? r.item_count ?? 0), 0);
  const avgCoverage = rows.length > 0
    ? Math.round(
        rows.reduce((acc, r) => acc + (r.coverage_pct ?? Math.min(100, (r.scenario_count ?? r.item_count ?? 0) * 8)), 0) / rows.length
      )
    : 0;
  const avgCovColor: "emerald" | "amber" | "red" | "slate" =
    totalSets === 0 ? "slate" : avgCoverage >= 70 ? "emerald" : avgCoverage >= 40 ? "amber" : "red";

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="regression-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        }
        title="Regresyon Setleri"
        description="Test regresyon setlerini yönetin, önceliklendirin ve AI ile keşfedin"
        right={
          <ToolbarActions>
            <button
              onClick={handleSuggest}
              disabled={suggesting}
              className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-300 transition-all hover:border-violet-500/50 hover:text-violet-300 disabled:opacity-50"
              data-testid="regression-btn-suggest"
            >
              {suggesting ? (
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-600 border-t-violet-400" />
              ) : (
                <svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              )}
              AI Öner
            </button>
          </ToolbarActions>
        }
      />

      {/* Stats */}
      <MetricRow cols={3} className="mb-5">
        <StatCard label="Toplam Set" value={totalSets} color="slate" />
        <StatCard label="Kapsanan Senaryo" value={totalScenariosInSets} color="blue" />
        <StatCard
          label="Ortalama Kapsam"
          value={totalSets === 0 ? "—" : `${avgCoverage}%`}
          color={avgCovColor}
        />
      </MetricRow>

      {/* Create form */}
      <SectionCard title="Yeni Set Oluştur" className="mb-4">
        <form onSubmit={create} className="flex gap-2" data-testid="regression-form">
          <input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Set adı..."
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 transition-colors focus:border-slate-500 focus:outline-none"
            data-testid="regression-input-name"
          />
          <button
            type="submit"
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
            data-testid="regression-btn-create"
          >
            Oluştur
          </button>
        </form>
        {err && <p className="mt-2 text-sm text-red-400">{err}</p>}
      </SectionCard>

      {/* AI Suggestions panel */}
      {suggestions && (
        <SectionCard
          title="AI Set Önerileri"
          icon={<svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          className="mb-4 border-violet-500/20"
          right={
            <div className="flex items-center gap-2">
              <button
                onClick={() => { setSuggestions(null); setSelected(new Set()); }}
                className="rounded px-2 py-1 text-xs text-slate-400 transition-colors hover:text-white"
              >
                Kapat
              </button>
              <button
                onClick={acceptSelected}
                disabled={selected.size === 0 || accepting}
                className="rounded-lg bg-violet-600 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
              >
                {accepting ? "Oluşturuluyor..." : `Seçilenleri Oluştur (${selected.size})`}
              </button>
            </div>
          }
        >
          <p className="mb-3 text-xs text-slate-400">{suggestions.length} set önerisi — kabul etmek istediklerinizi seçin</p>

          <div className="mb-3 flex gap-2">
            <input
              value={extraInstructions}
              onChange={e => setExtraInstructions(e.target.value)}
              placeholder="Ek talimat (opsiyonel)"
              className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-white placeholder-slate-500 transition-colors focus:border-slate-500 focus:outline-none"
            />
            <button
              onClick={handleSuggest}
              disabled={suggesting}
              className="rounded-lg border border-violet-500/30 px-3 py-1.5 text-xs font-medium text-violet-300 transition-all hover:bg-violet-500/10 disabled:opacity-50"
            >
              Tekrar Öner
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {suggestions.map((s, i) => {
              const isSelected = selected.has(i);
              const pBadge = PRIORITY_BADGE[s.priority] ?? PRIORITY_BADGE.medium;
              return (
                <label
                  key={i}
                  className={`flex cursor-pointer gap-3 rounded-xl border p-4 transition-all ${
                    isSelected ? "border-violet-500/40 bg-violet-500/5" : "border-slate-700 bg-slate-800/30 opacity-60"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {
                      setSelected(prev => {
                        const n = new Set(prev);
                        if (n.has(i)) n.delete(i); else n.add(i);
                        return n;
                      });
                    }}
                    className="mt-1 shrink-0 cursor-pointer rounded border-slate-600 text-violet-500 focus:ring-violet-500/30"
                  />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-white">{s.name}</span>
                      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${pBadge}`}>
                        {PRIORITY_LABELS[s.priority] ?? s.priority}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400">{s.description}</p>
                    <p className="mt-2 text-xs font-medium text-violet-400">{s.scenario_ids.length} senaryo</p>
                  </div>
                </label>
              );
            })}
          </div>
        </SectionCard>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-slate-700 bg-slate-900/40">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="w-8 pl-2" />
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Set Adı</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Senaryo</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Kapsam</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
                <th className="px-4 py-2.5 text-left" />
              </tr>
            </thead>
            <SortableContext items={rows.map(r => r.id)} strategy={verticalListSortingStrategy}>
              <tbody>
                {sortMode ? (
                  rows.map(r => (
                    <SortableSetRow key={r.id} row={r} projectId={projectId} />
                  ))
                ) : (
                  rows.map(r => {
                    const count = r.scenario_count ?? r.item_count ?? 0;
                    return (
                      <tr key={r.id} className="border-b border-slate-800 hover:bg-slate-800/40 transition-colors group">
                        <td className="w-8 pl-2" />
                        <td className="px-4 py-3">
                          <Link href={`/p/${projectId}/regression/${r.id}`} className="text-sm font-medium text-white hover:text-blue-400 transition-colors">
                            {r.name}
                          </Link>
                          {r.description && <p className="text-xs text-slate-500 mt-0.5 truncate max-w-64">{r.description}</p>}
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                            {count} senaryo
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          {r.created_at ? new Date(r.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" }) : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            href={`/p/${projectId}/regression/${r.id}`}
                            className="opacity-0 group-hover:opacity-100 text-xs px-2 py-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-all inline-flex"
                          >
                            Düzenle →
                          </Link>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </SortableContext>
          </table>

          <DragOverlay>
            {activeItem && (
              <div className="rounded-xl border border-violet-500/20 bg-slate-800 px-4 py-3 text-sm text-white shadow-xl">
                {activeItem.name}
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>
    </div>
  );
}
