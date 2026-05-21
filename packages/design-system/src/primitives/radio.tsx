"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

// ─── Radio (single) ─────────────────────────────────────────────────────

export interface RadioProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  label?: React.ReactNode;
  description?: React.ReactNode;
  invalid?: boolean;
}

export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(function Radio(
  { label, description, invalid, disabled, className, id, ...rest },
  ref,
) {
  const reactId = React.useId();
  const inputId = id ?? reactId;

  const input = (
    <input
      ref={ref}
      id={inputId}
      type="radio"
      disabled={disabled}
      aria-invalid={invalid || undefined}
      className={cn(
        "h-4 w-4 shrink-0 rounded-full border border-border bg-surface-base",
        "checked:border-brand-primary checked:border-[5px]",
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

// ─── RadioGroup ─────────────────────────────────────────────────────────

export interface RadioOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
}

export interface RadioGroupProps<T extends string = string> {
  name: string;
  options: ReadonlyArray<RadioOption<T>>;
  value?: T;
  defaultValue?: T;
  onValueChange?: (value: T) => void;
  orientation?: "vertical" | "horizontal";
  className?: string;
  /** Pasif tüm seçenekler için */
  disabled?: boolean;
}

export function RadioGroup<T extends string = string>({
  name,
  options,
  value,
  defaultValue,
  onValueChange,
  orientation = "vertical",
  className,
  disabled,
}: RadioGroupProps<T>) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState<T | undefined>(defaultValue);
  const current = isControlled ? value : internal;

  const handleChange = (next: T) => {
    if (!isControlled) setInternal(next);
    onValueChange?.(next);
  };

  return (
    <div
      role="radiogroup"
      className={cn(
        orientation === "horizontal" ? "flex flex-wrap gap-4" : "flex flex-col gap-2",
        className,
      )}
    >
      {options.map(opt => (
        <Radio
          key={opt.value}
          name={name}
          value={opt.value}
          checked={current === opt.value}
          disabled={disabled || opt.disabled}
          label={opt.label}
          description={opt.description}
          onChange={() => handleChange(opt.value)}
        />
      ))}
    </div>
  );
}
