"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  label?: React.ReactNode;
  description?: React.ReactNode;
  /** Üç durumlu (yarı işaretli) */
  indeterminate?: boolean;
  invalid?: boolean;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, description, indeterminate, invalid, disabled, className, id, ...rest },
  forwardedRef,
) {
  const reactId = React.useId();
  const inputId = id ?? reactId;
  const innerRef = React.useRef<HTMLInputElement | null>(null);

  React.useImperativeHandle(forwardedRef, () => innerRef.current as HTMLInputElement);

  React.useEffect(() => {
    if (innerRef.current) {
      innerRef.current.indeterminate = !!indeterminate;
    }
  }, [indeterminate]);

  const input = (
    <input
      ref={innerRef}
      id={inputId}
      type="checkbox"
      disabled={disabled}
      aria-invalid={invalid || undefined}
      className={cn(
        "h-4 w-4 shrink-0 rounded border border-border bg-surface-base",
        "checked:bg-brand-primary checked:border-brand-primary",
        "indeterminate:bg-brand-primary indeterminate:border-brand-primary",
        invalid && "border-danger",
        "cursor-pointer disabled:cursor-not-allowed disabled:opacity-50",
        focusRing,
        className,
      )}
      {...rest}
    />
  );

  if (!label && !description) return input;

  return (
    <label
      htmlFor={inputId}
      className={cn(
        "flex items-start gap-2 text-sm",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
      )}
    >
      {input}
      <span className="min-w-0 flex-1">
        {label && <span className="block text-fg">{label}</span>}
        {description && <span className="mt-0.5 block text-xs text-fg-subtle">{description}</span>}
      </span>
    </label>
  );
});
