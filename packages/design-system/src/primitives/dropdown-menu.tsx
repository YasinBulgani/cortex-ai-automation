"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";
import { useClickOutside } from "../hooks/use-click-outside";

export interface DropdownItem {
  /** Benzersiz key */
  key: string;
  /** Görünür label */
  label: React.ReactNode;
  /** Sol ikon */
  icon?: React.ReactNode;
  /** Sağ kısayol metni */
  shortcut?: string;
  /** Tehlikeli işlem (farklı renk) */
  danger?: boolean;
  /** Devre dışı */
  disabled?: boolean;
  /** Seçildiğinde */
  onSelect?: () => void;
}

export interface DropdownSeparator {
  key: string;
  separator: true;
}

export interface DropdownHeading {
  key: string;
  heading: React.ReactNode;
}

export type DropdownEntry = DropdownItem | DropdownSeparator | DropdownHeading;

export type DropdownAlign = "start" | "center" | "end";
export type DropdownSide = "top" | "bottom";

export interface DropdownMenuProps {
  /** Tetikleyici (render prop ile) */
  trigger: (props: { open: boolean; toggle: () => void; "aria-expanded": boolean; "aria-haspopup": "menu" }) => React.ReactNode;
  /** Menü öğeleri */
  items: DropdownEntry[];
  /** Hizalama (tetikleyiciye göre) */
  align?: DropdownAlign;
  /** Yön: tetikleyicinin üstü ya da altı */
  side?: DropdownSide;
  /** Menü genişliği (Tailwind sınıfı, ör. "w-56") */
  menuWidth?: string;
  className?: string;
}

export function DropdownMenu({
  trigger,
  items,
  align = "start",
  side = "bottom",
  menuWidth = "w-56",
  className,
}: DropdownMenuProps) {
  const [open, setOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(-1);
  const containerRef = useClickOutside<HTMLDivElement>(() => setOpen(false), open);
  const menuRef = React.useRef<HTMLDivElement | null>(null);

  // Filtre — sadece selectable item'lar keyboard nav için
  const selectable = items
    .map((it, i) => ({ entry: it, index: i }))
    .filter(({ entry }) => "label" in entry && !entry.disabled) as Array<{ entry: DropdownItem; index: number }>;

  const close = React.useCallback(() => setOpen(false), []);
  const toggle = React.useCallback(() => setOpen(o => !o), []);

  // Keyboard nav
  React.useEffect(() => {
    if (!open) {
      setActiveIndex(-1);
      return;
    }
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex(prev => (prev + 1) % selectable.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex(prev => (prev <= 0 ? selectable.length - 1 : prev - 1));
      } else if (e.key === "Home") {
        e.preventDefault();
        setActiveIndex(0);
      } else if (e.key === "End") {
        e.preventDefault();
        setActiveIndex(selectable.length - 1);
      } else if (e.key === "Enter" || e.key === " ") {
        if (activeIndex >= 0 && activeIndex < selectable.length) {
          e.preventDefault();
          const item = selectable[activeIndex].entry;
          item.onSelect?.();
          close();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, selectable, activeIndex, close]);

  const sideClass = side === "top" ? "bottom-full mb-1" : "top-full mt-1";
  const alignClass = align === "start" ? "left-0" : align === "end" ? "right-0" : "left-1/2 -translate-x-1/2";

  return (
    <div ref={containerRef} className={cn("relative inline-block", className)}>
      {trigger({ open, toggle, "aria-expanded": open, "aria-haspopup": "menu" })}
      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-orientation="vertical"
          className={cn(
            "absolute z-50 rounded-lg border border-border bg-surface-raised p-1 shadow-2xl",
            menuWidth,
            sideClass,
            alignClass,
          )}
          data-testid="dropdown-menu"
        >
          {items.map((entry) => {
            if ("separator" in entry) {
              return (
                <div
                  key={entry.key}
                  role="separator"
                  className="my-1 h-px bg-border"
                />
              );
            }
            if ("heading" in entry) {
              return (
                <div
                  key={entry.key}
                  role="presentation"
                  className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle"
                >
                  {entry.heading}
                </div>
              );
            }
            const idx = selectable.findIndex(s => s.entry === entry);
            const isActive = idx === activeIndex;
            return (
              <button
                key={entry.key}
                type="button"
                role="menuitem"
                disabled={entry.disabled}
                onMouseEnter={() => !entry.disabled && setActiveIndex(idx)}
                onClick={() => {
                  if (entry.disabled) return;
                  entry.onSelect?.();
                  close();
                }}
                className={cn(
                  "flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm text-left transition-colors",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                  entry.danger
                    ? "text-danger hover:bg-danger-subtle"
                    : "text-fg hover:bg-surface-overlay",
                  isActive && (entry.danger ? "bg-danger-subtle" : "bg-surface-overlay"),
                  focusRing,
                )}
                data-testid={`dropdown-item-${entry.key}`}
              >
                {entry.icon && <span className="shrink-0">{entry.icon}</span>}
                <span className="flex-1 truncate">{entry.label}</span>
                {entry.shortcut && (
                  <span className="ml-2 text-xs text-fg-subtle">{entry.shortcut}</span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
