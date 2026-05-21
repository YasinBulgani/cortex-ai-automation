"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export type RatingSize = "sm" | "md" | "lg";

const SIZE: Record<RatingSize, string> = {
  sm: "h-4 w-4 text-base",
  md: "h-5 w-5 text-lg",
  lg: "h-6 w-6 text-xl",
};

export interface RatingProps {
  /** Mevcut değer (controlled) */
  value?: number;
  /** Başlangıç değeri (uncontrolled) */
  defaultValue?: number;
  /** Maks yıldız (default 5) */
  max?: number;
  /** Boyut */
  size?: RatingSize;
  /** Salt-okuma (görsel) */
  readOnly?: boolean;
  /** Devre dışı */
  disabled?: boolean;
  /** Değişiklik callback */
  onValueChange?: (value: number) => void;
  /** Aria label */
  label?: string;
  /** Boş yıldız da gösterilsin (default true) */
  showEmpty?: boolean;
  className?: string;
}

export function Rating({
  value,
  defaultValue = 0,
  max = 5,
  size = "md",
  readOnly,
  disabled,
  onValueChange,
  label,
  showEmpty = true,
  className,
}: RatingProps) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState(defaultValue);
  const current = isControlled ? value : internal;
  const [hover, setHover] = React.useState<number | null>(null);

  const setValue = (next: number) => {
    if (readOnly || disabled) return;
    const clamped = Math.max(0, Math.min(max, next));
    if (!isControlled) setInternal(clamped);
    onValueChange?.(clamped);
  };

  const interactive = !readOnly && !disabled;
  const displayValue = hover ?? current;

  return (
    <div
      role={interactive ? "slider" : "img"}
      aria-label={label ?? `Puan: ${current} / ${max}`}
      aria-valuemin={interactive ? 0 : undefined}
      aria-valuemax={interactive ? max : undefined}
      aria-valuenow={interactive ? current : undefined}
      aria-readonly={readOnly || undefined}
      aria-disabled={disabled || undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={(e) => {
        if (!interactive) return;
        if (e.key === "ArrowRight" || e.key === "ArrowUp") {
          e.preventDefault();
          setValue(current + 1);
        } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
          e.preventDefault();
          setValue(current - 1);
        } else if (e.key === "Home") {
          e.preventDefault();
          setValue(0);
        } else if (e.key === "End") {
          e.preventDefault();
          setValue(max);
        }
      }}
      className={cn(
        "inline-flex items-center gap-0.5 outline-none",
        interactive && focusRing,
        disabled && "opacity-50",
        className,
      )}
      onMouseLeave={() => setHover(null)}
    >
      {Array.from({ length: max }).map((_, i) => {
        const idx = i + 1;
        const filled = idx <= displayValue;
        if (!filled && !showEmpty) return null;
        return (
          <button
            key={i}
            type="button"
            disabled={!interactive}
            tabIndex={-1}
            aria-hidden
            onMouseEnter={() => interactive && setHover(idx)}
            onClick={() => setValue(idx === current ? 0 : idx)}
            className={cn(
              "inline-flex items-center justify-center leading-none",
              SIZE[size],
              interactive ? "cursor-pointer transition-transform hover:scale-110" : "cursor-default",
              filled ? "text-warning" : "text-fg-subtle",
            )}
          >
            {filled ? "★" : "☆"}
          </button>
        );
      })}
    </div>
  );
}
