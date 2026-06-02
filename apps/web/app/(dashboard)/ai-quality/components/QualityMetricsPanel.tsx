"use client";

/**
 * QualityMetricsPanel
 *
 * Displays the aggregated AI quality metrics: overview stat cards,
 * per-model performance/cost table, LLM-as-Judge scores, Smart Model
 * Router config and circuit state, and RAG ingestion statistics.
 *
 * All data is received via props from the parent AiQualityDashboardPage.
 */

import { SectionCard } from "@/components/nexus/SectionCard";

// ── Shared helpers (duplicated here to keep the component self-contained) ──

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

interface ModelRow {
  model: string;
  calls: number;
  success_rate: number;
  json_parse_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  total_cost_usd?: number;
  avg_cost_usd?: number;
}

interface JudgeData {
  total?: number;
  avg_overall?: number;
  avg_correctness?: number;
  avg_completeness?: number;
  avg_domain_fit?: number;
  avg_format_validity?: number;
  by_task?: Array<{ task_type: string; count: number; avg_overall: number }>;
}

interface RoutingData {
  routing_mode?: string;
  tiers?: Record<string, string>;
  provider_availability?: Record<string, boolean>;
  fallback_chain?: string;
  circuit_state?: Record<string, { failures: number; last_failure_ts: number }>;
}

interface IngestionData {
  total?: number;
  sources?: Array<{
    source: string;
    count: number;
    last_ingest: string | null;
    dedup_events: number;
  }>;
}

interface RegressionAlert {
  severity: string;
  metric: string;
  message: string;
}

interface OverviewData {
  total_calls?: number;
  success_rate?: number;
  json_parse_rate?: number;
  avg_latency_ms?: number;
  total_cost_usd?: number;
  avg_cost_usd?: number;
  cost_per_1k_calls_usd?: number;
}

export interface QualityMetricsPanelProps {
  days: number;
  overview: OverviewData;
  byModel: ModelRow[];
  regressionAlerts: RegressionAlert[];
  judge: JudgeData;
  routing: RoutingData;
  ingestion: IngestionData;
}

// ── Main component ─────────────────────────────────────────────────────────

export function QualityMetricsPanel({
  days,
  overview: ov,
  byModel,
  regressionAlerts: alerts,
  judge,
  routing,
  ingestion,
}: QualityMetricsPanelProps) {
  return (
    <div className="space-y-4">
      {/* Regression alerts */}
      {alerts.length > 0 && (
        <SectionCard
          title="Regresyon Uyarilari"
          subtitle="24 saat vs 7 gun hareketli ortalama"
        >
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div
                key={i}
                className={`px-3 py-2 rounded-lg border text-sm ${sevColor(a.severity)}`}
              >
                <span className="font-mono text-xs mr-2">[{a.severity}]</span>
                <span className="font-medium mr-2">{a.metric}:</span>
                <span>{a.message}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* Overview stat cards */}
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

      {/* Per-model table */}
      <SectionCard
        title="Model Performans + Maliyet"
        subtitle="Her model bazli başarı/latency/maliyet"
      >
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
              {byModel.map((m) => (
                <tr key={m.model} className="border-b border-slate-800/50">
                  <td className="py-2 px-3 font-mono text-xs text-slate-300">
                    {m.model}
                  </td>
                  <td className="text-right py-2 px-3">{m.calls}</td>
                  <td
                    className={`text-right py-2 px-3 ${rateColor(m.success_rate)}`}
                  >
                    %{m.success_rate.toFixed(1)}
                  </td>
                  <td
                    className={`text-right py-2 px-3 ${rateColor(m.json_parse_rate)}`}
                  >
                    %{m.json_parse_rate.toFixed(1)}
                  </td>
                  <td className="text-right py-2 px-3">{m.avg_latency_ms}ms</td>
                  <td className="text-right py-2 px-3">{m.p95_latency_ms}ms</td>
                  <td className="text-right py-2 px-3">
                    ${(m.total_cost_usd ?? 0).toFixed(4)}
                  </td>
                  <td className="text-right py-2 px-3">
                    ${(m.avg_cost_usd ?? 0).toFixed(6)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      {/* LLM-as-Judge scores */}
      {judge && judge.total !== undefined && judge.total > 0 && (
        <SectionCard
          title="LLM-as-Judge Skorlari"
          subtitle={`Son ${days} gun — ${judge.total} degerlendirme`}
        >
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard
              label="Genel"
              value={`${(judge.avg_overall ?? 0).toFixed(1)}/10`}
            />
            <StatCard
              label="Correctness"
              value={`${(judge.avg_correctness ?? 0).toFixed(1)}/10`}
            />
            <StatCard
              label="Completeness"
              value={`${(judge.avg_completeness ?? 0).toFixed(1)}/10`}
            />
            <StatCard
              label="Domain Fit"
              value={`${(judge.avg_domain_fit ?? 0).toFixed(1)}/10`}
            />
            <StatCard
              label="Format"
              value={`${(judge.avg_format_validity ?? 0).toFixed(1)}/10`}
            />
          </div>
          {judge.by_task && judge.by_task.length > 0 && (
            <div className="mt-3 text-xs text-slate-400">
              {judge.by_task.map((t) => (
                <span key={t.task_type} className="inline-block mr-3">
                  {t.task_type}: {t.count} × {t.avg_overall.toFixed(1)}
                </span>
              ))}
            </div>
          )}
        </SectionCard>
      )}

      {/* Smart Model Router */}
      <SectionCard
        title="Smart Model Router"
        subtitle={`Mod: ${routing.routing_mode}`}
      >
        <div className="text-sm grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-xs uppercase text-slate-400 mb-1">
              Tier&apos;lar
            </h4>
            <ul className="font-mono text-xs space-y-0.5">
              {Object.entries(routing.tiers ?? {}).map(([tier, model]) => (
                <li key={tier}>
                  <span className="text-slate-400">{tier}</span>:{" "}
                  <span className="text-slate-200">{model}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500 mt-2">
              {routing.fallback_chain}
            </p>
          </div>
          <div>
            <h4 className="text-xs uppercase text-slate-400 mb-1">Provider</h4>
            <ul className="text-xs space-y-0.5">
              {Object.entries(routing.provider_availability ?? {}).map(
                ([p, ok]) => (
                  <li key={p}>
                    <span className={ok ? "text-emerald-400" : "text-red-400"}>
                      ●
                    </span>{" "}
                    {p}
                  </li>
                )
              )}
            </ul>
            {Object.keys(routing.circuit_state ?? {}).length > 0 && (
              <div className="mt-2">
                <h4 className="text-xs uppercase text-slate-400 mb-1">
                  Circuit State
                </h4>
                <ul className="text-xs space-y-0.5 font-mono">
                  {Object.entries(routing.circuit_state ?? {}).map(([m, s]) => (
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

      {/* RAG ingestion stats */}
      <SectionCard
        title="RAG KnowledgeStore"
        subtitle={`Toplam ${ingestion.total ?? 0} kayit`}
      >
        <div className="text-xs space-y-1">
          {(ingestion.sources ?? []).map((s) => (
            <div
              key={s.source}
              className="flex items-center justify-between border-b border-slate-800/30 py-1"
            >
              <span className="font-mono text-slate-300">{s.source}</span>
              <span className="text-slate-400">
                {s.count} kayit · {s.dedup_events} dedup ·{" "}
                {s.last_ingest ?? "-"}
              </span>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
