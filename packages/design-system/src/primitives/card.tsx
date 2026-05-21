"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Hover'da yükselme efekti */
  interactive?: boolean;
  /** Daha az padding (compact) */
  compact?: boolean;
  /** Border yok, sadece surface */
  borderless?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { interactive, compact, borderless, className, ...rest },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-lg bg-surface-raised",
        !borderless && "border border-border",
        interactive && "transition-shadow hover:shadow-lg cursor-pointer",
        compact ? "p-3" : "p-4",
        className,
      )}
      {...rest}
    />
  );
});

export interface CardHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
}

export function CardHeader({ title, description, action, className, children, ...rest }: CardHeaderProps) {
  return (
    <div
      className={cn("flex items-start justify-between gap-3 mb-3", className)}
      {...rest}
    >
      <div className="min-w-0 flex-1">
        {title && (
          <h3 className="text-base font-semibold text-fg truncate">{title}</h3>
        )}
        {description && (
          <p className="mt-0.5 text-sm text-fg-muted">{description}</p>
        )}
        {children}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({ className, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("text-sm text-fg", className)} {...rest} />;
}

export function CardFooter({ className, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mt-3 pt-3 border-t border-border flex items-center justify-end gap-2", className)}
      {...rest}
    />
  );
}
