"use client";

import { useCallback, useEffect, useState } from "react";

export type WidgetType =
  | "pass-rate"
  | "execution-count"
  | "flaky-trend"
  | "failure-density"
  | "ai-cost"
  | "test-coverage"
  | "recent-runs"
  | "active-incidents"
  | "custom-text";

export type Widget = {
  id: string;
  type: WidgetType;
  title: string;
  x: number;
  y: number;
  w: number;
  h: number;
  config?: Record<string, unknown>;
};

export type Dashboard = {
  id: string;
  name: string;
  widgets: Widget[];
  createdAt: number;
  updatedAt: number;
};

const STORAGE_KEY = "neurex_dashboards_v1";
const DASHBOARDS_API_BASE = "/api/v1/dashboards";

function readStorage(): Dashboard[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeStorage(items: Dashboard[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    /* ignore quota / unavailable */
  }
}

// Backend-first with localStorage fallback.
// Tries to fetch dashboards from the backend API first; if unavailable or
// the project has no server-side dashboards yet, falls back to localStorage
// so existing user data is never lost.
async function fetchFromBackend(projectId: string): Promise<Dashboard[] | null> {
  try {
    const res = await fetch(`${DASHBOARDS_API_BASE}?project_id=${projectId}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) return null; // backend unavailable or auth required → use localStorage
    const data: Dashboard[] = await res.json();
    return Array.isArray(data) ? data : null;
  } catch {
    return null; // network error → graceful fallback
  }
}

function newId(): string {
  return `dash-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function newWidgetId(): string {
  return `w-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

/**
 * Hook for managing user-customised dashboards.
 *
 * Storage: backend-first (GET /api/v1/dashboards?project_id=...) with
 * localStorage fallback for offline use and when the backend is unavailable.
 * Mutations still write to localStorage; backend write-back is planned.
 */
export function useCustomDashboard(projectId: string) {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Initial load: localStorage first for instant paint, then backend overrides
  useEffect(() => {
    const local = readStorage().filter((d) => d.id.startsWith("dash-"));
    if (local.length > 0) {
      setDashboards(local);
      setActiveId((prev) => (prev === null && local.length > 0 ? local[0].id : prev));
    }

    // Then try backend — if it responds, prefer its data (authoritative source)
    fetchFromBackend(projectId).then((backendData) => {
      if (backendData && backendData.length > 0) {
        setDashboards(backendData);
        writeStorage(backendData); // sync to localStorage for offline use
        setActiveId((prev) => (prev === null ? backendData[0].id : prev));
      } else if (local.length === 0) {
        setDashboards([]); // both empty
      }
    });
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  const persist = useCallback((next: Dashboard[]) => {
    setDashboards(next);
    writeStorage(next);
  }, []);

  const createDashboard = useCallback(
    (name: string) => {
      const dash: Dashboard = {
        id: newId(),
        name,
        widgets: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      const next = [...readStorage(), dash];
      persist(next);
      setActiveId(dash.id);
      return dash;
    },
    [persist],
  );

  const deleteDashboard = useCallback(
    (id: string) => {
      const next = readStorage().filter((d) => d.id !== id);
      persist(next);
      if (activeId === id) {
        setActiveId(next.length > 0 ? next[0].id : null);
      }
    },
    [activeId, persist],
  );

  const renameDashboard = useCallback(
    (id: string, name: string) => {
      persist(
        readStorage().map((d) =>
          d.id === id ? { ...d, name, updatedAt: Date.now() } : d,
        ),
      );
    },
    [persist],
  );

  const addWidget = useCallback(
    (dashId: string, widget: Omit<Widget, "id">) => {
      const w: Widget = { ...widget, id: newWidgetId() };
      persist(
        readStorage().map((d) =>
          d.id === dashId
            ? { ...d, widgets: [...d.widgets, w], updatedAt: Date.now() }
            : d,
        ),
      );
      return w;
    },
    [persist],
  );

  const removeWidget = useCallback(
    (dashId: string, widgetId: string) => {
      persist(
        readStorage().map((d) =>
          d.id === dashId
            ? {
                ...d,
                widgets: d.widgets.filter((w) => w.id !== widgetId),
                updatedAt: Date.now(),
              }
            : d,
        ),
      );
    },
    [persist],
  );

  const updateWidget = useCallback(
    (dashId: string, widgetId: string, patch: Partial<Widget>) => {
      persist(
        readStorage().map((d) =>
          d.id === dashId
            ? {
                ...d,
                widgets: d.widgets.map((w) =>
                  w.id === widgetId ? { ...w, ...patch } : w,
                ),
                updatedAt: Date.now(),
              }
            : d,
        ),
      );
    },
    [persist],
  );

  const active = dashboards.find((d) => d.id === activeId) ?? null;

  return {
    dashboards,
    active,
    activeId,
    setActiveId,
    createDashboard,
    deleteDashboard,
    renameDashboard,
    addWidget,
    removeWidget,
    updateWidget,
  };
}
