"use client";

import { useState, useMemo } from "react";

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

// ── Risk matrix scatter chart ─────────────────────────────────────────────────
const RISK_X: Record<string, number> = { low: 15, medium: 38, high: 65, critical: 88 };

function RiskMatrixChart({ tests }: { tests: PrioritizedTest[] }) {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="relative w-full" style={{ paddingTop: "60%" }}>
      <div className="absolute inset-0 rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden">
        {/* Grid */}
        <div className="absolute inset-0 grid grid-cols-4 opacity-20">
          {[0,1,2,3].map(i => <div key={i} className="border-l border-slate-600 first:border-0" />)}
        </div>
        <div className="absolute inset-0 grid grid-rows-4 opacity-20">
          {[0,1,2,3].map(i => <div key={i} className="border-t border-slate-600 first:border-0" />)}
        </div>

        {/* Labels */}
        <div className="absolute bottom-2 left-0 right-0 flex justify-around px-4 text-[10px] text-slate-600">
          <span>Düşük</span><span>Orta</span><span>Yüksek</span><span>Kritik</span>
        </div>
        <div className="absolute top-2 left-2 text-[10px] text-slate-600">Ön. Skor</div>
        <div className="absolute bottom-6 right-2 text-[10px] text-slate-600">Risk Seviyesi →</div>

        {/* Dots */}
        {tests.slice(0, 80).map((t) => {
          const x = RISK_X[t.risk_level] ?? 50;
          const y = 95 - t.priority_score * 0.9;
          const color =
            t.priority_score >= 70 ? "#ef4444" :
            t.priority_score >= 40 ? "#f59e0b" :
            "#22c55e";

          return (
            <div
              key={t.test_case_id}
              onMouseEnter={() => setHovered(t.test_case_id)}
              onMouseLeave={() => setHovered(null)}
              className="absolute h-2.5 w-2.5 rounded-full -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-transform hover:scale-150"
              style={{ left: `${x}%`, top: `${y}%`, background: color, opacity: 0.8 }}
              title={`${t.title} (${t.priority_score.toFixed(0)})`}
            />
          );
        })}

        {/* Tooltip */}
        {hovered && (() => {
          const t = tests.find(x => x.test_case_id === hovered);
          if (!t) return null;
          const x = RISK_X[t.risk_level] ?? 50;
          const y = 95 - t.priority_score * 0.9;
          return (
            <div
              className="absolute z-10 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs shadow-xl pointer-events-none max-w-[200px]"
              style={{ left: `${Math.min(x + 3, 60)}%`, top: `${Math.max(y - 10, 5)}%` }}
            >
              <p className="font-semibold text-white truncate">{t.title}</p>
              <p className="text-slate-400">Skor: {t.priority_score.toFixed(0)} · {t.risk_level}</p>
            </div>
          );
        })()}
      </div>
    </div>
  );
}

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
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkRunning, setBulkRunning] = useState(false);

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

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === tests.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(tests.map((t) => t.test_case_id)));
    }
  }

  async function handleBulkRun() {
    if (selectedIds.size === 0) return;
    setBulkRunning(true);
    setActionError(null);
    try {
      await fetch(`/api/v1/tspm/projects/${projectId}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ test_case_ids: Array.from(selectedIds) }),
      });
      setSelectedIds(new Set());
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "Toplu çalıştırma başlatılamadı.");
    } finally {
      setBulkRunning(false);
    }
  }

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
            "Test onceliklendirme verisi su anda yüklenemedi."}
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

      {/* Risk matrix scatter chart */}
      {tests.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          <SectionCard title="Risk Matrisi" icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="2" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2v4m0 12v4m8-8h-4M8 12H4" /></svg>}>
            <RiskMatrixChart tests={tests} />
            <div className="mt-3 flex justify-center gap-4 text-[10px] text-slate-500">
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" />Yüksek</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-amber-500" />Orta</span>
              <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" />Düşük</span>
            </div>
          </SectionCard>

          <SectionCard title="Faktör Dağılımı" icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}>
            {tests.length > 0 && (() => {
              const avg = {
                failure: tests.reduce((s, t) => s + t.breakdown.failure, 0) / tests.length,
                risk: tests.reduce((s, t) => s + t.breakdown.risk, 0) / tests.length,
                recency: tests.reduce((s, t) => s + t.breakdown.recency, 0) / tests.length,
                sensitivity: tests.reduce((s, t) => s + t.breakdown.sensitivity, 0) / tests.length,
                change_impact: tests.reduce((s, t) => s + t.breakdown.change_impact, 0) / tests.length,
              };
              const bars = [
                { label: "Hata Geçmişi", value: avg.failure, color: "bg-red-500" },
                { label: "Risk Seviyesi", value: avg.risk, color: "bg-orange-500" },
                { label: "Son Değişim", value: avg.recency, color: "bg-blue-500" },
                { label: "Hassasiyet", value: avg.sensitivity, color: "bg-purple-500" },
                { label: "Değişim Etkisi", value: avg.change_impact, color: "bg-cyan-500" },
              ];
              const maxVal = Math.max(...bars.map(b => b.value));
              return (
                <div className="space-y-3">
                  {bars.map((b) => (
                    <div key={b.label}>
                      <div className="flex justify-between mb-1">
                        <span className="text-xs text-slate-400">{b.label}</span>
                        <span className="text-xs text-slate-300 tabular-nums">{b.value.toFixed(1)}</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-slate-800">
                        <div className={`h-full rounded-full ${b.color}`} style={{ width: `${maxVal > 0 ? (b.value / maxVal) * 100 : 0}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              );
            })()}
          </SectionCard>
        </div>
      )}

      {/* Priority list */}
      <SectionCard
        title="Önceliklendirilmiş Test Listesi"
        icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" /></svg>}
        right={
          <div className="flex items-center gap-2">
            {selectedIds.size > 0 && (
              <button
                onClick={handleBulkRun}
                disabled={bulkRunning}
                className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1 text-xs font-semibold text-white hover:bg-violet-500 disabled:opacity-50"
              >
                {bulkRunning ? "Çalışıyor…" : `${selectedIds.size} Testi Çalıştır`}
              </button>
            )}
            <span className="text-xs text-slate-500">{totalCount} test</span>
          </div>
        }
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
                <th className="px-4 py-2.5 w-8">
                  <input
                    type="checkbox"
                    checked={tests.length > 0 && selectedIds.size === tests.length}
                    onChange={toggleSelectAll}
                    className="rounded border-slate-600 bg-slate-800 accent-violet-500"
                  />
                </th>
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
                <tr key={t.test_case_id} className={`border-b border-slate-800 last:border-0 hover:bg-slate-800/30 ${selectedIds.has(t.test_case_id) ? "bg-violet-500/5" : ""}`}>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(t.test_case_id)}
                      onChange={() => toggleSelect(t.test_case_id)}
                      className="rounded border-slate-600 bg-slate-800 accent-violet-500"
                    />
                  </td>
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
