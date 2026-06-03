"use client";

import { useEffect, useState } from "react";

const KEY = "neurex_theme_v1";

function getStored(): boolean {
  try { return localStorage.getItem(KEY) !== "light"; }
  catch { return true; }
}

function applyDark(dark: boolean) {
  if (dark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
  try { localStorage.setItem(KEY, dark ? "dark" : "light"); } catch {}
}

export function ThemeToggle() {
  const [dark, setDark] = useState(true);

  useEffect(() => {
    const isDark = getStored();
    setDark(isDark);
    applyDark(isDark);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    applyDark(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Açık moda geç" : "Koyu moda geç"}
      data-testid="header-btn-theme"
      title={dark ? "Açık mod" : "Koyu mod"}
      className="flex h-8 w-8 items-center justify-center rounded-lg text-fg-subtle hover:bg-surface-overlay hover:text-fg transition-colors"
    >
      {dark ? (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <circle cx="12" cy="12" r="4" />
          <path strokeLinecap="round" d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
        </svg>
      ) : (
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
      )}
    </button>
  );
}
