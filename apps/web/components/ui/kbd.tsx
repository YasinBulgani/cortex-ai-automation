"use client";

import { cn } from "@/lib/utils";

export interface KbdProps extends React.HTMLAttributes<HTMLElement> {
  size?: "sm" | "md";
}

/**
 * Klavye kısayolu görseli — <kbd>K</kbd>
 *
 * Kullanım:
 *   <Kbd>⌘</Kbd><Kbd>K</Kbd>
 *   <Kbd>Ctrl</Kbd><span className="text-fg-muted">+</span><Kbd>P</Kbd>
 */
export function Kbd({ size = "md", className, children, ...rest }: KbdProps) {
  return (
    <kbd
      className={cn(
        "inline-flex items-center justify-center rounded border font-mono font-medium",
        "bg-surface-overlay border-border text-fg-muted",
        "shadow-[inset_0_-1px_0_var(--border)]",
        size === "sm" && "h-4 min-w-4 px-1 text-[10px]",
        size === "md" && "h-5 min-w-5 px-1.5 text-[11px]",
        className,
      )}
      {...rest}
    >
      {children}
    </kbd>
  );
}

export function KbdGroup({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)}>
      {children}
    </span>
  );
}
