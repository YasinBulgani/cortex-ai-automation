"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export type SwitchSize = "sm" | "md";

const SIZES: Record<SwitchSize, { track: string; thumb: string; translate: string }> = {
  sm: { track: "h-4 w-7",  thumb: "h-3 w-3", translate: "peer-checked:translate-x-3"   },
  md: { track: "h-5 w-9",  thumb: "h-4 w-4", translate: "peer-checked:translate-x-4"   },
};

export interface SwitchProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  switchSize?: SwitchSize;
  /** Label metni (varsa input ile etiketlenir) */
  label?: React.ReactNode;
}

export const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(function Switch(
  { switchSize = "md", label, disabled, className, id, ...rest },
  ref,
) {
  const reactId = React.useId();
  const inputId = id ?? reactId;
  const { track, thumb, translate } = SIZES[switchSize];

  const control = (
    <span className={cn("relative inline-flex items-center", track, className)}>
      <input
        ref={ref}
        id={inputId}
        type="checkbox"
        role="switch"
        disabled={disabled}
        className={cn(
          "peer absolute inset-0 m-0 h-full w-full cursor-pointer appearance-none rounded-full",
          "bg-surface-overlay border border-border",
          "checked:bg-brand-primary checked:border-brand-primary",
          "disabled:cursor-not-allowed disabled:opacity-50",
          focusRing,
        )}
        {...rest}
      />
      <span
        aria-hidden
        className={cn(
          "pointer-events-none relative ml-0.5 inline-block rounded-full bg-white shadow transition-transform",
          thumb,
          translate,
        )}
      />
    </span>
  );

  if (!label) return control;

  return (
    <label
      htmlFor={inputId}
      className={cn(
        "inline-flex items-center gap-2 text-sm text-fg",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
      )}
    >
      {control}
      <span>{label}</span>
    </label>
  );
});
