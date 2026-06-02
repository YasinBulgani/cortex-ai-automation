"use client";

/**
 * Shared global Notification Bell for the Neurex Management (M-45) inbox.
 *
 * Promoted from `apps/web/app/(dashboard)/p/[projectId]/management/_components/NotificationBell.tsx`
 * so it can be mounted in the global AppShell without project context.
 *
 * The legacy WebSocket-only bell at `@/components/NotificationBell` is
 * deprecated — keep importing from `@/components/management/NotificationBell`.
 */

import Link from "next/link";
import { useState } from "react";

import {
  type MgmtNotification,
  useMarkAllRead,
  useMarkArchived,
  useMarkRead,
  useNotificationStream,
  useNotifications,
  useNotificationDigest,
  useUnreadCount,
} from "@/lib/hooks/use-mgmt-notifications";

export interface NotificationBellProps {
  /** Optional class for the trigger button. */
  className?: string;
  /** When provided, only notifications for this project are shown. */
  projectId?: string | null;
}

export function NotificationBell({ className, projectId = null }: NotificationBellProps) {
  const [open, setOpen] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [showDigest, setShowDigest] = useState(false);
  const { data: counts } = useUnreadCount();
  const { data: notifications = [], isLoading, isError } = useNotifications({
    unreadOnly,
    projectId,
  });
  const markRead = useMarkRead();
  const markArchived = useMarkArchived();
  const markAllRead = useMarkAllRead();
  const digest = useNotificationDigest("24h", showDigest);

  useNotificationStream(true);

  const unread = counts?.unread ?? 0;

  return (
    <div className={`relative ${className ?? ""}`}>
      <button
        type="button"
        aria-label={`Notifications${unread > 0 ? `, ${unread} unread` : ""}`}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-slate-200 transition hover:bg-slate-800"
      >
        <BellIcon />
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1 inline-flex min-w-[18px] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <>
          <div
            aria-hidden
            className="fixed inset-0 z-30"
            onClick={() => setOpen(false)}
          />
          <div
            role="dialog"
            aria-label="Notifications"
            className="absolute right-0 z-40 mt-2 w-[360px] max-w-[90vw] rounded-lg border border-slate-800 bg-slate-950 p-3 shadow-xl"
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">Notifications</h3>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className={`text-[11px] ${
                    showDigest ? "text-teal-300" : "text-slate-400 hover:text-slate-200"
                  }`}
                  onClick={() => setShowDigest((v) => !v)}
                  aria-pressed={showDigest}
                >
                  {showDigest ? "Hide AI digest" : "AI Özet (24h)"}
                </button>
                <button
                  type="button"
                  className={`text-[11px] ${
                    unreadOnly ? "text-teal-300" : "text-slate-400 hover:text-slate-200"
                  }`}
                  onClick={() => setUnreadOnly((v) => !v)}
                >
                  {unreadOnly ? "Showing unread" : "Show unread only"}
                </button>
                <button
                  type="button"
                  className="text-[11px] text-slate-400 hover:text-slate-200"
                  onClick={() => void markAllRead.mutateAsync()}
                  disabled={markAllRead.isPending || unread === 0}
                >
                  Mark all read
                </button>
              </div>
            </div>

            {showDigest ? (
              <div className="mb-3 rounded-md border border-teal-500/30 bg-teal-500/5 p-2">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-teal-300">
                  AI digest — last 24h
                </p>
                {digest.isLoading ? (
                  <p className="text-[11px] text-slate-400">Generating…</p>
                ) : digest.data?.groups?.length ? (
                  <ul className="space-y-1">
                    {digest.data.groups.map((g, i) => (
                      <li key={`${g.theme}-${i}`} className="text-[11px] text-slate-200">
                        <span className="font-semibold text-teal-200">{g.theme}</span>{" "}
                        <span className="text-slate-400">({g.count})</span> — {g.oneLine}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[11px] text-slate-500">No activity in window.</p>
                )}
              </div>
            ) : null}

            <div className="max-h-[420px] overflow-y-auto pr-1">
              {isError ? (
                <p className="rounded border border-rose-800 bg-rose-950/30 p-3 text-xs text-rose-200">
                  Failed to load notifications.
                </p>
              ) : isLoading ? (
                <p className="px-2 py-4 text-xs text-slate-500">Loading…</p>
              ) : notifications.length === 0 ? (
                <p className="px-2 py-6 text-center text-xs text-slate-500">
                  {unreadOnly ? "No unread notifications." : "Nothing here yet."}
                </p>
              ) : (
                <ul className="space-y-1">
                  {notifications.map((n) => (
                    <li key={n.id}>
                      <NotificationRow
                        notification={n}
                        onRead={() => markRead.mutateAsync(n.id)}
                        onArchive={() => markArchived.mutateAsync(n.id)}
                        onNavigate={() => setOpen(false)}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="mt-3 border-t border-slate-800 pt-2 text-right">
              <Link
                href="/management/notifications"
                className="text-[11px] text-teal-300 hover:text-teal-100"
                onClick={() => setOpen(false)}
              >
                View all →
              </Link>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

interface NotificationRowProps {
  notification: MgmtNotification;
  onRead: () => Promise<MgmtNotification>;
  onArchive: () => Promise<MgmtNotification>;
  onNavigate: () => void;
}

function NotificationRow({
  notification,
  onRead,
  onArchive,
  onNavigate,
}: NotificationRowProps) {
  const isUnread = notification.read_at == null;
  const tone =
    notification.severity === "critical"
      ? "border-rose-700 bg-rose-950/30"
      : notification.severity === "warning"
        ? "border-amber-700 bg-amber-950/30"
        : "border-slate-800 bg-slate-900";

  return (
    <div
      className={`rounded-md border ${tone} p-2 transition ${
        isUnread ? "ring-1 ring-teal-500/30" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-white">{notification.title}</p>
          {notification.body ? (
            <p className="mt-0.5 line-clamp-2 text-[11px] text-slate-300">{notification.body}</p>
          ) : null}
          <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">
            {notification.kind} · {new Date(notification.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {isUnread ? (
            <button
              type="button"
              className="text-[10px] text-teal-300 hover:text-teal-100"
              onClick={() => void onRead()}
            >
              Mark read
            </button>
          ) : null}
          <button
            type="button"
            className="text-[10px] text-slate-400 hover:text-slate-200"
            onClick={() => void onArchive()}
          >
            Archive
          </button>
        </div>
      </div>
      {notification.link_path ? (
        <div className="mt-1.5">
          <Link
            href={notification.link_path}
            onClick={() => {
              if (isUnread) void onRead();
              onNavigate();
            }}
            className="text-[11px] text-teal-300 hover:text-teal-100"
          >
            Open →
          </Link>
        </div>
      ) : null}
    </div>
  );
}

function BellIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9z" />
      <path d="M10 21a2 2 0 0 0 4 0" />
    </svg>
  );
}
