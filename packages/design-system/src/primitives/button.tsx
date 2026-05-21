"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing, focusRingDanger } from "../tokens/design-tokens";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "outline"
  | "ghost"
  | "subtle"
  | "danger"
  | "ghost-danger"
  | "link";

export type ButtonSize = "xs" | "sm" | "md" | "lg" | "icon";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-primary text-brand-on-primary hover:bg-brand-primary/90 active:bg-brand-primary/80",
  secondary:
    "bg-surface-overlay text-fg hover:bg-surface-accent border border-border",
  outline:
    "border border-border bg-transparent text-fg hover:bg-surface-overlay",
  ghost:
    "bg-transparent text-fg hover:bg-surface-overlay",
  subtle:
    "bg-surface-raised text-fg-muted hover:text-fg hover:bg-surface-overlay",
  danger:
    "bg-danger text-white hover:bg-danger/90 active:bg-danger/80",
  "ghost-danger":
    "bg-transparent text-danger hover:bg-danger-subtle",
  link:
    "bg-transparent text-brand-primary underline-offset-4 hover:underline px-0 py-0 h-auto",
};

const SIZES: Record<ButtonSize, string> = {
  xs:   "h-7 px-2 text-xs gap-1.5",
  sm:   "h-8 px-3 text-sm gap-2",
  md:   "h-9 px-4 text-sm gap-2",
  lg:   "h-11 px-6 text-base gap-2.5",
  icon: "h-9 w-9 p-0",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Soldan ikon */
  leadingIcon?: React.ReactNode;
  /** Sağdan ikon */
  trailingIcon?: React.ReactNode;
  /** Çağrı sırasında spinner göster + disable */
  loading?: boolean;
  /** Tam genişlik */
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    leadingIcon,
    trailingIcon,
    loading,
    fullWidth,
    disabled,
    className,
    children,
    type = "button",
    ...rest
  },
  ref,
) {
  const isDanger = variant === "danger" || variant === "ghost-danger";
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "relative inline-flex select-none items-center justify-center rounded font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        isDanger ? focusRingDanger : focusRing,
        VARIANTS[variant],
        SIZES[size],
        fullWidth && "w-full",
        className,
      )}
      {...rest}
    >
      {loading && (
        <span
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
          aria-hidden
        >
          <Spinner />
        </span>
      )}
      <span
        className={cn(
          "inline-flex items-center gap-2",
          loading && "invisible",
        )}
      >
        {leadingIcon}
        {children}
        {trailingIcon}
      </span>
    </button>
  );
});

function Spinner() {
  return (
    <svg
      className="animate-spin"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
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
