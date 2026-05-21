"use client";

import { useEffect, useState } from "react";

/**
 * PWA bootstrap:
 *  - Production'da /sw.js'i register et
 *  - beforeinstallprompt'u yakala, dismissable install button göster
 *  - Tıklayınca prompt.prompt() çağır
 *
 * Development'ta SW kaydetmez (hot reload + cache conflict önler).
 */
export function PWARegister() {
  const [installEvent, setInstallEvent] = useState<any>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Service worker — production only
    const isDev =
      process.env.NODE_ENV === "development" ||
      window.location.hostname === "localhost" ||
      window.location.hostname.startsWith("127.");
    if (!isDev && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch((err) => {
        // Silently swallow — SW failures should not break the app
        if (process.env.NODE_ENV !== "test") {
          // eslint-disable-next-line no-console
          console.warn("SW registration failed:", err);
        }
      });
    }

    // Install prompt capture
    const onPrompt = (e: Event) => {
      e.preventDefault();
      // Restore prior dismissal preference from localStorage
      try {
        if (localStorage.getItem("neurex_pwa_dismissed") === "1") {
          setDismissed(true);
          return;
        }
      } catch {
        /* localStorage may be unavailable in sandboxed contexts */
      }
      setInstallEvent(e);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  if (!installEvent || dismissed) return null;

  const onInstall = async () => {
    try {
      await installEvent.prompt();
      const choice = await installEvent.userChoice;
      if (choice?.outcome !== "accepted") {
        try {
          localStorage.setItem("neurex_pwa_dismissed", "1");
        } catch {
          /* ignore */
        }
      }
    } finally {
      setInstallEvent(null);
    }
  };

  const onDismiss = () => {
    try {
      localStorage.setItem("neurex_pwa_dismissed", "1");
    } catch {
      /* ignore */
    }
    setDismissed(true);
    setInstallEvent(null);
  };

  return (
    <div
      className="fixed bottom-4 right-4 z-50 max-w-xs rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-2xl"
      data-testid="pwa-install-prompt"
    >
      <p className="text-sm font-medium text-white">Neurex'i uygulama olarak yükle</p>
      <p className="mt-1 text-xs text-slate-400">
        Hızlı erişim için ana ekrana ekleyebilirsin.
      </p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={onInstall}
          data-testid="pwa-install-btn"
          className="flex-1 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
        >
          Yükle
        </button>
        <button
          type="button"
          onClick={onDismiss}
          data-testid="pwa-dismiss-btn"
          className="rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          Şimdi değil
        </button>
      </div>
    </div>
  );
}
