"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export interface DividerProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
  /** Ortada label varsa */
  label?: React.ReactNode;
  /** Daha az belirgin (subtle) */
  subtle?: boolean;
}

export function Divider({
  orientation = "horizontal",
  label,
  subtle,
  className,
  ...rest
}: DividerProps) {
  const colorClass = subtle ? "border-border/40" : "border-border";

  if (orientation === "vertical") {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={cn("inline-block h-full w-px self-stretch border-l", colorClass, className)}
        {...rest}
      />
    );
  }

  if (label) {
    return (
      <div
        role="separator"
        aria-orientation="horizontal"
        className={cn("flex items-center gap-3 text-xs text-fg-subtle", className)}
        {...rest}
      >
        <span className={cn("h-px flex-1 border-t", colorClass)} />
        <span>{label}</span>
        <span className={cn("h-px flex-1 border-t", colorClass)} />
      </div>
    );
  }

  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      className={cn("h-px w-full border-t", colorClass, className)}
      {...rest}
    />
  );
}
