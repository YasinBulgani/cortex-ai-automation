"use client";

import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";

import { useCallback, useEffect, useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
} from "@/components/nexus";

type LocatorEntry = {
  id?: number;
  name: string;
  locator_value: string;
  page_url?: string;
};

export default function PageObjectsPage() {
  const projectId = useRouteParam("projectId");

  const [locators, setLocators] = useState<LocatorEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterText, setFilterText] = useState("");
  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newPageUrl, setNewPageUrl] = useState("");

  const basePath = `/api/v1/tspm/projects/${projectId}/locators`;

  const loadLocators = useCallback(() => {
    setLoading(true);
    apiFetch<LocatorEntry[] | { locators: LocatorEntry[] }>(basePath)
      .then(data => {
        if (Array.isArray(data)) setLocators(data);
        else if ("locators" in data && data.locators) setLocators(data.locators);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Locator listesi yüklenemedi"))
      .finally(() => setLoading(false));
  }, [basePath]);

  useEffect(() => { loadLocators(); }, [loadLocators]);

  async function addLocator() {
    if (!newName.trim() || !newValue.trim()) return;
    setError(null);
    try {
      await apiFetch(basePath, {
        method: "POST",
        json: { name: newName, locator_value: newValue, page_url: newPageUrl },
      });
      setNewName("");
      setNewValue("");
      setNewPageUrl("");
      loadLocators();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ekleme hatası");
    }
  }

  async function deleteLocator(id: number) {
    try {
      await apiFetch(`${basePath}/${id}`, { method: "DELETE" });
      loadLocators();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Silme hatası");
    }
  }

  const filteredLocators = locators.filter(
    l => !filterText || l.name.toLowerCase().includes(filterText.toLowerCase()) || l.locator_value.toLowerCase().includes(filterText.toLowerCase()),
  );

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="page-objects-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        }
        title="Page Objects"
        description="Locator yönetimi ve element deposu"
      />

      {error && (
        <div className="flex items-center justify-between rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
          <button type="button" onClick={() => setError(null)} className="text-red-400 hover:text-red-200 ml-3">✕</button>
        </div>
      )}

      {/* Add Locator */}
      <SectionCard title="Yeni Locator Ekle">
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-3 gap-3">
            <input placeholder="İsim (ör: login_button)" value={newName} onChange={e => setNewName(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
            <input placeholder="Selector (ör: #btnLogin)" value={newValue} onChange={e => setNewValue(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 font-mono" />
            <input placeholder="Sayfa URL (opsiyonel)" value={newPageUrl} onChange={e => setNewPageUrl(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
          </div>
          <button type="button" onClick={addLocator} disabled={!newName.trim() || !newValue.trim()}
            className="w-fit px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50">
            Ekle
          </button>
        </div>
      </SectionCard>

      {/* Locator List */}
      <SectionCard
        title="Locator Listesi"
        right={<span className="text-xs text-slate-500">{locators.length} locator</span>}
        noPad
      >
        <div className="px-4 py-3 border-b border-slate-800">
          <input placeholder="Filtrele…" value={filterText} onChange={e => setFilterText(e.target.value)}
            className="w-64 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50" />
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">Yükleniyor...</div>
        ) : filteredLocators.length === 0 ? (
          <div className="p-8">
            <EmptyState icon="🗄️"
              title={locators.length === 0 ? "Henüz locator yok" : "Filtre sonucu boş"}
              description={locators.length === 0 ? "Yukarıdan yeni locator ekleyin" : "Filtreyi temizleyin"} />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead className="border-b border-slate-800 bg-slate-900/60">
                <tr>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400">İsim</th>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400">Selector</th>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400">Sayfa URL</th>
                  <th className="px-4 py-2.5 text-xs font-medium text-slate-400 w-16" />
                </tr>
              </thead>
              <tbody>
                {filteredLocators.map((loc, i) => (
                  <tr key={loc.id ?? i} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30 group">
                    <td className="px-4 py-3 font-semibold text-white">{loc.name}</td>
                    <td className="px-4 py-3 max-w-[300px] truncate font-mono text-xs text-slate-400">{loc.locator_value}</td>
                    <td className="px-4 py-3 max-w-[200px] truncate text-xs text-slate-500">{loc.page_url || "—"}</td>
                    <td className="px-4 py-3">
                      {loc.id && (
                        <button type="button" onClick={() => deleteLocator(loc.id!)}
                          className="text-xs px-2 py-1 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100">
                          Sil
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
      <PageFeedbackWidget />

    </div>
  );
}
