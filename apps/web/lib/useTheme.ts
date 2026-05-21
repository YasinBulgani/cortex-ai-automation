"use client";

import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "neurex_theme_v1";

function readSystemPref(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches
    ? "dark"
    : "light";
}

function readStored(): Theme {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") return raw;
  } catch {
    /* ignore */
  }
  return "system";
}

function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  const resolved = theme === "system" ? readSystemPref() : theme;
  const root = document.documentElement;
  if (resolved === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  root.style.colorScheme = resolved;
}

/**
 * Full dark/light theme toggle — J2.
 *
 * Modes:
 *  - light  : light theme
 *  - dark   : dark theme (current default)
 *  - system : follow OS preference
 *
 * Persisted to localStorage; system mode reactive to OS changes.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("dark");

  // Initial load + cross-tab sync
  useEffect(() => {
    const initial = readStored();
    setThemeState(initial);
    applyTheme(initial);

    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        const next = e.newValue as Theme;
        setThemeState(next);
        applyTheme(next);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // React to OS preference changes when in "system" mode
  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mq) return;
    const onChange = () => applyTheme("system");
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
    applyTheme(next);
  }, []);

  const toggle = useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [theme, setTheme]);

  return { theme, setTheme, toggle, resolved: theme === "system" ? readSystemPref() : theme };
}
