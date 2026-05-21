"use client";

import { useCallback, useEffect, useState } from "react";

export type NotificationLevel = "info" | "success" | "warning" | "error";

export type Notification = {
  id: string;
  level: NotificationLevel;
  title: string;
  body?: string;
  url?: string;
  source?: string;
  timestamp: number;
  read: boolean;
};

const STORAGE_KEY = "neurex_notifications_v1";
const MAX_NOTIFICATIONS = 100;

function readStorage(): Notification[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function writeStorage(items: Notification[]) {
  try {
    // Trim before write — bound memory
    const trimmed = items.slice(0, MAX_NOTIFICATIONS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    /* localStorage full / unavailable */
  }
}

/**
 * In-app notification center hook.
 *
 * Storage: localStorage (per-browser; cross-device sync ayrı iş — server-side
 * notification table + WebSocket push gerekli).
 *
 * Cross-tab sync: storage event listener — başka tab notification eklerse
 * bu tab da görür.
 */
export function useNotifications() {
  const [items, setItems] = useState<Notification[]>([]);

  // Initial load + cross-tab sync
  useEffect(() => {
    setItems(readStorage());
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) {
        setItems(readStorage());
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const persist = useCallback((next: Notification[]) => {
    setItems(next);
    writeStorage(next);
  }, []);

  const add = useCallback(
    (n: Omit<Notification, "id" | "timestamp" | "read">) => {
      const notification: Notification = {
        ...n,
        id: `n-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: Date.now(),
        read: false,
      };
      persist([notification, ...readStorage()]);
      return notification;
    },
    [persist],
  );

  const markRead = useCallback(
    (id: string) => {
      persist(readStorage().map((n) => (n.id === id ? { ...n, read: true } : n)));
    },
    [persist],
  );

  const markAllRead = useCallback(() => {
    persist(readStorage().map((n) => ({ ...n, read: true })));
  }, [persist]);

  const remove = useCallback(
    (id: string) => {
      persist(readStorage().filter((n) => n.id !== id));
    },
    [persist],
  );

  const clear = useCallback(() => {
    persist([]);
  }, [persist]);

  const unreadCount = items.filter((n) => !n.read).length;

  return {
    items,
    unreadCount,
    add,
    markRead,
    markAllRead,
    remove,
    clear,
  };
}
