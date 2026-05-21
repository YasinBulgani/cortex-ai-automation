"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";

const PER_PAGE = 50;

type AuditEvent = {
  id: string;
  ts: string;
  actor_email: string | null;
  actor_name: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
};

const actionBadge: Record<string, string> = {
  create: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  update: "border-blue-500/20 bg-blue-500/10 text-blue-400",
  delete: "border-red-500/20 bg-red-500/10 text-red-400",
  login: "border-violet-500/20 bg-violet-500/10 text-violet-400",
  logout: "border-slate-600 bg-slate-800/50 text-slate-400",
};

export default function AuditLogPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiFetch<AuditEvent[]>(`/api/v1/audit/events?page=${page}&per_page=${PER_PAGE}`)
      .then((data) => {
        setEvents(data);
        setHasMore(data.length === PER_PAGE);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-6" data-testid="audit-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        }
        title="Denetim Günlüğü"
        description="Platform üzerindeki tüm işlemler"
        data-testid="audit-heading"
      />

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-3">
          <span className="text-xs text-slate-500">Sayfa {page} · {events.length} kayıt</span>
          {loading && <span className="text-xs text-slate-500 animate-pulse">Yükleniyor…</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm" data-testid="audit-table">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-500">
                <th className="px-5 py-3 font-medium">Zaman</th>
                <th className="px-5 py-3 font-medium">Kullanıcı</th>
                <th className="px-5 py-3 font-medium">İşlem</th>
                <th className="px-5 py-3 font-medium">Kaynak</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30 transition-colors" data-testid={`audit-row-${e.id}`}>
                  <td className="px-5 py-3 text-slate-400 whitespace-nowrap font-mono text-xs">
                    {new Date(e.ts).toLocaleString("tr-TR")}
                  </td>
                  <td className="px-5 py-3 text-white">{e.actor_name || e.actor_email || "Sistem"}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${actionBadge[e.action] ?? "border-slate-700 bg-slate-800 text-slate-300"}`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-slate-400">
                    {e.resource_type}
                    {e.resource_id ? (
                      <span className="ml-1 font-mono text-xs text-slate-600">{e.resource_id.slice(0, 8)}&hellip;</span>
                    ) : ""}
                  </td>
                </tr>
              ))}
              {!loading && events.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-10 text-center text-sm text-slate-500">
                    Kayıt bulunamadı
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-center gap-3">
        <button
          type="button"
          disabled={page <= 1 || loading}
          onClick={() => setPage(page - 1)}
          className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-40"
          data-testid="audit-btn-prev"
        >
          ‹ Önceki
        </button>
        <span className="text-xs text-slate-500">Sayfa {page}</span>
        <button
          type="button"
          disabled={!hasMore || loading}
          onClick={() => setPage(page + 1)}
          className="rounded-xl border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 hover:text-white transition-colors disabled:opacity-40"
          data-testid="audit-btn-next"
        >
          Sonraki ›
        </button>
      </div>
    </div>
  );
}
