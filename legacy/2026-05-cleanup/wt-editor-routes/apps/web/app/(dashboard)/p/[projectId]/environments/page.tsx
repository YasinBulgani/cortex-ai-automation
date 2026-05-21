"use client";

import { useCallback, useMemo, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  useEnvironments,
  useCreateEnvironment,
  useUpdateEnvironment,
  useDeleteEnvironment,
  type ApiEnvironment,
} from "@/lib/hooks/use-api-testing";

interface VarRow { key: string; value: string }

function varsToRows(variables: Record<string, string>): VarRow[] {
  return Object.entries(variables).map(([key, value]) => ({ key, value }));
}

export default function EnvironmentsPage() {
  const projectId = useRouteParam("projectId");

  const { data: environments = [], isLoading } = useEnvironments(projectId);
  const createMut = useCreateEnvironment(projectId);
  const updateMut = useUpdateEnvironment(projectId);
  const deleteMut = useDeleteEnvironment(projectId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editRows, setEditRows] = useState<VarRow[]>([]);

  const selected = useMemo(
    () => environments.find((e) => e.id === selectedId) ?? null,
    [environments, selectedId],
  );

  const selectEnv = useCallback((env: ApiEnvironment) => {
    setSelectedId(env.id);
    setEditName(env.name);
    setEditRows(varsToRows(env.variables));
  }, []);

  const handleCreate = useCallback(() => {
    createMut.mutate(
      { name: "Yeni Ortam", variables: {}, is_default: false },
      { onSuccess: (env) => selectEnv(env) },
    );
  }, [createMut, selectEnv]);

  const handleSave = useCallback(() => {
    if (!selectedId) return;
    const variables: Record<string, string> = {};
    for (const r of editRows) {
      const k = r.key.trim();
      if (k) variables[k] = r.value;
    }
    updateMut.mutate({ envId: selectedId, name: editName, variables });
  }, [selectedId, editName, editRows, updateMut]);

  const handleDelete = useCallback(
    (envId: string) => {
      deleteMut.mutate(envId, {
        onSuccess: () => {
          if (selectedId === envId) {
            setSelectedId(null);
            setEditRows([]);
          }
        },
      });
    },
    [deleteMut, selectedId],
  );

  const addRow = useCallback(() => {
    setEditRows((prev) => [...prev, { key: "", value: "" }]);
  }, []);

  const updateRow = useCallback((idx: number, patch: Partial<VarRow>) => {
    setEditRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  }, []);

  const removeRow = useCallback((idx: number) => {
    setEditRows((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const inputCls = "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none";

  return (
    <div className="space-y-6" data-testid="environments-page">
      <PageHeader
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-9.64a3.375 3.375 0 00-3.285-2.602H7.923a3.375 3.375 0 00-3.285 2.602l-2.268 9.64a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008zm-3 0h.008v.008h-.008v-.008z" />
          </svg>
        }
        title="Ortam Yönetimi"
        description="API test ortamlarını oluşturun ve değişkenleri yönetin."
        right={
          <button type="button" className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors disabled:opacity-50" onClick={handleCreate} disabled={createMut.isPending}>
            + Yeni Ortam
          </button>
        }
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-600 border-t-blue-500" />
        </div>
      ) : environments.length === 0 ? (
        <EmptyState icon="🌍" title="Henüz ortam yok" description="API testleriniz için ortam değişkenleri tanımlamaya başlayın." action={<button type="button" className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500" onClick={handleCreate} disabled={createMut.isPending}>İlk Ortamı Oluştur</button>} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-4">
            <SectionCard title="Ortamlar" right={<span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">{environments.length}</span>} noPad>
              <div className="divide-y divide-slate-800">
                {environments.map((env) => (
                  <button key={env.id} type="button" onClick={() => selectEnv(env)} className={`w-full px-4 py-3 text-left transition-colors hover:bg-slate-800/60 ${selectedId === env.id ? "bg-slate-800/80 border-l-2 border-blue-500" : ""}`}>
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-sm font-medium text-white truncate">{env.name}</span>
                      <div className="flex items-center gap-1.5">
                        {env.is_default && <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-medium text-emerald-400">Varsayılan</span>}
                        <span className="rounded-full bg-slate-700/60 px-2 py-0.5 text-[10px] text-slate-400">{Object.keys(env.variables).length} değişken</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </SectionCard>
          </div>

          <div className="lg:col-span-8 space-y-4">
            {!selected ? (
              <SectionCard>
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-sm text-slate-400">Düzenlemek için sol taraftan bir ortam seçin</p>
                </div>
              </SectionCard>
            ) : (
              <>
                <SectionCard title="Ortam Bilgileri">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Ortam Adı</label>
                    <input type="text" className={inputCls} value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Örneğin: Production" />
                  </div>
                </SectionCard>

                <SectionCard title="Değişkenler" right={<span className="text-xs text-slate-500">{editRows.length} değişken</span>}>
                  {editRows.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">Henüz değişken eklenmedi.</p>
                  ) : (
                    <div className="space-y-2">
                      <div className="hidden md:grid grid-cols-12 gap-2 px-1 text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                        <div className="col-span-5">Anahtar</div>
                        <div className="col-span-6">Değer</div>
                        <div className="col-span-1 text-center">Sil</div>
                      </div>
                      {editRows.map((row, idx) => (
                        <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-2 items-center rounded-lg bg-slate-800/40 p-2">
                          <div className="md:col-span-5">
                            <input type="text" className={`${inputCls} font-mono text-xs`} value={row.key} onChange={(e) => updateRow(idx, { key: e.target.value })} placeholder="key" />
                          </div>
                          <div className="md:col-span-6">
                            <input type="text" className={`${inputCls} text-xs`} value={row.value} onChange={(e) => updateRow(idx, { value: e.target.value })} placeholder="value" />
                          </div>
                          <div className="md:col-span-1 flex justify-center">
                            <button type="button" onClick={() => removeRow(idx)} className="rounded p-1.5 text-slate-500 hover:text-red-400 hover:bg-slate-700 transition-colors" title="Değişkeni kaldır">✕</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <div className="mt-4">
                    <button type="button" className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors" onClick={addRow}>+ Değişken Ekle</button>
                  </div>
                </SectionCard>

                <div className="flex items-center justify-between">
                  <button type="button" className="inline-flex items-center gap-1.5 rounded-lg bg-red-600/20 border border-red-500/30 px-3 py-1.5 text-sm font-medium text-red-400 hover:bg-red-600/30 transition-colors" onClick={() => handleDelete(selectedId!)}>Ortamı Sil</button>
                  <button type="button" className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors disabled:opacity-50" onClick={handleSave} disabled={updateMut.isPending || !editName.trim()}>
                    {updateMut.isPending ? "Kaydediliyor..." : "Kaydet"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
