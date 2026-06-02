"use client";

import Link from "next/link";
import { useState } from "react";

import {
  type MgmtNotification,
  useMarkAllRead,
  useMarkArchived,
  useMarkRead,
  useNotifications,
  useUnreadCount,
} from "@/lib/hooks/use-mgmt-notifications";

type Filter = "all" | "unread" | "archived";

export default function ManagementNotificationsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const { data: counts } = useUnreadCount();
  const { data: notifications = [], isLoading, isError, error } = useNotifications({
    unreadOnly: filter === "unread",
    includeArchived: filter === "archived",
    limit: 200,
  });
  const markRead = useMarkRead();
  const markArchived = useMarkArchived();
  const markAllRead = useMarkAllRead();

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <header className="mb-6 flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-teal-300">
          Neurex Management
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-white">Notifications</h1>
        <p className="text-sm text-slate-400">
          Mentions, assignments, SLA breaches, comment replies and review requests across all
          your projects. {counts ? `${counts.unread} unread of ${counts.total} active.` : ""}
        </p>
      </header>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FilterButton current={filter} value="all" onClick={setFilter}>
          All
        </FilterButton>
        <FilterButton current={filter} value="unread" onClick={setFilter}>
          Unread
        </FilterButton>
        <FilterButton current={filter} value="archived" onClick={setFilter}>
          Archived
        </FilterButton>
        <button
          type="button"
          onClick={() => void markAllRead.mutateAsync()}
          disabled={markAllRead.isPending || (counts?.unread ?? 0) === 0}
          className="ml-auto rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-200 transition hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Mark all read
        </button>
      </div>

      {isError ? (
        <p className="rounded border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-200">
          Failed to load notifications: {(error as Error)?.message ?? "unknown error"}
        </p>
      ) : isLoading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : notifications.length === 0 ? (
        <p className="rounded border border-dashed border-slate-700 bg-slate-900/40 p-6 text-center text-sm text-slate-500">
          Nothing to show.
        </p>
      ) : (
        <ul className="space-y-2">
          {notifications.map((n) => (
            <li key={n.id}>
              <NotificationListItem
                notification={n}
                onRead={() => markRead.mutateAsync(n.id)}
                onArchive={() => markArchived.mutateAsync(n.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function FilterButton({
  current,
  value,
  onClick,
  children,
}: {
  current: Filter;
  value: Filter;
  onClick: (v: Filter) => void;
  children: React.ReactNode;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      className={`rounded-md border px-3 py-1.5 text-xs transition ${
        active
          ? "border-teal-400 bg-teal-500/15 text-teal-200"
          : "border-slate-700 text-slate-400 hover:bg-slate-900"
      }`}
    >
      {children}
    </button>
  );
}

interface NotificationListItemProps {
  notification: MgmtNotification;
  onRead: () => Promise<MgmtNotification>;
  onArchive: () => Promise<MgmtNotification>;
}

function NotificationListItem({ notification, onRead, onArchive }: NotificationListItemProps) {
  const isUnread = notification.read_at == null;
  const isArchived = notification.archived_at != null;
  const tone =
    notification.severity === "critical"
      ? "border-rose-700"
      : notification.severity === "warning"
        ? "border-amber-700"
        : "border-slate-800";

  return (
    <div
      className={`rounded-lg border ${tone} bg-slate-900 p-4 transition ${
        isUnread ? "ring-1 ring-teal-500/30" : ""
      } ${isArchived ? "opacity-60" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-white">{notification.title}</p>
          {notification.body ? (
            <p className="mt-1 text-xs text-slate-300">{notification.body}</p>
          ) : null}
          <p className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
            {notification.kind} · {notification.severity} ·{" "}
            {new Date(notification.created_at).toLocaleString()}
            {notification.project_id ? ` · project ${notification.project_id.slice(0, 8)}` : ""}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {isUnread ? (
            <button
              type="button"
              className="text-[11px] text-teal-300 hover:text-teal-100"
              onClick={() => void onRead()}
            >
              Mark read
            </button>
          ) : null}
          {!isArchived ? (
            <button
              type="button"
              className="text-[11px] text-slate-400 hover:text-slate-200"
              onClick={() => void onArchive()}
            >
              Archive
            </button>
          ) : null}
        </div>
      </div>
      {notification.link_path ? (
        <div className="mt-2">
          <Link
            href={notification.link_path}
            onClick={() => {
              if (isUnread) void onRead();
            }}
            className="text-xs text-teal-300 hover:text-teal-100"
          >
            Open →
          </Link>
        </div>
      ) : null}
    </div>
  );
}
