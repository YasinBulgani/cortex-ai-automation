"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  useExecutionHistory,
  useTestTrends,
  type ExecutionHistoryItem,
} from "@/lib/hooks/use-api-testing";

const STATUS_BADGE: Record<string, string> = {
  passed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
  mixed: "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

function PassRateBar({ rate }: { rate: number }) {
  const color = rate >= 80 ? "bg-emerald-500" : rate >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${rate}%` }} />
      </div>
      <span className="text-[10px] text-slate-400 w-10 text-right">{rate}%</span>
    </div>
  );
}

export default function TestHistoryPage() {
  const projectId = useRouteParam("projectId");
  const [days, setDays] = useState(30);
  const [page, setPage] = useState(1);
  const perPage = 15;

  const { data: trends, isLoading: trendsLoading } = useTestTrends(projectId, days);
  const { data: history, isLoading: historyLoading } = useExecutionHistory(projectId, {
    page,
    per_page: perPage,
  });

  const items = history?.items ?? [];
  const totalCount = history?.total_count ?? 0;
  const totalPages = Math.max(Math.ceil(totalCount / perPage), 1);

  const summaryCards = [
    { label: "Toplam Koşu", value: trends?.total_runs ?? 0, color: "text-blue-400" },
    { label: "Ort. Pass Rate", value: `${trends?.avg_pass_rate ?? 0}%`, color: (trends?.avg_pass_rate ?? 0) >= 80 ? "text-emerald-400" : "text-amber-400" },
    { label: "Ort. Yanıt Süresi", value: `${(trends?.avg_response_ms ?? 0).toFixed(0)}ms`, color: "text-cyan-400" },
    { label: "En Çok Fail", value: trends?.most_failed_test_type ?? "-", color: "text-red-400" },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-4" data-testid="test-history-page">
      <PageHeader
        title="Test Geçmişi & Trendler"
        description="Çalışma geçmişi, başarı oranları ve trend analizi"
        badge={
          totalCount > 0 ? (
            <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400 font-medium">
              {totalCount} koşu
            </span>
          ) : undefined
        }
      />

      {/* Trend Summary */}
      <SectionCard
        title="Trend Özeti"
        right={
          <div className="flex gap-1">
            {[7, 30, 90].map(d => (
              <button key={d} onClick={() => { setDays(d); setPage(1); }}
                className={`rounded px-2 py-1 text-[10px] font-medium transition-colors ${
                  days === d ? "bg-blue-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                }`}>
                {d} Gün
              </button>
            ))}
          </div>
        }
      >
        {trendsLoading ? (
          <div className="h-20 flex items-center justify-center text-sm text-slate-500">Yükleniyor...</div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {summaryCards.map(c => (
              <div key={c.label} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-center">
                <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
                <div className="text-[10px] text-slate-500 mt-1">{c.label}</div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      {/* History Table */}
      <SectionCard title="Çalışma Geçmişi" noPad>
        {historyLoading ? (
          <div className="p-6 text-center text-sm text-slate-500">Yükleniyor...</div>
        ) : items.length === 0 ? (
          <div className="p-6">
            <EmptyState icon="🕰️" title="Henüz çalışma geçmişi yok"
              description="Servis veya API koleksiyon koşuları tamamlandığında detaylar burada görünecek." />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-left text-slate-500">
                    <th className="p-3">Tarih</th>
                    <th className="p-3 text-center">Toplam</th>
                    <th className="p-3 text-center">Başarılı</th>
                    <th className="p-3 text-center">Başarısız</th>
                    <th className="p-3 w-40">Pass Rate</th>
                    <th className="p-3 text-right">Süre</th>
                    <th className="p-3 text-center">Durum</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item: ExecutionHistoryItem) => {
                    const date = item.timestamp
                      ? new Date(item.timestamp).toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
                      : "-";
                    const dur = item.duration_ms >= 1000 ? `${(item.duration_ms / 1000).toFixed(1)}s` : `${item.duration_ms.toFixed(0)}ms`;
                    return (
                      <tr key={item.run_id} className="border-b border-slate-800/50 hover:bg-slate-800/40">
                        <td className="p-3 text-slate-300 whitespace-nowrap">{date}</td>
                        <td className="p-3 text-center text-slate-300 font-medium">{item.total}</td>
                        <td className="p-3 text-center text-emerald-400 font-medium">{item.passed}</td>
                        <td className="p-3 text-center text-red-400 font-medium">{item.failed}</td>
                        <td className="p-3"><PassRateBar rate={item.pass_rate} /></td>
                        <td className="p-3 text-right text-slate-400 whitespace-nowrap font-mono text-[10px]">{dur}</td>
                        <td className="p-3 text-center">
                          <span className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold ${STATUS_BADGE[item.status] ?? "bg-slate-800 text-slate-400 border-slate-700"}`}>
                            {item.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
                <span className="text-[10px] text-slate-500">Sayfa {page} / {totalPages} ({totalCount} sonuç)</span>
                <div className="flex gap-1">
                  <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1}
                    className="rounded px-3 py-1 text-[10px] font-medium bg-slate-800 text-slate-400 hover:bg-slate-700 disabled:opacity-40 transition-colors">
                    Önceki
                  </button>
                  <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages}
                    className="rounded px-3 py-1 text-[10px] font-medium bg-slate-800 text-slate-400 hover:bg-slate-700 disabled:opacity-40 transition-colors">
                    Sonraki
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </SectionCard>
    </div>
  );
}
