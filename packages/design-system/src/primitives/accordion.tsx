"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";

export interface AccordionItem {
  value: string;
  title: React.ReactNode;
  content: React.ReactNode;
  /** Sol ikon */
  icon?: React.ReactNode;
  /** Devre dışı */
  disabled?: boolean;
}

export type AccordionType = "single" | "multiple";

export interface AccordionProps {
  items: ReadonlyArray<AccordionItem>;
  /** "single" = tek seferde 1 açık, "multiple" = birden fazla */
  type?: AccordionType;
  /** Controlled: tip="single" → string?, tip="multiple" → string[] */
  value?: string | string[];
  /** Uncontrolled başlangıç */
  defaultValue?: string | string[];
  /** Tip="single"da kapalı olabilir mi (default true) */
  collapsible?: boolean;
  onValueChange?: (value: string | string[]) => void;
  className?: string;
}

export function Accordion({
  items,
  type = "single",
  value,
  defaultValue,
  collapsible = true,
  onValueChange,
  className,
}: AccordionProps) {
  const isControlled = value !== undefined;
  const [internal, setInternal] = React.useState<string | string[]>(
    defaultValue ?? (type === "multiple" ? [] : ""),
  );
  const current = isControlled ? (value as string | string[]) : internal;

  const isOpen = (val: string) =>
    type === "multiple"
      ? (current as string[]).includes(val)
      : current === val;

  const toggle = (val: string) => {
    let next: string | string[];
    if (type === "multiple") {
      const arr = current as string[];
      next = arr.includes(val) ? arr.filter(v => v !== val) : [...arr, val];
    } else {
      next = current === val ? (collapsible ? "" : (current as string)) : val;
    }
    if (!isControlled) setInternal(next);
    onValueChange?.(next);
  };

  return (
    <div className={cn("divide-y divide-border rounded-lg border border-border bg-surface-raised", className)}>
      {items.map(it => {
        const open = isOpen(it.value);
        const panelId = `acc-panel-${it.value}`;
        const triggerId = `acc-trigger-${it.value}`;
        return (
          <div key={it.value}>
            <h3>
              <button
                id={triggerId}
                type="button"
                aria-expanded={open}
                aria-controls={panelId}
                disabled={it.disabled}
                onClick={() => toggle(it.value)}
                className={cn(
                  "flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-medium",
                  "text-fg hover:bg-surface-overlay/50 transition-colors",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  focusRing,
                )}
              >
                <span className="inline-flex items-center gap-2">
                  {it.icon}
                  {it.title}
                </span>
                <span
                  className={cn("transition-transform text-fg-muted", open && "rotate-180")}
                  aria-hidden
                >
                  ▾
                </span>
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={triggerId}
              hidden={!open}
              className={cn("px-4 pb-3 text-sm text-fg-muted", open ? "block" : "hidden")}
            >
              {open && it.content}
            </div>
          </div>
        );
      })}
    </div>
  );
}
