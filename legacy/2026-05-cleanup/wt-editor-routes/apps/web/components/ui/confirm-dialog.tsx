"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "default";
}

interface ConfirmContextValue {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmContext = createContext<ConfirmContextValue>({ confirm: async () => false });

export function useConfirm() {
  return useContext(ConfirmContext);
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions>({ message: "" });
  const resolveRef = useRef<(value: boolean) => void>();

  const showConfirm = useCallback((opts: ConfirmOptions) => {
    setOptions(opts);
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
    });
  }, []);

  function handleConfirm() {
    setOpen(false);
    resolveRef.current?.(true);
  }

  function handleCancel() {
    setOpen(false);
    resolveRef.current?.(false);
  }

  return (
    <ConfirmContext.Provider value={{ confirm: showConfirm }}>
      {children}
      {open && (
        <>
          <div className="fixed inset-0 z-[9998] bg-black/40" onClick={handleCancel} />
          <div
            className="fixed left-1/2 top-1/2 z-[9999] w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-slate-800 bg-slate-900 p-6 shadow-2xl"
            data-testid="confirm-dialog"
          >
            {options.title && (
              <h3 className="text-lg font-semibold" data-testid="confirm-dialog-heading">
                {options.title}
              </h3>
            )}
            <p className="mt-2 text-sm text-slate-400">{options.message}</p>
            <div className="mt-6 flex justify-end gap-3">
              <Button variant="secondary" onClick={handleCancel} data-testid="confirm-btn-cancel">
                {options.cancelLabel || "İptal"}
              </Button>
              <Button
                onClick={handleConfirm}
                className={options.variant === "danger" ? "bg-red-600 text-white hover:bg-red-700" : ""}
                data-testid="confirm-btn-confirm"
              >
                {options.confirmLabel || "Onayla"}
              </Button>
            </div>
          </div>
        </>
      )}
    </ConfirmContext.Provider>
  );
}
