"use client";

import { useState } from "react";
import {
  useRegressionSets,
  useCreateRegressionSet,
  type RegressionSet,
  type RegressionSetCase,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

const LAST_RUN_DOT: Record<string, string> = {
  passed:  "bg-emerald-500",
  failed:  "bg-red-500",
  blocked: "bg-amber-500",
  not_run: "bg-slate-600",
};

const SET_TYPE_OPTIONS = ["regression", "smoke", "release", "sprint"] as const;

const PAGE_SIZE = 20;

export default function ManagementRegressionPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: sets, isLoading, isError } = useRegressionSets(mpid || undefined);
  const createSet                 = useCreateRegressionSet(mpid || "");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showNewPanel, setShowNewPanel] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<string>("regression");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const filtered = (sets ?? []).filter((r: RegressionSet) =>
    !search || r.name.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const selectedSet = (sets ?? []).find((s: RegressionSet) => s.id === selectedId) ?? null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    const set = await createSet.mutateAsync({ name: newName.trim(), set_type: newType });
    setNewName("");
    setShowNewPanel(false);
    setSelectedId(set.id);
  };

  return (
    <div className="min-h-[calc(100vh-88px)] flex bg-[#0a0f1e] text-slate-200">
      {/* Left panel */}
      <div className="w-64 shrink-0 flex flex-col border-r border-white/[0.06] bg-[#0d1221]">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
          <span className="text-[13px] font-semibold text-slate-200">Regresyon Setleri</span>
          <button
            onClick={() => { setShowNewPanel(true); setSelectedId(null); }}
            className="rounded bg-blue-600 px-2 py-1 text-[10px] font-medium text-white hover:bg-blue-500 transition-colors"
          >
            + Yeni
          </button>
        </div>

        {/* Search input */}
        <div className="px-3 py-2 border-b border-white/[0.06]">
          <input
            type="text"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
            placeholder="Regresyon seti ara..."
            className="rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-[13px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-white/[0.15] w-full"
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-white/[0.04]" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center py-16">
              <p className="text-sm text-red-400/80">Veri yüklenemedi — lütfen sayfayı yenileyin</p>
            </div>
          ) : (sets ?? []).length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3 text-center px-4">
              <div className="rounded-full bg-white/[0.04] p-4">
                <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <p className="text-sm font-medium text-slate-300">Henüz regresyon seti yok</p>
              <p className="text-xs text-slate-500 max-w-xs">İlk seti oluşturmak için yukarıdaki "+ Yeni" butonunu kullanın.</p>
            </div>
          ) : filtered.length === 0 && search ? (
            <p className="text-center py-8 text-sm text-slate-500">"{search}" için sonuç bulunamadı</p>
          ) : (
            <>
              {paginated.map((set: RegressionSet) => {
                const isActive = selectedId === set.id;
                return (
                  <button
                    key={set.id}
                    onClick={() => { setSelectedId(set.id); setShowNewPanel(false); }}
                    className={[
                      "w-full text-left px-4 py-3 border-b border-white/[0.04] transition-colors",
                      isActive
                        ? "bg-blue-500/[0.06] border-l-2 border-l-blue-500/50"
                        : "hover:bg-white/[0.04]",
                    ].join(" ")}
                  >
                    <p className="text-[13px] text-slate-200 truncate">{set.name}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
                      {set.set_type} · {set.cases.length} case ·{" "}
                      {new Date(set.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                    </p>
                  </button>
                );
              })}

              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-2 border-t border-white/[0.06]">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
                  >
                    Önceki
                  </button>
                  <span className="text-[10px] text-slate-600">{page + 1} / {totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="text-[11px] text-slate-400 hover:text-slate-200 disabled:opacity-30 transition-colors"
                  >
                    Sonraki
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 w-full animate-pulse rounded-xl bg-white/[0.04]" />
            ))}
          </div>
        ) : isError ? (
          <div className="flex items-center justify-center py-16">
            <p className="text-sm text-red-400/80">Veri yüklenemedi — lütfen sayfayı yenileyin</p>
          </div>
        ) : showNewPanel ? (
          <div className="p-6 max-w-lg">
            <h2 className="mb-4 text-[13px] font-semibold text-slate-200">Yeni Regresyon Seti</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Set Adı</label>
                <input
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  placeholder="örn. Sprint 24 Regression"
                  required
                  className="w-full rounded-md border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-blue-500/50"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Set Tipi</label>
                <select
                  value={newType}
                  onChange={e => setNewType(e.target.value)}
                  className="w-full rounded-md border border-white/[0.08] bg-[#0a0f1e] px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-blue-500/50"
                >
                  {SET_TYPE_OPTIONS.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setShowNewPanel(false)}
                  className="rounded-md border border-white/[0.08] px-4 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  disabled={createSet.isPending || !newName.trim()}
                  className="rounded-md bg-blue-600 px-4 py-2 text-[11px] font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
                >
                  {createSet.isPending ? "Oluşturuluyor…" : "Oluştur"}
                </button>
              </div>
            </form>
          </div>
        ) : selectedSet ? (
          <div>
            <div className="border-b border-white/[0.06] bg-[#0d1221] px-6 py-4">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-slate-200">{selectedSet.name}</span>
                <span className="text-[10px] text-slate-500 border border-white/[0.06] rounded px-1.5 py-0.5">
                  {selectedSet.set_type}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {selectedSet.cases.length} case ·{" "}
                {new Date(selectedSet.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" })}
              </p>
            </div>

            {selectedSet.cases.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
                <div className="rounded-full bg-white/[0.04] p-4">
                  <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p className="text-sm font-medium text-slate-300">Bu sette henüz case yok</p>
                <p className="text-xs text-slate-500 max-w-xs">Bu regresyon setine case eklemek için repository'den case bağlayın.</p>
              </div>
            ) : (
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-white/[0.06] bg-[#0d1221]">
                    {["Key", "Başlık", "Öncelik", "Son Durum", "Risk"].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {selectedSet.cases.map((c: RegressionSetCase) => {
                    const lrDot = LAST_RUN_DOT[c.last_run_status ?? "not_run"] ?? "bg-slate-600";
                    return (
                      <tr key={c.id} className="border-b border-white/[0.04] hover:bg-white/[0.04] transition-colors">
                        <td className="px-4 py-3">
                          <span className="text-[11px] font-mono text-slate-400">{c.case_key}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[13px] text-slate-200">{c.title}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[11px] text-slate-400">{c.priority}</span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <span className={`h-1.5 w-1.5 rounded-full ${lrDot}`} />
                            <span className="text-[11px] text-slate-400">{c.last_run_status ?? "not_run"}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-[11px] text-slate-400">{c.risk_score.toFixed(1)}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full py-20 gap-3 text-center">
            <div className="rounded-full bg-white/[0.04] p-4">
              <svg className="h-8 w-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-300">Bir set seçin</p>
            <p className="text-xs text-slate-500 max-w-xs">Sol panelden bir regresyon seti seçerek içeriğini görüntüleyin.</p>
          </div>
        )}
      </div>
    </div>
  );
}
