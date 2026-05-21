"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";
import { EmptyState } from "@/components/nexus/EmptyState";

type Project = { id: string; name: string; description: string; archived: boolean };

const inputCls = "w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 transition-colors";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [lastProjectId, setLastProjectId] = useState<string | null>(null);

  function load() {
    apiFetch<Project[]>("/api/v1/tspm/projects").then(setProjects).catch((e) => setErr(String(e)));
  }

  useEffect(() => {
    load();
    try {
      const raw = localStorage.getItem("bgts_active_project");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.id) setLastProjectId(String(parsed.id));
      }
    } catch {}
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setCreating(true);
    try {
      await apiFetch("/api/v1/tspm/projects", {
        method: "POST",
        json: { name, description: desc },
      });
      setName("");
      setDesc("");
      load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    } finally {
      setCreating(false);
    }
  }

  const orderedProjects = useMemo(() => {
    return [...projects].sort((a, b) => {
      const aPinned = a.id === lastProjectId ? 0 : 1;
      const bPinned = b.id === lastProjectId ? 0 : 1;
      if (aPinned !== bPinned) return aPinned - bPinned;
      if (a.archived !== b.archived) return Number(a.archived) - Number(b.archived);
      return a.name.localeCompare(b.name, "tr");
    });
  }, [projects, lastProjectId]);

  const activeCount = projects.filter((p) => !p.archived).length;

  return (
    <div className="min-h-screen bg-bg text-fg p-6 flex flex-col gap-6" data-testid="projects-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
          </svg>
        }
        title="Projeler"
        description={`${activeCount} aktif proje`}
        data-testid="projects-heading"
      />

      <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-4">
          <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Yeni Proje Oluştur
        </h2>

        <form onSubmit={create} className="flex flex-wrap items-end gap-3" data-testid="projects-form">
          <div className="min-w-[180px] flex-1 flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Ad</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Örn. Ödeme API"
              data-testid="projects-input-name"
              className={inputCls}
            />
          </div>
          <div className="min-w-[200px] flex-[2] flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Açıklama</label>
            <input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="Kısa açıklama"
              data-testid="projects-input-desc"
              className={inputCls}
            />
          </div>
          <button
            type="submit"
            disabled={creating}
            data-testid="projects-btn-create"
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
          >
            {creating ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Oluşturuluyor...
              </>
            ) : "Oluştur"}
          </button>
        </form>

        {err && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="projects-alert-error">
            {err}
          </div>
        )}
      </section>

      <section>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="projects-grid">
          {orderedProjects.length === 0 ? (
            <div className="sm:col-span-2 lg:col-span-3">
              <EmptyState
                icon="📁"
                title="Henüz proje yok"
                description="İlk projeyi oluşturup çalışmaya başlayın."
                data-testid="projects-empty"
              />
            </div>
          ) : (
            orderedProjects.map((p) => (
              <Link
                key={p.id}
                href={`/p/${p.id}`}
                className="group rounded-xl border border-slate-800 bg-slate-900/40 p-5 hover:border-blue-500/30 hover:bg-slate-900/70 transition-all"
                data-testid={`projects-card-${p.id}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="font-semibold text-white truncate">{p.name}</h2>
                    {p.description && (
                      <p className="mt-1 text-sm text-slate-400 line-clamp-2">{p.description}</p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {p.archived && (
                      <span className="rounded-full border border-slate-700 bg-slate-900/70 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                        Arşiv
                      </span>
                    )}
                    {p.id === lastProjectId && (
                      <span className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-100">
                        Son aktif
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
