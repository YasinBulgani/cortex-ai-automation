"use client";

import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import { useHealingStats, type HealingCategoryStats } from "@/lib/hooks/use-api-testing";

const CATEGORY_LABELS: Record<string, string> = {
  timeout: "Zaman Aşımı",
  auth_expired: "Oturum Süresi",
  rate_limited: "Rate Limit",
  server_error: "Sunucu Hatası",
  data_dependency: "Veri Bağımlılığı",
  assertion_drift: "Assertion Kayması",
  network: "Ağ Hatası",
  unknown: "Bilinmeyen",
};

const CATEGORY_COLORS: Record<string, string> = {
  timeout: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  auth_expired: "bg-purple-500/10 border-purple-500/20 text-purple-400",
  rate_limited: "bg-orange-500/10 border-orange-500/20 text-orange-400",
  server_error: "bg-red-500/10 border-red-500/20 text-red-400",
  data_dependency: "bg-blue-500/10 border-blue-500/20 text-blue-400",
  assertion_drift: "bg-cyan-500/10 border-cyan-500/20 text-cyan-400",
  network: "bg-slate-500/10 border-slate-500/20 text-slate-400",
  unknown: "bg-slate-800 border-slate-700 text-slate-300",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}dk`;
}

export default function HealingPage() {
  const projectId = useRouteParam("projectId");
  const { data: stats, isLoading } = useHealingStats(projectId);

  const successRate = stats ? Math.round(stats.success_rate * 100) : 0;

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="healing-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        }
        title="Self-Healing CI"
        description="Otomatik hata analizi ve akıllı yeniden deneme istatistikleri"
      />

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center py-16">
          <div className="flex items-center gap-3 text-slate-500">
            <div className="w-5 h-5 border-2 border-slate-700 border-t-emerald-400 rounded-full animate-spin" />
            Yükleniyor…
          </div>
        </div>
      ) : !stats || stats.total_healing_attempts === 0 ? (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
          <EmptyState icon="💊" title="Henüz healing verisi yok" description="Test koşumlarında hatalar self-heal edildiğinde burada gösterilecek" />
        </div>
      ) : (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-5 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Toplam Deneme</p>
              <p className="text-2xl font-bold text-white">{stats.total_healing_attempts}</p>
            </div>
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Başarı Oranı</p>
              <p className={`text-2xl font-bold ${successRate >= 70 ? "text-emerald-400" : successRate >= 40 ? "text-amber-400" : "text-red-400"}`}>
                {successRate}%
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Ort. Retry</p>
              <p className="text-2xl font-bold text-blue-400">{stats.avg_retries_needed.toFixed(1)}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Ort. Healing Süresi</p>
              <p className="text-2xl font-bold text-violet-400">{formatDuration(stats.avg_healing_time_ms)}</p>
            </div>
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
              <p className="text-xs text-slate-400 mb-1">Kazanılan CI Süresi</p>
              <p className="text-2xl font-bold text-emerald-400">{formatDuration(stats.saved_ci_time_ms)}</p>
            </div>
          </div>

          {/* Success gauge */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
            <div className="flex items-end justify-between mb-3">
              <div>
                <p className="text-sm font-medium text-slate-400">Self-Healing Başarı Oranı</p>
                <p className="text-xs text-slate-500 mt-0.5">Son 30 gün</p>
              </div>
              <span className={`text-4xl font-bold tabular-nums ${successRate >= 70 ? "text-emerald-400" : successRate >= 40 ? "text-amber-400" : "text-red-400"}`}>
                {successRate}%
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
              <div
                className={`h-full rounded-full transition-all ${successRate >= 70 ? "bg-emerald-500" : successRate >= 40 ? "bg-amber-500" : "bg-red-500"}`}
                style={{ width: `${successRate}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* By category */}
            <SectionCard
              title="Kategori Bazlı İstatistik"
              icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
              noPad
            >
              {Object.entries(stats.by_category).map(([cat, catStats]: [string, HealingCategoryStats]) => (
                <div key={cat} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.unknown}`}>
                      {CATEGORY_LABELS[cat] ?? cat}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-slate-400">{catStats.healed}/{catStats.attempts}</span>
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${catStats.rate >= 0.7 ? "bg-emerald-500" : catStats.rate >= 0.4 ? "bg-amber-500" : "bg-red-500"}`}
                          style={{ width: `${Math.round(catStats.rate * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-300 tabular-nums w-10 text-right">{Math.round(catStats.rate * 100)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </SectionCard>

            {/* Top healed tests */}
            <SectionCard
              title="En Çok İyileştirilen Testler"
              icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              noPad
            >
              {stats.top_healed_tests.length === 0 ? (
                <div className="p-6">
                  <EmptyState icon="🔍" title="Veri yok" description="Henüz iyileştirilen test bulunmuyor" />
                </div>
              ) : (
                stats.top_healed_tests.map((t, i) => (
                  <div key={t.test_case_id} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 tabular-nums">{i + 1}.</span>
                      <span className="text-sm text-white truncate max-w-[200px]">{t.title}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
                      {t.heal_count}x
                    </span>
                  </div>
                ))
              )}
            </SectionCard>
          </div>
        </>
      )}
    </div>
  );
}
