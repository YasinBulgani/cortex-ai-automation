"use client";

import Link from "next/link";
import { useProject } from "@/lib/useProject";
import { useProjects } from "@/lib/hooks/use-projects";

interface ProjectGateProps {
  title?: string;
  hint?: string;
}

export function ProjectGate({
  title = "Önce bir proje seç",
  hint = "Dashboard'u açmak için aşağıdan hedef projeyi seç.",
}: ProjectGateProps) {
  const { setProject } = useProject();
  const { data: projects, isLoading, error } = useProjects();

  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-slate-900 via-slate-900 to-emerald-950/30 p-8 shadow-2xl">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-2xl">
            📁
          </div>
          <h1 className="text-xl font-semibold text-white">{title}</h1>
          <p className="mt-2 text-sm text-slate-400">{hint}</p>
        </div>

        {isLoading ? (
          <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-center text-sm text-slate-400">
            Projeler yükleniyor…
          </div>
        ) : error ? (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-center text-sm text-rose-300">
            Projeler alınamadı. Daha sonra tekrar dene.
          </div>
        ) : !projects || projects.length === 0 ? (
          <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-center text-sm text-slate-400">
            Henüz proje yok. Aşağıdan yeni bir proje oluştur.
          </div>
        ) : (
          <select
            defaultValue=""
            onChange={(e) => {
              const p = projects.find((x) => x.id === e.target.value);
              if (p) setProject({ id: p.id, name: p.name });
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-white focus:border-emerald-500/50 focus:outline-none"
          >
            <option value="" disabled>
              Hedef proje seç…
            </option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}

        <div className="mt-4 flex items-center gap-2">
          <div className="h-px flex-1 bg-slate-800" />
          <span className="text-[11px] uppercase tracking-wider text-slate-500">veya</span>
          <div className="h-px flex-1 bg-slate-800" />
        </div>

        <Link
          href="/new-project"
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2.5 text-sm font-semibold text-emerald-200 transition-colors hover:bg-emerald-500/20"
        >
          <span className="text-base leading-none">＋</span>
          Yeni Proje Oluştur
        </Link>
      </div>
    </div>
  );
}
