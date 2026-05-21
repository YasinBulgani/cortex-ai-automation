"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface DatePickerProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const DatePicker = React.forwardRef<HTMLInputElement, DatePickerProps>(
  ({ className, label, ...props }, ref) => (
    <div className="flex flex-col gap-1">
      {label && <label className="text-xs font-medium text-slate-400">{label}</label>}
      <input
        type="date"
        ref={ref}
        className={cn(
          "flex h-9 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white shadow-sm transition-colors hover:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50",
          "[color-scheme:dark]",
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
      <span className="mt-5 text-slate-400">–</span>
      <DatePicker
        label="Bitiş"
        value={to}
        onChange={(e) => onToChange?.(e.target.value)}
        min={from}
      />
    </div>
  );
}
