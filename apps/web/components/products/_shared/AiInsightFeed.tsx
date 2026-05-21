"use client";

import { useState } from "react";
import type { AiInsight } from "@/lib/products/telemetry-types";

interface AiInsightFeedProps {
  insights: AiInsight[];
  brandBorder: string;
  brandText: string;
  loading?: boolean;
}

const SEVERITY = {
  critical: { dot: "bg-rose-500", bg: "bg-rose-500/10 border-rose-500/25", badge: "text-rose-300", label: "Kritik" },
  warning:  { dot: "bg-amber-400", bg: "bg-amber-500/10 border-amber-500/25", badge: "text-amber-300", label: "Uyarı" },
  info:     { dot: "bg-sky-400",   bg: "bg-sky-500/10 border-sky-500/25",   badge: "text-sky-300",  label: "Bilgi" },
  success:  { dot: "bg-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/25", badge: "text-emerald-300", label: "Başarı" },
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins} dk önce`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} sa önce`;
  return `${Math.floor(hrs / 24)} gün önce`;
}

export function AiInsightFeed({ insights, brandText, loading }: AiInsightFeedProps) {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-slate-900/60 animate-pulse" />
        ))}
      </div>
    );
  }

  const visible = insights.filter((i) => !dismissed.has(i.id));

  if (visible.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
        <span className="text-3xl mb-2">✓</span>
        <p className="text-sm">Tüm öngörüler gözden geçirildi</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-80 overflow-y-auto pr-1 scrollbar-thin">
      {visible.map((insight) => {
        const s = SEVERITY[insight.severity];
        return (
          <div key={insight.id} className={`rounded-xl border p-4 ${s.bg} transition-all`}>
            <div className="flex items-start gap-3">
              <span className={`mt-1 flex-shrink-0 w-2 h-2 rounded-full ${s.dot}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={`text-xs font-semibold uppercase tracking-wide ${s.badge}`}>{s.label}</span>
                  <span className="text-xs text-slate-400">{insight.category}</span>
                  {insight.confidence !== undefined && (
                    <span className="text-xs text-slate-400 ml-auto">%{insight.confidence} güven</span>
                  )}
                </div>
                <p className="text-sm font-medium text-white mb-1">{insight.title}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{insight.description}</p>
                <div className="flex items-center gap-3 mt-2">
                  {insight.ctaLabel && (
                    <button className={`text-xs font-medium ${brandText} hover:underline`}>
                      {insight.ctaLabel} →
                    </button>
                  )}
                  <span className="text-xs text-white-subtle">{timeAgo(insight.createdAt)}</span>
                  <button
                    className="ml-auto text-xs text-slate-400 hover:text-white-subtle"
                    onClick={() => setDismissed((prev) => new Set(prev).add(insight.id))}
                  >
                    Kapat
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
