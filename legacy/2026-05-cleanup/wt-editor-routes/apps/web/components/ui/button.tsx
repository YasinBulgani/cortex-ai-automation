"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const variants = cva(
  "inline-flex items-center justify-center rounded font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-blue-600 text-blue-400-fg hover:opacity-90",
        secondary:
          "border border-slate-800 bg-transparent text-white hover:bg-black/5 dark:hover:bg-white/10",
        outline:
          "border border-slate-800 bg-transparent text-white hover:bg-black/5 dark:hover:bg-white/10",
        ghost: "text-white hover:bg-black/5 dark:hover:bg-white/10",
        subtle:
          "border border-slate-700 bg-slate-800/60 text-slate-300 hover:border-slate-500 hover:text-white",
        "ghost-danger":
          "text-red-400 hover:bg-red-500/10 hover:text-red-300",
        destructive: "bg-red-600 text-white hover:bg-red-700",
      },
      size: {
        default: "px-4 py-2 text-sm",
        sm: "px-3 py-1.5 text-xs",
        lg: "px-6 py-3 text-base",
        icon: "h-8 w-8 p-0",
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
