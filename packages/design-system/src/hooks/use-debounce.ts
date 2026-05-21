"use client";

import { useEffect, useState } from "react";

/**
 * useDebounce — bir değeri belirli süre boyunca beklemeden değiştirme.
 * Search input, autosave, throttle gibi senaryolar için.
 *
 * @example
 *   const [q, setQ] = useState("");
 *   const debouncedQ = useDebounce(q, 300);
 *   // debouncedQ değişince fetch
 */
export function useDebounce<T>(value: T, delay_ms = 300): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay_ms);
    return () => clearTimeout(id);
  }, [value, delay_ms]);

  return debounced;
}
