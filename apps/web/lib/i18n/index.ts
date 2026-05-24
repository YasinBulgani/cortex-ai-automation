"use client";

/**
 * Cortex AI Automation — i18n infrastructure.
 *
 * Lightweight, no-dependency translation layer.
 *
 * Usage:
 *   const t = useT();
 *   t("common.save")          // "Kaydet" | "Save"
 *   t("management.status.passed") // "Geçti"  | "Passed"
 *
 * Language preference is stored in localStorage under `cortex_lang`
 * and defaults to the browser language (or "tr" for Turkish first).
 *
 * To wrap the whole app:
 *   <I18nProvider><App /></I18nProvider>
 *
 * The provider is already wired into apps/web/app/layout.tsx.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { tr, type TranslationDictionary } from "./locales/tr";
import { en } from "./locales/en";

// ── Types ─────────────────────────────────────────────────────────────────────

export type Locale = "tr" | "en";

/** Deeply nested key path for TranslationDictionary, e.g. "common.save" */
type DotPath<T, Prefix extends string = ""> = T extends string
  ? Prefix
  : {
      [K in keyof T & string]: DotPath<
        T[K],
        Prefix extends "" ? K : `${Prefix}.${K}`
      >;
    }[keyof T & string];

export type TranslationKey = DotPath<TranslationDictionary>;

/** Retrieve deeply nested value by dot-path */
function getByPath(obj: Record<string, unknown>, path: string): string {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const part of parts) {
    if (current == null || typeof current !== "object") return path;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current : path;
}

// ── Locales map ───────────────────────────────────────────────────────────────

const LOCALES: Record<Locale, TranslationDictionary> = { tr, en };

const LOCALE_LABELS: Record<Locale, string> = {
  tr: "Türkçe",
  en: "English",
};

const LOCALE_FLAG: Record<Locale, string> = {
  tr: "🇹🇷",
  en: "🇬🇧",
};

const STORAGE_KEY = "cortex_lang";

function detectLocale(): Locale {
  if (typeof window === "undefined") return "tr";
  const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
  if (stored && stored in LOCALES) return stored;
  const browser = navigator.language?.slice(0, 2).toLowerCase();
  return browser === "en" ? "en" : "tr";
}

// ── Context ───────────────────────────────────────────────────────────────────

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
  locales: Locale[];
  localeLabel: (l: Locale) => string;
  localeFlag: (l: Locale) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("tr");

  // Hydrate from localStorage on first client render
  useEffect(() => {
    setLocaleState(detectLocale());
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(STORAGE_KEY, l);
    // Update html lang attribute for accessibility / SEO
    document.documentElement.lang = l;
  }, []);

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>): string => {
      const dict = LOCALES[locale] ?? tr;
      let value = getByPath(dict as unknown as Record<string, unknown>, key);
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          value = value.replace(new RegExp(`\\{\\{${k}\\}\\}`, "g"), String(v));
        }
      }
      return value;
    },
    [locale],
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      t,
      locales: ["tr", "en"] as Locale[],
      localeLabel: (l) => LOCALE_LABELS[l],
      localeFlag: (l) => LOCALE_FLAG[l],
    }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * Returns the `t()` translation function for the current locale.
 *
 * @example
 *   const t = useT();
 *   <button>{t("common.save")}</button>
 */
export function useT(): I18nContextValue["t"] {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useT must be used inside <I18nProvider>");
  return ctx.t;
}

/**
 * Returns the full i18n context (locale, setLocale, t, etc.).
 */
export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}
