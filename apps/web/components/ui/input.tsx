"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-fg",
        "placeholder:text-fg-subtle",
        "shadow-xs",
        "transition-colors duration-fast",
        "focus:outline-none focus:ring-2 focus:ring-brand focus:ring-offset-1 focus:ring-offset-surface-base focus:border-brand",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-surface-overlay",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Input.displayName = "Input";
