"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export type StepStatus = "complete" | "current" | "upcoming" | "error";

export interface StepDef {
  /** Benzersiz key */
  key: string;
  /** Görünür başlık */
  title: React.ReactNode;
  /** Opsiyonel açıklama */
  description?: React.ReactNode;
  /** Açıkça status — yoksa current/upcoming akışından türetilir */
  status?: StepStatus;
}

export interface StepperProps {
  steps: ReadonlyArray<StepDef>;
  /** Hangi step aktif (0-tabanlı) */
  active: number;
  /** Yatay (default) ya da dikey */
  orientation?: "horizontal" | "vertical";
  /** Step'e tıklamayı engelle (default: complete olanlar tıklanabilir) */
  onStepClick?: (index: number, step: StepDef) => void;
  className?: string;
  /** Aria label */
  label?: string;
}

export function Stepper({
  steps,
  active,
  orientation = "horizontal",
  onStepClick,
  className,
  label = "Adımlar",
}: StepperProps) {
  return (
    <ol
      role="list"
      aria-label={label}
      className={cn(
        orientation === "horizontal"
          ? "flex w-full items-start"
          : "flex flex-col gap-3",
        className,
      )}
    >
      {steps.map((step, i) => {
        const status: StepStatus = step.status ?? (
          i < active ? "complete" :
          i === active ? "current" :
          "upcoming"
        );
        const isLast = i === steps.length - 1;
        const clickable = !!onStepClick && status !== "upcoming";
        return (
          <li
            key={step.key}
            aria-current={status === "current" ? "step" : undefined}
            className={cn(
              orientation === "horizontal" ? "flex-1 flex items-start" : "flex items-start gap-3",
            )}
          >
            <div className={cn("flex", orientation === "horizontal" ? "flex-col items-center w-full" : "flex-row items-start gap-3 w-full")}>
              <div className={cn(orientation === "horizontal" ? "flex w-full items-center" : "flex flex-col items-center")}>
                {/* connector before (skip on first) */}
                {i > 0 && orientation === "horizontal" && (
                  <span
                    aria-hidden
                    className={cn(
                      "h-px flex-1",
                      status === "complete" || status === "current"
                        ? "bg-brand-primary"
                        : "bg-border",
                    )}
                  />
                )}

                <button
                  type="button"
                  disabled={!clickable}
                  onClick={() => clickable && onStepClick?.(i, step)}
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-medium transition-colors",
                    status === "complete" && "bg-brand-primary border-brand-primary text-brand-on-primary",
                    status === "current"  && "border-brand-primary text-brand-primary",
                    status === "upcoming" && "border-border text-fg-subtle",
                    status === "error"    && "bg-danger border-danger text-white",
                    clickable && "cursor-pointer hover:opacity-90",
                    !clickable && "cursor-default",
                  )}
                  aria-label={`Adım ${i + 1}`}
                >
                  {status === "complete" ? "✓" : status === "error" ? "!" : i + 1}
                </button>

                {/* connector after (skip on last) */}
                {!isLast && orientation === "horizontal" && (
                  <span
                    aria-hidden
                    className={cn(
                      "h-px flex-1",
                      i < active ? "bg-brand-primary" : "bg-border",
                    )}
                  />
                )}
                {!isLast && orientation === "vertical" && (
                  <span
                    aria-hidden
                    className={cn("mt-1 h-8 w-px",
                      i < active ? "bg-brand-primary" : "bg-border",
                    )}
                  />
                )}
              </div>

              {/* Title/description */}
              <div className={cn(
                orientation === "horizontal" ? "mt-2 text-center" : "flex-1",
                orientation === "vertical" && "pb-3",
              )}>
                <div className={cn(
                  "text-xs font-medium",
                  status === "current" ? "text-fg" : "text-fg-muted",
                )}>
                  {step.title}
                </div>
                {step.description && (
                  <div className="mt-0.5 text-[11px] text-fg-subtle">{step.description}</div>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
