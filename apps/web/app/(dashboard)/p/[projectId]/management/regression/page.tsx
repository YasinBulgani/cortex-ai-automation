"use client";

import { useState } from "react";
import {
  useRegressionSets,
  useCreateRegressionSet,
  useSuggestRegressionCandidates,
  useAddCasesToRegressionSet,
  useDeleteRegressionSet,
  type RegressionSet,
  type RegressionSetCase,
  type RegressionCandidate,
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

// Hook not yet in API — local mock
function useUpdateRegressionSet(_mpid: string) {
  return { mutateAsync: async (_args: { id: string; name: string; set_type: string }) => {}, isPending: false };
}

const safeUseUpdateRegressionSet = useUpdateRegressionSet;

export default function ManagementRegressionPage() {
  const projectId = useRouteParam("projectId");
  const mpid = useManagementProjectId(projectId || undefined);

  const { data: sets, isLoading, isError } = useRegressionSets(mpid || undefined);
  const createSet     = useCreateRegressionSet(mpid || "");
  const updateSet     = safeUseUpdateRegressionSet(mpid || "");
  const deleteSet     = useDeleteRegressionSet(mpid || "");
  const suggestCandidates = useSuggestRegressionCandidates(mpid || "");
  const addCases      = useAddCasesToRegressionSet(mpid || "");

  const [selectedId, setSelectedId]             = useState<string | null>(null);
  const [showNewPanel, setShowNewPanel]         = useState(false);
  const [showAISuggest, setShowAISuggest]       = useState(false);
  const [aiSuggestSetId, setAiSuggestSetId]     = useState<string | null>(null);
  const [aiCandidates, setAiCandidates]         = useState<RegressionCandidate[]>([]);
  const [selectedCandidates, setSelectedCandidates] = useState<Set<string>>(new Set());
  const [newName, setNewName]           = useState("");
  const [newType, setNewType]           = useState<string>("regression");
  const [search, setSearch]             = useState("");
  const [page, setPage]                 = useState(0);

  // Edit state
  const [editingId, setEditingId]     = useState<string | null>(null);
  const [editName, setEditName]       = useState("");
  const [editType, setEditType]       = useState<string>("regression");

  // Delete confirm state
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const filtered = (sets ?? []).filter((r: RegressionSet) =>
    !search || r.name.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated  = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const selectedSet = (sets ?? []).find((s: RegressionSet) => s.id === selectedId) ?? null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    const set = await createSet.mutateAsync({ name: newName.trim(), set_type: newType });
    setNewName("");
    setShowNewPanel(false);
    setSelectedId(set.id);
  };

  const handleEditStart = (set: RegressionSet, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(set.id);
    setEditName(set.name);
    setEditType(set.set_type);
    setShowNewPanel(false);
  };

  const handleEditSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editName.trim() || !editingId) return;
    await updateSet.mutateAsync({ id: editingId, name: editName.trim(), set_type: editType });
    setEditingId(null);
  };

  const handleEditCancel = () => {
    setEditingId(null);
  };

  const handleDeleteRequest = (setId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(setId);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteConfirmId) return;
    await deleteSet.mutateAsync({ id: deleteConfirmId });
    if (selectedId === deleteConfirmId) setSelectedId(null);
    setDeleteConfirmId(null);
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmId(null);
  };

  const handleAISuggest = async (setId: string) => {
    setAiSuggestSetId(setId);
    setShowAISuggest(true);
    setAiCandidates([]);
    setSelectedCandidates(new Set());
    try {
      const result = await suggestCandidates.mutateAsync({});
      setAiCandidates(result);
    } catch {
      // sessiz
    }
  };

  const handleAddCandidates = async () => {
    if (!aiSuggestSetId || selectedCandidates.size === 0) return;
    await addCases.mutateAsync({
      setId: aiSuggestSetId,
      caseIds: [...selectedCandidates],
    });
    setShowAISuggest(false);
    setAiCandidates([]);
    setSelectedCandidates(new Set());
  };

  const setToDelete = deleteConfirmId
    ? (sets ?? []).find((s: RegressionSet) => s.id === deleteConfirmId)
    : null;

  return (
    <div className="min-h-[calc(100vh-88px)] flex bg-bg text-slate-200">
      {/* Left panel */}
      <div className="w-64 shrink-0 flex flex-col border-r border-border bg-surface-raised">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-[13px] font-semibold text-slate-200">Regresyon Setleri</span>
          <button
            onClick={() => { setShowNewPanel(true); setSelectedId(null); setEditingId(null); }}
            className="rounded bg-teal-600 px-2 py-1 text-[10px] font-medium text-white hover:bg-teal-700 transition-colors"
          >
            + Yeni
          </button>
        </div>

        {/* Search input */}
        <div className="px-3 py-2 border-b border-border">
          <input
            type="text"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
            placeholder="Regresyon seti ara..."
            className="rounded-lg border border-border bg-white/[0.04] px-3 py-1.5 text-[13px] text-slate-300 placeholder:text-slate-600 focus:outline-none focus:border-white/[0.15] w-full"
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
                const isActive  = selectedId === set.id;
                const isEditing = editingId === set.id;

                if (isEditing) {
                  return (
                    <div
                      key={set.id}
                      className="border-b border-border bg-teal-500/[0.06] px-3 py-2"
                    >
                      <form onSubmit={handleEditSave} className="space-y-1.5">
                        <input
                          autoFocus
                          value={editName}
                          onChange={e => setEditName(e.target.value)}
                          className="w-full rounded border border-border bg-white/[0.06] px-2 py-1 text-[12px] text-slate-200 outline-none focus:border-teal-500/50"
                          placeholder="Set adı"
                        />
                        <select
                          value={editType}
                          onChange={e => setEditType(e.target.value)}
                          className="w-full rounded border border-border bg-bg px-2 py-1 text-[12px] text-slate-200 outline-none focus:border-teal-500/50"
                        >
                          {SET_TYPE_OPTIONS.map(t => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        </select>
                        <div className="flex gap-1.5 pt-0.5">
                          <button
                            type="button"
                            onClick={handleEditCancel}
                            className="flex-1 rounded border border-border px-2 py-1 text-[10px] text-slate-400 hover:text-slate-200 transition-colors"
                          >
                            İptal
                          </button>
                          <button
                            type="submit"
                            disabled={updateSet.isPending || !editName.trim()}
                            className="flex-1 rounded bg-teal-600 px-2 py-1 text-[10px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors"
                          >
                            {updateSet.isPending ? "…" : "Kaydet"}
                          </button>
                        </div>
                      </form>
                    </div>
                  );
                }

                return (
                  <div
                    key={set.id}
                    className={[
                      "group relative w-full text-left border-b border-border transition-colors",
                      isActive
                        ? "bg-teal-500/[0.06] border-l-2 border-l-teal-500/50"
                        : "hover:bg-white/[0.04]",
                    ].join(" ")}
                  >
                    <button
                      onClick={() => { setSelectedId(set.id); setShowNewPanel(false); }}
                      className="w-full text-left px-4 py-3 pr-16"
                    >
                      <p className="text-[13px] text-slate-200 truncate">{set.name}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        {set.set_type} · {set.cases.length} case ·{" "}
                        {new Date(set.created_at).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" })}
                      </p>
                    </button>

                    {/* Hover action buttons */}
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {/* Edit button */}
                      <button
                        onClick={(e) => handleEditStart(set, e)}
                        title="Düzenle"
                        className="rounded p-1 text-slate-500 hover:text-teal-400 hover:bg-white/[0.06] transition-colors"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 012.828 0l.172.172a2 2 0 010 2.828L12 16H9v-3z" />
                        </svg>
                      </button>
                      {/* Delete button */}
                      <button
                        onClick={(e) => handleDeleteRequest(set.id, e)}
                        title="Sil"
                        className="rounded p-1 text-slate-500 hover:text-red-400 hover:bg-white/[0.06] transition-colors"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7h6m-7 0a1 1 0 01-1-1V5a1 1 0 011-1h6a1 1 0 011 1v1a1 1 0 01-1 1H9z" />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}

              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-2 border-t border-border">
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
                  className="w-full rounded-md border border-border bg-white/[0.04] px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 outline-none focus:border-teal-500/50"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] text-slate-500">Set Tipi</label>
                <select
                  value={newType}
                  onChange={e => setNewType(e.target.value)}
                  className="w-full rounded-md border border-border bg-bg px-3 py-2 text-[13px] text-slate-200 outline-none focus:border-teal-500/50"
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
                  className="rounded-md border border-border px-4 py-2 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
                >
                  İptal
                </button>
                <button
                  type="submit"
                  disabled={createSet.isPending || !newName.trim()}
                  className="rounded-md bg-teal-600 px-4 py-2 text-[11px] font-medium text-white hover:bg-teal-700 disabled:opacity-40 transition-colors"
                >
                  {createSet.isPending ? "Oluşturuluyor…" : "Oluştur"}
                </button>
              </div>
            </form>
          </div>
        ) : selectedSet ? (
          <div>
            <div className="border-b border-border bg-surface-raised px-6 py-4">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-slate-200">{selectedSet.name}</span>
                <span className="text-[10px] text-slate-500 border border-border rounded px-1.5 py-0.5">
                  {selectedSet.set_type}
                </span>
                <div className="ml-auto flex items-center gap-2">
                  <button type="button"
                    onClick={() => handleAISuggest(selectedSet.id)}
                    disabled={suggestCandidates.isPending}
                    className="flex items-center gap-1.5 rounded-lg border border-teal-500/30 bg-teal-500/10 px-2.5 py-1.5 text-[11px] font-medium text-teal-400 hover:bg-teal-500/20 disabled:opacity-40 transition-colors">
                    ✦ AI Öner
                  </button>
                </div>
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
                  <tr className="border-b border-border bg-surface-raised">
                    {["Key", "Başlık", "Öncelik", "Son Durum", "Risk"].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {selectedSet.cases.map((c: RegressionSetCase) => {
                    const lrDot = LAST_RUN_DOT[c.last_run_status ?? "not_run"] ?? "bg-slate-600";
                    return (
                      <tr key={c.id} className="border-b border-border hover:bg-white/[0.04] transition-colors">
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

      {/* Delete confirm modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-80 rounded-xl border border-border bg-surface-raised p-5 shadow-2xl">
            <h3 className="text-[13px] font-semibold text-slate-200 mb-2">Seti Sil</h3>
            <p className="text-[12px] text-slate-400 mb-1">
              Bu seti silmek istediğinizden emin misiniz?
            </p>
            {setToDelete && (
              <p className="text-[11px] text-slate-500 mb-4 truncate">
                <span className="font-medium text-slate-300">{setToDelete.name}</span> silinecek ve geri alınamaz.
              </p>
            )}
            <div className="flex gap-2 justify-end">
              <button
                onClick={handleDeleteCancel}
                className="rounded-md border border-border px-3 py-1.5 text-[11px] text-slate-400 hover:text-slate-200 transition-colors"
              >
                İptal
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={deleteSet.isPending}
                className="rounded-md bg-red-600 px-3 py-1.5 text-[11px] font-medium text-white hover:bg-red-700 disabled:opacity-40 transition-colors"
              >
                {deleteSet.isPending ? "Siliniyor…" : "Sil"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── AI Suggest Modal ───────────────────────────────────────────────── */}
      {showAISuggest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-xl border border-border bg-[#0d1220] shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <h3 className="text-[14px] font-semibold text-slate-200">AI Regresyon Adayları</h3>
                <p className="mt-0.5 text-[11px] text-slate-500">Risk ve geçmiş başarısızlığa göre önerilen case&apos;ler</p>
              </div>
              <button type="button" onClick={() => setShowAISuggest(false)}
                className="rounded-lg p-1.5 text-slate-500 hover:text-slate-300">✕</button>
            </div>

            <div className="max-h-[60vh] overflow-y-auto">
              {suggestCandidates.isPending ? (
                <div className="flex items-center justify-center py-16">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-teal-500 border-t-transparent" />
                </div>
              ) : aiCandidates.length === 0 ? (
                <div className="py-12 text-center text-[13px] text-slate-500">
                  Aday bulunamadı. Daha fazla test koşumu yapıldıktan sonra AI önerileri iyileşir.
                </div>
              ) : (
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-surface-raised">
                      <th className="w-10 px-4 py-2.5">
                        <input type="checkbox"
                          checked={selectedCandidates.size === aiCandidates.length}
                          onChange={e => setSelectedCandidates(e.target.checked ? new Set(aiCandidates.map(c => c.case_id)) : new Set())}
                          className="h-3 w-3 accent-teal-500" />
                      </th>
                      {["Key", "Başlık", "Öncelik", "Neden"].map(h => (
                        <th key={h} className="px-4 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider text-slate-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {aiCandidates.map((c: RegressionCandidate) => (
                      <tr key={c.case_id} className="border-b border-border hover:bg-white/[0.03]">
                        <td className="px-4 py-2.5">
                          <input type="checkbox"
                            checked={selectedCandidates.has(c.case_id)}
                            onChange={e => setSelectedCandidates(prev => {
                              const n = new Set(prev);
                              e.target.checked ? n.add(c.case_id) : n.delete(c.case_id);
                              return n;
                            })}
                            className="h-3 w-3 accent-teal-500" />
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="font-mono text-[10px] text-slate-500">{c.case_key}</span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-[13px] text-slate-200 line-clamp-1">{c.title}</span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] text-slate-400">{c.priority}</span>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className="text-[10px] text-teal-400/70 line-clamp-1">{c.reasons?.[0] ?? "Yüksek risk"}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="flex items-center justify-between border-t border-border px-5 py-3">
              <span className="text-[11px] text-slate-500">{selectedCandidates.size} seçili</span>
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowAISuggest(false)}
                  className="rounded-lg border border-border px-3 py-1.5 text-[12px] text-slate-400 hover:text-slate-200">
                  İptal
                </button>
                <button type="button" onClick={handleAddCandidates}
                  disabled={selectedCandidates.size === 0 || addCases.isPending}
                  className="rounded-lg bg-teal-600 px-4 py-1.5 text-[12px] font-semibold text-white hover:bg-teal-500 disabled:opacity-40">
                  {addCases.isPending ? "Ekleniyor…" : `${selectedCandidates.size} Case Ekle`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
