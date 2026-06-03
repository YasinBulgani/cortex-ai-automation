"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const variants = cva(
  "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface-base disabled:pointer-events-none disabled:opacity-50 select-none whitespace-nowrap",
  {
    variants: {
      variant: {
        primary:
          "bg-brand text-brand-fg shadow-sm hover:brightness-110 active:brightness-95",
        secondary:
          "border border-border bg-surface-raised text-fg shadow-xs hover:bg-surface-overlay hover:border-border-strong active:bg-surface-accent",
        outline:
          "border border-border bg-transparent text-fg hover:bg-surface-overlay hover:border-border-strong active:bg-surface-accent",
        ghost:
          "text-fg-muted hover:bg-surface-overlay hover:text-fg active:bg-surface-accent",
        subtle:
          "border border-border bg-surface-overlay text-fg-muted hover:border-border-strong hover:text-fg active:bg-surface-accent",
        "ghost-danger":
          "text-danger hover:bg-danger-subtle hover:text-danger active:bg-danger-subtle",
        destructive:
          "bg-danger text-danger-fg shadow-sm hover:brightness-110 active:brightness-95",
      },
      size: {
        default: "h-9 px-4 py-2 text-sm",
        sm:      "h-7 px-3 py-1 text-xs rounded-md",
        lg:      "h-11 px-6 py-3 text-base",
        icon:    "h-8 w-8 p-0",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof variants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(variants({ variant, size }), className)} ref={ref} {...props} />
    );
  }
);
Button.displayName = "Button";
