"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { useClickOutside } from "../hooks/use-click-outside";

export type PopoverAlign = "start" | "center" | "end";
export type PopoverSide = "top" | "bottom" | "left" | "right";

export interface PopoverProps {
  /** Controlled açık mı */
  open?: boolean;
  /** Uncontrolled başlangıç */
  defaultOpen?: boolean;
  /** Değişiklik callback */
  onOpenChange?: (open: boolean) => void;
  /** Tetikleyici (render prop) */
  trigger: (api: {
    open: boolean;
    toggle: () => void;
    "aria-expanded": boolean;
    "aria-haspopup": "dialog";
    ref: React.RefObject<HTMLButtonElement | null>;
  }) => React.ReactNode;
  /** İçerik */
  children: React.ReactNode;
  /** Tetikleyiciye göre yön */
  side?: PopoverSide;
  /** Hizalama */
  align?: PopoverAlign;
  /** Tetikleyiciyle gap (px) */
  sideOffset?: number;
  /** Genişlik (Tailwind sınıfı) */
  width?: string;
  /** ESC ile kapansın mı (default true) */
  closeOnEsc?: boolean;
  /** Dışarı tıklamada kapansın mı (default true) */
  closeOnOutside?: boolean;
  /** Modal=true → arkadakine focus kilidi (varsayılan false) */
  modal?: boolean;
  className?: string;
}

export function Popover({
  open: controlledOpen,
  defaultOpen = false,
  onOpenChange,
  trigger,
  children,
  side = "bottom",
  align = "start",
  sideOffset = 4,
  width,
  closeOnEsc = true,
  closeOnOutside = true,
  modal = false,
  className,
}: PopoverProps) {
  const isControlled = controlledOpen !== undefined;
  const [internal, setInternal] = React.useState(defaultOpen);
  const open = isControlled ? controlledOpen : internal;

  const setOpen = React.useCallback(
    (next: boolean) => {
      if (!isControlled) setInternal(next);
      onOpenChange?.(next);
    },
    [isControlled, onOpenChange],
  );

  const triggerRef = React.useRef<HTMLButtonElement | null>(null);
  const containerRef = useClickOutside<HTMLDivElement>(
    () => closeOnOutside && setOpen(false),
    open,
  );

  React.useEffect(() => {
    if (!open || !closeOnEsc) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, closeOnEsc, setOpen]);

  const toggle = React.useCallback(() => setOpen(!open), [open, setOpen]);

  const sideClass = (() => {
    switch (side) {
      case "top":    return "bottom-full";
      case "bottom": return "top-full";
      case "left":   return "right-full top-0";
      case "right":  return "left-full top-0";
    }
  })();

  const alignClass = (() => {
    if (side === "left" || side === "right") {
      if (align === "start")  return "top-0";
      if (align === "end")    return "bottom-0";
      return "top-1/2 -translate-y-1/2";
    }
    if (align === "start") return "left-0";
    if (align === "end")   return "right-0";
    return "left-1/2 -translate-x-1/2";
  })();

  const offsetStyle = (() => {
    if (side === "top")    return { marginBottom: sideOffset };
    if (side === "bottom") return { marginTop: sideOffset };
    if (side === "left")   return { marginRight: sideOffset };
    if (side === "right")  return { marginLeft: sideOffset };
    return undefined;
  })();

  return (
    <div ref={containerRef} className="relative inline-block">
      {trigger({
        open,
        toggle,
        "aria-expanded": open,
        "aria-haspopup": "dialog",
        ref: triggerRef,
      })}
      {open && (
        <div
          role="dialog"
          aria-modal={modal || undefined}
          style={offsetStyle}
          className={cn(
            "absolute z-50 rounded-lg border border-border bg-surface-raised shadow-2xl p-3 text-sm text-fg",
            width,
            sideClass,
            alignClass,
            className,
          )}
          data-testid="popover-content"
        >
          {children}
        </div>
      )}
    </div>
  );
}
