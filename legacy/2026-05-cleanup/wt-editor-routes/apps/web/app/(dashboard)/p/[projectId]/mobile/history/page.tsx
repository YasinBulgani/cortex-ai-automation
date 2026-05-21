"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/nexus/PageHeader";
import { StatusBadge } from "@/components/nexus/StatusBadge";
import { ProgressBar } from "@/components/nexus/ProgressBar";
import { EmptyState } from "@/components/nexus/EmptyState";

type MobileRun = {
  id: string;
  name: string;
  status: string;
  created_at: string | null;
  scenario_total: number;
  passed_count: number;
  failed_count: number;
  platform: string;
  device_name: string | null;
};

export default function MobileHistoryPage() {
  const projectId = useRouteParam("projectId");
  const [runs, setRuns] = useState<MobileRun[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [ios, android] = await Promise.all([
        apiFetch<MobileRun[]>(`/api/v1/tspm/projects/${projectId}/executions?platform=ios&limit=200`),
        apiFetch<MobileRun[]>(`/api/v1/tspm/projects/${projectId}/executions?platform=android&limit=200`),
      ]);
      setRuns(
        [...ios, ...android].sort((a, b) => new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()),
      );
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="mobile-history-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        }
        title="Mobil Koşum Geçmişi"
        description="Cihazlarda yapılan tüm mobil test koşumları"
        right={
          <Link
            href={`/p/${projectId}/mobile`}
            className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-colors"
          >
            Yeni Koşum
          </Link>
        }
      />

      <div className="grid grid-cols-3 gap-3 my-5">
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">Toplam</span>
          <span className="text-xl font-bold text-white">{runs.length}</span>
        </div>
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">iOS</span>
          <span className="text-xl font-bold text-blue-400">{runs.filter(r => r.platform === "ios").length}</span>
        </div>
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">Android</span>
          <span className="text-xl font-bold text-green-400">{runs.filter(r => r.platform === "android").length}</span>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-slate-700 border-t-indigo-400 rounded-full animate-spin" />
          <span className="ml-3 text-sm text-slate-500">Yükleniyor…</span>
        </div>
      ) : runs.length === 0 ? (
        <EmptyState
          icon="📱"
          title="Mobil koşum bulunamadı"
          description="İlk mobil test koşumunuzu başlatın"
          action={
            <Link href={`/p/${projectId}/mobile`} className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-colors">
              Mobil Teste Git
            </Link>
          }
        />
      ) : (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Koşum Adı</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Platform</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Durum</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">İlerleme</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Tarih</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(r => {
                const tot = r.scenario_total || 0;
                const passed = r.passed_count || 0;
                const failed = r.failed_count || 0;
                const skipped = Math.max(0, tot - passed - failed);
                const createdAt = r.created_at ? new Date(r.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "—";

                return (
                  <tr key={r.id} className="border-b border-slate-800 hover:bg-slate-800/40 transition-colors" data-testid={`mobile-history-row-${r.id}`}>
                    <td className="px-4 py-3">
                      <Link href={`/p/${projectId}/executions/${r.id}`} className="text-sm font-medium text-white hover:text-indigo-400 transition-colors">
                        {r.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium ${r.platform === "ios" ? "text-blue-400" : "text-green-400"}`}>
                        {r.platform === "ios" ? "🍎 iOS" : "🤖 Android"}
                      </span>
                      {r.device_name && <div className="text-xs text-slate-500 mt-0.5">{r.device_name}</div>}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3 min-w-32">
                      <ProgressBar passed={passed} failed={failed} skipped={skipped} total={tot} height="sm" />
                      <div className="text-xs text-slate-500 mt-1">{passed}/{tot}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{createdAt}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="px-4 py-2.5 border-t border-slate-800">
            <span className="text-xs text-slate-500">{runs.length} koşum</span>
          </div>
        </div>
      )}
    </div>
  );
}
