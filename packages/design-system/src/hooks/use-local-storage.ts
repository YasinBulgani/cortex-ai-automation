"use client";

import { useCallback, useEffect, useState } from "react";

type SetValue<T> = T | ((prev: T) => T);

/**
 * useLocalStorage — localStorage ile senkron stateful değer.
 * Cross-tab senkronizasyon (storage event) destekler.
 * SSR-safe: server'da initialValue döner.
 *
 * @example
 *   const [theme, setTheme] = useLocalStorage("theme", "dark");
 *   setTheme("light");
 */
export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: SetValue<T>) => void, () => void] {
  const read = useCallback((): T => {
    if (typeof window === "undefined") return initialValue;
    try {
      const raw = window.localStorage.getItem(key);
      if (raw === null) return initialValue;
      return JSON.parse(raw) as T;
    } catch {
      return initialValue;
    }
  }, [key, initialValue]);

  const [stored, setStored] = useState<T>(read);

  const setValue = useCallback(
    (value: SetValue<T>) => {
      setStored(prev => {
        const next = value instanceof Function ? value(prev) : value;
        if (typeof window !== "undefined") {
          try {
            window.localStorage.setItem(key, JSON.stringify(next));
          } catch {
            // quota exceeded vb. — sessizce geç
          }
        }
        return next;
      });
    },
    [key],
  );

  const remove = useCallback(() => {
    if (typeof window !== "undefined") {
      try {
        window.localStorage.removeItem(key);
      } catch { /* ignore */ }
    }
    setStored(initialValue);
  }, [key, initialValue]);

  // Cross-tab sync via storage event
  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = (e: StorageEvent) => {
      if (e.key !== key) return;
      if (e.newValue === null) {
        setStored(initialValue);
        return;
      }
      try {
        setStored(JSON.parse(e.newValue) as T);
      } catch { /* ignore parse */ }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, [key, initialValue]);

  return [stored, setValue, remove];
}
