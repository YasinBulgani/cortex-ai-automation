"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export type SpinnerSize = "xs" | "sm" | "md" | "lg";

const SIZE_PX: Record<SpinnerSize, number> = {
  xs: 12,
  sm: 16,
  md: 24,
  lg: 32,
};

export interface SpinnerProps extends React.SVGAttributes<SVGSVGElement> {
  size?: SpinnerSize | number;
  /** Erişilebilirlik için label (default: "Yükleniyor"). Boşsa decorative. */
  label?: string | null;
}

export function Spinner({ size = "md", label = "Yükleniyor", className, ...rest }: SpinnerProps) {
  const px = typeof size === "number" ? size : SIZE_PX[size];
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      role={label ? "status" : undefined}
      aria-label={label ?? undefined}
      aria-hidden={label === null || undefined}
      className={cn("animate-spin text-current", className)}
      {...rest}
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
