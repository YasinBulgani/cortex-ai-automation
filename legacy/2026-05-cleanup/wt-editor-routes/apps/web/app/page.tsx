"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PLATFORM_BRAND, PRODUCT_TAGLINE } from "@/lib/product";

type Project = { id: string; name: string; description: string; archived: boolean };

export default function LandingPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [lastProjectId, setLastProjectId] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Project[]>("/api/v1/tspm/projects")
      .then(setProjects)
      .catch(() => setProjects([]));

    try {
      const raw = localStorage.getItem("bgts_active_project");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed?.id) setLastProjectId(String(parsed.id));
      }
    } catch {}
  }, []);

  const available = projects.filter((p) => !p.archived);
  const targetProjectId = lastProjectId ?? available[0]?.id ?? null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,#e0ecff_0%,#fffbf5_45%,#fffbf5_100%)]">
      <div className="mx-auto w-full max-w-lg px-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-violet-400/20 bg-violet-500/10 shadow-lg">
          <span className="text-2xl font-black tracking-[0.2em] text-violet-100">V</span>
        </div>

        <h1 className="mt-6 text-3xl font-bold text-white">{PLATFORM_BRAND.name}</h1>
        <p className="mt-2 text-sm text-slate-400">{PRODUCT_TAGLINE}</p>

        <div className="mt-8 flex flex-col gap-3">
          {targetProjectId && (
            <button
              type="button"
              onClick={() => router.push(`/p/${targetProjectId}`)}
              className="w-full rounded-xl border border-violet-300/30 bg-violet-500/15 px-5 py-3 text-sm font-semibold text-violet-50 transition hover:border-violet-200/40 hover:bg-violet-500/25"
            >
              Projeye devam et
            </button>
          )}
          <Link
            href="/projects"
            className="w-full rounded-xl border border-slate-700 bg-slate-900/70 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-slate-500 hover:text-white"
          >
            {available.length > 0 ? `Projeler (${available.length})` : "Projeler"}
          </Link>
          <Link
            href="/new-project"
            className="w-full rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-5 py-3 text-sm font-semibold text-emerald-100 transition hover:border-emerald-300/30 hover:bg-emerald-500/15"
          >
            Yeni proje oluştur
          </Link>
        </div>
      </div>
    </div>
  );
}
