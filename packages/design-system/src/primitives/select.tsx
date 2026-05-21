"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing, focusRingDanger } from "../tokens/design-tokens";

export type SelectSize = "sm" | "md" | "lg";

const SIZES: Record<SelectSize, string> = {
  sm: "h-8 pl-2.5 pr-7 text-sm",
  md: "h-9 pl-3   pr-8 text-sm",
  lg: "h-11 pl-4  pr-9 text-base",
};

export interface SelectOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  disabled?: boolean;
}

export interface SelectProps<T extends string = string>
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size"> {
  selectSize?: SelectSize;
  invalid?: boolean;
  fullWidth?: boolean;
  options?: ReadonlyArray<SelectOption<T>>;
  placeholder?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  {
    selectSize = "md",
    invalid,
    fullWidth = true,
    options,
    placeholder,
    className,
    "aria-invalid": ariaInvalid,
    children,
    ...rest
  },
  ref,
) {
  const isInvalid = invalid || ariaInvalid === true || ariaInvalid === "true";

  return (
    <div className={cn("relative inline-block", fullWidth && "w-full")}>
      <select
        ref={ref}
        aria-invalid={isInvalid || undefined}
        className={cn(
          "block w-full appearance-none rounded border bg-surface-base text-fg",
          "border-border",
          isInvalid && "border-danger",
          isInvalid ? focusRingDanger : focusRing,
          "disabled:cursor-not-allowed disabled:opacity-50",
          "transition-colors",
          SIZES[selectSize],
          !fullWidth && "w-auto",
          className,
        )}
        {...rest}
      >
        {placeholder && (
          <option value="" disabled hidden>
            {placeholder}
          </option>
        )}
        {options
          ? options.map(opt => (
              <option key={opt.value} value={opt.value} disabled={opt.disabled}>
                {opt.label}
              </option>
            ))
          : children}
      </select>
      <span
        aria-hidden
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-fg-subtle"
      >
        ▾
      </span>
    </div>
  );
});
