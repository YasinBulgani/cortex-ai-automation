"use client";

import { useEffect, useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import {
  PageHeader,
  SectionCard,
  EmptyState,
  StatCard,
  MetricRow,
  ToolbarActions,
} from "@/components/nexus";
import {
  useFlakyTests,
  useQuarantineList,
  useQuarantineTest,
  type FlakyTest as ApiFlakyTest,
} from "@/lib/hooks/use-api-testing";

type FlakyTest = {
  scenario_id: string;
  scenario_title: string;
  flip_count: number;
  last_results: string[];
};

export default function FlakyTestsPage() {
  const projectId = useRouteParam("projectId");
  const [tests, setTests] = useState<FlakyTest[]>([]);

  useEffect(() => {
    apiFetch<FlakyTest[]>(`/api/v1/tspm/projects/${projectId}/flaky-tests`).then(setTests).catch(() => {});
  }, [projectId]);

  const highFlip = tests.filter(t => t.flip_count >= 3).length;
  const avgFlip = tests.length > 0 ? (tests.reduce((a, t) => a + t.flip_count, 0) / tests.length).toFixed(1) : "0";

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="flaky-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        }
        title="Flaky Testler"
        description="Son 10 koşuda tutarsız sonuç veren testler"
        right={
          <ToolbarActions>
            {tests.length > 0 && (
              <button
                onClick={runAnomalyDetection}
                disabled={analyzing}
                className="flex items-center gap-2 rounded-xl border border-violet-500/30 px-4 py-1.5 text-sm font-semibold text-violet-300 transition-all hover:bg-violet-500/10 disabled:opacity-50"
              >
                {analyzing ? (
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-violet-300/30 border-t-violet-300" />
                ) : (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                )}
                AI Anomali Analizi
              </button>
            )}
          </ToolbarActions>
        }
      />

      {/* Stats */}
      <MetricRow cols={3}>
        <StatCard label="Toplam Flaky" value={tests.length} color={tests.length > 0 ? "amber" : "slate"} />
        <StatCard label="Yüksek Risk" value={highFlip} color={highFlip > 0 ? "red" : "slate"} sub="≥3 flip" />
        <StatCard label="AI Anomali" value={anomalyReport?.anomaly_count ?? "—"} color="violet" />
      </MetricRow>

      <SectionCard title="Flaky Test Listesi" noPad>
        {tests.length === 0 ? (
          <div className="p-8">
            <EmptyState icon="🎉" title="Flaky test yok — tebrikler!" description="Tüm testler tutarlı sonuç veriyor" data-testid="flaky-empty" />
          </div>
        ) : (
          <table className="w-full" data-testid="flaky-table">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Senaryo</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Stabilite</th>
                <th className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">Son 10 Koşu</th>
              </tr>
            </thead>
            <tbody>
              {tests.map(t => {
                const passCount = t.last_results.filter(r => r === "passed").length;
                const stability = Math.round((passCount / Math.max(t.last_results.length, 1)) * 100);

      {/* List tab */}
      {activeTab === "list" && (
        <SectionCard
          title="Flaky Test Listesi"
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
          noPad
        >
          {tests.length === 0 ? (
            <div className="p-8">
              <EmptyState icon="🎉" title="Flaky test yok — tebrikler!" description="Tüm testler tutarlı sonuç veriyor" data-testid="flaky-empty" />
            </div>
          ) : (
            <table className="w-full" data-testid="flaky-table">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Senaryo</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Değişim</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Son 10 Koşu</th>
                </tr>
              </thead>
              <tbody>
                {tests.map(t => (
                  <tr key={t.scenario_id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30" data-testid={`flaky-row-${t.scenario_id}`}>
                    <td className="px-4 py-3 text-sm font-medium text-white">{t.scenario_title}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${stability >= 80 ? "bg-emerald-500" : stability >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                            style={{ width: `${stability}%` }}
                          />
                        </div>
                        <span className={`text-xs font-medium ${stability >= 80 ? "text-emerald-400" : stability >= 50 ? "text-amber-400" : "text-red-400"}`}>
                          {stability}%
                        </span>
                        <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${
                          t.flip_count >= 5 ? "bg-red-500/10 border-red-500/20 text-red-400"
                          : t.flip_count >= 3 ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                          : "bg-slate-800 border-slate-700 text-slate-300"
                        }`}>
                          {t.flip_count} flip
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        {t.last_results.map((r, i) => (
                          <span key={i} className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                            r === "passed" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
                          }`}>
                            {r === "passed" ? "P" : "F"}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>
      )}

      {/* API Flaky tab */}
      {activeTab === "api-flaky" && (
        <SectionCard
          title="API Test Flaky Analizi"
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
          noPad
        >
          {flakyLoading ? (
            <div className="flex justify-center p-10">
              <div className="w-6 h-6 border-2 border-amber-400/30 border-t-amber-400 rounded-full animate-spin" />
            </div>
          ) : apiFlaky.length === 0 ? (
            <div className="p-8">
              <EmptyState icon="✅" title="Flaky API testi yok" description="Tüm API testleri tutarlı sonuç veriyor" />
            </div>
          ) : (
            <table className="w-full" data-testid="api-flaky-table">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Test</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tip</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Flaky Skor</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Koşu / Geçme</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Öneri</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">İşlem</th>
                </tr>
              </thead>
              <tbody>
                {apiFlaky.map((t) => (
                  <tr key={t.test_case_id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30" data-testid={`api-flaky-row-${t.test_case_id}`}>
                    <td className="px-4 py-3 text-sm font-medium text-white max-w-[260px] truncate">{t.title}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-xs text-slate-300">{t.test_type}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${t.flaky_score >= 0.7 ? "bg-red-500" : t.flaky_score >= 0.4 ? "bg-amber-500" : "bg-emerald-500"}`}
                            style={{ width: `${Math.round(t.flaky_score * 100)}%` }}
                          />
                        </div>
                        <span className={`text-xs font-mono ${t.flaky_score >= 0.7 ? "text-red-400" : t.flaky_score >= 0.4 ? "text-amber-400" : "text-emerald-400"}`}>
                          {(t.flaky_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-300">
                      {t.run_count} koşu · %{(t.pass_rate * 100).toFixed(0)} geçme
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${REC_COLORS[t.recommendation] ?? "bg-slate-800 border-slate-700 text-slate-300"}`}>
                        {t.recommendation === "quarantine" ? "🔒 Karantina" : t.recommendation === "investigate" ? "🔍 İncele" : "✅ Stabil"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {t.recommendation === "quarantine" && (
                        <button
                          onClick={() => quarantineMut.mutate({ testCaseId: t.test_case_id, reason: `Flaky score: ${(t.flaky_score * 100).toFixed(0)}% — otomatik öneri` })}
                          disabled={quarantineMut.isPending}
                          className="px-2.5 py-1 text-xs font-medium text-red-300 border border-red-500/30 rounded-lg hover:bg-red-500/10 transition-all disabled:opacity-50"
                        >
                          Karantinala
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>
      )}

      {/* Quarantine tab */}
      {activeTab === "quarantine" && (
        <SectionCard
          title="Karantina Listesi"
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>}
          noPad
        >
          {qLoading ? (
            <div className="flex justify-center p-10">
              <div className="w-6 h-6 border-2 border-red-400/30 border-t-red-400 rounded-full animate-spin" />
            </div>
          ) : quarantined.length === 0 ? (
            <div className="p-8">
              <EmptyState icon="🔓" title="Karantinada test yok" description="Henüz karantinaya alınmış test bulunmuyor" />
            </div>
          ) : (
            <table className="w-full" data-testid="quarantine-table">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Test</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Tip</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Flaky Skor</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Sebep</th>
                  <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400">Geçme Oranı</th>
                </tr>
              </thead>
              <tbody>
                {quarantined.map((q) => (
                  <tr key={q.id} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                    <td className="px-4 py-3 text-sm font-medium text-white max-w-[260px] truncate">{q.title}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-xs text-slate-300">{q.test_type}</span>
                    </td>
                    <td className="px-4 py-3">
                      {q.flaky_score != null ? (
                        <span className={`text-xs font-mono ${q.flaky_score >= 0.7 ? "text-red-400" : q.flaky_score >= 0.4 ? "text-amber-400" : "text-emerald-400"}`}>
                          {(q.flaky_score * 100).toFixed(0)}%
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-[200px] truncate">{q.quarantine_reason ?? "—"}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-slate-300">{q.run_count} koşu · %{(q.pass_rate * 100).toFixed(0)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>
      )}

      {/* Anomaly tab */}
      {activeTab === "anomaly" && anomalyReport && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-2xl font-bold text-white">{anomalyReport.total_tested}</p>
              <p className="text-xs text-slate-400 mt-1">Test İncelendi</p>
            </div>
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 text-center">
              <p className="text-2xl font-bold text-red-400">{anomalyReport.anomaly_count}</p>
              <p className="text-xs text-slate-400 mt-1">Anomali</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3 text-center">
              <p className="text-2xl font-bold text-blue-400">{anomalyReport.avg_duration_ms.toFixed(0)}ms</p>
              <p className="text-xs text-slate-400 mt-1">Ort. Süre</p>
            </div>
          </div>

          <SectionCard
            title="Anomaliler"
            icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
            noPad
          >
            {anomalyReport.anomalies.length === 0 ? (
              <div className="p-8">
                <EmptyState icon="✅" title="Anomali tespit edilmedi" description="Tüm testler normal görünüyor" />
              </div>
            ) : (
              anomalyReport.anomalies.map((a, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                  <span className="text-sm font-mono text-slate-300">{a.testId}</span>
                  <div className="flex gap-1.5">
                    {a.issues.map(issue => (
                      <span key={issue} className={`px-2 py-0.5 rounded-full border text-xs font-medium ${ISSUE_COLORS[issue] ?? "bg-slate-800 border-slate-700 text-slate-300"}`}>
                        {issue}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </SectionCard>
        </div>
      )}
    </div>
  );
}
