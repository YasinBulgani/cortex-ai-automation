"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { PRODUCT_FAMILY } from "@/lib/product";
import { VirtualList } from "@/components/ui/virtual-list";

type Project = {
  id: string;
  name: string;
  description?: string;
  base_url?: string;
  archived?: boolean;
  // Optional enriched fields (available on dashboard endpoint, not list endpoint)
  scenario_count?: number;
  last_run?: string | null;
  pass_rate?: number | null;
};

type ViewMode = "grid" | "list";

const AVATAR_GRADIENTS = [
  "from-blue-600 to-violet-600",
  "from-emerald-600 to-teal-600",
  "from-rose-600 to-pink-600",
  "from-amber-600 to-orange-600",
  "from-cyan-600 to-sky-600",
  "from-indigo-600 to-purple-600",
];

function avatarColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  return AVATAR_GRADIENTS[hash % AVATAR_GRADIENTS.length];
}

function ProjectCard({
  project, selected, onToggle,
}: { project: Project; selected: boolean; onToggle: (id: string) => void }) {
  const initials = project.name.split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const grad = avatarColor(project.id);
  const passRate = project.pass_rate;

  return (
    <div className={`group relative flex flex-col gap-2 rounded-xl border bg-slate-900 p-3.5 transition-all duration-150 ${selected ? "border-blue-500/50 bg-blue-500/5" : "border-slate-800 hover:border-slate-600 hover:bg-slate-800/60"}`}>
      {/* Checkbox overlay */}
      <button
        type="button"
        onClick={() => onToggle(project.id)}
        className={`absolute right-2.5 top-2.5 z-10 flex h-5 w-5 items-center justify-center rounded border transition-all ${selected ? "border-blue-500 bg-blue-600 text-white" : "border-slate-700 bg-slate-800 text-transparent hover:border-slate-500"}`}
        aria-label={selected ? "Seçimi kaldır" : "Seç"}
      >
        {selected && (
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </button>

      <Link
        href={`/p/${project.id}/scenarios`}
        className="flex flex-col gap-2"
        data-testid={`project-card-${project.id}`}
      >
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${grad} text-sm font-bold text-white shadow-md`}>
          {initials || "?"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-semibold text-white group-hover:text-blue-300 transition-colors">{project.name}</h3>
            {project.archived && (
              <span className="shrink-0 rounded-full bg-slate-800 border border-slate-700 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500">Arşiv</span>
            )}
          </div>
          <p className="truncate text-xs text-slate-500 mt-0.5">
            {project.description?.trim() || project.base_url?.trim() || "Açıklama yok"}
          </p>
        </div>
        <svg className="h-4 w-4 shrink-0 text-slate-700 group-hover:text-blue-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </div>
      {/* Pass rate bar */}
      {passRate !== null && passRate !== undefined && (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${passRate >= 80 ? "bg-emerald-500" : passRate >= 50 ? "bg-amber-500" : "bg-red-500"}`}
              style={{ width: `${passRate}%` }}
            />
          </div>
          <span className="text-[10px] tabular-nums text-slate-500">{passRate.toFixed(0)}%</span>
        </div>
      )}
      {project.last_run && (
        <p className="text-[10px] text-slate-600">Son koşum: {new Date(project.last_run).toLocaleDateString("tr-TR")}</p>
      )}
      </Link>
    </div>
  );
}

function ProjectRow({ project }: { project: Project }) {
  const initials = project.name.split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const grad = avatarColor(project.id);

  return (
    <Link
      href={`/p/${project.id}/scenarios`}
      className="group flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/60 transition-colors border-b border-slate-800 last:border-b-0"
    >
      <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br ${grad} text-[10px] font-bold text-white`}>
        {initials || "?"}
      </div>
      <span className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors flex-1 min-w-0 truncate">
        {project.name}
      </span>
      <span className="hidden md:block text-xs text-slate-500 truncate max-w-[40%]">
        {project.description?.trim() || project.base_url?.trim() || ""}
      </span>
      {project.archived && (
        <span className="rounded-full bg-slate-800 border border-slate-700 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500">Arşiv</span>
      )}
      <svg className="h-3.5 w-3.5 shrink-0 text-slate-700 group-hover:text-blue-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
      </svg>
    </Link>
  );
}

function NewProjectModal({ onClose, onCreated }: { onClose: () => void; onCreated: (p: Project) => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [desc, setDesc] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const p = await apiFetch<Project>("/api/v1/tspm/projects", {
        method: "POST",
        json: { name: name.trim(), base_url: url.trim() || undefined, description: desc.trim() || undefined },
      });
      onCreated(p);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Proje oluşturulamadı");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl animate-scale-in">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-bold text-white">Yeni Proje</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Proje Adı *</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Örn: Ödeme API"
              data-testid="project-name"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Hedef URL</label>
            <input
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Açıklama</label>
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              rows={2}
              placeholder="Proje hakkında kısa bilgi..."
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">
            İptal
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim() || loading}
            className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:opacity-90 transition-opacity"
          >
            {loading ? "Oluşturuluyor..." : "Oluştur"}
          </button>
        </div>
      </div>
    </div>
  );
}

const PAGE_SIZE = 60;

export default function PortfolioPage() {
  const [projects, setProjects]     = useState<Project[]>([]);
  const [loading, setLoading]       = useState(true);
  const [search, setSearch]         = useState("");
  const [showArchived, setShowArchived] = useState(false);
  const [view, setView]             = useState<ViewMode>("grid");
  const [page, setPage]             = useState(1);
  const [newOpen, setNewOpen]       = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const clearSelection = useCallback(() => setSelectedIds(new Set()), []);

  const handleBulkArchive = useCallback(async () => {
    setBulkLoading(true);
    try {
      await Promise.allSettled(
        [...selectedIds].map(id =>
          apiFetch(`/api/v1/tspm/projects/${id}`, { method: "PATCH", json: { archived: true } })
        )
      );
      setProjects(prev => prev.map(p => selectedIds.has(p.id) ? { ...p, archived: true } : p));
      clearSelection();
    } finally { setBulkLoading(false); }
  }, [selectedIds, clearSelection]);

  const handleBulkDelete = useCallback(async () => {
    if (!confirm(`${selectedIds.size} proje silinecek. Emin misiniz?`)) return;
    setBulkLoading(true);
    try {
      await Promise.allSettled(
        [...selectedIds].map(id =>
          apiFetch(`/api/v1/tspm/projects/${id}`, { method: "DELETE" })
        )
      );
      setProjects(prev => prev.filter(p => !selectedIds.has(p.id)));
      clearSelection();
    } finally { setBulkLoading(false); }
  }, [selectedIds, clearSelection]);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Project[]>("/api/v1/tspm/projects");
      setProjects(Array.isArray(data) ? data : []);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const filtered = useMemo(() => {
    const s = search.toLowerCase().trim();
    return projects.filter(p => {
      if (!showArchived && p.archived) return false;
      if (!s) return true;
      return (
        p.name.toLowerCase().includes(s) ||
        p.description?.toLowerCase().includes(s) ||
        p.base_url?.toLowerCase().includes(s)
      );
    });
  }, [projects, search, showArchived]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Reset page on filter change
  useEffect(() => { setPage(1); }, [search, showArchived, view]);

  return (
    <div className="flex flex-col gap-6 p-6">

      {/* Başlık */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Projeler</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {loading ? "Yükleniyor..." : `${filtered.length} proje${search ? ` (${projects.length} toplam)` : ""}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/new-project"
            className="hidden sm:flex items-center gap-2 rounded-xl border border-violet-500/30 bg-violet-500/10 px-4 py-2 text-sm font-medium text-violet-200 hover:bg-violet-500/20 transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
            Sihirbazla Oluştur
          </Link>
          <button
            onClick={() => setNewOpen(true)}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg hover:opacity-90 transition-opacity"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" /></svg>
            Yeni Proje
          </button>
        </div>
      </div>

      {/* Ürün ailesi sekme filtresi */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-3">
        <button
          className="flex items-center gap-1.5 rounded-lg bg-blue-900/30 px-3 py-1.5 text-xs font-semibold text-blue-400 border border-blue-500/30"
          aria-current="page"
        >
          Tümü
          <span className="rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-bold text-blue-300">{projects.length}</span>
        </button>
        {PRODUCT_FAMILY.map(p => (
          <Link
            key={p.id}
            href={`/products/${p.id}`}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white hover:border-slate-500 hover:bg-slate-800 transition-colors"
            data-testid={`product-tab-${p.id}`}
            title={p.tagline}
          >
            {p.shortName}
            <svg className="h-2.5 w-2.5 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </Link>
        ))}
      </div>

      {/* Arama + araç çubuğu */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48 max-w-md">
          <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Proje ara..."
            className="w-full rounded-xl border border-slate-700 bg-slate-800 py-2 pl-9 pr-4 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={e => setShowArchived(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-slate-700 bg-slate-800 text-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          Arşivlenmiş
        </label>
        {/* Görünüm değiştirici */}
        <div className="ml-auto flex rounded-lg border border-slate-700 bg-slate-800 p-0.5">
          <button
            onClick={() => setView("grid")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              view === "grid" ? "bg-slate-700 text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z" />
            </svg>
            Kart
          </button>
          <button
            onClick={() => setView("list")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              view === "list" ? "bg-slate-700 text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            Liste
          </button>
        </div>
      </div>

      {/* Proje listesi */}
      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
            <div key={i} className="rounded-xl border border-slate-800 bg-slate-900 p-3.5 animate-pulse">
              <div className="flex gap-3">
                <div className="h-10 w-10 rounded-lg bg-slate-800" />
                <div className="flex-1">
                  <div className="h-4 w-3/4 rounded bg-slate-800 mb-1.5" />
                  <div className="h-3 w-1/2 rounded bg-slate-800" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 py-20 text-center">
          <svg className="mx-auto mb-3 h-10 w-10 text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          <p className="text-sm text-slate-500">
            {search ? "Arama sonucu bulunamadı." : "Henüz proje yok."}
          </p>
          {!search && (
            <button
              onClick={() => setNewOpen(true)}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
            >
              İlk projeyi oluştur
            </button>
          )}
        </div>
      ) : view === "grid" ? (
        <div data-testid="project-list" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {paged.map(p => <ProjectCard key={p.id} project={p} selected={selectedIds.has(p.id)} onToggle={toggleSelect} />)}
        </div>
      ) : (
        // Liste görünümü — virtualized, tüm projeleri tek scroll'da gösterir
        <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
          <VirtualList
            items={filtered}
            estimateSize={49}
            className="max-h-[70vh]"
            itemKey={p => p.id}
            renderItem={(p) => <ProjectRow project={p} />}
          />
        </div>
      )}

      {/* Toplu seçim işlem çubuğu */}
      {selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 flex items-center gap-3 rounded-2xl border border-slate-600 bg-slate-900/95 px-5 py-3 shadow-2xl backdrop-blur-sm">
          <span className="text-sm font-medium text-white">{selectedIds.size} proje seçildi</span>
          <div className="h-4 w-px bg-slate-700" />
          <button
            type="button"
            onClick={handleBulkArchive}
            disabled={bulkLoading}
            className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-300 transition-colors hover:bg-amber-500/20 disabled:opacity-50"
          >
            Arşivle
          </button>
          <button
            type="button"
            onClick={handleBulkDelete}
            disabled={bulkLoading}
            className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-300 transition-colors hover:bg-red-500/20 disabled:opacity-50"
          >
            Sil
          </button>
          <button
            type="button"
            onClick={clearSelection}
            className="rounded-lg px-2 py-1.5 text-xs text-slate-400 transition-colors hover:text-white"
          >
            İptal
          </button>
        </div>
      )}

      {/* Sayfalama */}
      {!loading && filtered.length > PAGE_SIZE && (
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} / {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1 text-slate-300 disabled:opacity-40 hover:text-white transition-colors"
            >
              ← Önceki
            </button>
            <span className="px-3 text-slate-400">{page} / {totalPages}</span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1 text-slate-300 disabled:opacity-40 hover:text-white transition-colors"
            >
              Sonraki →
            </button>
          </div>
        </div>
      )}

      {newOpen && (
        <NewProjectModal
          onClose={() => setNewOpen(false)}
          onCreated={p => setProjects(prev => [p, ...prev])}
        />
      )}
    </div>
  );
}
