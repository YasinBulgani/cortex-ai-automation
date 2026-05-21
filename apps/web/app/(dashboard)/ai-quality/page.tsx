"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";

/**
 * Unified AI Quality Dashboard — GET /ai/quality/dashboard
 *
 * Gosterir:
 *   - overview (maliyet dahil)
 *   - regression alerts (24h vs 7d)
 *   - model tablosu + maliyet
 *   - LLM-as-Judge skorlari
 *   - Smart Router config + circuit state
 *   - RAG ingestion istatistikleri
 *   - son eval run
 */

interface DashboardPayload {
  period_days: number;
  overview: {
    total_calls?: number;
    success_rate?: number;
    json_parse_rate?: number;
    avg_latency_ms?: number;
    total_cost_usd?: number;
    avg_cost_usd?: number;
    cost_per_1k_calls_usd?: number;
  };
  by_model: Array<{
    model: string;
    calls: number;
    success_rate: number;
    json_parse_rate: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
    total_cost_usd?: number;
    avg_cost_usd?: number;
  }>;
  regression_alerts: Array<{
    severity: string;
    metric: string;
    message: string;
  }>;
  recommendations: string[];
  judge: {
    total?: number;
    avg_overall?: number;
    avg_correctness?: number;
    avg_completeness?: number;
    avg_domain_fit?: number;
    avg_format_validity?: number;
    by_task?: Array<{ task_type: string; count: number; avg_overall: number }>;
  };
  routing: {
    routing_mode?: string;
    tiers?: Record<string, string>;
    provider_availability?: Record<string, boolean>;
    fallback_chain?: string;
    circuit_state?: Record<string, { failures: number; last_failure_ts: number }>;
  };
  ingestion: {
    total?: number;
    sources?: Array<{ source: string; count: number; last_ingest: string | null; dedup_events: number }>;
  };
  eval_latest: {
    suite?: string;
    total?: number;
    pass_count?: number;
    pass_rate?: number;
    results?: Array<{
      prompt_id: string;
      task_type: string;
      model: string;
      tier: string;
      pass_all: boolean;
      judge_overall: number | null;
      latency_ms: number;
    }>;
  };
  eval_harness_latest?: EvalHarnessLatest | null;
  eval_harness_history?: EvalHarnessRun[];
  eval_harness_summary?: EvalHarnessSummary | null;
  workflow_signoff_latest?: {
    generated_at?: string | null;
    release_decision?: string | null;
    llm_quality_score?: number | null;
    prompt_center_hash?: string | null;
    report_path?: string | null;
    failed_required_checks?: string[];
    live_eval_gate?: {
      status?: string | null;
      required?: boolean;
      message?: string | null;
      started_at?: string | null;
      duration_ms?: number | null;
      report_path?: string | null;
      report_generated_at?: string | null;
    } | null;
  } | null;
}

interface EvalHarnessSuiteSummary {
  name: string;
  adapter: string;
  passed: boolean;
  skipped: boolean;
  cases_total: number;
  cases_passed: number;
  case_pass_rate?: number;
  total_latency_ms: number;
  aggregate?: Record<string, number>;
  threshold_failures?: string[];
}

interface EvalHarnessRun {
  generated_at: string;
  report_dir?: string;
  overall_passed: boolean;
  total_suites: number;
  total_cases: number;
  passed_cases: number;
  case_pass_rate: number;
  total_latency_ms: number;
  suites: EvalHarnessSuiteSummary[];
}

interface EvalHarnessLatest {
  generated_at: string;
  report_dir?: string;
  suites: Array<{
    suite_name: string;
    adapter_name: string;
    passed: boolean;
    aggregate: Record<string, number>;
    total_latency_ms: number;
    cases: Array<{
      case_id: string;
      passed: boolean;
      latency_ms: number;
      actual: {
        provider_used?: string;
        model_used?: string;
        attempts?: Array<Record<string, unknown>>;
      };
    }>;
  }>;
}

interface EvalHarnessSummary {
  status: "pass" | "warn" | "fail" | "unknown";
  total_runs: number;
  latest_generated_at?: string | null;
  latest_pass_rate: number;
  latest_latency_ms: number;
  previous_pass_rate?: number | null;
  pass_rate_delta?: number | null;
  latency_delta_pct?: number | null;
  alerts: Array<{ severity: string; metric: string; message: string }>;
  suite_health: Array<{
    name: string;
    adapter: string;
    status: "pass" | "warn" | "fail";
    runs: number;
    pass_rate: number;
    avg_case_pass_rate: number;
    latest_passed: boolean;
    latest_case_pass_rate: number;
    latest_latency_ms: number;
    latest_threshold_failures: string[];
  }>;
  runtime_matrix: Array<{
    provider: string;
    model: string;
    cases: number;
    attempts: number;
  }>;
}

function rateColor(rate: number | undefined) {
  if (rate === undefined) return "text-slate-400";
  if (rate > 90) return "text-emerald-400";
  if (rate > 80) return "text-amber-400";
  return "text-red-400";
}

function sevColor(sev: string) {
  if (sev === "P0" || sev === "P1") return "bg-red-500/10 text-red-400 border-red-500/30";
  return "bg-amber-500/10 text-amber-400 border-amber-500/30";
}

function fmtDateTime(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "medium" });
}

function pct(value?: number) {
  return `%${((value ?? 0) * 100).toFixed(1)}`;
}

function gateColor(status?: string) {
  if (status === "pass") return "text-emerald-400";
  if (status === "warn") return "text-amber-400";
  if (status === "fail") return "text-red-400";
  return "text-slate-400";
}

function gateLabel(status?: string) {
  if (status === "pass" || status === "passed") return "PASS";
  if (status === "warn") return "WARN";
  if (status === "fail" || status === "failed") return "FAIL";
  if (status === "skipped") return "SKIP";
  return "UNKNOWN";
}

function releaseDecisionLabel(value?: string | null) {
  if (value === "ready_for_operator_approval") return "Operator Onayına Hazır";
  if (value === "needs_external_soak_and_dr_signoff") return "External Soak / DR Bekliyor";
  if (value === "needs_remaining_release_gates") return "Kalan Release Gate'leri Var";
  if (value === "fail") return "Release Fail";
  return "Bilinmiyor";
}

function liveEvalColor(status?: string | null, required?: boolean) {
  if (status === "pass" || status === "passed") return "text-emerald-400";
  if (status === "warn") return "text-amber-400";
  if (status === "fail" || status === "failed") return "text-red-400";
  if (status === "skipped") return required ? "text-red-400" : "text-amber-400";
  return "text-slate-400";
}

function signedPctPoint(value?: number | null) {
  if (value === undefined || value === null) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)} puan`;
}

function signedPct(value?: number | null) {
  if (value === undefined || value === null) return "-";
  const sign = value > 0 ? "+" : "";
  return `${sign}%${(value * 100).toFixed(1)}`;
}

export default function AiQualityDashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiFetch<DashboardPayload>(`/api/v1/ai/quality/dashboard?days=${days}`)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Bilinmeyen hata");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-slate-950 p-6">
        <PageHeader
          icon={<span className="text-lg">🧭</span>}
          title="AI Quality Dashboard"
          description="Yukleniyor..."
        />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-800 border border-slate-700" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    const isHtmlError = error?.trim().startsWith("<");
    const friendly = isHtmlError
      ? "AI Quality endpoint'i (/ai/quality/dashboard) backend'de bulunamadı veya hazır değil."
      : (error ?? "Bilinmeyen hata");
    return (
      <div className="min-h-screen bg-slate-950 p-6">
        <PageHeader
          icon={<span className="text-lg">🧭</span>}
          title="AI Quality Dashboard"
          description="Veri çekilemedi"
        />
        <SectionCard title="Bağlantı Hatası">
          <div className="text-sm text-red-400 mb-3">{friendly}</div>
          <p className="text-xs text-slate-400">
            Bu panel router metrikleri, judge skorları ve eval sonuçlarını gösterir.
            Backend servisi ayağa kalkınca veriler otomatik yüklenir.
          </p>
        </SectionCard>
      </div>
    );
  }

  const ov = data.overview;
  const alerts = data.regression_alerts ?? [];
  const harnessHistory = data.eval_harness_history ?? [];
  const harnessLatestRun = harnessHistory[harnessHistory.length - 1] ?? null;
  const harnessLatest = data.eval_harness_latest ?? null;
  const harnessTrend = harnessHistory.slice(-8);
  const harnessSummary = data.eval_harness_summary ?? null;
  const workflowSignoff = data.workflow_signoff_latest ?? null;
  const liveEvalGate = workflowSignoff?.live_eval_gate ?? null;

  return (
    <div className="min-h-screen bg-slate-950 p-6 space-y-4">
      <PageHeader
        icon={<span className="text-lg">🧭</span>}
        title="AI Quality Dashboard"
        description={`Router + Judge + Eval + RAG — son ${days} gun`}
        right={
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 border border-slate-700 text-slate-300"
          >
            {[1, 7, 14, 30].map((d) => (
              <option key={d} value={d}>
                {d} gun
              </option>
            ))}
          </select>
        }
      />

      {alerts.length > 0 && (
        <SectionCard title="Regresyon Uyarilari" subtitle="24 saat vs 7 gun hareketli ortalama">
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className={`px-3 py-2 rounded-lg border text-sm ${sevColor(a.severity)}`}>
                <span className="font-mono text-xs mr-2">[{a.severity}]</span>
                <span className="font-medium mr-2">{a.metric}:</span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Toplam Cagri" value={String(ov.total_calls ?? 0)} />
        <StatCard
          label="Başarı Orani"
          value={`%${(ov.success_rate ?? 0).toFixed(1)}`}
          color={rateColor(ov.success_rate)}
        />
        <StatCard
          label="JSON Parse"
          value={`%${(ov.json_parse_rate ?? 0).toFixed(1)}`}
          color={rateColor(ov.json_parse_rate)}
        />
        <StatCard
          label={`Toplam Maliyet (son ${days}g)`}
          value={`$${(ov.total_cost_usd ?? 0).toFixed(2)}`}
        />
      </div>

      <SectionCard title="Model Performans + Maliyet" subtitle="Her model bazli başarı/latency/maliyet">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase text-slate-400 border-b border-slate-800">
              <tr>
                <th className="text-left py-2 px-3">Model</th>
                <th className="text-right py-2 px-3">Cagri</th>
                <th className="text-right py-2 px-3">Basari</th>
                <th className="text-right py-2 px-3">JSON</th>
                <th className="text-right py-2 px-3">Avg Lat</th>
                <th className="text-right py-2 px-3">P95 Lat</th>
                <th className="text-right py-2 px-3">Toplam $</th>
                <th className="text-right py-2 px-3">Avg $</th>
              </tr>
            </thead>
            <tbody>
              {data.by_model.map((m) => (
                <tr key={m.model} className="border-b border-slate-800/50">
                  <td className="py-2 px-3 font-mono text-xs text-slate-300">{m.model}</td>
                  <td className="text-right py-2 px-3">{m.calls}</td>
                  <td className={`text-right py-2 px-3 ${rateColor(m.success_rate)}`}>%{m.success_rate.toFixed(1)}</td>
                  <td className={`text-right py-2 px-3 ${rateColor(m.json_parse_rate)}`}>%{m.json_parse_rate.toFixed(1)}</td>
                  <td className="text-right py-2 px-3">{m.avg_latency_ms}ms</td>
                  <td className="text-right py-2 px-3">{m.p95_latency_ms}ms</td>
                  <td className="text-right py-2 px-3">${(m.total_cost_usd ?? 0).toFixed(4)}</td>
                  <td className="text-right py-2 px-3">${(m.avg_cost_usd ?? 0).toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      {data.judge && data.judge.total !== undefined && data.judge.total > 0 && (
        <SectionCard title="LLM-as-Judge Skorlari" subtitle={`Son ${days} gun — ${data.judge.total} degerlendirme`}>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Genel" value={`${(data.judge.avg_overall ?? 0).toFixed(1)}/10`} />
            <StatCard label="Correctness" value={`${(data.judge.avg_correctness ?? 0).toFixed(1)}/10`} />
            <StatCard label="Completeness" value={`${(data.judge.avg_completeness ?? 0).toFixed(1)}/10`} />
            <StatCard label="Domain Fit" value={`${(data.judge.avg_domain_fit ?? 0).toFixed(1)}/10`} />
            <StatCard label="Format" value={`${(data.judge.avg_format_validity ?? 0).toFixed(1)}/10`} />
          </div>
          {data.judge.by_task && data.judge.by_task.length > 0 && (
            <div className="mt-3 text-xs text-slate-400">
              {data.judge.by_task.map((t) => (
                <span key={t.task_type} className="inline-block mr-3">
                  {t.task_type}: {t.count} × {t.avg_overall.toFixed(1)}
                </span>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      <SectionCard title="Smart Model Router" subtitle={`Mod: ${data.routing.routing_mode}`}>
        <div className="text-sm grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-xs uppercase text-slate-400 mb-1">Tier&apos;lar</h4>
            <ul className="font-mono text-xs space-y-0.5">
              {Object.entries(data.routing.tiers ?? {}).map(([tier, model]) => (
                <li key={tier}>
                  <span className="text-slate-400">{tier}</span>: <span className="text-slate-200">{model}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500 mt-2">{data.routing.fallback_chain}</p>
          </div>
          <div>
            <h4 className="text-xs uppercase text-slate-400 mb-1">Provider</h4>
            <ul className="text-xs space-y-0.5">
              {Object.entries(data.routing.provider_availability ?? {}).map(([p, ok]) => (
                <li key={p}>
                  <span className={ok ? "text-emerald-400" : "text-red-400"}>●</span> {p}
                </li>
              ))}
            </ul>
            {Object.keys(data.routing.circuit_state ?? {}).length > 0 && (
              <div className="mt-2">
                <h4 className="text-xs uppercase text-slate-400 mb-1">Circuit State</h4>
                <ul className="text-xs space-y-0.5 font-mono">
                  {Object.entries(data.routing.circuit_state ?? {}).map(([m, s]) => (
                    <li key={m}>
                      {m}: {s.failures} basarisizlik
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </SectionCard>

      <SectionCard title="RAG KnowledgeStore" subtitle={`Toplam ${data.ingestion.total ?? 0} kayit`}>
        <div className="text-xs space-y-1">
          {(data.ingestion.sources ?? []).map((s) => (
            <div key={s.source} className="flex items-center justify-between border-b border-slate-800/30 py-1">
              <span className="font-mono text-slate-300">{s.source}</span>
              <span className="text-slate-400">
                {s.count} kayit · {s.dedup_events} dedup · {s.last_ingest ?? "-"}
              </span>
            </div>
          ))}
        </div>
      </SectionCard>

      {data.eval_latest?.total !== undefined && data.eval_latest.total > 0 && (
        <SectionCard
          title="Son Eval Run"
          subtitle={`${data.eval_latest.suite} — %${(data.eval_latest.pass_rate ?? 0).toFixed(1)} gecti (${data.eval_latest.pass_count}/${data.eval_latest.total})`}
        >
          <div className="text-xs font-mono space-y-1">
            {(data.eval_latest.results ?? []).slice(0, 20).map((r, i) => (
              <div key={i} className="flex items-center justify-between border-b border-slate-800/30 py-1">
                <span>
                  <span className={r.pass_all ? "text-emerald-400" : "text-red-400"}>●</span> {r.prompt_id}{" "}
                  <span className="text-slate-500">[{r.task_type}]</span>
                </span>
                <span className="text-slate-400">
                  {r.model} · {r.tier} · {r.latency_ms}ms
                  {r.judge_overall !== null ? ` · judge ${r.judge_overall.toFixed(1)}/10` : ""}
                </span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {harnessSummary && (
        <div data-testid="ai-quality-eval-gate">
          <SectionCard
            title="Eval Quality Gate"
            subtitle={`Son koşum: ${fmtDateTime(harnessSummary.latest_generated_at ?? undefined)} — ${harnessSummary.total_runs} history kaydı`}
          >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard
              label="Gate"
              value={gateLabel(harnessSummary.status)}
              color={gateColor(harnessSummary.status)}
            />
            <StatCard
              label="Pass Rate"
              value={pct(harnessSummary.latest_pass_rate)}
              color={rateColor(harnessSummary.latest_pass_rate * 100)}
            />
            <StatCard
              label="Pass Delta"
              value={signedPctPoint(harnessSummary.pass_rate_delta)}
              color={(harnessSummary.pass_rate_delta ?? 0) < 0 ? "text-red-400" : "text-emerald-400"}
            />
            <StatCard
              label="Latency Delta"
              value={signedPct(harnessSummary.latency_delta_pct)}
              color={(harnessSummary.latency_delta_pct ?? 0) > 0.25 ? "text-amber-400" : "text-slate-100"}
            />
          </div>

          {harnessSummary.alerts.length > 0 && (
            <div className="mb-4 space-y-2">
              {harnessSummary.alerts.map((alert, i) => (
                <div key={`${alert.metric}-${i}`} className={`px-3 py-2 rounded-lg border text-xs ${sevColor(alert.severity)}`}>
                  <span className="font-mono mr-2">[{alert.severity}]</span>
                  <span className="font-medium mr-2">{alert.metric}:</span>
                  <span>{alert.message}</span>
                </div>
              ))}
            </div>
          )}

          {harnessSummary.suite_health.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="text-left py-2 px-3">Suite</th>
                    <th className="text-right py-2 px-3">Sağlık</th>
                    <th className="text-right py-2 px-3">Run Pass</th>
                    <th className="text-right py-2 px-3">Avg Case</th>
                    <th className="text-right py-2 px-3">Son Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {harnessSummary.suite_health.map((suite) => (
                    <tr key={suite.name} className="border-b border-slate-800/50">
                      <td className="py-2 px-3">
                        <div className="font-mono text-slate-300">{suite.name}</div>
                        <div className="text-[11px] text-slate-500">{suite.adapter}</div>
                      </td>
                      <td className={`text-right py-2 px-3 ${gateColor(suite.status)}`}>{gateLabel(suite.status)}</td>
                      <td className="text-right py-2 px-3">{pct(suite.pass_rate)}</td>
                      <td className="text-right py-2 px-3">{pct(suite.avg_case_pass_rate)}</td>
                      <td className="text-right py-2 px-3">{suite.latest_latency_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {harnessSummary.runtime_matrix.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {harnessSummary.runtime_matrix.map((row) => (
                <span key={`${row.provider}-${row.model}`} className="rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1 text-slate-300">
                  <span className="font-mono">{row.provider}</span> / {row.model} · {row.cases} case · {row.attempts} deneme
                </span>
              ))}
            </div>
          )}
          </SectionCard>
        </div>
      )}

      {workflowSignoff && (
        <div data-testid="ai-quality-live-eval">
          <SectionCard
            title="Live Eval + Release Signoff"
            subtitle={`Son signoff: ${fmtDateTime(workflowSignoff.generated_at ?? undefined)} — ${releaseDecisionLabel(workflowSignoff.release_decision)}`}
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <StatCard
                label="Live Eval"
                value={gateLabel(liveEvalGate?.status ?? undefined)}
                color={liveEvalColor(liveEvalGate?.status, liveEvalGate?.required)}
              />
              <StatCard
                label="Release"
                value={releaseDecisionLabel(workflowSignoff.release_decision)}
                color={workflowSignoff.release_decision === "ready_for_operator_approval" ? "text-emerald-400" : "text-amber-400"}
              />
              <StatCard
                label="LLM Skoru"
                value={workflowSignoff.llm_quality_score !== null && workflowSignoff.llm_quality_score !== undefined ? workflowSignoff.llm_quality_score.toFixed(2) : "-"}
              />
              <StatCard
                label="Gate Türü"
                value={liveEvalGate?.required ? "Blocking" : "Advisory"}
                color={liveEvalGate?.required ? "text-red-400" : "text-slate-100"}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-2">
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                  <div className="text-slate-400 mb-1">Live eval durumu</div>
                  <div className={`${liveEvalColor(liveEvalGate?.status, liveEvalGate?.required)} font-medium`}>
                    {liveEvalGate?.message || "Canlı live eval sonucu son signoff raporunda bulunamadı."}
                  </div>
                  {liveEvalGate?.report_generated_at && (
                    <div className="mt-2 text-slate-500">
                      Kaynak rapor: {fmtDateTime(liveEvalGate.report_generated_at)}
                    </div>
                  )}
                </div>
                {workflowSignoff.failed_required_checks && workflowSignoff.failed_required_checks.length > 0 && (
                  <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-red-300">
                    Zorunlu gate sorunları: {workflowSignoff.failed_required_checks.join(", ")}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                  <div className="text-slate-400 mb-1">Prompt hash</div>
                  <div className="font-mono text-slate-300 break-all">
                    {workflowSignoff.prompt_center_hash || "-"}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                  <div className="text-slate-400 mb-1">Kanıt dosyası</div>
                  <div className="font-mono text-slate-500 break-all">
                    {liveEvalGate?.report_path || workflowSignoff.report_path || "-"}
                  </div>
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      )}

      {(harnessLatestRun || harnessLatest) && (
        <SectionCard
          title="Eval Harness Geçmişi"
          subtitle={
            harnessLatestRun
              ? `Son koşum: ${fmtDateTime(harnessLatestRun.generated_at)} — ${pct(harnessLatestRun.case_pass_rate)} geçti`
              : `Son rapor: ${fmtDateTime(harnessLatest?.generated_at)}`
          }
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <StatCard
              label="Harness Durumu"
              value={harnessLatestRun?.overall_passed ?? true ? "PASS" : "FAIL"}
              color={harnessLatestRun?.overall_passed ?? true ? "text-emerald-400" : "text-red-400"}
            />
            <StatCard
              label="Case Pass"
              value={harnessLatestRun ? `${harnessLatestRun.passed_cases}/${harnessLatestRun.total_cases}` : "-"}
              color={rateColor((harnessLatestRun?.case_pass_rate ?? 0) * 100)}
            />
            <StatCard
              label="Suite"
              value={String(harnessLatestRun?.total_suites ?? harnessLatest?.suites?.length ?? 0)}
            />
            <StatCard
              label="Latency"
              value={`${harnessLatestRun?.total_latency_ms ?? harnessLatest?.suites?.reduce((sum, s) => sum + s.total_latency_ms, 0) ?? 0}ms`}
            />
          </div>

          {harnessTrend.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs uppercase text-slate-400 mb-2">Son Koşum Trendi</h4>
              <div className="flex items-end gap-1 h-16 border-b border-slate-800 pb-1">
                {harnessTrend.map((run, i) => {
                  const height = Math.max(8, Math.round((run.case_pass_rate || 0) * 56));
                  return (
                    <div
                      key={`${run.generated_at}-${i}`}
                      title={`${fmtDateTime(run.generated_at)} · ${pct(run.case_pass_rate)}`}
                      className={`w-8 rounded-t ${run.overall_passed ? "bg-emerald-500/70" : "bg-red-500/70"}`}
                      style={{ height }}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {harnessLatest?.suites && harnessLatest.suites.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="uppercase text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="text-left py-2 px-3">Suite</th>
                    <th className="text-right py-2 px-3">Durum</th>
                    <th className="text-right py-2 px-3">Case</th>
                    <th className="text-right py-2 px-3">Provider / Model</th>
                    <th className="text-right py-2 px-3">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {harnessLatest.suites.map((suite) => {
                    const firstCase = suite.cases?.[0];
                    const actual = firstCase?.actual ?? {};
                    const attempts = actual.attempts?.length ?? 0;
                    return (
                      <tr key={suite.suite_name} className="border-b border-slate-800/50">
                        <td className="py-2 px-3 font-mono text-slate-300">{suite.suite_name}</td>
                        <td className={`text-right py-2 px-3 ${suite.passed ? "text-emerald-400" : "text-red-400"}`}>
                          {suite.passed ? "PASS" : "FAIL"}
                        </td>
                        <td className="text-right py-2 px-3">
                          {suite.cases.filter((c) => c.passed).length}/{suite.cases.length}
                        </td>
                        <td className="text-right py-2 px-3 font-mono text-slate-400">
                          {actual.provider_used ?? "-"} / {actual.model_used ?? "-"} / {attempts} deneme
                        </td>
                        <td className="text-right py-2 px-3">{suite.total_latency_ms}ms</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      )}

      {(data.recommendations ?? []).length > 0 && (
        <SectionCard title="Oneriler">
          <ul className="text-sm text-slate-300 space-y-1 list-disc list-inside">
            {data.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </SectionCard>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 px-4 py-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`text-xl font-semibold mt-1 ${color ?? "text-slate-100"}`}>{value}</div>
    </div>
  );
}
