"use client";

import { useEffect, useState } from "react";
import { registerServiceWorker, requestNotificationPermission, subscribeToPush } from "@/lib/pwa";
import { Bell, Download, X } from "lucide-react";

/**
 * PWA bootstrap:
 *  - Production'da /sw.js'i register et
 *  - beforeinstallprompt'u yakala, dismissable install button göster
 *  - Push notifications + subscription setup
 *  - Service worker controller listener
 *
 * Development'ta SW kaydetmez (hot reload + cache conflict önler).
 */
export function PWARegister() {
  const [installEvent, setInstallEvent] = useState<any>(null);
  const [dismissed, setDismissed] = useState(false);
  const [notificationEnabled, setNotificationEnabled] = useState(false);
  const [swReady, setSwReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Service worker registration
    const isDev =
      process.env.NODE_ENV === "development" ||
      window.location.hostname === "localhost" ||
      window.location.hostname.startsWith("127.");

    if (isDev) {
      // Clean up caches in development
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker
          .getRegistrations()
          .then((registrations) => Promise.all(registrations.map((r) => r.unregister())))
          .catch(() => {});
      }
      if ("caches" in window) {
        caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k)))).catch(() => {});
      }
    } else {
      // Register SW in production
      registerServiceWorker()
        .then((reg) => {
          if (reg) {
            setSwReady(true);
            // Listen for controller change (SW update)
            navigator.serviceWorker.addEventListener("controllerchange", () => {
              console.log("Service Worker updated");
            });
          }
        })
        .catch((err) => {
          if (process.env.NODE_ENV !== "test") {
            console.warn("SW registration failed:", err);
          }
        });
    }

    // Install prompt capture
    const onPrompt = (e: Event) => {
      e.preventDefault();
      try {
        if (localStorage.getItem("neurex_pwa_dismissed") === "1") {
          setDismissed(true);
          return;
        }
      } catch {
        /* ignore */
      }
      setInstallEvent(e);
    };

    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  // Check notification permission on mount
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setNotificationEnabled(Notification.permission === "granted");
    }
  }, []);

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

  const onEnableNotifications = async () => {
    try {
      const permission = await requestNotificationPermission();
      if (permission === "granted" && swReady) {
        // Subscribe to push (requires VAPID key from backend)
        const vapidKey = process.env.NEXT_PUBLIC_VAPID_KEY;
        if (vapidKey) {
          try {
            await subscribeToPush(vapidKey);
          } catch (err) {
            console.error("Push subscription failed:", err);
          }
        }
        setNotificationEnabled(true);
      }
    } catch (err) {
      console.error("Notification permission request failed:", err);
    }
  };

  if (!installEvent && dismissed) return null;

  if (!installEvent) {
    // Show minimal notification badge when notifications are disabled
    if (!notificationEnabled && swReady && Notification && Notification.permission === "default") {
      return (
        <div
          className="fixed bottom-4 left-4 z-50 rounded-lg border border-amber-700 bg-amber-900/50 p-3 shadow-lg"
          data-testid="pwa-notification-prompt"
        >
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-amber-300" />
            <div className="text-sm text-amber-100">
              <p className="font-medium">Bildirimlerden haberdar ol</p>
              <p className="mt-0.5 text-xs text-amber-200">Önemli güncellemeleri kaçırmayın</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onEnableNotifications}
                className="rounded-md bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-500"
              >
                Etkinleştir
              </button>
              <button
                type="button"
                onClick={onDismiss}
                className="text-amber-300 hover:text-amber-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div
      className="fixed bottom-4 right-4 z-50 max-w-xs rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-2xl"
      data-testid="pwa-install-prompt"
    >
      <div className="flex items-start gap-3">
        <Download className="mt-1 h-5 w-5 text-indigo-400 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-white">Neurex'i uygulama olarak yükle</p>
          <p className="mt-1 text-xs text-slate-400">
            Hızlı erişim için ana ekrana ekleyebilirsin.
          </p>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={onInstall}
          data-testid="pwa-install-btn"
          className="flex-1 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 transition-colors"
        >
          Yükle
        </button>
        <button
          type="button"
          onClick={onDismiss}
          data-testid="pwa-dismiss-btn"
          className="rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 transition-colors"
        >
          Şimdi değil
        </button>
      </div>
    </div>
  );
}
