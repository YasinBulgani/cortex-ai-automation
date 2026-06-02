"use client";

/**
 * EvalHistoryList
 *
 * Displays the evaluation history section of the AI Quality Dashboard:
 *   - Eval Quality Gate (summary status, pass-rate delta, alerts, suite health table)
 *   - Live Eval + Release Signoff card
 *   - Eval Harness History card (trend bar chart + latest suite table)
 *   - Latest eval run row list
 *
 * All data is received via props from the parent AiQualityDashboardPage.
 */

import { SectionCard } from "@/components/nexus/SectionCard";

// ── Shared helpers ─────────────────────────────────────────────────────────

function rateColor(rate: number | undefined) {
  if (rate === undefined) return "text-slate-400";
  if (rate > 90) return "text-emerald-400";
  if (rate > 80) return "text-amber-400";
  return "text-red-400";
}

function sevColor(sev: string) {
  if (sev === "P0" || sev === "P1")
    return "bg-red-500/10 text-red-400 border-red-500/30";
  return "bg-amber-500/10 text-amber-400 border-amber-500/30";
}

function fmtDateTime(value?: string) {
  if (!value) return "-";
  return new Date(value).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "medium",
  });
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
  if (value === "needs_external_soak_and_dr_signoff")
    return "External Soak / DR Bekliyor";
  if (value === "needs_remaining_release_gates")
    return "Kalan Release Gate'leri Var";
  if (value === "fail") return "Release Fail";
  return "Bilinmiyor";
}

function liveEvalColor(status?: string | null, required?: boolean) {
  if (status === "pass" || status === "passed") return "text-emerald-400";
  if (status === "warn") return "text-amber-400";
  if (status === "fail" || status === "failed") return "text-red-400";
  if (status === "skipped")
    return required ? "text-red-400" : "text-amber-400";
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

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-xl bg-slate-900/60 border border-slate-800 px-4 py-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className={`text-xl font-semibold mt-1 ${color ?? "text-slate-100"}`}>
        {value}
      </div>
    </div>
  );
}

// ── Prop types ─────────────────────────────────────────────────────────────

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

interface WorkflowSignoff {
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
}

interface EvalLatest {
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
}

export interface EvalHistoryListProps {
  evalLatest: EvalLatest;
  harnessHistory: EvalHarnessRun[];
  harnessLatest: EvalHarnessLatest | null;
  harnessSummary: EvalHarnessSummary | null;
  workflowSignoff: WorkflowSignoff | null;
  recommendations: string[];
}

// ── Main component ─────────────────────────────────────────────────────────

export function EvalHistoryList({
  evalLatest,
  harnessHistory,
  harnessLatest,
  harnessSummary,
  workflowSignoff,
  recommendations,
}: EvalHistoryListProps) {
  const harnessLatestRun = harnessHistory[harnessHistory.length - 1] ?? null;
  const harnessTrend = harnessHistory.slice(-8);
  const liveEvalGate = workflowSignoff?.live_eval_gate ?? null;

  return (
    <div className="space-y-4">
      {/* Latest eval run */}
      {evalLatest?.total !== undefined && evalLatest.total > 0 && (
        <SectionCard
          title="Son Eval Run"
          subtitle={`${evalLatest.suite} — %${(evalLatest.pass_rate ?? 0).toFixed(1)} gecti (${evalLatest.pass_count}/${evalLatest.total})`}
        >
          <div className="text-xs font-mono space-y-1">
            {(evalLatest.results ?? []).slice(0, 20).map((r, i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-slate-800/30 py-1"
              >
                <span>
                  <span
                    className={r.pass_all ? "text-emerald-400" : "text-red-400"}
                  >
                    ●
                  </span>{" "}
                  {r.prompt_id}{" "}
                  <span className="text-slate-500">[{r.task_type}]</span>
                </span>
                <span className="text-slate-400">
                  {r.model} · {r.tier} · {r.latency_ms}ms
                  {r.judge_overall !== null
                    ? ` · judge ${r.judge_overall.toFixed(1)}/10`
                    : ""}
                </span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Eval Quality Gate */}
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
                color={
                  (harnessSummary.pass_rate_delta ?? 0) < 0
                    ? "text-red-400"
                    : "text-emerald-400"
                }
              />
              <StatCard
                label="Latency Delta"
                value={signedPct(harnessSummary.latency_delta_pct)}
                color={
                  (harnessSummary.latency_delta_pct ?? 0) > 0.25
                    ? "text-amber-400"
                    : "text-slate-100"
                }
              />
            </div>

            {harnessSummary.alerts.length > 0 && (
              <div className="mb-4 space-y-2">
                {harnessSummary.alerts.map((alert, i) => (
                  <div
                    key={`${alert.metric}-${i}`}
                    className={`px-3 py-2 rounded-lg border text-xs ${sevColor(alert.severity)}`}
                  >
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
                      <tr
                        key={suite.name}
                        className="border-b border-slate-800/50"
                      >
                        <td className="py-2 px-3">
                          <div className="font-mono text-slate-300">
                            {suite.name}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {suite.adapter}
                          </div>
                        </td>
                        <td
                          className={`text-right py-2 px-3 ${gateColor(suite.status)}`}
                        >
                          {gateLabel(suite.status)}
                        </td>
                        <td className="text-right py-2 px-3">
                          {pct(suite.pass_rate)}
                        </td>
                        <td className="text-right py-2 px-3">
                          {pct(suite.avg_case_pass_rate)}
                        </td>
                        <td className="text-right py-2 px-3">
                          {suite.latest_latency_ms}ms
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {harnessSummary.runtime_matrix.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                {harnessSummary.runtime_matrix.map((row) => (
                  <span
                    key={`${row.provider}-${row.model}`}
                    className="rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1 text-slate-300"
                  >
                    <span className="font-mono">{row.provider}</span> /{" "}
                    {row.model} · {row.cases} case · {row.attempts} deneme
                  </span>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      )}

      {/* Live Eval + Release Signoff */}
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
                color={liveEvalColor(
                  liveEvalGate?.status,
                  liveEvalGate?.required
                )}
              />
              <StatCard
                label="Release"
                value={releaseDecisionLabel(workflowSignoff.release_decision)}
                color={
                  workflowSignoff.release_decision ===
                  "ready_for_operator_approval"
                    ? "text-emerald-400"
                    : "text-amber-400"
                }
              />
              <StatCard
                label="LLM Skoru"
                value={
                  workflowSignoff.llm_quality_score !== null &&
                  workflowSignoff.llm_quality_score !== undefined
                    ? workflowSignoff.llm_quality_score.toFixed(2)
                    : "-"
                }
              />
              <StatCard
                label="Gate Türü"
                value={liveEvalGate?.required ? "Blocking" : "Advisory"}
                color={
                  liveEvalGate?.required ? "text-red-400" : "text-slate-100"
                }
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-2">
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                  <div className="text-slate-400 mb-1">Live eval durumu</div>
                  <div
                    className={`${liveEvalColor(liveEvalGate?.status, liveEvalGate?.required)} font-medium`}
                  >
                    {liveEvalGate?.message ||
                      "Canlı live eval sonucu son signoff raporunda bulunamadı."}
                  </div>
                  {liveEvalGate?.report_generated_at && (
                    <div className="mt-2 text-slate-500">
                      Kaynak rapor:{" "}
                      {fmtDateTime(liveEvalGate.report_generated_at)}
                    </div>
                  )}
                </div>
                {workflowSignoff.failed_required_checks &&
                  workflowSignoff.failed_required_checks.length > 0 && (
                    <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-red-300">
                      Zorunlu gate sorunları:{" "}
                      {workflowSignoff.failed_required_checks.join(", ")}
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
                    {liveEvalGate?.report_path ||
                      workflowSignoff.report_path ||
                      "-"}
                  </div>
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      )}

      {/* Eval Harness History */}
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
              color={
                harnessLatestRun?.overall_passed ?? true
                  ? "text-emerald-400"
                  : "text-red-400"
              }
            />
            <StatCard
              label="Case Pass"
              value={
                harnessLatestRun
                  ? `${harnessLatestRun.passed_cases}/${harnessLatestRun.total_cases}`
                  : "-"
              }
              color={rateColor((harnessLatestRun?.case_pass_rate ?? 0) * 100)}
            />
            <StatCard
              label="Suite"
              value={String(
                harnessLatestRun?.total_suites ??
                  harnessLatest?.suites?.length ??
                  0
              )}
            />
            <StatCard
              label="Latency"
              value={`${harnessLatestRun?.total_latency_ms ?? harnessLatest?.suites?.reduce((sum, s) => sum + s.total_latency_ms, 0) ?? 0}ms`}
            />
          </div>

          {harnessTrend.length > 0 && (
            <div className="mb-4">
              <h4 className="text-xs uppercase text-slate-400 mb-2">
                Son Koşum Trendi
              </h4>
              <div className="flex items-end gap-1 h-16 border-b border-slate-800 pb-1">
                {harnessTrend.map((run, i) => {
                  const height = Math.max(
                    8,
                    Math.round((run.case_pass_rate || 0) * 56)
                  );
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
                      <tr
                        key={suite.suite_name}
                        className="border-b border-slate-800/50"
                      >
                        <td className="py-2 px-3 font-mono text-slate-300">
                          {suite.suite_name}
                        </td>
                        <td
                          className={`text-right py-2 px-3 ${suite.passed ? "text-emerald-400" : "text-red-400"}`}
                        >
                          {suite.passed ? "PASS" : "FAIL"}
                        </td>
                        <td className="text-right py-2 px-3">
                          {suite.cases.filter((c) => c.passed).length}/
                          {suite.cases.length}
                        </td>
                        <td className="text-right py-2 px-3 font-mono text-slate-400">
                          {actual.provider_used ?? "-"} /{" "}
                          {actual.model_used ?? "-"} / {attempts} deneme
                        </td>
                        <td className="text-right py-2 px-3">
                          {suite.total_latency_ms}ms
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      )}

      {/* Recommendations */}
      {(recommendations ?? []).length > 0 && (
        <SectionCard title="Oneriler">
          <ul className="text-sm text-slate-300 space-y-1 list-disc list-inside">
            {recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </SectionCard>
      )}
    </div>
  );
}
