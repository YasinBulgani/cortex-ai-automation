"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export interface TabItem<T extends string = string> {
  value: T;
  label: React.ReactNode;
  /** Devre dışı */
  disabled?: boolean;
  /** Sağda badge */
  badge?: React.ReactNode;
}

export type TabsVariant = "line" | "pills";
export type TabsSize = "sm" | "md";

export interface TabsProps<T extends string = string> {
  /** Sekme tanımları */
  items: ReadonlyArray<TabItem<T>>;
  /** Aktif sekme (controlled) */
  value?: T;
  /** Başlangıç değeri (uncontrolled) */
  defaultValue?: T;
  /** Değişiklik callback'i */
  onValueChange?: (value: T) => void;
  /** Görsel stil */
  variant?: TabsVariant;
  /** Boyut */
  size?: TabsSize;
  /** Aria label (tablist için) */
  label?: string;
  className?: string;
}

const SIZE: Record<TabsSize, { padding: string; text: string }> = {
  sm: { padding: "px-2.5 py-1", text: "text-xs" },
  md: { padding: "px-3 py-1.5", text: "text-sm" },
};

export function Tabs<T extends string = string>({
  items,
  value,
  defaultValue,
  onValueChange,
  variant = "line",
  size = "md",
  label,
  className,
}: TabsProps<T>) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState<T>(
    defaultValue ?? (items[0]?.value as T),
  );
  const current = isControlled ? (value as T) : internal;

  const setActive = (next: T) => {
    if (!isControlled) setInternal(next);
    onValueChange?.(next);
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, idx: number) => {
    const enabledIdxs = items.map((it, i) => (it.disabled ? -1 : i)).filter(i => i >= 0);
    const currentPos = enabledIdxs.indexOf(idx);
    if (currentPos === -1) return;

    let nextPos = currentPos;
    if (e.key === "ArrowRight") nextPos = (currentPos + 1) % enabledIdxs.length;
    else if (e.key === "ArrowLeft") nextPos = (currentPos - 1 + enabledIdxs.length) % enabledIdxs.length;
    else if (e.key === "Home") nextPos = 0;
    else if (e.key === "End") nextPos = enabledIdxs.length - 1;
    else return;

    e.preventDefault();
    const next = items[enabledIdxs[nextPos]];
    setActive(next.value);
  };

  return (
    <div
      role="tablist"
      aria-label={label}
      aria-orientation="horizontal"
      className={cn(
        "flex items-center gap-1",
        variant === "line" && "border-b border-border",
        className,
      )}
    >
      {items.map((it, idx) => {
        const isActive = it.value === current;
        return (
          <button
            key={it.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${it.value}`}
            id={`tab-${it.value}`}
            disabled={it.disabled}
            tabIndex={isActive ? 0 : -1}
            onClick={() => setActive(it.value)}
            onKeyDown={(e) => handleKeyDown(e, idx)}
            className={cn(
              "relative inline-flex items-center gap-2 font-medium transition-colors",
              SIZE[size].padding,
              SIZE[size].text,
              focusRing,
              "disabled:cursor-not-allowed disabled:opacity-50",
              variant === "line" && [
                "-mb-px border-b-2",
                isActive
                  ? "border-brand-primary text-fg"
                  : "border-transparent text-fg-muted hover:text-fg",
              ],
              variant === "pills" && [
                "rounded-md",
                isActive
                  ? "bg-brand-primary text-brand-on-primary"
                  : "text-fg-muted hover:bg-surface-overlay",
              ],
            )}
          >
            <span>{it.label}</span>
            {it.badge}
          </button>
        );
      })}
    </div>
  );
}

export interface TabPanelProps {
  /** Eşleşen TabItem.value */
  value: string;
  /** Aktif değerle eşleşirse görünür */
  activeValue: string;
  children?: React.ReactNode;
  className?: string;
}

export function TabPanel({ value, activeValue, children, className }: TabPanelProps) {
  const isActive = value === activeValue;
  return (
    <div
      role="tabpanel"
      id={`panel-${value}`}
      aria-labelledby={`tab-${value}`}
      hidden={!isActive}
      tabIndex={0}
      className={cn(isActive ? "block" : "hidden", className)}
    >
      {isActive && children}
    </div>
  );
}
