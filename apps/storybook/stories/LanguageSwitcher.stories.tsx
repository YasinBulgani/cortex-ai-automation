/**
 * Stories for the LanguageSwitcher component.
 *
 * The component requires I18nProvider; we wrap it inline in the decorators.
 */

import type { Meta, StoryObj } from "@storybook/react";
import React, { useState } from "react";

// ── Minimal I18n stub (avoids importing the full Next.js app) ─────────────────

type Locale = "tr" | "en";

const LABELS: Record<Locale, string> = { tr: "Türkçe", en: "English" };
const FLAGS: Record<Locale, string>  = { tr: "🇹🇷",    en: "🇬🇧" };

interface I18nCtx {
  locale: Locale;
  setLocale: (l: Locale) => void;
  locales: Locale[];
  localeLabel: (l: Locale) => string;
  localeFlag: (l: Locale) => string;
  t: (k: string) => string;
}

const I18nContext = React.createContext<I18nCtx | null>(null);

function useI18n() {
  const ctx = React.useContext(I18nContext);
  if (!ctx) throw new Error("No I18nContext");
  return ctx;
}

// ── Minimal LanguageSwitcher (no imports from app) ────────────────────────────

function SwitcherDemo({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, locales, localeLabel, localeFlag } = useI18n();

  const next = locales.find((l) => l !== locale) as Locale;

  return (
    <button
      onClick={() => setLocale(next)}
      title={`Switch to ${localeLabel(next)}`}
      className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-slate-400 transition
        bg-slate-800 hover:bg-slate-700 hover:text-slate-200"
    >
      <span>{localeFlag(locale)}</span>
      {!compact && <span className="uppercase tracking-wide text-xs">{locale}</span>}
    </button>
  );
}

function Provider({ children, initial = "tr" }: { children: React.ReactNode; initial?: Locale }) {
  const [locale, setLocale] = useState<Locale>(initial);
  return (
    <I18nContext.Provider
      value={{
        locale,
        setLocale,
        locales: ["tr", "en"],
        localeLabel: (l) => LABELS[l],
        localeFlag: (l) => FLAGS[l],
        t: (k) => k,
      }}
    >
      {children}
    </I18nContext.Provider>
  );
}

// ── Meta ──────────────────────────────────────────────────────────────────────

const meta: Meta<typeof SwitcherDemo> = {
  title: "App / LanguageSwitcher",
  component: SwitcherDemo,
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <Provider>
        <div className="flex items-center justify-center p-8 bg-slate-950 min-h-24">
          <Story />
        </div>
      </Provider>
    ),
  ],
  argTypes: {
    compact: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof SwitcherDemo>;

export const Default: Story = {
  args: { compact: false },
};

export const Compact: Story = {
  args: { compact: true },
};

export const StartingInEnglish: Story = {
  decorators: [
    (Story) => (
      <Provider initial="en">
        <div className="flex items-center justify-center p-8 bg-slate-950 min-h-24">
          <Story />
        </div>
      </Provider>
    ),
  ],
  args: { compact: false },
};

export const InNavBar: Story = {
  render: () => (
    <Provider>
      <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 w-80">
        <span className="text-sm font-semibold text-white">Neurex Management</span>
        <SwitcherDemo compact />
      </div>
    </Provider>
  ),
};
