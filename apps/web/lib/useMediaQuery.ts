"use client";

import { useEffect, useState } from "react";

/**
 * Returns true while the given media query matches.
 * SSR-safe: returns `defaultValue` (false) on the server.
 */
export function useMediaQuery(query: string, defaultValue = false): boolean {
  const [matches, setMatches] = useState(defaultValue);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia(query);
    setMatches(mql.matches);

    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);

  return matches;
}

/** Convenience: true when viewport is < 768px (Tailwind `md` breakpoint) */
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 767px)");
}
