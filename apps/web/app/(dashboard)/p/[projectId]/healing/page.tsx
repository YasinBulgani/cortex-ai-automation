"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import { EmptyState } from "@/components/nexus/EmptyState";
import { PageFeedbackWidget } from "@/components/PageFeedbackWidget";
import {
  useHealingStats,
  useHealHistory,
  useManualHeal,
  type HealingCategoryStats,
} from "@/lib/hooks/use-api-testing";

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

const PIE_COLORS = [
  "#f59e0b", "#a855f7", "#f97316", "#ef4444",
  "#3b82f6", "#06b6d4", "#64748b", "#6b7280",
];

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}dk`;
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "az önce";
  if (mins < 60) return `${mins}dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}s önce`;
  return `${Math.floor(hrs / 24)}g önce`;
}

// ── CSS Pie Chart ─────────────────────────────────────────────────────────────
function PieChart({ data }: { data: Array<{ label: string; value: number; color: string }> }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;

  let cumulative = 0;
  const segments = data.map((d, i) => {
    const pct = (d.value / total) * 100;
    const start = cumulative;
    cumulative += pct;
    return { ...d, pct, start, color: d.color || PIE_COLORS[i % PIE_COLORS.length] };
  });

  const gradient = segments
    .map((s) => `${s.color} ${s.start.toFixed(1)}% ${(s.start + s.pct).toFixed(1)}%`)
    .join(", ");

  return (
    <div className="flex items-center gap-6">
      <div
        className="h-32 w-32 shrink-0 rounded-full"
        style={{ background: `conic-gradient(${gradient})` }}
      />
      <div className="space-y-1.5 flex-1 min-w-0">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: s.color }} />
            <span className="text-xs text-slate-300 truncate">{s.label}</span>
            <span className="ml-auto text-xs text-slate-500 tabular-nums">{s.pct.toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Manual Heal Drawer ────────────────────────────────────────────────────────
interface HealDrawerProps {
  projectId: string;
  onClose: () => void;
}

function ManualHealDrawer({ projectId, onClose }: HealDrawerProps) {
  const [runId, setRunId] = useState("");
  const { mutateAsync, isPending, isSuccess, isError, error, data } = useManualHeal(projectId);

  async function handleHeal() {
    if (!runId.trim()) return;
    await mutateAsync({ run_id: runId.trim() });
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-slate-700 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-white">Manuel Onarım</h2>
            <p className="text-xs text-slate-400 mt-0.5">Belirli bir test koşumunu elle onar</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-400">Run ID</label>
            <input
              type="text"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="Onarılacak run ID'sini girin…"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <p className="mt-1 text-[11px] text-slate-600">
              Healing, seçilen test koşumunu AI destekli kategorizasyon + retry ile onarır.
            </p>
          </div>

          {isSuccess && (
            <div className="rounded-lg border border-emerald-400/20 bg-emerald-500/10 p-4">
              <p className="text-sm font-semibold text-emerald-300">
                {data?.healed ? "✓ Onarım başarılı" : "⚠ Onarım kısmen tamamlandı"}
              </p>
              <p className="mt-1 text-xs text-slate-400">{data?.message}</p>
            </div>
          )}

          {isError && (
            <div className="rounded-lg border border-red-400/20 bg-red-500/10 p-4">
              <p className="text-sm font-semibold text-red-300">Onarım başlatılamadı</p>
              <p className="mt-1 text-xs text-slate-400">{(error as Error)?.message}</p>
            </div>
          )}
        </div>

        <div className="border-t border-slate-800 px-6 py-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-600 hover:text-white transition-colors">
            Kapat
          </button>
          <button
            onClick={handleHeal}
            disabled={isPending || !runId.trim() || isSuccess}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isPending ? "Onarılıyor…" : "Onarımı Başlat"}
          </button>
        </div>
      </div>
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function HealingPage() {
  const projectId = useRouteParam("projectId");
  const [showHealDrawer, setShowHealDrawer] = useState(false);
  const { data: stats, isLoading } = useHealingStats(projectId);
  const { data: history } = useHealHistory(projectId, 15);

  const successRate = stats ? Math.round(stats.success_rate * 100) : 0;

  // Build pie chart data from by_category
  const pieData = stats
    ? Object.entries(stats.by_category).map(([cat, s]: [string, HealingCategoryStats], i) => ({
        label: CATEGORY_LABELS[cat] ?? cat,
        value: s.attempts,
        color: PIE_COLORS[i % PIE_COLORS.length],
      }))
    : [];

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="healing-page">
      {showHealDrawer && projectId && (
        <ManualHealDrawer projectId={projectId} onClose={() => setShowHealDrawer(false)} />
      )}

      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
        }
        title="Otomatik Onarım (Self-Healing)"
        description="Otomatik hata analizi ve akıllı yeniden deneme istatistikleri"
        right={
          <button
            onClick={() => setShowHealDrawer(true)}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 transition-colors"
          >
            <span>💊</span> Manuel Onar
          </button>
        }
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

          {/* Success gauge + pie chart */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
              <div className="flex items-end justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-slate-400">Otomatik Onarım Başarı Oranı</p>
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
              {/* Milestones */}
              <div className="mt-2 flex justify-between text-[10px] text-slate-600">
                <span>0%</span><span>40%</span><span>70%</span><span>100%</span>
              </div>
            </div>

            {/* Pie chart — kategori dağılımı */}
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-5">
              <p className="text-sm font-medium text-slate-400 mb-4">Kategori Dağılımı</p>
              {pieData.length > 0 ? (
                <PieChart data={pieData} />
              ) : (
                <p className="text-xs text-slate-600">Veri yok</p>
              )}
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

          {/* Healing timeline */}
          {history && history.length > 0 && (
            <SectionCard
              title="Onarım Geçmişi"
              icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
              noPad
            >
              <div className="divide-y divide-slate-800">
                {history.map((entry) => (
                  <div key={entry.id} className="flex items-center gap-4 px-4 py-3 hover:bg-slate-800/30">
                    <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${entry.healed ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`}>
                      {entry.healed ? "✓" : "✗"}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-white">{entry.title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] border ${CATEGORY_COLORS[entry.category] ?? CATEGORY_COLORS.unknown}`}>
                          {CATEGORY_LABELS[entry.category] ?? entry.category}
                        </span>
                        <span className="text-[10px] text-slate-500">{entry.retries} retry</span>
                        <span className="text-[10px] text-slate-500">{formatDuration(entry.healing_time_ms)}</span>
                      </div>
                    </div>
                    <span className="shrink-0 text-xs text-slate-600">{formatRelativeTime(entry.created_at)}</span>
                  </div>
                ))}
              </div>
            </SectionCard>
          )}
        </>
      )}
      <PageFeedbackWidget />

    </div>
  );
}
