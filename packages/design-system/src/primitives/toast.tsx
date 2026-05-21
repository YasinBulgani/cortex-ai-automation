"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { statusBadge } from "../tokens/design-tokens";

export type ToastVariant = "info" | "success" | "warning" | "danger";
export type ToastPosition =
  | "top-left" | "top-right" | "top-center"
  | "bottom-left" | "bottom-right" | "bottom-center";

export interface ToastOptions {
  /** İçerik metni (veya React node) */
  message: React.ReactNode;
  /** Renk tonu — default "info" */
  variant?: ToastVariant;
  /** Otomatik kapanma süresi (ms). 0 = manuel kapanır. Default 4000. */
  duration_ms?: number;
  /** Sol ikon */
  icon?: React.ReactNode;
  /** Sağda aksiyon butonu */
  action?: { label: string; onClick: () => void };
  /** Erişilebilirlik etiketi (kapatma butonu) */
  closeLabel?: string;
}

interface ToastInternal extends ToastOptions {
  id: number;
}

interface ToastContextValue {
  /** Toast aç — id döner (manuel kapatma için) */
  toast: (opts: ToastOptions | string) => number;
  success: (message: React.ReactNode, opts?: Partial<ToastOptions>) => number;
  error:   (message: React.ReactNode, opts?: Partial<ToastOptions>) => number;
  warning: (message: React.ReactNode, opts?: Partial<ToastOptions>) => number;
  info:    (message: React.ReactNode, opts?: Partial<ToastOptions>) => number;
  /** Belirli toast'ı kapat */
  dismiss: (id: number) => void;
  /** Hepsini kapat */
  dismissAll: () => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = React.useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within <ToastProvider>");
  }
  return ctx;
}

const POSITION_CLASSES: Record<ToastPosition, string> = {
  "top-left":      "top-4 left-4 items-start",
  "top-right":     "top-4 right-4 items-end",
  "top-center":    "top-4 left-1/2 -translate-x-1/2 items-center",
  "bottom-left":   "bottom-4 left-4 items-start",
  "bottom-right":  "bottom-4 right-4 items-end",
  "bottom-center": "bottom-4 left-1/2 -translate-x-1/2 items-center",
};

const STATUS_TO_BADGE: Record<ToastVariant, keyof typeof statusBadge> = {
  info:    "info",
  success: "success",
  warning: "warning",
  danger:  "danger",
};

export interface ToastProviderProps {
  children: React.ReactNode;
  position?: ToastPosition;
  /** Maks aynı anda görünen toast sayısı */
  max?: number;
}

let _id = 0;

export function ToastProvider({
  children,
  position = "bottom-right",
  max = 5,
}: ToastProviderProps) {
  const [toasts, setToasts] = React.useState<ToastInternal[]>([]);
  const timersRef = React.useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const dismiss = React.useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const dismissAll = React.useCallback(() => {
    timersRef.current.forEach(t => clearTimeout(t));
    timersRef.current.clear();
    setToasts([]);
  }, []);

  const enqueue = React.useCallback(
    (opts: ToastOptions): number => {
      const id = ++_id;
      const duration = opts.duration_ms ?? 4000;
      setToasts(prev => {
        const next = [...prev, { ...opts, id }];
        return next.length > max ? next.slice(next.length - max) : next;
      });
      if (duration > 0) {
        const timer = setTimeout(() => dismiss(id), duration);
        timersRef.current.set(id, timer);
      }
      return id;
    },
    [dismiss, max],
  );

  React.useEffect(() => {
    return () => {
      timersRef.current.forEach(t => clearTimeout(t));
      timersRef.current.clear();
    };
  }, []);

  const value: ToastContextValue = React.useMemo(
    () => ({
      toast: (opts) => enqueue(typeof opts === "string" ? { message: opts } : opts),
      success: (message, opts) => enqueue({ ...opts, message, variant: "success" }),
      error:   (message, opts) => enqueue({ ...opts, message, variant: "danger" }),
      warning: (message, opts) => enqueue({ ...opts, message, variant: "warning" }),
      info:    (message, opts) => enqueue({ ...opts, message, variant: "info" }),
      dismiss,
      dismissAll,
    }),
    [enqueue, dismiss, dismissAll],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className={cn(
          "pointer-events-none fixed z-[9999] flex flex-col gap-2",
          POSITION_CLASSES[position],
        )}
        data-testid="toast-container"
      >
        {toasts.map(t => (
          <ToastItem
            key={t.id}
            toast={t}
            onClose={() => dismiss(t.id)}
          />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({
  toast,
  onClose,
}: {
  toast: ToastInternal;
  onClose: () => void;
}) {
  const variant = toast.variant ?? "info";
  return (
    <div
      role={variant === "danger" ? "alert" : "status"}
      className={cn(
        "pointer-events-auto flex min-w-[260px] max-w-md items-start gap-3 rounded-lg border px-4 py-3 text-sm shadow-2xl",
        statusBadge[STATUS_TO_BADGE[variant]],
      )}
      data-testid={`toast-${variant}`}
    >
      {toast.icon && <span aria-hidden className="mt-0.5 shrink-0">{toast.icon}</span>}
      <div className="min-w-0 flex-1">{toast.message}</div>
      {toast.action && (
        <button
          type="button"
          onClick={toast.action.onClick}
          className="shrink-0 font-medium underline-offset-4 hover:underline"
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        onClick={onClose}
        aria-label={toast.closeLabel ?? "Kapat"}
        className="shrink-0 rounded p-1 opacity-60 hover:opacity-100 transition-opacity"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M6 6 18 18 M18 6 6 18" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}
