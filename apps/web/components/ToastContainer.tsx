"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { Toast, ToastType } from "@/lib/useToast";

// Re-subscribe to the singleton store directly so this component does not need
// to be a child of any context provider.
type Listener = (toasts: Toast[]) => void;

// We import the internal helpers from useToast via a small coupling:
// since the singleton lives in the module scope, we access it via dynamic import.
// Instead, we simply re-export a React component that subscribes to the same
// module-level state by importing useToast.
import { useToast } from "@/lib/useToast";

function IcCheck() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}
function IcX() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}
function IcInfo() {
  return (
    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

const TOAST_STYLES: Record<ToastType, { container: string; icon: React.ReactNode }> = {
  success: {
    container: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    icon: <IcCheck />,
  },
  error: {
    container: "border-red-500/30 bg-red-500/10 text-red-300",
    icon: <IcX />,
  },
  info: {
    container: "border-blue-500/30 bg-blue-500/10 text-blue-300",
    icon: <IcInfo />,
  },
};

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [visible, setVisible] = useState(false);
  const style = TOAST_STYLES[toast.type];

  // Trigger slide-in on mount
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex items-center gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-sm",
        "transition-all duration-300 ease-out",
        visible ? "translate-x-0 opacity-100" : "translate-x-8 opacity-0",
        style.container,
        "min-w-[260px] max-w-[380px]",
      )}
    >
      <span className="shrink-0">{style.icon}</span>
      <p className="flex-1 text-[13px] font-medium leading-snug">{toast.message}</p>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Bildirimi kapat"
        className="shrink-0 rounded-md p-0.5 opacity-60 transition-opacity hover:opacity-100"
      >
        <IcX />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, dismiss } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-label="Bildirimler"
      className="pointer-events-none fixed bottom-5 right-5 z-[9999] flex flex-col gap-2"
    >
      {toasts.map(t => (
        <div key={t.id} className="pointer-events-auto">
          <ToastItem toast={t} onDismiss={dismiss} />
        </div>
      ))}
    </div>
  );
}
