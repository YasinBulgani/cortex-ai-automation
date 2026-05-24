"use client";

import { cn } from "@/lib/utils";
import { SectionCard } from "@/components/nexus/SectionCard";

// ── Tab config ───────────────────────────────────────────────────────────────

export const TAB_KEYS = ["session", "selectors", "dom", "heal"] as const;
export type TabKey = (typeof TAB_KEYS)[number];

export const TAB_LABELS: Record<TabKey, string> = {
  session:   "Oturum & Navigasyon",
  selectors: "Selector Dogrulama",
  dom:       "DOM Keşfet",
  heal:      "Heal Dogrulama",
};

// ── Color helpers ────────────────────────────────────────────────────────────

export function stabilityColor(score: number): string {
  if (score >= 5) return "bg-emerald-500/15 border-emerald-500/30 text-emerald-400";
  if (score >= 4) return "bg-blue-500/15 border-blue-500/30 text-blue-400";
  if (score >= 3) return "bg-amber-500/15 border-amber-500/30 text-amber-400";
  if (score >= 2) return "bg-orange-500/15 border-orange-500/30 text-orange-400";
  return "bg-red-500/15 border-red-500/30 text-red-400";
}

export function confidenceColor(c: number): string {
  if (c >= 0.8) return "text-emerald-400";
  if (c >= 0.5) return "text-amber-400";
  return "text-red-400";
}

// ── Shared UI micro-components ───────────────────────────────────────────────

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <div
      className={cn(
        "h-4 w-4 animate-spin rounded-full border-2 border-slate-700 border-t-emerald-400",
        className,
      )}
    />
  );
}

export function RetryButton({
  onClick,
  label = "Tekrar Dene",
}: {
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 transition-colors"
    >
      {label}
    </button>
  );
}

// ── Playwright unavailable banner ────────────────────────────────────────────

export function PlaywrightUnavailable() {
  return (
    <SectionCard
      title="Playwright Bulunamadi"
      icon={
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-slate-300">
          Playwright MCP servisi su anda kullanilamiyor. Backend sunucusunda Playwright kurulu
          oldugundan emin olun.
        </p>
        <div className="rounded-lg border border-slate-700 bg-slate-950 p-3">
          <p className="mb-1 text-xs font-semibold text-slate-400">Kurulum:</p>
          <code className="block text-xs text-emerald-400 font-mono">
            pip install playwright && playwright install chromium
          </code>
        </div>
        <p className="text-xs text-slate-500">
          Kurulumdan sonra backend servisini yeniden başlatmaniz gerekebilir.
        </p>
      </div>
    </SectionCard>
  );
}
