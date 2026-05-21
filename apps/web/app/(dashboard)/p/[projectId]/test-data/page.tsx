"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import { DataParameterTable } from "@/components/DataParameterTable";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
} from "@/components/nexus";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent,
  DragOverlay,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

type DataSet = {
  id: string;
  name: string;
  description: string;
  columns: string[];
  rows: string[][];
  created_at: string | null;
};

export default function TestDataPage() {
  const projectId = useRouteParam("projectId");
  const basePath = `/api/v1/tspm/projects/${projectId}/test-data`;

  const [dataSets, setDataSets] = useState<DataSet[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newDs, setNewDs] = useState({ name: "", description: "" });

  const load = useCallback(() => {
    apiFetch<DataSet[]>(basePath).then(setDataSets).catch((err) => console.warn("[test-data]:", err));
  }, [basePath]);

  useEffect(() => { load(); }, [load]);

  const selected = dataSets.find(d => d.id === selectedId);
  const [saving, setSaving] = useState(false);
  const [columns, setColumns] = useState<string[]>(selected?.columns ?? []);
  const [rowsWithIds, setRowsWithIds] = useState<{ _id: string; cells: string[] }[]>(
    selected?.rows.map((r, i) => ({ _id: `row-${i}`, cells: r })) ?? []
  );
  const [activeRowId, setActiveRowId] = useState<string | null>(null);
  const inputCls = "rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50";

  async function createDataSet() {
    if (!newDs.name.trim()) return;
    await apiFetch(basePath, { method: "POST", json: newDs });
    setNewDs({ name: "", description: "" });
    setShowCreate(false);
    load();
  }

  async function deleteDataSet(id: string) {
    if (!confirm("Bu veri setini silmek istediğinize emin misiniz?")) return;
    await apiFetch(`${basePath}/${id}`, { method: "DELETE" });
    if (selectedId === id) setSelectedId(null);
    load();
  }

  async function saveDataSet() {
    if (!selectedId) return;
    setSaving(true);
    try {
      await apiFetch(`${basePath}/${selectedId}`, {
        method: "PUT",
        json: { columns, rows: rowsWithIds.map(r => r.cells) },
      });
      load();
    } finally { setSaving(false); }
  }

  function addColumn() {
    const colName = `Kolon ${columns.length + 1}`;
    setColumns([...columns, colName]);
    setRowsWithIds(rowsWithIds.map(r => ({ ...r, cells: [...r.cells, ""] })));
  }

  function addRow() {
    setRowsWithIds([...rowsWithIds, { _id: `row-new-${Date.now()}`, cells: columns.map(() => "") }]);
  }

  function updateColumnName(idx: number, val: string) {
    const next = [...columns]; next[idx] = val; setColumns(next);
  }

  function updateCell(rowIdx: number, colIdx: number, val: string) {
    setRowsWithIds(prev => {
      const next = [...prev];
      next[rowIdx] = { ...next[rowIdx], cells: [...next[rowIdx].cells] };
      next[rowIdx].cells[colIdx] = val;
      return next;
    });
  }

  function removeRow(rowIdx: number) {
    setRowsWithIds(prev => prev.filter((_, i) => i !== rowIdx));
  }

  function handleDragStart(event: DragStartEvent) { setActiveRowId(event.active.id as string); }
  function handleDragEnd(event: DragEndEvent) {
    setActiveRowId(null);
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = rowsWithIds.findIndex(r => r._id === active.id);
      const newIndex = rowsWithIds.findIndex(r => r._id === over.id);
      setRowsWithIds(arrayMove(rowsWithIds, oldIndex, newIndex));
    }
  }

  const activeRow = activeRowId ? rowsWithIds.find(r => r._id === activeRowId) : null;

  async function exportDataSet(format: "csv" | "json") {
    if (!selectedId) return;
    const { API_BASE, getToken } = await import("@/lib/api");
    const token = getToken();
    const url = `${API_BASE}/api/v1/tspm/projects/${projectId}/test-data/${selectedId}/export?format=${format}`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${selected?.name ?? "data"}.${format}`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function maskColumns(columnsToMask: string[]) {
    if (!selectedId || columnsToMask.length === 0) return;
    if (!confirm(`${columnsToMask.join(", ")} sütunları maskelensin mi?`)) return;
    await apiFetch(`/api/v1/tspm/projects/${projectId}/test-data/${selectedId}/mask`, {
      method: "POST",
      json: { columns_to_mask: columnsToMask, mask_type: "asterisk" },
    });
    load();
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="test-data-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18M10 4v16M14 4v16" />
          </svg>
        }
        title="Test Verileri"
        description="Test veri setlerini yönetin"
        data-testid="test-data-heading"
        right={
          <button
            onClick={() => setShowCreate(f => !f)}
            className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors"
          >
            + Yeni Veri Seti
          </button>
        }
      />

      {/* Stats */}
      <MetricRow cols={2}>
        <StatCard label="Toplam Veri Seti" value={dataSets.length} color={dataSets.length > 0 ? "blue" : "slate"} />
        <StatCard label="Seçili" value={selected ? "1" : "—"} color={selected ? "emerald" : "slate"} />
      </MetricRow>

      {/* Create form */}
      {showCreate && (
        <SectionCard title="Yeni Veri Seti">
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <input placeholder="İsim" value={newDs.name} onChange={e => setNewDs({ ...newDs, name: e.target.value })} className={inputCls} />
              <input placeholder="Açıklama" value={newDs.description} onChange={e => setNewDs({ ...newDs, description: e.target.value })} className={inputCls} />
            </div>
            <div className="flex gap-2">
              <button onClick={createDataSet} disabled={!newDs.name.trim()} className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
                Oluştur
              </button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">
                İptal
              </button>
            </div>
          </div>
        </SectionCard>
      )}

      <SectionCard
        title="Veri Setleri"
        right={<span className="text-xs text-slate-500">{dataSets.length} veri seti</span>}
        noPad
      >
        {dataSets.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon="🗂️"
              title="Veri seti yok"
              description="Yeni veri seti oluşturarak başlayın"
              action={
                <button onClick={() => setShowCreate(true)} className="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors">
                  Veri Seti Ekle
                </button>
              }
            />
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-800 bg-slate-900/60">
              <tr>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400">İsim</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400">Açıklama</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-right">Kolonlar</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-right">Satırlar</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400">Tarih</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 w-16" />
              </tr>
            </thead>
            <tbody>
              {dataSets.map(ds => (
                <tr
                  key={ds.id}
                  className={`cursor-pointer border-b border-slate-800 last:border-0 hover:bg-slate-800/30 group ${selectedId === ds.id ? "bg-blue-500/5 border-l-2 border-l-blue-500" : ""}`}
                  onClick={() => setSelectedId(ds.id)}
                >
                  <td className="px-4 py-3 font-semibold text-white">{ds.name}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{ds.description || "—"}</td>
                  <td className="px-4 py-3 text-slate-400 tabular-nums text-right">{ds.columns?.length ?? 0}</td>
                  <td className="px-4 py-3 text-slate-400 tabular-nums text-right">{ds.rows?.length ?? 0}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {ds.created_at ? new Date(ds.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); deleteDataSet(ds.id); }}
                      className="text-xs px-2 py-1 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                    >
                      Sil
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>

      {selected && (
        <SectionCard title={`${selected.name} — Önizleme`}>
          {(selected.columns?.length ?? 0) === 0 ? (
            <EmptyState icon="📋" title="Henüz veri yok" description="Bu veri seti boş" />
          ) : (
            <div className="overflow-auto max-h-64 rounded-lg border border-slate-700">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-800">
                  <tr>
                    {selected.columns.map(col => (
                      <th key={col} className="px-3 py-2 text-left font-medium text-slate-400 whitespace-nowrap">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {(selected.rows ?? []).slice(0, 20).map((row, i) => (
                    <tr key={i} className="hover:bg-slate-800/50">
                      {row.map((cell, ci) => (
                        <td key={ci} className="px-3 py-1.5 text-slate-300 whitespace-nowrap">{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      )}

      {/* Inline data parametre tablosu — A5 component */}
      <SectionCard
        title="Test Verisi Parametrelendirme"
        data-testid="test-data-param-section"
      >
        <DataParameterTable
          initialColumns={["username", "password", "expected_result"]}
          initialRows={[
            { username: "alice@test.com", password: "Pass123", expected_result: "success" },
            { username: "bob@test.com", password: "wrong", expected_result: "fail" },
          ]}
          storageKey={`test-data-params-${projectId}`}
        />
        <p className="mt-2 text-[10px] text-slate-600">
          Bu tablodaki her satır bir test iteration'ı oluşturur (parametre binding).
        </p>
      </SectionCard>

      <PageFeedbackWidget />
    </div>
  );
}
