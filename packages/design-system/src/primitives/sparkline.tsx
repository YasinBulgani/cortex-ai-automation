"use client";

import { cn } from "../utils/cn";

type SparklineVariant = "line" | "area" | "bar";

export interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  variant?: SparklineVariant;
  /** Tailwind text-* class (uses currentColor) */
  className?: string;
  showLast?: boolean;
  smooth?: boolean;
  ariaLabel?: string;
}

/**
 * Sparkline — küçük, bağlamsal trend grafiği.
 *
 * Kullanım:
 *   <Sparkline data={[3, 5, 4, 6, 7, 6, 8]} className="text-emerald-400 h-6 w-20" />
 *
 * Stil:
 *   - Renk currentColor → parent text-* class'ından alınır
 *   - variant: line / area (filled) / bar
 *   - showLast: son noktada nokta gösterir
 */
export function Sparkline({
  data,
  width = 80,
  height = 24,
  variant = "line",
  className,
  showLast = true,
  smooth = true,
  ariaLabel,
}: SparklineProps) {
  if (data.length < 2) {
    return (
      <div
        className={cn("inline-flex items-center justify-center text-fg-disabled", className)}
        style={{ width, height }}
        aria-label={ariaLabel ?? "Yetersiz veri"}
      >
        —
      </div>
    );
  }

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);

  // Y koordinatları (SVG'de yukarı = düşük y)
  const points = data.map((v, i) => ({
    x: i * stepX,
    y: height - 2 - ((v - min) / range) * (height - 4),
  }));

  // Smooth path with quadratic bezier
  const linePath = smooth
    ? points.reduce((acc, p, i) => {
        if (i === 0) return `M ${p.x},${p.y}`;
        const prev = points[i - 1];
        const cx = (prev.x + p.x) / 2;
        return `${acc} Q ${cx},${prev.y} ${cx},${(prev.y + p.y) / 2} T ${p.x},${p.y}`;
      }, "")
    : points.reduce((acc, p, i) => acc + (i === 0 ? `M ${p.x},${p.y}` : ` L ${p.x},${p.y}`), "");

  const areaPath = `${linePath} L ${width},${height} L 0,${height} Z`;
  const last = points[points.length - 1];

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn("inline-block", className)}
      role="img"
      aria-label={ariaLabel ?? `Trend: son değer ${data[data.length - 1]}`}
    >
      {variant === "area" && (
        <path d={areaPath} fill="currentColor" fillOpacity="0.12" />
      )}
      {variant === "bar" ? (
        points.map((p, i) => {
          const barWidth = Math.max(1, stepX * 0.6);
          const barH = height - p.y;
          return (
            <rect
              key={i}
              x={p.x - barWidth / 2}
              y={p.y}
              width={barWidth}
              height={barH}
              fill="currentColor"
              rx={0.5}
              fillOpacity={i === points.length - 1 ? 1 : 0.5}
            />
          );
        })
      ) : (
        <path d={linePath} stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinejoin="round" strokeLinecap="round" />
      )}
      {showLast && variant !== "bar" && (
        <circle cx={last.x} cy={last.y} r="2" fill="currentColor" />
      )}
    </svg>
  );
}
