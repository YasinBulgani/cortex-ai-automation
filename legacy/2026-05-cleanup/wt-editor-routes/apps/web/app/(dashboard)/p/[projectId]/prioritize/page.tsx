"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import {
  usePrioritizedTests,
  usePrioritizationStats,
  useOptimalSuite,
  type PrioritizedTest,
} from "@/lib/hooks/use-api-testing";

const SCORE_COLOR = (s: number) =>
  s >= 70 ? "text-red-400" : s >= 40 ? "text-amber-400" : "text-emerald-400";
const SCORE_BG = (s: number) =>
  s >= 70 ? "bg-red-500" : s >= 40 ? "bg-amber-500" : "bg-emerald-500";

const RISK_COLORS: Record<string, string> = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-amber-400",
  low: "text-emerald-400",
};

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-emerald-500/20 text-emerald-400",
  POST: "bg-blue-500/20 text-blue-400",
  PUT: "bg-amber-500/20 text-amber-400",
  DELETE: "bg-red-500/20 text-red-400",
  PATCH: "bg-purple-500/20 text-purple-400",
};

export default function PrioritizePage() {
  const projectId = useRouteParam("projectId");
  const [timeBudget, setTimeBudget] = useState<number>(60000);
  const [actionError, setActionError] = useState<string | null>(null);

  const {
    data: prioritized,
    isLoading,
    isError: prioritizedFailed,
    error: prioritizedError,
  } = usePrioritizedTests(projectId);
  const {
    data: stats,
    isError: statsFailed,
    error: statsError,
  } = usePrioritizationStats(projectId);
  const optimalMut = useOptimalSuite(projectId);

  const tests = prioritized?.items ?? [];
  const totalCount = prioritized?.total_count ?? 0;

  async function handleOptimalSuite() {
    try {
      setActionError(null);
      await optimalMut.mutateAsync({ time_budget_ms: timeBudget });
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Optimal test seti hesaplanamadi.");
    }
  }

  function formatDuration(ms: number): string {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}dk`;
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="prioritize-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
          </svg>
        }
        title="Test Önceliklendirme"
        description="Risk, hata geçmişi ve değişim etkisine göre akıllı test sıralaması"
      />
      {(actionError || prioritizedFailed || statsFailed) && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {actionError ||
            (prioritizedError instanceof Error && prioritizedError.message) ||
            (statsError instanceof Error && statsError.message) ||
            "Test onceliklendirme verisi su anda yuklenemedi."}
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-5 gap-3">
          <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
            <p className="text-xs text-slate-400 mb-1">Toplam Test</p>
            <p className="text-2xl font-bold text-white">{stats.total_tests}</p>
          </div>
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
            <p className="text-xs text-slate-400 mb-1">Yüksek Öncelik</p>
            <p className="text-2xl font-bold text-red-400">{stats.high_priority_count}</p>
          </div>
          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <p className="text-xs text-slate-400 mb-1">Orta Öncelik</p>
            <p className="text-2xl font-bold text-amber-400">{stats.medium_priority_count}</p>
          </div>
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
            <p className="text-xs text-slate-400 mb-1">Düşük Öncelik</p>
            <p className="text-2xl font-bold text-emerald-400">{stats.low_priority_count}</p>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
            <p className="text-xs text-slate-400 mb-1">Ort. Skor</p>
            <p className={`text-2xl font-bold ${SCORE_COLOR(stats.avg_score)}`}>{stats.avg_score.toFixed(0)}</p>
          </div>
        </div>
      )}

      {/* Optimal suite builder */}
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-violet-300">Optimal Test Seti Oluştur</p>
            <p className="text-xs text-slate-400 mt-0.5">Zaman bütçesine göre en etkili test setini seç</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <label className="text-xs text-slate-400">Bütçe:</label>
              <select
                value={timeBudget}
                onChange={(e) => setTimeBudget(Number(e.target.value))}
                aria-label="Zaman butcesi"
                title="Zaman butcesi"
                className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-sm text-white"
              >
                <option value={30000}>30 sn</option>
                <option value={60000}>1 dk</option>
                <option value={180000}>3 dk</option>
                <option value={300000}>5 dk</option>
                <option value={600000}>10 dk</option>
              </select>
            </div>
            <button
              onClick={handleOptimalSuite}
              disabled={optimalMut.isPending}
              className="flex items-center gap-2 px-4 py-1.5 text-sm font-semibold text-violet-300 border border-violet-500/30 rounded-xl hover:bg-violet-500/10 transition-all disabled:opacity-50"
            >
              {optimalMut.isPending ? (
                <div className="w-3.5 h-3.5 border-2 border-violet-300/30 border-t-violet-300 rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              )}
              Hesapla
            </button>
          </div>
        </div>
        {optimalMut.data && (
          <div className="mt-3 pt-3 border-t border-violet-500/20 grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-slate-400">Seçilen Test</p>
              <p className="text-lg font-bold text-white">{optimalMut.data.total_count}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Toplam Süre</p>
              <p className="text-lg font-bold text-blue-400">{formatDuration(optimalMut.data.total_duration_ms)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Kapsam</p>
              <p className="text-sm text-slate-300 mt-0.5">{optimalMut.data.coverage_summary}</p>
            </div>
          </div>
        )}
      </div>

      {/* Priority list */}
      <SectionCard
        title="Önceliklendirilmiş Test Listesi"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" /></svg>}
        right={<span className="text-xs text-slate-500">{totalCount} test</span>}
        noPad
      >
        {isLoading ? (
          <div className="flex justify-center p-10">
            <div className="w-6 h-6 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
          </div>
        ) : tests.length === 0 ? (
          <div className="p-8">
            <EmptyState icon="📋" title="Önceliklendirilecek test yok" description="Önce API test case'leri oluşturun" />
          </div>
        ) : (
          <table className="w-full" data-testid="priority-table">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left w-8">#</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Test</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Endpoint</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Skor</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Dağılım</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Risk</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-right">Süre</th>
              </tr>
            </thead>
            <tbody>
              {tests.map((t: PrioritizedTest, idx: number) => (
                <tr key={t.test_case_id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <td className="px-4 py-3 text-xs text-slate-500 tabular-nums">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium text-white truncate max-w-[220px]">{t.title}</span>
                      <span className="text-[10px] text-slate-500">{t.test_type} · {t.last_run_status ?? "hiç"}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${METHOD_COLORS[t.endpoint_method] ?? "bg-slate-800 text-slate-300"}`}>
                        {t.endpoint_method}
                      </span>
                      <span className="text-xs font-mono text-slate-400 truncate max-w-[140px]">{t.endpoint_path}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div className={`h-full rounded-full ${SCORE_BG(t.priority_score)}`} style={{ width: `${t.priority_score}%` }} />
                      </div>
                      <span className={`text-xs font-bold tabular-nums ${SCORE_COLOR(t.priority_score)}`}>
                        {t.priority_score.toFixed(0)}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-0.5 h-3">
                      {[
                        { val: t.breakdown.failure, color: "bg-red-500", label: "Hata" },
                        { val: t.breakdown.risk, color: "bg-orange-500", label: "Risk" },
                        { val: t.breakdown.recency, color: "bg-blue-500", label: "Yenilik" },
                        { val: t.breakdown.sensitivity, color: "bg-purple-500", label: "Hassasiyet" },
                        { val: t.breakdown.change_impact, color: "bg-cyan-500", label: "Değişim" },
                      ].map((b) => (
                        <div
                          key={b.label}
                          title={`${b.label}: ${b.val.toFixed(1)}`}
                          className={`rounded-sm ${b.color}`}
                          style={{ width: `${Math.max(b.val * 0.3, 1)}px`, minWidth: "2px" }}
                        />
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium capitalize ${RISK_COLORS[t.risk_level] ?? "text-slate-300"}`}>
                      {t.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400 tabular-nums text-right">
                    {formatDuration(t.estimated_duration_ms)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>

      {/* Risk distribution */}
      {stats && (
        <div className="grid grid-cols-2 gap-3">
          <SectionCard
            title="Risk Dağılımı"
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" /></svg>}
            noPad
          >
            {Object.entries(stats.risk_distribution).map(([risk, count]) => (
              <div key={risk} className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 last:border-0">
                <span className={`text-sm font-medium capitalize ${RISK_COLORS[risk] ?? "text-slate-300"}`}>{risk}</span>
                <span className="text-sm font-bold text-white">{count}</span>
              </div>
            ))}
          </SectionCard>
          <SectionCard
            title="Tahmini Süre"
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
          >
            <div className="flex flex-col gap-2">
              <div className="flex justify-between">
                <span className="text-sm text-slate-400">Toplam</span>
                <span className="text-sm font-bold text-white">{formatDuration(stats.estimated_total_duration_ms)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-slate-400">Karantina Atlanan</span>
                <span className="text-sm font-bold text-slate-300">{stats.quarantined_skipped}</span>
              </div>
            </div>
          </SectionCard>
        </div>
      )}
    </div>
  );
}
