"use client";
import React from "react";

interface ProgressBarProps {
  passed?: number;
  failed?: number;
  skipped?: number;
  total?: number;
  value?: number;       // 0-100 basit kullanım için
  color?: "blue" | "emerald" | "red" | "amber" | "violet";
  showLabel?: boolean;
  height?: "sm" | "md" | "lg";
}

const heightMap = { sm: "h-1", md: "h-1.5", lg: "h-2.5" };

export function ProgressBar({
  passed, failed, skipped, total,
  value, color = "blue", showLabel = false, height = "md",
}: ProgressBarProps) {
  const h = heightMap[height];

  // Segmented mode
  if (total !== undefined && total > 0) {
    const p = passed ?? 0;
    const f = failed ?? 0;
    const s = skipped ?? 0;
    const pPct = (p / total) * 100;
    const fPct = (f / total) * 100;
    const sPct = (s / total) * 100;

    return (
      <div className="w-full">
        {showLabel && (
          <div className="flex items-center justify-between mb-1 text-xs text-slate-400">
            <span>{p} geçti</span>
            <span>{f} kaldı</span>
          </div>
        )}
        <div className={`w-full ${h} rounded-full bg-slate-800 overflow-hidden flex`}>
          {pPct > 0 && (
            <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${pPct}%` }} />
          )}
          {fPct > 0 && (
            <div className="h-full bg-red-500 transition-all duration-500" style={{ width: `${fPct}%` }} />
          )}
          {sPct > 0 && (
            <div className="h-full bg-slate-600 transition-all duration-500" style={{ width: `${sPct}%` }} />
          )}
        </div>
      </div>
    );
  }

  // Simple mode
  const pct = Math.min(100, Math.max(0, value ?? 0));
  const colorMap: Record<string, string> = {
    blue: "bg-blue-500",
    emerald: "bg-emerald-500",
    red: "bg-red-500",
    amber: "bg-amber-500",
    violet: "bg-violet-500",
  };

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex items-center justify-between mb-1 text-xs text-slate-400">
          <span>{pct.toFixed(0)}%</span>
        </div>
      )}
      <div className={`w-full ${h} rounded-full bg-slate-800 overflow-hidden`}>
        <div
          className={`h-full ${colorMap[color]} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
