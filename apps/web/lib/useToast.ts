"use client";

import { useState, useCallback, useEffect, useRef } from "react";

export type ToastType = "success" | "error" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

// Singleton store — shared across all useToast() callers in the same render tree
// because Next.js "use client" modules are singletons per page load.
type Listener = (toasts: Toast[]) => void;

let _toasts: Toast[] = [];
const _listeners = new Set<Listener>();

function _notify() {
  _listeners.forEach(fn => fn([..._toasts]));
}

function _add(type: ToastType, message: string) {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  _toasts = [..._toasts, { id, type, message }];
  _notify();
  // Auto-dismiss after 4s
  setTimeout(() => _dismiss(id), 4000);
}

function _dismiss(id: string) {
  _toasts = _toasts.filter(t => t.id !== id);
  _notify();
}

export function useToast() {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const listener: Listener = () => forceUpdate(n => n + 1);
    _listeners.add(listener);
    return () => { _listeners.delete(listener); };
  }, []);

  const success = useCallback((message: string) => _add("success", message), []);
  const error   = useCallback((message: string) => _add("error", message), []);
  const info    = useCallback((message: string) => _add("info", message), []);
  const dismiss = useCallback((id: string) => _dismiss(id), []);

  return { success, error, info, dismiss, toasts: _toasts };
}

// Imperative helpers — usable outside React components (e.g. in event handlers
// that are already executing, but need to show a toast after an await).
export const toast = {
  success: (message: string) => _add("success", message),
  error:   (message: string) => _add("error", message),
  info:    (message: string) => _add("info", message),
};
