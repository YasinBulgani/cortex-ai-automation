"use client";

import { useState } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { PageHeader } from "@/components/nexus/PageHeader";
import { EmptyState } from "@/components/nexus/EmptyState";

interface QACycleResponse {
  plan_id: string;
  goal_achieved: boolean;
  coverage_before: number;
  coverage_after: number;
  coverage_delta: number;
  tests_generated: number;
  tests_executed: number;
  tests_passed: number;
  failures_healed: number;
  flaky_detected: number;
  assertions_added: number;
  quality_score: number;
  next_recommendations: string[];
}

const PRESET_GOALS = [
  { label: "Kapsam Artır", goal: "Kapsam oranını artırmak için eksik endpoint'lere test üret ve çalıştır" },
  { label: "Güvenlik Tarama", goal: "Critical ve high risk endpoint'lere güvenlik testi üret ve çalıştır" },
  { label: "Flaky Temizle", goal: "Flaky testleri tespit et, karantinaya al ve stabil testleri yeniden çalıştır" },
  { label: "Tam Döngü", goal: "Tüm endpoint'lere kapsam analizi yap, test üret, çalıştır ve raporla" },
];

function useFullCycle(projectId: string) {
  return useMutation({
    mutationFn: (args: { goal: string; context?: Record<string, unknown> }) =>
      apiFetch<QACycleResponse>(
        `/api/v1/ai/qa/full-cycle?project_id=${projectId}`,
        { method: "POST", json: args },
      ),
  });
}

export default function QAOrchestratorPage() {
  const projectId = useRouteParam("projectId");
  const [customGoal, setCustomGoal] = useState("");
  const [cycleResult, setCycleResult] = useState<QACycleResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cycleMut = useFullCycle(projectId);

  async function handleRun(goal: string) {
    setCycleResult(null);
    try {
      setError(null);
      const result = await cycleMut.mutateAsync({ goal });
      setCycleResult(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "QA dongusu baslatilamadi.");
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="qa-orchestrator-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        }
        title="QA Orkestratör"
        description="Plan → Act → Verify otonom test döngüsü"
      />

      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Goal input */}
      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-5">
        <p className="text-sm font-medium text-violet-300 mb-3">Hedef Belirle</p>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={customGoal}
            onChange={(e) => setCustomGoal(e.target.value)}
            placeholder="Örn: Ödeme API'leri için tam kapsam oluştur..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500"
          />
          <button
            onClick={() => customGoal && handleRun(customGoal)}
            disabled={!customGoal || cycleMut.isPending}
            className="px-4 py-2 text-sm font-semibold text-violet-300 border border-violet-500/30 rounded-xl hover:bg-violet-500/10 transition-all disabled:opacity-50"
          >
            {cycleMut.isPending ? (
              <div className="w-4 h-4 border-2 border-violet-300/30 border-t-violet-300 rounded-full animate-spin" />
            ) : (
              "Çalıştır"
            )}
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESET_GOALS.map((pg) => (
            <button
              key={pg.label}
              onClick={() => {
                setCustomGoal(pg.goal);
                handleRun(pg.goal);
              }}
              disabled={cycleMut.isPending}
              className="px-3 py-1.5 text-xs font-medium text-slate-300 border border-slate-700 rounded-lg hover:bg-slate-800 transition-all disabled:opacity-50"
            >
              {pg.label}
            </button>
          ))}
        </div>
      </div>

      {/* Running indicator */}
      {cycleMut.isPending && (
        <div className="rounded-xl border border-violet-500/20 bg-slate-900/40 p-6 flex items-center justify-center gap-3">
          <div className="w-5 h-5 border-2 border-violet-400/30 border-t-violet-400 rounded-full animate-spin" />
          <span className="text-sm text-violet-300">QA döngüsü çalışıyor...</span>
        </div>
      )}

      {/* Cycle result */}
      {cycleResult && (
        <div className="space-y-4">
          <div className={`rounded-xl border p-5 ${cycleResult.goal_achieved ? "border-emerald-500/20 bg-emerald-500/5" : "border-amber-500/20 bg-amber-500/5"}`}>
            <div className="flex items-center gap-3">
              <span className="text-3xl">{cycleResult.goal_achieved ? "✅" : "⚠️"}</span>
              <div>
                <p className="text-sm font-medium text-white">
                  {cycleResult.goal_achieved ? "Hedef Başarıldı" : "Hedef Kısmen Tamamlandı"}
                </p>
                <p className="text-xs text-slate-400">Kalite Skoru: {cycleResult.quality_score.toFixed(1)}/10</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Kapsam Değişimi</p>
              <p className={`text-2xl font-bold ${cycleResult.coverage_delta > 0 ? "text-emerald-400" : "text-slate-300"}`}>
                {cycleResult.coverage_delta > 0 ? "+" : ""}{cycleResult.coverage_delta.toFixed(1)}%
              </p>
              <p className="text-[10px] text-slate-500">{cycleResult.coverage_before.toFixed(0)}% → {cycleResult.coverage_after.toFixed(0)}%</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Üretilen / Geçen</p>
              <p className="text-2xl font-bold text-blue-400">{cycleResult.tests_generated} / {cycleResult.tests_passed}</p>
              <p className="text-[10px] text-slate-500">{cycleResult.tests_executed} çalıştırıldı</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-xs text-slate-400 mb-1">Heal / Flaky</p>
              <p className="text-2xl font-bold text-violet-400">{cycleResult.failures_healed} / {cycleResult.flaky_detected}</p>
            </div>
          </div>

          {cycleResult.next_recommendations.length > 0 && (
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
              <p className="text-xs font-medium text-slate-400 mb-2">Sonraki Adımlar</p>
              <ul className="space-y-1">
                {cycleResult.next_recommendations.map((r, i) => (
                  <li key={i} className="text-sm text-slate-300">
                    <span className="text-violet-400">{i + 1}.</span> {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!cycleMut.isPending && !cycleResult && (
        <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-16">
          <EmptyState
            icon="🧪"
            title="Otonom QA Döngüsü"
            description="Bir hedef girin veya hazır şablonlardan birini seçerek AI destekli test döngüsünü başlatın"
          />
        </div>
      )}
    </div>
  );
}
