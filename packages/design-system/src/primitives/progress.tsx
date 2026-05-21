"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 0..max — undefined = indeterminate */
  value?: number;
  max?: number;
  /** Aria etiketi (ekran okuyucular için) */
  label?: string;
  /** Boyut: ince, normal, kalın */
  size?: "sm" | "md" | "lg";
  status?: "default" | "success" | "warning" | "danger";
}

const SIZES: Record<NonNullable<ProgressProps["size"]>, string> = {
  sm: "h-1",
  md: "h-1.5",
  lg: "h-2.5",
};

const STATUS_BAR: Record<NonNullable<ProgressProps["status"]>, string> = {
  default: "bg-brand-primary",
  success: "bg-success",
  warning: "bg-warning",
  danger:  "bg-danger",
};

export function Progress({
  value,
  max = 100,
  label,
  size = "md",
  status = "default",
  className,
  ...rest
}: ProgressProps) {
  const isIndeterminate = value === undefined;
  const pct = isIndeterminate ? undefined : Math.max(0, Math.min(100, (value! / max) * 100));

  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={isIndeterminate ? undefined : value}
      className={cn(
        "relative w-full overflow-hidden rounded-full bg-surface-overlay",
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {isIndeterminate ? (
        <span
          className={cn(
            "absolute inset-y-0 left-0 w-1/3 animate-[progress-indeterminate_1.5s_ease-in-out_infinite] rounded-full",
            STATUS_BAR[status],
          )}
        />
      ) : (
        <span
          className={cn("block h-full rounded-full transition-[width] duration-300", STATUS_BAR[status])}
          style={{ width: `${pct}%` }}
        />
      )}
    </div>
  );
}
