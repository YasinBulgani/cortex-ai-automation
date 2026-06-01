"use client";

/**
 * LanguageSwitcher — compact TR/EN toggle for the app shell.
 *
 * Usage:
 *   <LanguageSwitcher />          // icon + label, medium size
 *   <LanguageSwitcher compact />  // flag only, small
 */

import { useI18n, type Locale } from "@/lib/i18n";

interface Props {
  /** Show only the flag emoji without the locale label. */
  compact?: boolean;
  /** Extra CSS classes for the wrapper. */
  className?: string;
}

export function LanguageSwitcher({ compact = false, className = "" }: Props) {
  const { locale, setLocale, locales, localeLabel, localeFlag } = useI18n();

  // Toggle between tr ↔ en when there are exactly 2 locales; otherwise show a
  // dropdown.
  if (locales.length === 2) {
    const next = locales.find((l) => l !== locale) as Locale;
    return (
      <button
        onClick={() => setLocale(next)}
        title={`Switch to ${localeLabel(next)}`}
        aria-label={`Switch language to ${localeLabel(next)}`}
        className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-slate-400 transition
          hover:bg-slate-800 hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2
          focus-visible:ring-teal-500 ${className}`}
      >
        <span aria-hidden="true">{localeFlag(locale)}</span>
        {!compact && (
          <span className="uppercase tracking-wide text-xs">{locale}</span>
        )}
      </button>
    );
  }

  // Dropdown for >2 locales
  return (
    <div className={`relative ${className}`}>
      <select
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        aria-label="Select language"
        className="appearance-none rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 pr-8
          text-sm text-slate-300 focus:border-teal-500 focus:outline-none"
      >
        {locales.map((l) => (
          <option key={l} value={l}>
            {localeFlag(l)} {localeLabel(l)}
          </option>
        ))}
      </select>
    </div>
  );
}
