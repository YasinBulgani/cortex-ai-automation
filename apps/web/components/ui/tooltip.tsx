"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

type Placement = "top" | "bottom" | "left" | "right";

export interface TooltipProps {
  content: React.ReactNode;
  placement?: Placement;
  delay?: number;
  className?: string;
  children: React.ReactNode;
  shortcut?: string;
  disabled?: boolean;
}

/**
 * Tooltip — hafif, dependency'siz, klavye erişimli.
 *
 * Anchor element'i bir span ile wrap'lenir (inline-block, transparent).
 * Position fixed portal-less basit kullanım için yeterli.
 */
export function Tooltip({
  content,
  placement = "top",
  delay = 400,
  className,
  children,
  shortcut,
  disabled,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const wrapperRef = useRef<HTMLSpanElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = () => {
    if (disabled) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (wrapperRef.current) {
        const rect = wrapperRef.current.getBoundingClientRect();
        const offsets = {
          top:    { x: rect.left + rect.width / 2, y: rect.top },
          bottom: { x: rect.left + rect.width / 2, y: rect.bottom },
          left:   { x: rect.left, y: rect.top + rect.height / 2 },
          right:  { x: rect.right, y: rect.top + rect.height / 2 },
        };
        setCoords(offsets[placement]);
        setOpen(true);
      }
    }, delay);
  };

  const hide = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setOpen(false);
  };

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  const placementClasses: Record<Placement, string> = {
    top:    "-translate-x-1/2 -translate-y-full -mt-2",
    bottom: "-translate-x-1/2 mt-2",
    left:   "-translate-x-full -translate-y-1/2 -ml-2",
    right:  "translate-y-[-50%] ml-2",
  };

  return (
    <>
      <span
        ref={wrapperRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        className="inline-flex"
      >
        {children}
      </span>
      {open && (
        <div
          role="tooltip"
          className={cn(
            "fixed z-tooltip pointer-events-none animate-fade-in",
            "flex items-center gap-1.5 rounded-md bg-surface-accent border border-border-strong px-2 py-1 text-xs text-fg shadow-elevated whitespace-nowrap",
            placementClasses[placement],
            className,
          )}
          style={{ left: coords.x, top: coords.y }}
        >
          {content}
          {shortcut && (
            <kbd className="rounded bg-surface-base border border-border px-1 py-px text-[10px] font-mono text-fg-muted">
              {shortcut}
            </kbd>
          )}
        </div>
      )}
    </>
  );
}
