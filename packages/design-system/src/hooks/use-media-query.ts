"use client";

import { useEffect, useState } from "react";

/**
 * useMediaQuery — bir CSS media query'nin eşleşip eşleşmediğini izler.
 * SSR-safe: server'da default değer döner.
 *
 * @example
 *   const isMobile = useMediaQuery("(max-width: 768px)");
 *   const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");
 */
export function useMediaQuery(query: string, defaultValue = false): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined") return defaultValue;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    if (mql.addEventListener) {
      mql.addEventListener("change", listener);
      return () => mql.removeEventListener("change", listener);
    }
    // Safari < 14 fallback
    mql.addListener(listener);
    return () => mql.removeListener(listener);
  }, [query]);

  return matches;
}

/** Yaygın breakpoint helper'ları (Tailwind defaults ile uyumlu) */
export const breakpoints = {
  sm: "(min-width: 640px)",
  md: "(min-width: 768px)",
  lg: "(min-width: 1024px)",
  xl: "(min-width: 1280px)",
  "2xl": "(min-width: 1536px)",
} as const;
