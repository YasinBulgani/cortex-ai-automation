"use client";

import { useState } from "react";
import Link from "next/link";

import { useNotifications, type Notification } from "@/lib/useNotifications";

const LEVEL_DOT: Record<Notification["level"], string> = {
  info: "bg-sky-400",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  error: "bg-red-400",
};

const LEVEL_LABEL: Record<Notification["level"], string> = {
  info: "Bilgi",
  success: "Başarı",
  warning: "Uyarı",
  error: "Hata",
};

function formatRelative(ts: number): string {
  const diff = Date.now() - ts;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s önce`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}dk önce`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour}sa önce`;
  const day = Math.floor(hour / 24);
  return `${day}g önce`;
}

/**
 * Full in-app notification center.
 *
 * Mevcut NotificationBell sadece WebSocket mesajlarını gösteriyor; bu component
 * persisted notifications + read/unread state + filter + URL navigation sunar.
 */
export function NotificationCenter() {
  const { items, unreadCount, markRead, markAllRead, remove, clear } = useNotifications();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const visible = filter === "unread" ? items.filter((n) => !n.read) : items;

  return (
    <div className="relative" data-testid="notification-center">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="relative flex h-8 w-8 items-center justify-center rounded-full hover:bg-black/5 dark:hover:bg-white/10"
        aria-label="Bildirim merkezi"
        data-testid="notification-center-toggle"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="h-5 w-5"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span
            className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white"
            data-testid="notification-center-badge"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            data-testid="notification-center-backdrop"
          />
          <div
            className="absolute right-0 top-10 z-50 w-96 max-w-[calc(100vw-2rem)] rounded-xl border border-slate-800 bg-slate-900 shadow-2xl"
            data-testid="notification-center-panel"
          >
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <span className="text-sm font-semibold text-white">Bildirimler</span>
              <div className="flex items-center gap-2 text-xs">
                <button
                  type="button"
                  onClick={() => setFilter(filter === "all" ? "unread" : "all")}
                  className="rounded-md border border-slate-700 px-2 py-1 text-slate-300 hover:bg-slate-800"
                  data-testid="notification-center-filter"
                >
                  {filter === "all" ? "Sadece okunmamış" : "Tümü"}
                </button>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={markAllRead}
                    className="text-slate-400 hover:text-white"
                    data-testid="notification-center-mark-all-read"
                  >
                    Tümünü oku
                  </button>
                )}
                {items.length > 0 && (
                  <button
                    type="button"
                    onClick={clear}
                    className="text-slate-400 hover:text-white"
                    data-testid="notification-center-clear"
                  >
                    Temizle
                  </button>
                )}
              </div>
            </div>

            <div className="max-h-96 overflow-auto">
              {visible.length === 0 ? (
                <p
                  className="py-12 text-center text-xs text-slate-500"
                  data-testid="notification-center-empty"
                >
                  {filter === "unread" ? "Okunmamış bildirim yok" : "Bildirim yok"}
                </p>
              ) : (
                visible.map((n) => {
                  const content = (
                    <div className="flex items-start gap-3">
                      <span
                        className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${LEVEL_DOT[n.level]}`}
                        aria-hidden="true"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className={`text-xs font-medium ${
                              n.read ? "text-slate-400" : "text-white"
                            }`}
                          >
                            {n.title}
                          </span>
                          <span className="flex-shrink-0 text-[10px] text-slate-500">
                            {formatRelative(n.timestamp)}
                          </span>
                        </div>
                        {n.body && (
                          <p className="mt-0.5 line-clamp-2 text-xs text-slate-400">
                            {n.body}
                          </p>
                        )}
                        {n.source && (
                          <p className="mt-0.5 text-[10px] text-slate-500">
                            <span className="opacity-60">{LEVEL_LABEL[n.level]} · </span>
                            {n.source}
                          </p>
                        )}
                      </div>
                    </div>
                  );

                  const wrapperClass =
                    "border-b border-slate-800 px-4 py-3 last:border-0 hover:bg-slate-800/40 cursor-pointer";

                  return (
                    <div
                      key={n.id}
                      className={wrapperClass}
                      data-testid={`notification-item-${n.id}`}
                      onClick={(e) => {
                        // Remove button click bubbles too — only mark-read here, not for the X click
                        if ((e.target as HTMLElement).closest("[data-notification-remove]")) {
                          return;
                        }
                        markRead(n.id);
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        {n.url ? (
                          <Link href={n.url} className="flex-1">
                            {content}
                          </Link>
                        ) : (
                          <div className="flex-1">{content}</div>
                        )}
                        <button
                          type="button"
                          data-notification-remove
                          onClick={(e) => {
                            e.stopPropagation();
                            remove(n.id);
                          }}
                          className="ml-2 text-slate-600 hover:text-slate-300"
                          aria-label="Bildirimi sil"
                          data-testid={`notification-remove-${n.id}`}
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
