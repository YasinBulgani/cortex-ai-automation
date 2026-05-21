"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-400",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Input.displayName = "Input";
