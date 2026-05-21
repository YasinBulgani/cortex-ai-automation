"use client";

import { StatCard } from "@neurex/design-system";
import type { ProductLiveStat } from "@/lib/products/telemetry-types";

interface LiveStatsBarProps {
  stats: ProductLiveStat[];
  loading?: boolean;
  brandText?: string;
}

type StatTone = "default" | "success" | "warning" | "danger" | "brand" | "info" | "ai";

function toTone(s: ProductLiveStat): StatTone {
  if (s.severity === "critical") return "danger";
  if (s.severity === "warn")     return "warning";
  if (s.trend === "up")          return "success";
  return "default";
}

function toTrend(s: ProductLiveStat): number | undefined {
  if (s.delta === undefined || s.delta === 0) return undefined;
  return s.trend === "down" ? -Math.abs(s.delta) : Math.abs(s.delta);
}

export function LiveStatsBar({ stats, loading }: LiveStatsBarProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-28 rounded-2xl border border-slate-800 bg-slate-900/60 animate-pulse" />
        ))}
      </div>
    );
  }

  if (!stats.length) return null;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {stats.slice(0, 6).map((stat) => (
        <StatCard
          key={stat.key}
          label={stat.label}
          value={stat.unit ? `${stat.value}${stat.unit}` : stat.value}
          tone={toTone(stat)}
          sparkline={stat.sparkline}
          trend={toTrend(stat)}
          hint={stat.deltaLabel}
        />
      ))}
    </div>
  );
}
