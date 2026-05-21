"use client";
import React from "react";

interface StatCardProps {
  icon?: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color?: "blue" | "emerald" | "red" | "amber" | "violet" | "slate";
  trend?: "up" | "down" | "neutral";
}

const colorMap = {
  blue:    { bg: "bg-blue-500/10",    text: "text-blue-400",    border: "border-blue-500/20" },
  emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  red:     { bg: "bg-red-500/10",     text: "text-red-400",     border: "border-red-500/20" },
  amber:   { bg: "bg-amber-500/10",   text: "text-amber-400",   border: "border-amber-500/20" },
  violet:  { bg: "bg-violet-500/10",  text: "text-violet-400",  border: "border-violet-500/20" },
  slate:   { bg: "bg-slate-800",      text: "text-slate-400",   border: "border-slate-700" },
};

const trendIcon = { up: "↑", down: "↓", neutral: "→" };
const trendColor = { up: "text-emerald-400", down: "text-red-400", neutral: "text-slate-400" };

export function StatCard({ icon, label, value, sub, color = "slate", trend }: StatCardProps) {
  const c = colorMap[color];
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4 flex items-start gap-3 hover:border-slate-600 transition-colors">
      {icon && (
        <div className={`p-2 rounded-lg ${c.bg} border ${c.border} ${c.text} mt-0.5 shrink-0`}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-slate-400 font-medium truncate">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
        {(sub || trend) && (
          <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
            {trend && <span className={trendIcon[trend] ? trendColor[trend] : ""}>{trendIcon[trend]}</span>}
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}
