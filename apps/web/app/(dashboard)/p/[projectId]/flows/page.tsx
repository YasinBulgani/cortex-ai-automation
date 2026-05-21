"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  EmptyState,
  StatCard,
  MetricRow,
} from "@/components/nexus";

type FlowRow = {
  id: string;
  name: string;
  description: string;
  created_at: string | null;
};

export default function FlowsListPage() {
  const router = useRouter();
  const projectId = useRouteParam("projectId");
  const [rows, setRows] = useState<FlowRow[]>([]);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<FlowRow[]>(`/api/v1/tspm/projects/${projectId}/flows`).then(setRows).catch((err) => console.warn("[flows]:", err));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setCreating(true);
    try {
      const f = await apiFetch<{ id: string }>(`/api/v1/tspm/projects/${projectId}/flows`, {
        method: "POST",
        json: { name: name.trim() || "Yeni akış" },
      });
      setName("");
      router.push(`/p/${projectId}/flows/${f.id}`);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    } finally { setCreating(false); }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="flows-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
          </svg>
        }
        title="Test Akışları"
        description="Senaryoları akış grafiği ile ilişkilendirin"
      />

      {/* Stats */}
      <MetricRow cols={2}>
        <StatCard label="Toplam Akış" value={rows.length} color={rows.length > 0 ? "blue" : "slate"} />
        <StatCard
          label="Son 30 Gün"
          value={rows.filter(r => r.created_at && (Date.now() - new Date(r.created_at).getTime()) < 30 * 86400_000).length}
          color="emerald"
        />
      </MetricRow>

      {/* Create form */}
      <form onSubmit={create} className="flex items-center gap-3" data-testid="flows-form">
        <input
          placeholder="Akış adı…"
          value={name}
          onChange={e => setName(e.target.value)}
          data-testid="flows-input-name"
          className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500/50 w-72"
        />
        <button
          type="submit"
          disabled={creating}
          data-testid="flows-btn-create"
          className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-colors disabled:opacity-50"
        >
          {creating ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          )}
          Oluştur
        </button>
        {err && <p className="text-sm text-red-400">{err}</p>}
      </form>

      {/* Flow grid */}
      {rows.length === 0 ? (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
          <EmptyState
            icon="🔧"
            title="Henüz akış yok"
            description="Akış adı girerek yeni bir test akışı oluşturun"
          />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="flows-grid">
          {rows.map(f => (
            <Link
              key={f.id}
              href={`/p/${projectId}/flows/${f.id}`}
              data-testid={`flows-card-${f.id}`}
              className="group rounded-xl border border-slate-700 bg-slate-900/40 p-4 hover:border-blue-500/40 hover:bg-blue-500/5 transition-all"
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 group-hover:border-blue-500/30 transition-colors">
                  <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <h2 className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors truncate">{f.name}</h2>
                  {f.description && (
                    <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">{f.description}</p>
                  )}
                </div>
                <svg className="w-4 h-4 text-slate-600 group-hover:text-blue-400 transition-colors shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
              {f.created_at && (
                <p className="text-xs text-slate-600">
                  {new Date(f.created_at).toLocaleDateString("tr-TR")}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
