"use client";

import { useState } from "react";
import { useRouteParam } from "@/lib/use-route-param";
import { PageHeader } from "@/components/nexus/PageHeader";
import { SectionCard } from "@/components/nexus/SectionCard";
import {
  useQualityMetrics,
  useLlmTraceStats,
} from "@/lib/hooks/use-ai-metrics";

function rateColor(rate: number) {
  if (rate > 90) return "text-emerald-400";
  if (rate > 80) return "text-amber-400";
  return "text-red-400";
}

export default function AiMetricsPage() {
  const projectId = useRouteParam("projectId");
  const [days, setDays] = useState(30);

  const { data: metrics, isLoading } = useQualityMetrics(projectId, days);
  const { data: traceStats } = useLlmTraceStats(projectId);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 p-6" data-testid="ai-metrics-loading">
        <PageHeader
          icon={<span className="text-lg">🤖</span>}
          title="LLM Kalite Metrikleri"
          description="Yukleniyor..."
        />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-800 border border-slate-700" />
          ))}
        </div>
      </div>
    );
  }

  const overview = metrics?.overview ?? {
    total_calls: 0,
    success_rate: 0,
    json_parse_rate: 0,
    avg_latency_ms: 0,
  };
  const agents = metrics?.by_agent ?? [];
  const recommendations = metrics?.recommendations ?? [];

  if (overview.total_calls === 0) {
    return (
      <div className="min-h-screen bg-slate-950 p-6" data-testid="ai-metrics-empty">
        <PageHeader
          icon={<span className="text-lg">🤖</span>}
          title="LLM Kalite Metrikleri"
          description="AI agent performans analizi ve optimizasyon onerileri"
        />
        <div className="flex flex-col items-center justify-center py-32 text-slate-500">
          <span className="text-5xl mb-4">📭</span>
          <p className="text-lg font-medium">Henuz veri yok</p>
          <p className="text-sm mt-1">AI agentler calistiginda metrikler burada gorunecek</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 space-y-4" data-testid="ai-metrics-page">
      <PageHeader
        icon={<span className="text-lg">🤖</span>}
        title="LLM Kalite Metrikleri"
        description="AI agent performans analizi ve optimizasyon onerileri"
        right={
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            aria-label="Zaman araligi sec"
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:border-slate-500 transition-colors"
          >
            {[7, 14, 30, 60, 90].map((d) => (
              <option key={d} value={d}>{d} gun</option>
            ))}
          </select>
        }
      />

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatTile icon="📊" label="Toplam LLM Cagri" value={overview.total_calls.toLocaleString()} />
        <StatTile
          icon="✅"
          label="Basari Orani"
          value={`${overview.success_rate.toFixed(1)}%`}
          className={rateColor(overview.success_rate)}
        />
        <StatTile icon="🧩" label="JSON Parse Orani" value={`${overview.json_parse_rate.toFixed(1)}%`} />
        <StatTile icon="⏱️" label="Ort. Gecikme" value={`${Math.round(overview.avg_latency_ms)} ms`} />
      </div>

      {/* Trace Stats */}
      {traceStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <StatTile icon="📝" label="Toplam Trace" value={String(traceStats.total_traces ?? 0)} />
          <StatTile icon="💰" label="Toplam Token" value={(traceStats.total_tokens ?? 0).toLocaleString()} />
          <StatTile icon="⏱️" label="Ort. Trace Süresi" value={`${Math.round(traceStats.avg_latency_ms ?? 0)} ms`} />
        </div>
      )}

      {/* Agent Performance */}
      {agents.length > 0 && (
        <SectionCard title="Agent Performansi" icon={<span>🤖</span>} noPad>
          <table className="table-auto w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                {["Agent", "Cagri", "Basari %", "Ort. Gecikme"].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-xs font-medium text-slate-400 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...agents].sort((a, b) => b.calls - a.calls).map((a) => (
                <tr key={a.agent} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/50">
                  <td className="px-4 py-3 font-medium text-white">{a.agent}</td>
                  <td className="px-4 py-3 text-slate-300">{a.calls.toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`font-semibold ${rateColor(a.success_rate)}`}>{a.success_rate.toFixed(1)}%</span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{Math.round(a.avg_latency_ms)} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </SectionCard>
      )}

      {/* AI Recommendations */}
      {recommendations.length > 0 && (
        <SectionCard title="AI Onerileri" icon={<span>💡</span>}>
          <ul className="space-y-2">
            {recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="shrink-0 mt-0.5">{r.includes("normal") ? "✅" : "⚠️"}</span>
                <span className="text-slate-300">{r}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      )}
    </div>
  );
}

function StatTile({
  icon,
  label,
  value,
  className = "",
}: {
  icon: string;
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-slate-700 bg-slate-900/40 p-4 ${className}`}>
      <div className="flex items-center gap-2 mb-1">
        <span>{icon}</span>
        <span className="text-xs text-slate-400">{label}</span>
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}
