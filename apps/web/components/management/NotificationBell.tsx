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
import { useEffect, useState } from "react";

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
import { useCurrentUser } from "@/lib/hooks/use-auth";
import { Skeleton } from "@/components/ui/skeleton";

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
  // Hydration güvenliği: ilk client render server ile aynı olsun (rozet yok).
  // unread sayısı client-only kaynaklardan (query cache/backend-first) gelir.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const { user } = useCurrentUser();
  const { data: counts } = useUnreadCount();
  const { data: notifications = [], isLoading, isError } = useNotifications({
    unreadOnly,
    projectId,
  });
  const markRead = useMarkRead();
  const markArchived = useMarkArchived();
  const markAllRead = useMarkAllRead();
  const digest = useNotificationDigest("24h", showDigest);

  // Stream is only opened when authenticated; hook cleanup closes EventSource on unmount.
  useNotificationStream(!!user);

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
        {mounted && unread > 0 ? (
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
                <div className="space-y-2 p-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-3/4" />
                </div>
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
        <div className="flex items-start gap-2">
          <span className={`mt-0.5 ${kindIconColor(notification.kind)}`}>
            <KindIcon kind={notification.kind} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold text-white">{notification.title}</p>
            {notification.body ? (
              <p className="mt-0.5 line-clamp-2 text-[11px] text-slate-300">{notification.body}</p>
            ) : null}
            <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">
              {notification.kind} · {new Date(notification.created_at).toLocaleString()}
            </p>
          </div>
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

function KindIcon({ kind }: { kind: string }) {
  if (kind.includes("fail") || kind.includes("error"))
    return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
  if (kind.includes("success") || kind.includes("complete") || kind.includes("pass"))
    return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
  if (kind.includes("warn") || kind.includes("flaky"))
    return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>;
  if (kind.includes("approval") || kind.includes("review") || kind.includes("action"))
    return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>;
  if (kind.includes("ai") || kind.includes("generate"))
    return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>;
  // default
  return <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
}

function kindIconColor(kind: string): string {
  if (kind.includes("fail") || kind.includes("error")) return "text-red-400";
  if (kind.includes("success") || kind.includes("complete") || kind.includes("pass")) return "text-emerald-400";
  if (kind.includes("warn") || kind.includes("flaky")) return "text-amber-400";
  if (kind.includes("approval") || kind.includes("review") || kind.includes("action")) return "text-blue-400";
  if (kind.includes("ai") || kind.includes("generate")) return "text-violet-400";
  return "text-slate-400";
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
