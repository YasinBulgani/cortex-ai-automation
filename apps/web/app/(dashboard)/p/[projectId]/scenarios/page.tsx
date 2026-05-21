"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

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
import { FlowGuideCard } from "@/components/FlowGuideCard";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";
import {
  PageHeader,
  StatCard,
  StatusBadge,
  FilterBar,
  EmptyState,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";

type Scenario = {
  id: string;
  title: string;
  status: string;
  current_version: number;
  updated_at?: string | null;
  tags?: string[];
};

/* ── Drag Handle ─────────────────────────────────────────────────────────── */
function DragHandle(props: Record<string, unknown>) {
  return (
    <button
      type="button"
      aria-label="Sürükle"
      className="cursor-grab touch-none rounded p-1 text-slate-600 transition-colors hover:text-slate-400 active:cursor-grabbing"
      {...props}
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
        <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 5A.75.75 0 012.75 9h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 9.75zm0 5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z" clipRule="evenodd" />
      </svg>
    </button>
  );
}

/* ── Sortable Row ─────────────────────────────────────────────────────────── */
function SortableRow({
  scenario, projectId, selected, onToggle,
}: {
  scenario: Scenario; projectId: string; selected: boolean; onToggle: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: scenario.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  const updatedAt = scenario.updated_at
    ? new Date(scenario.updated_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })
    : "—";

  return (
    <tr
      ref={setNodeRef}
      style={style}
      className="group border-b border-slate-800 transition-colors hover:bg-slate-800/40"
      data-testid={`scenarios-row-${scenario.id}`}
    >
      {/* Drag */}
      <td className="w-8 pl-2">
        <DragHandle {...attributes} {...listeners} data-testid={`scenarios-drag-${scenario.id}`} />
      </td>

      {/* Checkbox */}
      <td className="w-8 px-2">
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          aria-label={scenario.title}
          className="cursor-pointer rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500/30"
          data-testid={`scenarios-check-${scenario.id}`}
        />
      </td>

      {/* Title */}
      <td className="px-4 py-3">
        <Link
          href={`/p/${projectId}/scenarios/${scenario.id}`}
          className="text-sm font-medium text-white transition-colors hover:text-blue-400"
          data-testid={`scenarios-link-${scenario.id}`}
        >
          {scenario.title}
        </Link>
        {scenario.tags && scenario.tags.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1">
            {scenario.tags.slice(0, 3).map(t => (
              <span key={t} className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                {t}
              </span>
            ))}
          </div>
        )}
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <StatusBadge status={scenario.status} />
      </td>

      {/* Version */}
      <td className="px-4 py-3">
        <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-400">
          v{scenario.current_version}
        </span>
      </td>

      {/* Updated */}
      <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">{updatedAt}</td>

      {/* Actions */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          <Link
            href={`/p/${projectId}/scenarios/${scenario.id}`}
            className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
            title="Düzenle"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </Link>
        </div>
      </td>
    </tr>
  );
}

/* ── Main Page ────────────────────────────────────────────────────────────── */
export default function ScenariosPage() {
  const projectId = useRouteParam("projectId");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [reorderError, setReorderError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiFetch<Scenario[]>(`/api/v1/tspm/projects/${projectId}/scenarios`);
      setScenarios(data);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  const filtered = scenarios.filter(s =>
    s.title.toLowerCase().includes(search.toLowerCase()) &&
    (!statusFilter || s.status === statusFilter),
  );

  const allSelected = filtered.length > 0 && filtered.every(s => selected.has(s.id));
  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(filtered.map(s => s.id)));
  };

  function handleDragStart(e: DragStartEvent) { setActiveId(String(e.active.id)); }
  function handleDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const oldIdx = scenarios.findIndex(s => s.id === active.id);
    const newIdx = scenarios.findIndex(s => s.id === over.id);
    const prev = scenarios;
    const next = arrayMove(scenarios, oldIdx, newIdx);
    setScenarios(next);
    setReorderError(null);
    apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/reorder`, {
      method: "POST",
      json: { order: next.map(s => s.id) },
    }).catch(() => {
      setScenarios(prev);
      setReorderError("Sıralama kaydedilemedi — değişiklik geri alındı.");
      setTimeout(() => setReorderError(null), 4000);
    });
  }

  const handleGenerate = async () => {
    const ids = selected.size > 0 ? [...selected] : scenarios.map(s => s.id);
    if (ids.length === 0) return;
    setGenerating(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/ai-generate`, {
        method: "POST",
        json: { scenario_ids: ids },
      });
      await load();
    } catch { /* ignore */ }
    finally { setGenerating(false); }
  };

  const handleBulkDelete = async () => {
    if (selected.size === 0) return;
    const ids = [...selected];
    const previous = scenarios;
    setScenarios((current) => current.filter((scenario) => !selected.has(scenario.id)));
    setSelected(new Set());
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/scenarios/bulk-delete`, {
        method: "POST",
        json: { ids },
      });
      await load();
    } catch {
      setScenarios(previous);
      setReorderError("Seçilen senaryolar silinemedi.");
      setTimeout(() => setReorderError(null), 4000);
    }
  };

  const activeScenario = activeId ? scenarios.find(s => s.id === activeId) : null;
  const total = scenarios.length;
  const active = scenarios.filter(s => s.status === "active").length;
  const draft = scenarios.filter(s => s.status === "draft").length;
  const archived = scenarios.filter(s => s.status === "archived").length;

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      {reorderError && (
        <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-950/80 px-4 py-2.5 text-sm text-red-300 shadow-xl backdrop-blur">
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          {reorderError}
        </div>
      )}

      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        }
        title="Senaryolar"
        description="Test senaryolarını yönetin"
        right={
          <ToolbarActions>
            <Link
              href={`/p/${projectId}/scenarios/generate`}
              className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm font-medium text-slate-300 transition-all hover:border-slate-500 hover:text-white"
              data-testid="scenarios-bdd-btn"
            >
              <svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              BDD Üret
            </Link>
            <Link
              href={`/p/${projectId}/scenarios/new`}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              data-testid="scenarios-new-btn"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Yeni Senaryo
            </Link>
          </ToolbarActions>
        }
      />

      <div className="mb-5">
        <FlowGuideCard projectId={projectId} stage="design" />
      </div>

      {/* Pilot + Jira hızlı erişim banner — Yeni Senaryo akışına yönlendirir */}
      <div className="mb-5 grid gap-3 sm:grid-cols-2" data-testid="scenarios-quick-actions">
        <Link
          href={`/p/${projectId}/scenarios/new?source=jira`}
          data-testid="quick-action-jira"
          className="flex items-start gap-3 rounded-xl border border-blue-700/30 bg-blue-950/20 px-4 py-3 text-left hover:border-blue-500/50 transition"
        >
          <span className="text-2xl">📥</span>
          <div>
            <h3 className="text-sm font-semibold text-blue-200">Jira / Doküman içe aktar</h3>
            <p className="text-xs text-blue-300/70">Issue key veya yapıştırılmış metinden senaryo + AC üret.</p>
          </div>
        </Link>
        <Link
          href={`/p/${projectId}/sifir-bilgi`}
          data-testid="quick-action-sifir-bilgi"
          className="flex items-start gap-3 rounded-xl border border-violet-700/30 bg-violet-950/20 px-4 py-3 text-left hover:border-violet-500/50 transition"
        >
          <span className="text-2xl">🤖</span>
          <div>
            <h3 className="text-sm font-semibold text-violet-200">Sıfır Bilgi — 9 Ajanlı Pipeline</h3>
            <p className="text-xs text-violet-300/70">Analyst → Explorer → Locator → Scenario → Coder → Runner → Healer → Reviewer → Reporter (canlı SSE).</p>
          </div>
        </Link>
      </div>

      {/* Stats */}
      <MetricRow cols={4} className="mb-5">
        <div data-testid="dashboard-stat-scenario-count"><StatCard label="Toplam" value={total} color="slate" /></div>
        <StatCard label="Aktif" value={active} color="emerald" />
        <StatCard label="Taslak" value={draft} color="slate" />
        <StatCard label="Arşiv" value={archived} color="red" />
      </MetricRow>

      {/* Search */}
      <div className="mb-4">
        <FilterBar
          search={search}
          onSearch={setSearch}
          searchPlaceholder="Senaryo ara..."
          filters={[
            {
              key: "status",
              label: "Tüm Durumlar",
              value: statusFilter,
              onChange: setStatusFilter,
              options: [
                { label: "Aktif", value: "active" },
                { label: "Taslak", value: "draft" },
                { label: "Arşiv", value: "archived" },
              ],
            },
          ]}
          right={
            selected.size > 0 ? (
              <div data-testid="bulk-actions" className="flex items-center gap-2">
                <span className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-400">
                  {selected.size} seçili
                </span>
                <button
                  type="button"
                  onClick={handleBulkDelete}
                  className="rounded-lg border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs font-medium text-red-300 transition-colors hover:bg-red-500/20"
                >
                  Seçilenleri sil
                </button>
              </div>
            ) : undefined
          }
        />
      </div>

      {/* Table */}
      <div data-testid="scenario-table" className="overflow-hidden rounded-xl border border-slate-700 bg-slate-900/40">
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
                <th className="w-8 px-2">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    data-testid="select-all-checkbox"
                    className="cursor-pointer rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500/30"
                  />
                </th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Senaryo Başlığı</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Durum</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Versiyon</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Son Güncelleme</th>
                <th className="w-20 px-4 py-2.5 text-left" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center text-sm text-slate-500">
                    <div className="flex items-center justify-center gap-2">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-blue-400" />
                      Yükleniyor...
                    </div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <EmptyState
                      icon="🧪"
                      title="Senaryo bulunamadı"
                      description={search || statusFilter ? "Arama kriterlerinizi değiştirmeyi deneyin" : "İlk test senaryonuzu oluşturun"}
                      action={
                        !search && !statusFilter ? (
                          <Link
                            href={`/p/${projectId}/scenarios/new`}
                            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
                          >
                            Senaryo Oluştur
                          </Link>
                        ) : undefined
                      }
                    />
                  </td>
                </tr>
              ) : (
                <SortableContext items={filtered.map(s => s.id)} strategy={verticalListSortingStrategy}>
                  {filtered.map(s => (
                    <SortableRow
                      key={s.id}
                      scenario={s}
                      projectId={projectId}
                      selected={selected.has(s.id)}
                      onToggle={() => setSelected(prev => {
                        const next = new Set(prev);
                        if (next.has(s.id)) next.delete(s.id); else next.add(s.id);
                        return next;
                      })}
                    />
                  ))}
                </SortableContext>
              )}
            </tbody>
          </table>

          <DragOverlay>
            {activeScenario && (
              <div className="flex items-center gap-3 rounded-xl border border-blue-500/30 bg-slate-800 px-4 py-3 text-sm text-white shadow-xl">
                <DragHandle />
                <span className="font-medium">{activeScenario.title}</span>
                <StatusBadge status={activeScenario.status} />
              </div>
            )}
          </DragOverlay>
        </DndContext>

        {filtered.length > 0 && (
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-2.5">
            <span className="text-xs text-slate-500">{filtered.length} senaryo</span>
            {selected.size > 0 && (
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="text-xs text-violet-400 transition-colors hover:text-violet-300 disabled:opacity-50"
              >
                {selected.size} senaryo için AI kod üret →
              </button>
            )}
          </div>
        )}
      </div>
      <PageFeedbackWidget />

    </div>
  );
}
