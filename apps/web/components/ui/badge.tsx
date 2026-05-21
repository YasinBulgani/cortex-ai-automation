"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border font-medium",
  {
    variants: {
      variant: {
        default:  "border-border text-muted bg-transparent",
        success:  "border-success/30 bg-success-subtle text-success",
        danger:   "border-danger/30 bg-danger-subtle text-danger",
        warning:  "border-warning/30 bg-warning-subtle text-warning",
        info:     "border-accent/30 bg-accent-subtle text-accent",
        ai:       "border-ai/30 bg-ai-subtle text-ai",
      },
      size: {
        sm:      "px-1.5 py-0 text-[10px]",
        default: "px-2 py-0.5 text-xs",
        lg:      "px-3 py-1 text-sm",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, size, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {children}
    </span>
  );
}
