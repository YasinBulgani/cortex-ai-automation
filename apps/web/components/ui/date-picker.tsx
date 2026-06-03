"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface DatePickerProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const DatePicker = React.forwardRef<HTMLInputElement, DatePickerProps>(
  ({ className, label, ...props }, ref) => (
    <div className="flex flex-col gap-1">
      {label && <label className="text-xs font-medium text-fg-muted">{label}</label>}
      <input
        type="date"
        ref={ref}
        className={cn(
          "flex h-9 w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-fg shadow-xs transition-colors hover:border-border-strong focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        {...props}
      />
    </div>
  )
);
DatePicker.displayName = "DatePicker";

interface DateRangePickerProps {
  from?: string;
  to?: string;
  onFromChange?: (value: string) => void;
  onToChange?: (value: string) => void;
  className?: string;
}

export function DateRangePicker({ from, to, onFromChange, onToChange, className }: DateRangePickerProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <DatePicker
        label="Başlangıç"
        value={from}
        onChange={(e) => onFromChange?.(e.target.value)}
        max={to}
      />
      <span className="mt-5 text-fg-subtle">–</span>
      <DatePicker
        label="Bitiş"
        value={to}
        onChange={(e) => onToChange?.(e.target.value)}
        min={from}
      />
    </div>
  );
}
