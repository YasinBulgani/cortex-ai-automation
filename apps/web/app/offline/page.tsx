"use client";

import { useEffect, useState } from "react";

export default function OfflinePage() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    setOnline(typeof navigator !== "undefined" && navigator.onLine);
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center text-slate-100"
      data-testid="offline-page"
    >
      <div className="space-y-4 max-w-md">
        <div className="mx-auto h-16 w-16 rounded-full bg-slate-800 flex items-center justify-center text-3xl">
          📡
        </div>
        <h1 className="text-2xl font-bold">İnternet bağlantısı yok</h1>
        <p className="text-sm text-slate-400">
          Görünüşe göre çevrimdışısın. Bağlantı geri geldiğinde sayfayı otomatik
          yenilemeyi deneyeceğiz.
        </p>
        <div className="flex justify-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            data-testid="offline-retry"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
          >
            Tekrar dene
          </button>
        </div>
        {online && (
          <div
            className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300"
            data-testid="offline-back-online"
          >
            ✓ Bağlantı kuruldu — sayfayı yenileyebilirsin
          </div>
        )}
      </div>
    </div>
  );
}
