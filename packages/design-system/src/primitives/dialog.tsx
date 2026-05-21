"use client";

import * as React from "react";
import { cn } from "../utils/cn";

export type DialogSize = "sm" | "md" | "lg" | "xl" | "full";

const SIZE_CLASSES: Record<DialogSize, string> = {
  sm:   "max-w-sm",
  md:   "max-w-md",
  lg:   "max-w-2xl",
  xl:   "max-w-4xl",
  full: "max-w-[95vw] max-h-[95vh]",
};

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface DialogProps {
  /** Modal açık mı (controlled) */
  open: boolean;
  /** Kapanma talebi: ESC, overlay click, close button */
  onOpenChange: (open: boolean) => void;
  /** Başlık — aria-labelledby için */
  title?: React.ReactNode;
  /** Açıklama — aria-describedby için */
  description?: React.ReactNode;
  /** Footer slot (genelde butonlar) */
  footer?: React.ReactNode;
  /** İçerik */
  children?: React.ReactNode;
  /** Boyut */
  size?: DialogSize;
  /** Overlay'e tıklamada kapansın mı (default true) */
  closeOnOverlayClick?: boolean;
  /** ESC ile kapansın mı (default true) */
  closeOnEsc?: boolean;
  /** Close butonu görünsün mü (default true) */
  showCloseButton?: boolean;
  /** Erişilebilirlik için kapatma label'ı */
  closeLabel?: string;
  /** Ek className */
  className?: string;
  /** İçindeki ilk focusable yerine bu ref'i focus et */
  initialFocusRef?: React.RefObject<HTMLElement | null>;
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  footer,
  children,
  size = "md",
  closeOnOverlayClick = true,
  closeOnEsc = true,
  showCloseButton = true,
  closeLabel = "Kapat",
  className,
  initialFocusRef,
}: DialogProps) {
  const reactId = React.useId();
  const titleId = `${reactId}-title`;
  const descId = `${reactId}-desc`;
  const contentRef = React.useRef<HTMLDivElement | null>(null);
  const previouslyFocusedRef = React.useRef<HTMLElement | null>(null);

  // Body scroll lock + restore focus
  React.useEffect(() => {
    if (!open) return;
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
      previouslyFocusedRef.current?.focus?.();
    };
  }, [open]);

  // ESC to close
  React.useEffect(() => {
    if (!open || !closeOnEsc) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onOpenChange(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, closeOnEsc, onOpenChange]);

  // Initial focus
  React.useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus();
        return;
      }
      const focusable = contentRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      focusable?.[0]?.focus();
    }, 0);
    return () => clearTimeout(t);
  }, [open, initialFocusRef]);

  // Focus trap (Tab cycles inside)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Tab") return;
    const focusable = contentRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    if (!focusable || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
      aria-describedby={description ? descId : undefined}
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      onKeyDown={handleKeyDown}
      data-testid="dialog"
    >
      <div
        aria-hidden
        className="absolute inset-0 bg-black/60"
        onClick={() => closeOnOverlayClick && onOpenChange(false)}
        data-testid="dialog-overlay"
      />
      <div
        ref={contentRef}
        className={cn(
          "relative w-full overflow-hidden rounded-lg border border-border bg-surface-raised shadow-2xl",
          SIZE_CLASSES[size],
          className,
        )}
        data-testid="dialog-content"
      >
        {(title || showCloseButton) && (
          <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-3">
            <div className="min-w-0 flex-1">
              {title && (
                <h2 id={titleId} className="text-base font-semibold text-fg truncate">
                  {title}
                </h2>
              )}
              {description && (
                <p id={descId} className="mt-0.5 text-sm text-fg-muted">
                  {description}
                </p>
              )}
            </div>
            {showCloseButton && (
              <button
                type="button"
                aria-label={closeLabel}
                onClick={() => onOpenChange(false)}
                className="shrink-0 rounded p-1 text-fg-muted hover:text-fg hover:bg-surface-overlay transition-colors"
                data-testid="dialog-close"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 6 18 18 M18 6 6 18" strokeLinecap="round" />
                </svg>
              </button>
            )}
          </div>
        )}
        <div className="px-5 py-4 text-sm text-fg max-h-[70vh] overflow-y-auto">
          {children}
        </div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-border bg-surface-base/50 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
