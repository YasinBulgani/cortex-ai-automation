"use client";

import { cn } from "@/lib/utils";
import { Sparkline } from "./sparkline";

export interface StatCardProps {
  label: string;
  value: string | number;
  /** Yardımcı alt yazı (örn: "son 7 gün") */
  hint?: string;
  /** Trend: yüzde değişim (-15 → kırmızı, +12 → yeşil) */
  trend?: number;
  /** Sparkline verisi — son N gün */
  sparkline?: number[];
  /** Sayı vurgu rengi */
  tone?: "default" | "success" | "warning" | "danger" | "brand" | "info" | "ai";
  /** İkon (sol üst) */
  icon?: React.ReactNode;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
}

const TONE_CLASSES = {
  default: "text-fg",
  success: "text-success",
  warning: "text-warning",
  danger:  "text-danger",
  brand:   "text-brand-primary",
  info:    "text-info",
  ai:      "text-ai",
};

const TONE_BG_CLASSES = {
  default: "bg-surface-overlay text-fg-muted",
  success: "bg-success-subtle text-success",
  warning: "bg-warning-subtle text-warning",
  danger:  "bg-danger-subtle text-danger",
  brand:   "bg-brand-soft text-brand-primary",
  info:    "bg-info-subtle text-info",
  ai:      "bg-ai-subtle text-ai",
};

/**
 * StatCard — KPI gösterimi için ana primitive.
 *
 * Örnek:
 *   <StatCard label="Geçme Oranı" value="%94" trend={+2} sparkline={[80,82,85,90,92,93,94]} tone="success" />
 */
export function StatCard({
  label,
  value,
  hint,
  trend,
  sparkline,
  tone = "default",
  icon,
  loading,
  onClick,
  className,
}: StatCardProps) {
  const trendIsUp = trend !== undefined && trend > 0;
  const trendIsDown = trend !== undefined && trend < 0;

  const trendColor = trend === undefined
    ? "text-fg-subtle"
    : trendIsUp ? "text-success" : trendIsDown ? "text-danger" : "text-fg-muted";

  const Component = onClick ? "button" : "div";

  return (
    <Component
      onClick={onClick}
      className={cn(
        "group relative rounded-xl border border-border bg-surface-raised p-4 text-left transition-all duration-fast",
        onClick && "hover:border-border-strong hover:shadow-elevated cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary",
        className,
      )}
    >
      {/* Label & icon row */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-fg-muted">{label}</p>
        {icon && (
          <span className={cn("flex h-6 w-6 items-center justify-center rounded-md", TONE_BG_CLASSES[tone])}>
            {icon}
          </span>
        )}
      </div>

      {/* Value & sparkline */}
      <div className="mt-2 flex items-end justify-between gap-3">
        <div className="min-w-0">
          {loading ? (
            <div className="h-8 w-24 rounded bg-surface-overlay animate-pulse" />
          ) : (
            <p className={cn("text-2xl font-bold tabular-nums tracking-tight", TONE_CLASSES[tone])}>
              {value}
            </p>
          )}
          {(hint || trend !== undefined) && (
            <div className="mt-0.5 flex items-center gap-1.5 text-xs">
              {trend !== undefined && (
                <span className={cn("inline-flex items-center gap-0.5 font-semibold tabular-nums", trendColor)}>
                  {trendIsUp ? "▲" : trendIsDown ? "▼" : "—"}
                  {Math.abs(trend)}%
                </span>
              )}
              {hint && <span className="text-fg-subtle">{hint}</span>}
            </div>
          )}
        </div>
        {sparkline && sparkline.length > 1 && (
          <Sparkline
            data={sparkline}
            variant="area"
            width={60}
            height={28}
            className={cn("shrink-0", TONE_CLASSES[tone])}
          />
        )}
      </div>
    </Component>
  );
}
