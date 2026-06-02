"use client";

import { STEPS } from "../constants";

// ── Types ─────────────────────────────────────────────────────────────────────

type StepItem = (typeof STEPS)[number];

export interface StepIndicatorProps {
  /** Currently active step (1-based, matches STEPS[].id) */
  currentStep: number;
  /** Called when the user clicks a completed step to navigate back */
  onStepClick: (stepId: number) => void;
}

// ── StepIndicator — Desktop sidebar (md+) ────────────────────────────────────

export function StepIndicator({ currentStep, onStepClick }: StepIndicatorProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
        Kurulum Adımları
      </p>
      <ol className="mt-3 space-y-1">
        {STEPS.map((s: StepItem) => {
          const isActive = currentStep === s.id;
          const isDone = currentStep > s.id;
          return (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => { if (isDone) onStepClick(s.id); }}
                disabled={!isDone}
                className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition ${
                  isActive
                    ? "bg-blue-500/10 ring-1 ring-inset ring-blue-500/30"
                    : isDone
                      ? "hover:bg-slate-800/60 cursor-pointer"
                      : "opacity-60 cursor-not-allowed"
                }`}
              >
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
                    ${isActive ? "bg-blue-600 text-white ring-2 ring-blue-600/30" :
                      isDone  ? "bg-emerald-600 text-white" :
                                "bg-slate-800 text-slate-500"}`}
                >
                  {isDone ? (
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : s.id}
                </span>
                <span className="min-w-0 flex-1">
                  <span className={`block text-xs font-semibold leading-tight ${
                    isActive ? "text-blue-300" : isDone ? "text-emerald-400" : "text-slate-300"
                  }`}>
                    {s.label}
                  </span>
                  <span className="mt-0.5 block text-[10px] leading-tight text-slate-500">
                    {s.desc}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      <div className="mt-3 border-t border-slate-800 pt-3">
        <div className="flex items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500 transition-all"
              style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
            />
          </div>
          <span className="text-[10px] font-semibold text-slate-400">
            {Math.round((currentStep / STEPS.length) * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ── MobileStepRail — horizontal scrollable rail (< md) ───────────────────────

export function MobileStepRail({ currentStep }: { currentStep: number }) {
  return (
    <div className="mb-6 overflow-x-auto pb-1 md:hidden">
      <div className="flex items-center min-w-max">
        {STEPS.map((s: StepItem, i: number) => (
          <div key={s.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold
                  ${currentStep === s.id ? "bg-blue-600 ring-2 ring-blue-600/30 text-white" :
                    currentStep > s.id  ? "bg-emerald-600 text-white" :
                                         "bg-slate-800 text-slate-500"}`}
              >
                {currentStep > s.id ? (
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : s.id}
              </div>
              <span className={`mt-1 w-14 text-center text-[9px] leading-tight
                ${currentStep === s.id ? "text-blue-400 font-medium" : currentStep > s.id ? "text-emerald-600" : "text-slate-700"}`}>
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`mx-0.5 mb-4 h-px w-5 shrink-0 ${currentStep > s.id ? "bg-emerald-600" : "bg-slate-800"}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
