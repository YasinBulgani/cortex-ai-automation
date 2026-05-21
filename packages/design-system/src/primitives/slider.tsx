"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export interface SliderProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "defaultValue" | "onChange"> {
  /** Mevcut değer (controlled) */
  value?: number;
  /** Başlangıç değeri (uncontrolled) */
  defaultValue?: number;
  /** Değişiklik callback */
  onValueChange?: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  /** Aria label */
  label?: string;
  /** Mevcut değeri sağda göster */
  showValue?: boolean;
  /** Format helper (value → string) */
  formatValue?: (value: number) => string;
  invalid?: boolean;
}

export const Slider = React.forwardRef<HTMLInputElement, SliderProps>(function Slider(
  {
    value,
    defaultValue = 0,
    onValueChange,
    min = 0,
    max = 100,
    step = 1,
    label,
    showValue,
    formatValue,
    invalid,
    disabled,
    className,
    id,
    "aria-label": ariaLabel,
    ...rest
  },
  ref,
) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState(defaultValue);
  const current = isControlled ? value : internal;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(e.target.value);
    if (!isControlled) setInternal(next);
    onValueChange?.(next);
  };

  const pct = ((current - min) / (max - min)) * 100;
  const displayValue = formatValue ? formatValue(current) : current.toString();
  const reactId = React.useId();
  const inputId = id ?? reactId;

  return (
    <div className={cn("flex items-center gap-3", className)}>
      {label && (
        <span className="text-xs text-fg-muted shrink-0">{label}</span>
      )}
      <div className="relative flex-1">
        {/* Track + fill */}
        <div
          aria-hidden
          className={cn(
            "h-1.5 w-full rounded-full",
            invalid ? "bg-danger-subtle" : "bg-surface-overlay",
          )}
        >
          <div
            className={cn(
              "h-full rounded-full",
              invalid ? "bg-danger" : "bg-brand-primary",
            )}
            style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
          />
        </div>
        {/* Native input — visually overlays, keeps native a11y + keyboard */}
        <input
          ref={ref}
          id={inputId}
          type="range"
          min={min}
          max={max}
          step={step}
          value={current}
          onChange={handleChange}
          disabled={disabled}
          aria-label={ariaLabel ?? label}
          aria-invalid={invalid || undefined}
          className={cn(
            "absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer",
            "[&::-webkit-slider-thumb]:appearance-none",
            "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full",
            "[&::-webkit-slider-thumb]:bg-brand-primary [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-surface-base",
            "[&::-webkit-slider-thumb]:shadow",
            "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full",
            "[&::-moz-range-thumb]:bg-brand-primary [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-surface-base",
            "disabled:cursor-not-allowed disabled:opacity-50",
            focusRing,
          )}
          {...rest}
        />
      </div>
      {showValue && (
        <span className="text-xs font-medium text-fg tabular-nums min-w-10 text-right">
          {displayValue}
        </span>
      )}
    </div>
  );
});
