"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone = "blue" | "amber" | "cyan" | "red" | "emerald" | "violet" | "slate";

const TONE_CLASSES: Record<Tone, string> = {
  blue: "border-blue-500/30 text-blue-200 bg-blue-500/10",
  amber: "border-amber-500/30 text-amber-200 bg-amber-500/10",
  cyan: "border-cyan-500/30 text-cyan-200 bg-cyan-500/10",
  red: "border-red-500/30 text-red-200 bg-red-500/10",
  emerald: "border-emerald-500/30 text-emerald-200 bg-emerald-500/10",
  violet: "border-violet-500/30 text-violet-200 bg-violet-500/10",
  slate: "border-slate-700 text-slate-200 bg-slate-900",
};

interface WorkflowMetricCardProps {
  icon: ReactNode;
  label: string;
  value: string;
  tone: Tone;
  testId?: string;
}

export function WorkflowMetricCard({ icon, label, value, tone, testId }: WorkflowMetricCardProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4" data-testid={testId}>
      <div className="flex items-center justify-between gap-3">
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg border", TONE_CLASSES[tone])}>
          <span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span>
        </div>
        <span className="text-right text-2xl font-semibold text-white">{value}</span>
      </div>
      <p className="mt-3 text-xs font-medium uppercase tracking-normal text-slate-500">{label}</p>
    </div>
  );
}
