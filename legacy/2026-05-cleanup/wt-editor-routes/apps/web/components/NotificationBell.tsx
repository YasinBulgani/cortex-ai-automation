"use client";
import { useState } from "react";
import { useWebSocket } from "@/lib/useWebSocket";

export function NotificationBell() {
  const { messages, connected, clearMessages } = useWebSocket();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="relative flex h-8 w-8 items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10"
        title={connected ? "Bildirimler (bağlı)" : "Bildirimler (bağlantı yok)"}
        aria-label="Bildirimler"
        data-testid="header-btn-notifications"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        {messages.length > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
            {messages.length > 9 ? "9+" : messages.length}
          </span>
        )}
        <span className={`absolute bottom-0 right-0 h-2 w-2 rounded-full border border-bg ${connected ? "bg-green-500" : "bg-gray-400"}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border border-slate-800 bg-slate-900 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <span className="text-sm font-semibold">Bildirimler</span>
              <button
                type="button"
                onClick={() => { clearMessages(); }}
                className="text-xs text-slate-400 hover:text-white"
              >
                Temizle
              </button>
            </div>
            <div className="max-h-80 overflow-auto">
              {messages.length === 0 ? (
                <p className="py-8 text-center text-xs text-slate-400">Bildirim yok</p>
              ) : (
                messages.slice(0, 20).map((msg, i) => (
                  <div key={i} className="border-b border-slate-800 px-4 py-3 last:border-0">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full flex-shrink-0 ${
                        msg.type.includes("fail") || msg.type.includes("error") ? "bg-red-400" :
                        msg.type.includes("complete") || msg.type.includes("success") ? "bg-green-400" :
                        "bg-blue-400"
                      }`} />
                      <span className="text-xs font-medium text-white">{msg.type.replace(/\./g, " ")}</span>
                      <span className="ml-auto text-[10px] text-slate-400">
                        {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString("tr-TR") : ""}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-400 line-clamp-2">
                      {typeof msg.payload === "object"
                        ? JSON.stringify(msg.payload).slice(0, 100)
                        : String(msg.payload)}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
