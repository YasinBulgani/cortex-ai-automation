"use client";

import { useTheme } from "@/lib/useTheme";

/**
 * Full theme toggle UI — Light / Dark / System segmented control.
 *
 * Distinct from the existing simple toggle to avoid conflicts.
 */
export function ThemeToggleFull() {
  const { theme, setTheme } = useTheme();

  const opts: { value: "light" | "dark" | "system"; label: string; icon: string }[] = [
    { value: "light", label: "Açık", icon: "☀" },
    { value: "dark", label: "Koyu", icon: "☾" },
    { value: "system", label: "Sistem", icon: "⌘" },
  ];

  return (
    <div
      className="inline-flex items-center rounded-lg border border-border bg-surface-raised p-0.5"
      data-testid="theme-toggle-full"
      role="radiogroup"
      aria-label="Tema seçimi"
    >
      {opts.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => setTheme(o.value)}
          aria-pressed={theme === o.value}
          role="radio"
          aria-checked={theme === o.value}
          className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            theme === o.value
              ? "bg-surface-accent text-fg"
              : "text-fg-muted hover:text-fg"
          }`}
          data-testid={`theme-option-${o.value}`}
        >
          <span aria-hidden="true">{o.icon}</span>
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}
