"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type NotificationKind =
  | "mention"
  | "assignment"
  | "sla_breach"
  | "comment_reply"
  | "review_request"
  | "system";

export type NotificationSeverity = "info" | "warning" | "critical";

export interface MgmtNotification {
  id: string;
  tenant_id: string;
  user_id: string;
  project_id?: string | null;
  kind: NotificationKind | string;
  title: string;
  body: string;
  link_path?: string | null;
  severity: NotificationSeverity | string;
  source_trace: Record<string, unknown>;
  channel?: string;
  read_at?: string | null;
  archived_at?: string | null;
  created_at: string;
}

export interface NotificationDigestGroup {
  theme: string;
  count: number;
  oneLine: string;
}

export interface NotificationDigestOut {
  window: string;
  generated_at: string;
  groups: NotificationDigestGroup[];
  source: "llm" | "fallback";
}

export interface UnreadCount {
  unread: number;
  total: number;
}

export const notificationKeys = {
  all: ["mgmt-notifications"] as const,
  list: (opts: { unreadOnly?: boolean; includeArchived?: boolean; projectId?: string | null }) =>
    [
      ...notificationKeys.all,
      "list",
      opts.unreadOnly ?? false,
      opts.includeArchived ?? false,
      opts.projectId ?? null,
    ] as const,
  count: () => [...notificationKeys.all, "count"] as const,
};

const BASE = "/api/v1/test-management/notifications";

export interface UseNotificationsOptions {
  unreadOnly?: boolean;
  includeArchived?: boolean;
  projectId?: string | null;
  limit?: number;
}

export function useNotifications(opts: UseNotificationsOptions = {}) {
  const { unreadOnly = false, includeArchived = false, projectId = null, limit = 50 } = opts;
  return useQuery({
    queryKey: notificationKeys.list({ unreadOnly, includeArchived, projectId }),
    queryFn: () => {
      const params = new URLSearchParams();
      if (unreadOnly) params.set("unread_only", "true");
      if (includeArchived) params.set("include_archived", "true");
      if (projectId) params.set("project_id", projectId);
      params.set("limit", String(limit));
      return apiFetch<MgmtNotification[]>(`${BASE}?${params.toString()}`);
    },
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.count(),
    queryFn: () => apiFetch<UnreadCount>(`${BASE}/unread-count`),
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      apiFetch<MgmtNotification>(`${BASE}/${notificationId}/read`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkArchived() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      apiFetch<MgmtNotification>(`${BASE}/${notificationId}/archive`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ updated: number }>(`${BASE}/read-all`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}

/**
 * Subscribe to the live SSE stream. Each "notification" event triggers a
 * query refetch and exposes the latest payload via state for toast usage.
 *
 * EventSource doesn't support custom headers, so this relies on the API base
 * being same-origin (cookie auth) or the upstream stream endpoint allowing
 * token-via-query-string. The persistent inbox endpoint remains the source
 * of truth — the stream is purely a refresh trigger.
 */
export function useNotificationStream(enabled: boolean = true): MgmtNotification | null {
  const qc = useQueryClient();
  const [last, setLast] = useState<MgmtNotification | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || typeof window === "undefined" || typeof EventSource === "undefined") {
      return;
    }
    const apiBase = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");
    const url = `${apiBase}${BASE}/stream`;
    let cancelled = false;
    let retryHandle: ReturnType<typeof setTimeout> | null = null;
    let backoff = 1_000; // start at 1s, grow → 30s max
    const MAX_BACKOFF = 30_000;

    const connect = () => {
      if (cancelled) return;
      const es = new EventSource(url, { withCredentials: true });
      sourceRef.current = es;
      es.addEventListener("open", () => {
        // Reset backoff once we're stably connected.
        backoff = 1_000;
      });
      es.addEventListener("notification", (evt) => {
        try {
          const payload = JSON.parse((evt as MessageEvent).data) as MgmtNotification;
          setLast(payload);
          void qc.invalidateQueries({ queryKey: notificationKeys.all });
        } catch {
          // Ignore malformed payloads.
        }
      });
      es.onerror = () => {
        es.close();
        sourceRef.current = null;
        if (!cancelled) {
          const delay = backoff;
          backoff = Math.min(backoff * 2, MAX_BACKOFF);
          retryHandle = setTimeout(connect, delay);
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (retryHandle) clearTimeout(retryHandle);
      sourceRef.current?.close();
      sourceRef.current = null;
    };
  }, [enabled, qc]);

  return last;
}

/**
 * Fetch an AI-generated digest of the user's recent notifications.
 *
 * Powered by the `mgmt.me.notif_digest` prompt template; when the LLM
 * is unavailable the backend returns a kind-grouped fallback with
 * `source: "fallback"`.
 */
export function useNotificationDigest(window: "24h" | "7d" = "24h", enabled: boolean = true) {
  return useQuery({
    queryKey: [...notificationKeys.all, "digest", window] as const,
    queryFn: () =>
      apiFetch<NotificationDigestOut>(
        `${BASE}/digest?window=${encodeURIComponent(window)}`,
      ),
    enabled,
    staleTime: 60_000,
  });
}
