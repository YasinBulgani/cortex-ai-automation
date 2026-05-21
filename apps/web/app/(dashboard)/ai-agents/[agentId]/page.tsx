"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { AGENT_CATEGORIES, getAgentById } from "../agents-data";

type Project = {
  id: string;
  name: string;
  description?: string;
  archived?: boolean;
  last_opened_at?: string | null;
};

const AVAILABILITY_META = {
  active:       { label: "Active",  className: "border-emerald-400/20 bg-emerald-500/10 text-emerald-200" },
  beta:         { label: "Beta",    className: "border-amber-400/20 bg-amber-500/10 text-amber-200" },
  experimental: { label: "Deneysel", className: "border-violet-400/20 bg-violet-500/10 text-violet-200" },
} as const;

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

export default function AgentDetailPage() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const agentId = Array.isArray(params?.agentId) ? params.agentId[0] : params?.agentId;
  const agent = agentId ? getAgentById(agentId) : undefined;

  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!agent || !agent.projectRouteSegment) {
      setLoading(false);
      return;
    }
    apiFetch<Project[]>("/api/v1/tspm/projects?include_archived=false")
      .then((data) => {
        setProjects(data.filter((p) => !p.archived));
        setError(null);
      })
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 403) {
          setError("Proje listesine erişim yetkiniz yok.");
        } else {
          setError(null);
        }
      })
      .finally(() => setLoading(false));
  }, [agent]);

  const filteredProjects = useMemo(() => {
    const s = search.toLowerCase().trim();
    if (!s) return projects;
    return projects.filter(p =>
      p.name.toLowerCase().includes(s) ||
      p.description?.toLowerCase().includes(s)
    );
  }, [projects, search]);

  if (!agent) {
    return (
      <div className="p-6">
        <div className="mx-auto max-w-2xl rounded-xl border border-amber-400/20 bg-amber-500/5 p-8 text-center">
          <p className="text-3xl">🔍</p>
          <h1 className="mt-3 text-xl font-semibold text-white">Ajan bulunamadı</h1>
          <p className="mt-1 text-sm text-slate-400">"{agentId}" id'li bir AI ajanı tanımlı değil.</p>
          <Link href="/ai-agents" className="mt-4 inline-flex items-center rounded-lg border border-violet-400/30 bg-violet-500/10 px-4 py-2 text-sm font-medium text-violet-100 hover:bg-violet-500/20">
            ← Tüm Ajanlara Dön
          </Link>
        </div>
      </div>
    );
  }

  const category = AGENT_CATEGORIES[agent.category];
  const isGlobal = !!agent.globalHref;

  const handleProjectSelect = (projectId: string) => {
    if (agent.globalHref) {
      router.push(agent.globalHref);
    } else if (agent.projectRouteSegment) {
      router.push(`/p/${projectId}/${agent.projectRouteSegment}`);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">

      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-xs text-slate-500">
        <Link href="/ai-agents" className="hover:text-violet-300 transition-colors">AI Ajanları</Link>
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
        <span className="text-slate-300">{agent.name}</span>
      </nav>

      {/* 2 kolonlu layout: sol agent bilgisi, sağ proje seçici */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">

        {/* Sol: Agent bilgi + özellikler */}
        <div className="space-y-4">

          {/* Agent header */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="flex items-start gap-3">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-violet-400/30 bg-violet-500/10 text-2xl">
                {agent.emoji}
              </span>
              <div className="min-w-0 flex-1">
                <h1 className="text-lg font-bold text-white">{agent.name}</h1>
                <p className="text-xs text-violet-200/70 mt-0.5">{agent.tagline}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${AVAILABILITY_META[agent.availability].className}`}>
                    {AVAILABILITY_META[agent.availability].label}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${category.color}`}>
                    {category.emoji} {category.label}
                  </span>
                </div>
              </div>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-300">{agent.description}</p>
          </div>

          {/* Özellikler */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-3">Özellikler</h2>
            <ul className="space-y-2">
              {agent.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-slate-300">
                  <svg className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Geri dönüş */}
          <Link href="/ai-agents" className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-violet-300 transition-colors">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
            Tüm Ajanlara Dön
          </Link>
        </div>

        {/* Sağ: Aksiyon paneli */}
        <div>
          {isGlobal ? (
            <div className="rounded-xl border border-emerald-400/20 bg-emerald-500/5 p-8 text-center">
              <div className="text-3xl">🌐</div>
              <h2 className="mt-3 text-base font-semibold text-white">Genel Araç</h2>
              <p className="mt-1 text-sm text-slate-400">Bu ajan proje seçmeden kullanılır.</p>
              <Link href={agent.globalHref!} className="mt-4 inline-flex items-center rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 transition-opacity">
                {agent.name}'i Aç →
              </Link>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-900 flex flex-col" style={{ height: "calc(100vh - 180px)", minHeight: "500px", maxHeight: "780px" }}>
              <div className="border-b border-slate-800 p-5 shrink-0">
                <div className="flex items-center gap-2 mb-1">
                  <svg className="h-4 w-4 text-violet-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                  <h2 className="text-sm font-semibold text-white">Proje Seç</h2>
                  {!loading && (
                    <span className="text-xs text-slate-500">
                      {search ? `${filteredProjects.length} / ${projects.length}` : projects.length}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500">
                  {agent.name} bu projede çalıştırılacak.
                </p>

                {/* Arama */}
                <div className="relative mt-3">
                  <svg className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <input
                    type="text"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Proje ara..."
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 py-1.5 pl-8 pr-3 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
                  />
                </div>
              </div>

              {/* Liste */}
              <div className="flex-1 overflow-y-auto">
                {loading ? (
                  <div className="p-8 text-center text-sm text-slate-500">Projeler yükleniyor…</div>
                ) : error ? (
                  <div className="m-5 rounded-lg border border-amber-400/20 bg-amber-500/5 p-4 text-sm text-amber-200">{error}</div>
                ) : filteredProjects.length === 0 ? (
                  <div className="p-8 text-center">
                    <p className="text-sm text-slate-500">
                      {search ? "Arama sonucu bulunamadı." : "Henüz proje yok."}
                    </p>
                    {!search && (
                      <Link href="/new-project" className="mt-3 inline-flex items-center rounded-lg bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-500 transition-colors">
                        + Yeni Proje Oluştur
                      </Link>
                    )}
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {filteredProjects.slice(0, 100).map((p) => {
                      const initials = p.name.split(/\s+/).map(w => w[0]).join("").slice(0, 2).toUpperCase();
                      const grad = avatarColor(p.id);
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => handleProjectSelect(p.id)}
                          className="group flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-slate-800/60 transition-colors"
                        >
                          <div className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br ${grad} text-[10px] font-bold text-white`}>
                            {initials || "?"}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-white group-hover:text-violet-300 transition-colors">{p.name}</p>
                            {p.description && (
                              <p className="truncate text-xs text-slate-500">{p.description}</p>
                            )}
                          </div>
                          <svg className="h-3.5 w-3.5 shrink-0 text-slate-700 group-hover:text-violet-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      );
                    })}
                    {filteredProjects.length > 100 && (
                      <div className="px-4 py-2.5 text-center text-xs text-slate-600 bg-slate-900/50">
                        İlk 100 sonuç gösteriliyor — aramayı daraltın
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
