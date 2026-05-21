"use client";

import { useEffect, useState } from "react";
import { Kbd, KbdGroup } from "@/components/ui/kbd";
import { cn } from "@/lib/utils";

/**
 * OnboardingTour — ilk girişte gösterilen 4 adımlı mini tur.
 *
 * Adımlar:
 *   1. Hoşgeldin (genel)
 *   2. Cmd+K command palette
 *   3. Cmd+J AI asistan
 *   4. Ürün picker (sidebar logo)
 *
 * Bir kere kapatılınca localStorage'a kaydeder, bir daha gösterilmez.
 * Sıfırlamak için: localStorage.removeItem('neurex_onboarding_done')
 */

const STORAGE_KEY = "neurex_onboarding_done";

const STEPS = [
  {
    title: "Neurex QA'a Hoş Geldin",
    description: "AI destekli kalite operasyon platformu. Sana platformu hızlı tanıtayım — 30 saniye sürer.",
    illustration: "👋",
    cta: "Başla",
  },
  {
    title: "Her şey klavyeden",
    description: "İstediğin yere klavyeden ulaş. Sayfa değiştir, proje aç, komut çalıştır.",
    illustration: "⌘",
    hint: <KbdGroup><Kbd>⌘</Kbd><Kbd>K</Kbd></KbdGroup>,
    cta: "Sonraki",
  },
  {
    title: "AI her zaman yanında",
    description: "Bağlama duyarlı AI asistan. Bulunduğun sayfayı görür, ilgili önerileri sunar.",
    illustration: "✨",
    hint: <KbdGroup><Kbd>⌘</Kbd><Kbd>J</Kbd></KbdGroup>,
    cta: "Sonraki",
  },
  {
    title: "Ürün odağını seç",
    description: "Mobile, Web, Service... Sol üstte logo altından ürün ailesini değiştir, sidebar otomatik adapte olur.",
    illustration: "🎯",
    cta: "Anladım, kullanmaya başla",
  },
] as const;

export function OnboardingTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      // Sayfayı yüklediken kısa süre sonra aç
      const t = setTimeout(() => setOpen(true), 800);
      return () => clearTimeout(t);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    setOpen(false);
  };

  const next = () => {
    if (step < STEPS.length - 1) setStep(s => s + 1);
    else dismiss();
  };

  if (!open) return null;

  const cur = STEPS[step];
  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div
      className="fixed inset-0 z-modal flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in"
      onClick={dismiss}
      role="dialog"
      aria-labelledby="onboarding-title"
    >
      <div
        className="relative w-full max-w-md rounded-2xl border border-border-strong bg-surface-overlay p-7 shadow-xl animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Progress */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-surface-base rounded-t-2xl overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-indigo-500 transition-all duration-slow"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Skip button */}
        <button
          type="button"
          onClick={dismiss}
          className="absolute top-3 right-3 text-fg-subtle hover:text-fg transition-colors text-xs"
        >
          Atla
        </button>

        {/* Content */}
        <div className="text-center pt-3">
          <div className="mb-5 flex h-20 w-20 mx-auto items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 text-4xl">
            {cur.illustration}
          </div>
          <h2 id="onboarding-title" className="text-lg font-bold text-fg mb-2">
            {cur.title}
          </h2>
          <p className="text-sm text-fg-muted leading-relaxed mb-5">
            {cur.description}
          </p>
          {"hint" in cur && cur.hint && (
            <div className="mb-5 flex items-center justify-center gap-2 text-xs text-fg-subtle">
              <span>kısayol:</span>{cur.hint}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex gap-1">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className={cn(
                  "h-1.5 w-1.5 rounded-full transition-colors",
                  i === step ? "bg-brand-primary" : i < step ? "bg-brand-primary/40" : "bg-surface-accent"
                )}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={next}
            className="rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
            autoFocus
          >
            {cur.cta}
          </button>
        </div>
      </div>
    </div>
  );
}
