"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

// ── Detail ────────────────────────────────────────────────────────────────────

interface DetailProps {
  label: string;
  value: string;
}

export function Detail({ label, value }: DetailProps) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-100">{value}</p>
    </div>
  );
}

// ── ActionButton ──────────────────────────────────────────────────────────────

type ActionTone = "green" | "amber" | "red";

const ACTION_TONE_CLASSES: Record<ActionTone, string> = {
  green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20",
  amber: "border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20",
  red: "border-red-500/40 bg-red-500/10 text-red-200 hover:bg-red-500/20",
};

interface ActionButtonProps {
  onClick: () => void;
  disabled: boolean;
  tone: ActionTone;
  icon: ReactNode;
  label: string;
  testId: string;
}

export function ActionButton({ onClick, disabled, tone, icon, label, testId }: ActionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-lg border px-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        ACTION_TONE_CLASSES[tone],
      )}
      data-testid={testId}
    >
      <span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  );
}
