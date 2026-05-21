"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { statusBadge } from "../tokens/design-tokens";

export type BadgeStatus = keyof typeof statusBadge;
export type BadgeSize = "xs" | "sm" | "md";

const SIZES: Record<BadgeSize, string> = {
  xs: "px-1.5 py-0.5 text-[10px]",
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: BadgeStatus;
  size?: BadgeSize;
  /** Tıklanabilir badge (chip) için cursor + hover state */
  interactive?: boolean;
  /** Sol noktalı dot (dot indicator) */
  dot?: boolean;
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(function Badge(
  { status = "neutral", size = "sm", interactive, dot, className, children, ...rest },
  ref,
) {
  return (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium whitespace-nowrap",
        statusBadge[status],
        SIZES[size],
        interactive && "cursor-pointer hover:opacity-80 transition-opacity",
        className,
      )}
      {...rest}
    >
      {dot && (
        <span
          className={cn(
            "inline-block h-1.5 w-1.5 rounded-full",
            status === "success" && "bg-success",
            status === "warning" && "bg-warning",
            status === "danger"  && "bg-danger",
            status === "info"    && "bg-info",
            status === "neutral" && "bg-fg-muted",
          )}
          aria-hidden
        />
      )}
      {children}
    </span>
  );
});
