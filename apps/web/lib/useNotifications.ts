"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

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
const NOTIFICATIONS_API_BASE = "/api/v1/notifications";

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

// Backend-first with localStorage fallback.
// Fetches notifications from the backend API; if unavailable or auth required,
// falls back to localStorage so existing notifications are never lost.
async function fetchFromBackend(): Promise<Notification[] | null> {
  try {
    const data = await apiFetch<unknown>(NOTIFICATIONS_API_BASE);
    if (Array.isArray(data)) return data as Notification[];
    if (
      typeof data === "object" &&
      data !== null &&
      "notifications" in data &&
      Array.isArray((data as { notifications?: unknown }).notifications)
    ) {
      return (data as { notifications: Notification[] }).notifications;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * In-app notification center hook.
 *
 * Storage: backend-first (GET /api/v1/notifications) with localStorage
 * fallback for offline use and when the backend is unavailable.
 *
 * Cross-tab sync: storage event listener — başka tab notification eklerse
 * bu tab da görür.
 */
export function useNotifications() {
  const [items, setItems] = useState<Notification[]>([]);

  // Initial load: localStorage first for instant display, then backend overrides
  useEffect(() => {
    // 1. Load localStorage immediately for instant display
    const local = readStorage();
    if (local.length > 0) setItems(local);

    // 2. Then fetch from backend — if it responds, prefer its data (authoritative source)
    fetchFromBackend().then((backendData) => {
      if (backendData && backendData.length > 0) {
        setItems(backendData);
        writeStorage(backendData); // sync to localStorage for offline use
      }
    });

    // Cross-tab sync via storage events
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
        id: `n-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`}`,
        timestamp: Date.now(),
        read: false,
      };
      persist([notification, ...items]);
      return notification;
    },
    [items, persist],
  );

  const markRead = useCallback(
    (id: string) => {
      persist(items.map((n) => (n.id === id ? { ...n, read: true } : n)));
    },
    [items, persist],
  );

  const markAllRead = useCallback(() => {
    persist(items.map((n) => ({ ...n, read: true })));
  }, [items, persist]);

  const remove = useCallback(
    (id: string) => {
      persist(items.filter((n) => n.id !== id));
    },
    [items, persist],
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
