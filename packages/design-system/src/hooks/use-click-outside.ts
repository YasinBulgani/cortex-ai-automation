"use client";

import { useEffect, useRef } from "react";

/**
 * useClickOutside — bir element dışına tıklamada callback çağırır.
 * Dropdown, popover, modal kapatmak için kullanılır.
 *
 * @example
 *   const ref = useClickOutside<HTMLDivElement>(() => setOpen(false));
 *   return <div ref={ref}>...</div>;
 */
export function useClickOutside<T extends HTMLElement>(
  callback: (event: MouseEvent | TouchEvent) => void,
  enabled = true,
) {
  const ref = useRef<T | null>(null);
  const cbRef = useRef(callback);

  useEffect(() => { cbRef.current = callback; }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    const handler = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node | null;
      if (!target || !ref.current) return;
      if (ref.current.contains(target)) return;
      cbRef.current(e);
    };
    document.addEventListener("mousedown", handler);
    document.addEventListener("touchstart", handler);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("touchstart", handler);
    };
  }, [enabled]);

  return ref;
}
