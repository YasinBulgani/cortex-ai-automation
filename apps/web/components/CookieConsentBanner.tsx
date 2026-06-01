"use client";

/**
 * CookieConsentBanner — GDPR / KVKK uyumlu çerez onayı bileşeni.
 *
 * Davranış
 * ────────
 * • İlk ziyarette ekranın altında görünür.
 * • "Kabul Et" → tümünü kabul eder.
 * • "Yalnızca Zorunlu" → sadece zorunlu çerezlere izin verir.
 * • "Ayrıntılar" → granüler kategori seçimi panelini açar.
 * • Seçim localStorage'a yazılır (cortex_cookie_consent).
 * • Onaydan sonra banner kaybolur; kullanıcı /privacy sayfasından değiştirebilir.
 *
 * Kategori modeli
 * ───────────────
 * • necessary   — zorunlu, kapatılamaz
 * • analytics   — anonim kullanım analizi (isteğe bağlı)
 * • marketing   — retargeting / 3. taraf (isteğe bağlı)
 *
 * Bu bileşen GTM/GA entegrasyonu yapmaz — sadece onayla birlikte
 * window.cortexConsent event'i tetikler; harici entegrasyonlar onu dinler.
 */

import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export type ConsentCategories = {
  necessary: true;       // always true, cannot be disabled
  analytics: boolean;
  marketing: boolean;
};

const CONSENT_STORAGE_KEY = "cortex_cookie_consent";
const CONSENT_VERSION = "1";  // bump when categories change

const DEFAULT_DENIED: ConsentCategories = {
  necessary: true,
  analytics: false,
  marketing: false,
};

const ALL_ACCEPTED: ConsentCategories = {
  necessary: true,
  analytics: true,
  marketing: true,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function loadConsent(): ConsentCategories | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CONSENT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed.version !== CONSENT_VERSION) return null;  // re-prompt on version bump
    return parsed.categories as ConsentCategories;
  } catch {
    return null;
  }
}

function saveConsent(categories: ConsentCategories) {
  localStorage.setItem(
    CONSENT_STORAGE_KEY,
    JSON.stringify({ version: CONSENT_VERSION, categories, ts: Date.now() }),
  );
  // Notify external scripts (GTM, custom analytics, etc.)
  try {
    window.dispatchEvent(
      new CustomEvent("cortexConsent", { detail: categories }),
    );
  } catch {
    // Event not supported in very old browsers
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [draft, setDraft] = useState<ConsentCategories>({ ...DEFAULT_DENIED });

  useEffect(() => {
    const stored = loadConsent();
    if (!stored) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const handleAcceptAll = () => {
    saveConsent(ALL_ACCEPTED);
    setVisible(false);
  };

  const handleNecessaryOnly = () => {
    saveConsent(DEFAULT_DENIED);
    setVisible(false);
  };

  const handleSavePreferences = () => {
    saveConsent(draft);
    setVisible(false);
  };

  const toggleCategory = (key: keyof Omit<ConsentCategories, "necessary">) => {
    setDraft((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Çerez tercihleri"
      className="fixed bottom-0 left-0 right-0 z-[9999] border-t border-slate-700 bg-slate-900 p-4 shadow-2xl md:bottom-4 md:left-4 md:right-auto md:max-w-md md:rounded-2xl md:border"
    >
      <p className="mb-1 text-sm font-semibold text-white">🍪 Çerez Tercihleri</p>
      <p className="mb-4 text-xs leading-relaxed text-slate-400">
        Deneyiminizi iyileştirmek ve hizmetlerimizi geliştirmek için çerezler kullanıyoruz.
        Tercihlerinizi ayarlayabilir veya tümünü kabul edebilirsiniz.{" "}
        <a href="/privacy" className="underline hover:text-white">
          Gizlilik Politikası
        </a>
      </p>

      {/* Granular controls */}
      {showDetails && (
        <div className="mb-4 space-y-3 rounded-xl border border-slate-700 bg-slate-950 p-3">
          {/* Necessary — always on */}
          <ConsentRow
            label="Zorunlu Çerezler"
            desc="Oturum, güvenlik ve temel site işlevleri. Devre dışı bırakılamaz."
            checked
            disabled
          />
          {/* Analytics */}
          <ConsentRow
            label="Analitik Çerezler"
            desc="Anonim kullanım istatistikleri — hangi özelliklerin kullanıldığını anlamamıza yardımcı olur."
            checked={draft.analytics}
            onChange={() => toggleCategory("analytics")}
          />
          {/* Marketing */}
          <ConsentRow
            label="Pazarlama Çerezleri"
            desc="İlgi alanınıza göre içerik ve reklamlar için kullanılır."
            checked={draft.marketing}
            onChange={() => toggleCategory("marketing")}
          />
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          onClick={handleAcceptAll}
          className="flex-1 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 transition"
        >
          Tümünü Kabul Et
        </button>
        <button
          onClick={handleNecessaryOnly}
          className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 transition"
        >
          Yalnızca Zorunlu
        </button>
        {showDetails ? (
          <button
            onClick={handleSavePreferences}
            className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 transition"
          >
            Kaydet
          </button>
        ) : (
          <button
            onClick={() => setShowDetails(true)}
            className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 transition"
          >
            Ayrıntılar
          </button>
        )}
      </div>
    </div>
  );
}

// ── Sub-component ─────────────────────────────────────────────────────────────

function ConsentRow({
  label,
  desc,
  checked,
  disabled = false,
  onChange,
}: {
  label: string;
  desc: string;
  checked: boolean;
  disabled?: boolean;
  onChange?: () => void;
}) {
  const id = `consent-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 pt-0.5">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={onChange}
          className="h-4 w-4 cursor-pointer rounded accent-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>
      <label htmlFor={id} className={disabled ? "cursor-not-allowed" : "cursor-pointer"}>
        <p className="text-xs font-semibold text-white">{label}</p>
        <p className="text-[11px] text-slate-500">{desc}</p>
      </label>
    </div>
  );
}

// ── Hook for reading consent elsewhere in the app ─────────────────────────────

export function useConsentStatus(): ConsentCategories | null {
  const [consent, setConsent] = useState<ConsentCategories | null>(null);

  useEffect(() => {
    setConsent(loadConsent());
    const handler = (e: Event) => {
      setConsent((e as CustomEvent<ConsentCategories>).detail);
    };
    window.addEventListener("cortexConsent", handler);
    return () => window.removeEventListener("cortexConsent", handler);
  }, []);

  return consent;
}
