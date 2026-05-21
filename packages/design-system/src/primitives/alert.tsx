"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export type AlertVariant = "info" | "success" | "warning" | "danger";

const VARIANT_CONTAINER: Record<AlertVariant, string> = {
  info:    "bg-info-subtle border-info/30 text-info",
  success: "bg-success-subtle border-success/30 text-success",
  warning: "bg-warning-subtle border-warning/30 text-warning",
  danger:  "bg-danger-subtle border-danger/30 text-danger",
};

export interface AlertProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  variant?: AlertVariant;
  title?: React.ReactNode;
  /** Solda gösterilen ikon */
  icon?: React.ReactNode;
  /** Sağda kapatma butonu */
  onClose?: () => void;
  /** Closable: kullanıcı kapatabilir */
  closeLabel?: string;
}

export function Alert({
  variant = "info",
  title,
  icon,
  onClose,
  closeLabel = "Kapat",
  className,
  children,
  ...rest
}: AlertProps) {
  return (
    <div
      role={variant === "danger" || variant === "warning" ? "alert" : "status"}
      aria-live={variant === "danger" ? "assertive" : "polite"}
      className={cn(
        "flex items-start gap-3 rounded-lg border p-3 text-sm",
        VARIANT_CONTAINER[variant],
        className,
      )}
      {...rest}
    >
      {icon && <span aria-hidden className="mt-0.5 shrink-0">{icon}</span>}
      <div className="min-w-0 flex-1">
        {title && <div className="font-semibold">{title}</div>}
        <div className={cn(title ? "mt-0.5" : undefined, "text-fg")}>{children}</div>
      </div>
      {onClose && (
        <button
          type="button"
          aria-label={closeLabel}
          onClick={onClose}
          className="shrink-0 rounded p-1 opacity-60 hover:opacity-100 transition-opacity"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M6 6 18 18 M18 6 6 18" strokeLinecap="round" />
          </svg>
        </button>
      )}
    </div>
  );
}
