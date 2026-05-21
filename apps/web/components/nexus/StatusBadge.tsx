"use client";
import React from "react";

type StatusVariant =
  | "draft" | "active" | "archived" | "pending"
  | "running" | "completed" | "error" | "passed"
  | "failed" | "skipped" | "scheduled" | "paused"
  | "connected" | "disconnected" | "warning";

interface StatusBadgeProps {
  status: StatusVariant | string;
  label?: string;
  dot?: boolean;
  size?: "xs" | "sm";
}

const statusConfig: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  draft:        { bg: "bg-slate-800",      text: "text-slate-300",  dot: "bg-slate-400",   label: "Taslak" },
  active:       { bg: "bg-emerald-500/10", text: "text-emerald-400",dot: "bg-emerald-400", label: "Aktif" },
  archived:     { bg: "bg-red-500/10",     text: "text-red-400",    dot: "bg-red-400",     label: "Arşiv" },
  pending:      { bg: "bg-amber-500/10",   text: "text-amber-400",  dot: "bg-amber-400",   label: "Bekliyor" },
  running:      { bg: "bg-blue-500/10",    text: "text-blue-400",   dot: "bg-blue-400",    label: "Koşuyor" },
  completed:    { bg: "bg-emerald-500/10", text: "text-emerald-400",dot: "bg-emerald-400", label: "Tamamlandı" },
  error:        { bg: "bg-red-500/10",     text: "text-red-400",    dot: "bg-red-400",     label: "Hata" },
  passed:       { bg: "bg-emerald-500/10", text: "text-emerald-400",dot: "bg-emerald-400", label: "Geçti" },
  failed:       { bg: "bg-red-500/10",     text: "text-red-400",    dot: "bg-red-400",     label: "Başarısız" },
  skipped:      { bg: "bg-slate-800",      text: "text-slate-400",  dot: "bg-slate-500",   label: "Atlandı" },
  scheduled:    { bg: "bg-violet-500/10",  text: "text-violet-400", dot: "bg-violet-400",  label: "Zamanlandı" },
  paused:       { bg: "bg-amber-500/10",   text: "text-amber-400",  dot: "bg-amber-400",   label: "Duraklatıldı" },
  connected:    { bg: "bg-emerald-500/10", text: "text-emerald-400",dot: "bg-emerald-400", label: "Bağlı" },
  disconnected: { bg: "bg-slate-800",      text: "text-slate-400",  dot: "bg-slate-500",   label: "Bağlı Değil" },
  warning:      { bg: "bg-amber-500/10",   text: "text-amber-400",  dot: "bg-amber-400",   label: "Uyarı" },
};

export function StatusBadge({ status, label, dot = true, size = "xs" }: StatusBadgeProps) {
  const cfg = statusConfig[status] ?? {
    bg: "bg-slate-800", text: "text-slate-300", dot: "bg-slate-400", label: status,
  };
  const displayLabel = label ?? cfg.label;
  const padding = size === "xs" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border border-transparent ${cfg.bg} ${cfg.text} ${padding} font-medium`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} shrink-0`} />}
      {displayLabel}
    </span>
  );
}
