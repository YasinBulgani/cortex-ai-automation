"use client";

import { useCallback, useEffect, useState } from "react";

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
  EmptyState,
  SectionCard,
  StatCard,
  MetricRow,
  ToolbarActions,
  FilterBar,
} from "@/components/nexus";

type Requirement = {
  id: string; external_id: string; title: string; description: string;
  priority: string; source: string; scenario_count: number; created_at: string | null;
};

type Form = { external_id: string; title: string; description: string; priority: string; source: string };
const emptyForm: Form = { external_id: "", title: "", description: "", priority: "medium", source: "" };

const PRIORITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 border border-red-500/20 text-red-400",
  high:     "bg-orange-500/10 border border-orange-500/20 text-orange-400",
  medium:   "bg-blue-500/10 border border-blue-500/20 text-blue-400",
  low:      "bg-slate-800 border border-slate-700 text-slate-400",
};
const PRIORITY_LABELS: Record<string, string> = {
  critical: "Kritik", high: "Yüksek", medium: "Orta", low: "Düşük",
};

function SortableRequirementRow({ requirement, onDelete }: { requirement: Requirement; onDelete: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: requirement.id });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  return (
    <tr ref={setNodeRef} style={style} className="group border-b border-slate-800 transition-colors hover:bg-slate-800/40">
      <td className="w-8 pl-2">
        <button
          type="button" aria-label="Sürükle"
          className="cursor-grab touch-none text-slate-600 hover:text-slate-400 p-1 rounded transition-colors"
          {...attributes} {...listeners}
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
            <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 5A.75.75 0 012.75 9h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 9.75zm0 5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z" clipRule="evenodd" />
          </svg>
        </button>
      </td>
      <td className="px-4 py-3">
        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
          {requirement.external_id}
        </span>
      </td>
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-white">{requirement.title}</p>
        {requirement.description && (
          <p className="text-xs text-slate-500 mt-0.5 truncate max-w-48">{requirement.description}</p>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_BADGE[requirement.priority] ?? PRIORITY_BADGE.medium}`}>
          {PRIORITY_LABELS[requirement.priority] ?? requirement.priority}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`text-sm font-semibold ${requirement.scenario_count > 0 ? "text-emerald-400" : "text-slate-500"}`}>
          {requirement.scenario_count ?? 0}
        </span>
        {requirement.source && (
          <div className="text-xs text-slate-600 mt-0.5">{requirement.source}</div>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {requirement.created_at ? new Date(requirement.created_at).toLocaleDateString("tr-TR") : "—"}
      </td>
      <td className="px-4 py-3">
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </td>
    </tr>
  );
}

export default function RequirementsPage() {
  const projectId = useRouteParam("projectId");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [form, setForm] = useState<Form>(emptyForm);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const load = useCallback(() => {
    apiFetch<Requirement[]>(`/api/v1/tspm/projects/${projectId}/requirements`).then(setRequirements).catch((err) => console.warn("[requirements]:", err));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setLoading(true);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/requirements`, { method: "POST", json: form });
      setForm(emptyForm); setShowForm(false); load();
    } finally { setLoading(false); }
  }

  async function handleDelete(id: string) {
    await apiFetch(`/api/v1/tspm/projects/${projectId}/requirements/${id}`, { method: "DELETE" });
    load();
  }

  function handleDragStart(e: DragStartEvent) { setActiveId(e.active.id as string); }
  function handleDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (over && active.id !== over.id) {
      const oi = requirements.findIndex(i => i.id === active.id);
      const ni = requirements.findIndex(i => i.id === over.id);
      setRequirements(arrayMove(requirements, oi, ni));
    }
  }

  const activeItem = activeId ? requirements.find(r => r.id === activeId) : null;
  const filtered = priorityFilter ? requirements.filter(r => r.priority === priorityFilter) : requirements;

  const covered = requirements.filter(r => r.scenario_count > 0).length;
  const covPct = requirements.length > 0 ? Math.round((covered / requirements.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="requirements-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        }
        title="Gereksinimler"
        description="Test senaryolarına bağlı gereksinimleri yönetin ve önceliklendirin"
        right={
          <ToolbarActions>
            <button
              onClick={() => setShowForm(v => !v)}
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
              data-testid="requirements-btn-new"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {showForm ? "İptal" : "Yeni Gereksinim"}
            </button>
          </ToolbarActions>
        }
      />

      {/* Stats */}
      <MetricRow cols={3} className="mb-5">
        <StatCard label="Toplam" value={requirements.length} color="slate" />
        <StatCard label="Kapsanan" value={covered} color="emerald" />
        <StatCard
          label="Kapsam"
          value={requirements.length === 0 ? "—" : `${covPct}%`}
          color={requirements.length === 0 ? "slate" : covPct >= 70 ? "emerald" : "amber"}
        />
      </MetricRow>

      {/* Create form */}
      {showForm && (
        <SectionCard title="Yeni Gereksinim" className="mb-4">
          <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-2" data-testid="requirements-form">
            <input
              placeholder="External ID (ör. REQ-001) *"
              value={form.external_id}
              onChange={e => setForm({ ...form, external_id: e.target.value })}
              required
              className="px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
              data-testid="requirements-input-external-id"
            />
            <input
              placeholder="Başlık *"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
              required
              className="px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
              data-testid="requirements-input-title"
            />
            <input
              placeholder="Açıklama"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              className="sm:col-span-2 px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
              data-testid="requirements-input-desc"
            />
            <select
              value={form.priority}
              onChange={e => setForm({ ...form, priority: e.target.value })}
              className="px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-slate-300 focus:outline-none cursor-pointer"
              data-testid="requirements-select-priority"
            >
              <option value="critical">Kritik</option>
              <option value="high">Yüksek</option>
              <option value="medium">Orta</option>
              <option value="low">Düşük</option>
            </select>
            <input
              placeholder="Kaynak (ör. müşteri talebi)"
              value={form.source}
              onChange={e => setForm({ ...form, source: e.target.value })}
              className="px-3 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-slate-500"
              data-testid="requirements-input-source"
            />
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
                data-testid="requirements-btn-create"
              >
                {loading ? "Kaydediliyor..." : "Ekle"}
              </button>
            </div>
          </form>
        </SectionCard>
      )}

      {/* Filters */}
      <div className="mb-4">
        <FilterBar
          filters={[
            {
              key: "priority",
              label: "Tüm Öncelikler",
              value: priorityFilter,
              onChange: setPriorityFilter,
              options: [
                { label: "Kritik", value: "critical" },
                { label: "Yüksek", value: "high" },
                { label: "Orta", value: "medium" },
                { label: "Düşük", value: "low" },
              ],
            },
          ]}
          right={<span className="text-xs text-slate-500">{filtered.length} gereksinim</span>}
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
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
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">ID</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Başlık</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Öncelik</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Senaryo</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tarih</th>
                <th className="px-4 py-2.5 text-left" />
              </tr>
            </thead>
            <SortableContext items={filtered.map(r => r.id)} strategy={verticalListSortingStrategy}>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState
                        icon="📋"
                        title="Henüz gereksinim eklenmemiş"
                        description="İlk gereksinimi ekleyin ve senaryolarla eşleştirin"
                        action={
                          <button
                            onClick={() => setShowForm(true)}
                            className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors"
                          >
                            Gereksinim Ekle
                          </button>
                        }
                      />
                    </td>
                  </tr>
                ) : (
                  filtered.map(r => (
                    <SortableRequirementRow key={r.id} requirement={r} onDelete={() => handleDelete(r.id)} />
                  ))
                )}
              </tbody>
            </SortableContext>
          </table>

          <DragOverlay>
            {activeItem && (
              <div className="flex items-center gap-3 rounded-xl border border-blue-500/30 bg-slate-800 px-4 py-3 shadow-xl">
                <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_BADGE[activeItem.priority] ?? ""}`}>
                  {PRIORITY_LABELS[activeItem.priority]}
                </span>
                <span className="text-sm font-medium text-white">{activeItem.title}</span>
                <span className="font-mono text-xs text-slate-500">{activeItem.external_id}</span>
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>
    </div>
  );
}
