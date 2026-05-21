"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing, focusRingDanger } from "../tokens/design-tokens";

export type InputSize = "sm" | "md" | "lg";

const SIZES: Record<InputSize, string> = {
  sm: "h-8 px-2.5 text-sm",
  md: "h-9 px-3 text-sm",
  lg: "h-11 px-4 text-base",
};

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size"> {
  inputSize?: InputSize;
  invalid?: boolean;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
  /** Tam genişlik (default true) */
  fullWidth?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    inputSize = "md",
    invalid,
    leadingIcon,
    trailingIcon,
    fullWidth = true,
    className,
    "aria-invalid": ariaInvalid,
    ...rest
  },
  ref,
) {
  const isInvalid = invalid || ariaInvalid === true || ariaInvalid === "true";

  const inputEl = (
    <input
      ref={ref}
      aria-invalid={isInvalid || undefined}
      className={cn(
        "block w-full rounded border bg-surface-base text-fg placeholder:text-fg-subtle",
        "border-border",
        isInvalid && "border-danger",
        isInvalid ? focusRingDanger : focusRing,
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-colors",
        SIZES[inputSize],
        leadingIcon ? "pl-9" : undefined,
        trailingIcon ? "pr-9" : undefined,
        !fullWidth && "w-auto",
        className,
      )}
      {...rest}
    />
  );

  if (!leadingIcon && !trailingIcon) return inputEl;

  return (
    <div className={cn("relative inline-block", fullWidth && "w-full")}>
      {leadingIcon && (
        <span
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fg-subtle"
          aria-hidden
        >
          {leadingIcon}
        </span>
      )}
      {inputEl}
      {trailingIcon && (
        <span
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-fg-subtle"
          aria-hidden
        >
          {trailingIcon}
        </span>
      )}
    </div>
  );
});

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
  fullWidth?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid, fullWidth = true, className, "aria-invalid": ariaInvalid, rows = 4, ...rest },
  ref,
) {
  const isInvalid = invalid || ariaInvalid === true || ariaInvalid === "true";
  return (
    <textarea
      ref={ref}
      rows={rows}
      aria-invalid={isInvalid || undefined}
      className={cn(
        "block w-full rounded border bg-surface-base text-fg placeholder:text-fg-subtle px-3 py-2 text-sm",
        "border-border",
        isInvalid && "border-danger",
        isInvalid ? focusRingDanger : focusRing,
        "disabled:cursor-not-allowed disabled:opacity-50",
        "transition-colors resize-y",
        !fullWidth && "w-auto",
        className,
      )}
      {...rest}
    />
  );
});
