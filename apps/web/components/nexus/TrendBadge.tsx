"use client";
import React from "react";

interface TrendBadgeProps {
  /** signed percentage, e.g. +12 or -3.4 */
  value: number;
  /** override label (e.g. absolute value instead of %) */
  label?: string;
  /** force direction; defaults to sign of value */
  direction?: "up" | "down" | "neutral";
  size?: "xs" | "sm";
}

const dirStyle = {
  up: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20", icon: "↑" },
  down: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20", icon: "↓" },
  neutral: { bg: "bg-slate-800", text: "text-slate-400", border: "border-slate-700", icon: "→" },
};

const padding = {
  xs: "px-1.5 py-0.5 text-[11px]",
  sm: "px-2 py-0.5 text-xs",
};

export function TrendBadge({ value, label, direction, size = "xs" }: TrendBadgeProps) {
  const dir: keyof typeof dirStyle = direction ?? (value > 0 ? "up" : value < 0 ? "down" : "neutral");
  const s = dirStyle[dir];
  const displayLabel = label ?? `${value > 0 ? "+" : ""}${Number.isInteger(value) ? value : value.toFixed(1)}%`;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border ${s.border} ${s.bg} ${s.text} ${padding[size]} font-semibold`}
    >
      <span aria-hidden>{s.icon}</span>
      {displayLabel}
    </span>
  );
}
