"use client";

import Link from "next/link";
import type { OnboardingStep } from "@/lib/products/telemetry-types";

interface OnboardingChecklistProps {
  steps: OnboardingStep[];
  brandGradient: string;
  brandText: string;
  loading?: boolean;
}

export function OnboardingChecklist({ steps, brandGradient, brandText, loading }: OnboardingChecklistProps) {
  if (loading) {
    return <div className="h-32 rounded-xl bg-slate-900/60 animate-pulse" />;
  }

  const done = steps.filter((s) => s.done).length;
  const pct = steps.length > 0 ? Math.round((done / steps.length) * 100) : 0;

  return (
    <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white">Başlangıç Kılavuzu</h3>
          <p className="text-xs text-slate-400">{done}/{steps.length} tamamlandı</p>
        </div>
        <div className="text-2xl font-bold tabular-nums text-white">%{pct}</div>
      </div>

      <div className="mb-5 h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-full rounded-full bg-gradient-to-r ${brandGradient} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="space-y-3">
        {steps.map((step) => (
          <div key={step.id} className={`flex items-start gap-3 p-3 rounded-xl transition-colors ${step.done ? "opacity-60" : "hover:bg-slate-900/60"}`}>
            <div className={`flex-shrink-0 mt-0.5 w-5 h-5 rounded-full flex items-center justify-center border-2 transition-colors ${step.done ? `border-transparent bg-gradient-to-br ${brandGradient}` : "border-white/20"}`}>
              {step.done && (
                <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${step.done ? "line-through text-slate-400" : "text-white"}`}>{step.title}</p>
              <p className="text-xs text-slate-400 mt-0.5">{step.description}</p>
            </div>
            {!step.done && step.href && (
              <Link href={step.href} className={`flex-shrink-0 text-xs font-medium ${brandText} hover:underline`}>
                {step.ctaLabel} →
              </Link>
            )}
            {!step.done && !step.href && (
              <span className={`flex-shrink-0 text-xs font-medium ${brandText}`}>{step.ctaLabel}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
