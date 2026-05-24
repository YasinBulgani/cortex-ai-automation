/**
 * Stories for the CookieConsentBanner component.
 *
 * The banner reads/writes localStorage and fires CustomEvents.
 * We clear localStorage in each story so it renders unconditionally.
 */

import type { Meta, StoryObj } from "@storybook/react";
import React, { useEffect, useState } from "react";

// ── Inline copy of the CookieConsentBanner (avoids Next.js app context) ───────

type ConsentCategories = {
  necessary: true;
  analytics: boolean;
  marketing: boolean;
};

const CONSENT_STORAGE_KEY = "cortex_cookie_consent";
const CONSENT_VERSION = "1";

const DEFAULT_DENIED: ConsentCategories = { necessary: true, analytics: false, marketing: false };
const ALL_ACCEPTED: ConsentCategories = { necessary: true, analytics: true, marketing: true };

function saveConsent(categories: ConsentCategories) {
  localStorage.setItem(
    CONSENT_STORAGE_KEY,
    JSON.stringify({ version: CONSENT_VERSION, categories, ts: Date.now() }),
  );
  try {
    window.dispatchEvent(new CustomEvent("cortexConsent", { detail: categories }));
  } catch {}
}

function ConsentRow({
  label, desc, checked, disabled = false, onChange,
}: {
  label: string; desc: string; checked: boolean; disabled?: boolean; onChange?: () => void;
}) {
  const id = `consent-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 pt-0.5">
        <input id={id} type="checkbox" checked={checked} disabled={disabled}
          onChange={onChange}
          className="h-4 w-4 cursor-pointer rounded accent-violet-500 disabled:cursor-not-allowed disabled:opacity-50" />
      </div>
      <label htmlFor={id} className={disabled ? "cursor-not-allowed" : "cursor-pointer"}>
        <p className="text-xs font-semibold text-white">{label}</p>
        <p className="text-[11px] text-slate-500">{desc}</p>
      </label>
    </div>
  );
}

function CookieConsentBannerDemo({ forceShow = true }: { forceShow?: boolean }) {
  const [visible, setVisible] = useState(forceShow);
  const [showDetails, setShowDetails] = useState(false);
  const [draft, setDraft] = useState<ConsentCategories>({ ...DEFAULT_DENIED });
  const [lastSaved, setLastSaved] = useState<ConsentCategories | null>(null);

  if (!visible) {
    return (
      <div className="min-h-screen bg-slate-950 p-8 flex flex-col items-center justify-center gap-4">
        <p className="text-emerald-400 font-semibold">✓ Onay kaydedildi</p>
        {lastSaved && (
          <pre className="text-xs text-slate-400 bg-slate-900 rounded-xl p-4 font-mono">
            {JSON.stringify(lastSaved, null, 2)}
          </pre>
        )}
        <button
          onClick={() => { setVisible(true); setDraft({ ...DEFAULT_DENIED }); setShowDetails(false); }}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-500"
        >
          Tekrar Göster
        </button>
      </div>
    );
  }

  const handleAcceptAll = () => { setLastSaved(ALL_ACCEPTED); saveConsent(ALL_ACCEPTED); setVisible(false); };
  const handleNecessaryOnly = () => { setLastSaved(DEFAULT_DENIED); saveConsent(DEFAULT_DENIED); setVisible(false); };
  const handleSavePreferences = () => { setLastSaved(draft); saveConsent(draft); setVisible(false); };
  const toggleCategory = (key: keyof Omit<ConsentCategories, "necessary">) =>
    setDraft((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="min-h-screen bg-slate-950 p-8 relative">
      {/* Simulated page content */}
      <p className="text-slate-400 text-sm">← sayfa içeriği buradadır</p>

      {/* Banner */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Çerez tercihleri"
        className="fixed bottom-4 left-4 z-[9999] max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-4 shadow-2xl"
      >
        <p className="mb-1 text-sm font-semibold text-white">🍪 Çerez Tercihleri</p>
        <p className="mb-4 text-xs leading-relaxed text-slate-400">
          Deneyiminizi iyileştirmek için çerezler kullanıyoruz.{" "}
          <a href="#" className="underline hover:text-white">Gizlilik Politikası</a>
        </p>

        {showDetails && (
          <div className="mb-4 space-y-3 rounded-xl border border-slate-700 bg-slate-950 p-3">
            <ConsentRow label="Zorunlu Çerezler" desc="Oturum, güvenlik. Devre dışı bırakılamaz." checked disabled />
            <ConsentRow label="Analitik Çerezler" desc="Anonim kullanım istatistikleri." checked={draft.analytics}
              onChange={() => toggleCategory("analytics")} />
            <ConsentRow label="Pazarlama Çerezleri" desc="İlgi alanına göre reklamlar." checked={draft.marketing}
              onChange={() => toggleCategory("marketing")} />
          </div>
        )}

        <div className="flex flex-col gap-2 sm:flex-row">
          <button onClick={handleAcceptAll}
            className="flex-1 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 transition">
            Tümünü Kabul Et
          </button>
          <button onClick={handleNecessaryOnly}
            className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 transition">
            Yalnızca Zorunlu
          </button>
          {showDetails ? (
            <button onClick={handleSavePreferences}
              className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 transition">
              Kaydet
            </button>
          ) : (
            <button onClick={() => setShowDetails(true)}
              className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 transition">
              Ayrıntılar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Meta ──────────────────────────────────────────────────────────────────────

const meta: Meta<typeof CookieConsentBannerDemo> = {
  title: "Compliance/CookieConsentBanner",
  component: CookieConsentBannerDemo,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component: `
GDPR/KVKK-uyumlu çerez onayı bileşeni.

- Zorunlu + opsiyonel kategori ayrımı
- "Ayrıntılar" butonu → granüler seçim
- localStorage'a versiyonlu kayıt
- \`window.cortexConsent\` CustomEvent ile harici entegrasyon
        `,
      },
    },
  },
  decorators: [
    (Story) => (
      <div className="dark">
        <Story />
      </div>
    ),
  ],
  beforeEach: () => {
    localStorage.removeItem(CONSENT_STORAGE_KEY);
  },
};

export default meta;

type Story = StoryObj<typeof CookieConsentBannerDemo>;

// ── Stories ───────────────────────────────────────────────────────────────────

/** Default: first visit — banner visible with all 3 action buttons. */
export const Default: Story = {
  args: { forceShow: true },
};

/** With details panel open — shows granular category toggles. */
export const WithDetailPanel: Story = {
  args: { forceShow: true },
  play: async ({ canvasElement }) => {
    const details = canvasElement.querySelector<HTMLButtonElement>('button:last-of-type');
    if (details?.textContent?.includes("Ayrıntılar")) details.click();
  },
};

/** Mobile viewport — banner fills screen bottom. */
export const MobileViewport: Story = {
  args: { forceShow: true },
  parameters: {
    viewport: { defaultViewport: "mobile1" },
  },
};
