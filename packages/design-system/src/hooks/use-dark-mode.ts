"use client";

import { useCallback, useEffect } from "react";
import { useLocalStorage } from "./use-local-storage";
import { useMediaQuery } from "./use-media-query";

export type ThemePreference = "light" | "dark" | "system";

/**
 * useDarkMode — tema yönetimi.
 *  - system: OS tercihini izler (prefers-color-scheme: dark)
 *  - dark/light: zorla seçilir, localStorage'da saklanır
 *
 * DOM'a `data-theme` attribute'u + `dark` class'ı uygular (Tailwind dark variant).
 *
 * @example
 *   const { theme, setTheme, isDark } = useDarkMode();
 *   <button onClick={() => setTheme(isDark ? "light" : "dark")}>{isDark ? "☀" : "🌙"}</button>
 */
export function useDarkMode(storage_key = "neurex.theme"): {
  theme: ThemePreference;
  setTheme: (t: ThemePreference) => void;
  isDark: boolean;
} {
  const [theme, setStoredTheme] = useLocalStorage<ThemePreference>(storage_key, "system");
  const systemPrefersDark = useMediaQuery("(prefers-color-scheme: dark)");

  const isDark = theme === "dark" || (theme === "system" && systemPrefersDark);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      root.setAttribute("data-theme", "dark");
    } else {
      root.classList.remove("dark");
      root.setAttribute("data-theme", "light");
    }
  }, [isDark]);

  const setTheme = useCallback(
    (t: ThemePreference) => setStoredTheme(t),
    [setStoredTheme],
  );

  return { theme, setTheme, isDark };
}
