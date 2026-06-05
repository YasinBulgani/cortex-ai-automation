"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

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

function normalizeDashboards(payload: unknown): Dashboard[] | null {
  if (Array.isArray(payload)) return payload as Dashboard[];
  if (
    typeof payload === "object" &&
    payload !== null &&
    "dashboards" in payload &&
    Array.isArray((payload as { dashboards?: unknown }).dashboards)
  ) {
    return (payload as { dashboards: Dashboard[] }).dashboards;
  }
  return null;
}

// Backend-first with localStorage fallback. Existing browser data stays as an
// offline cache, but the shared apiFetch client keeps auth/refresh behavior
// consistent with the rest of the frontend.
async function fetchFromBackend(projectId: string): Promise<Dashboard[] | null> {
  try {
    const data = await apiFetch<unknown>(
      `${DASHBOARDS_API_BASE}?project_id=${encodeURIComponent(projectId)}`,
    );
    return normalizeDashboards(data);
  } catch {
    return null;
  }
}

function newId(): string {
  return `dash-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`}`;
}

function newWidgetId(): string {
  return `w-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`}`;
}

async function saveToBackend(projectId: string, next: Dashboard[]) {
  try {
    await apiFetch<unknown>(
      `${DASHBOARDS_API_BASE}?project_id=${encodeURIComponent(projectId)}`,
      {
        method: "PUT",
        json: { dashboards: next },
      },
    );
  } catch {
    // Backend endpoint may not be enabled in all environments yet. The local
    // cache above remains the durable fallback for the current browser.
  }
}

/**
 * Hook for managing user-customised dashboards.
 *
 * Storage: backend-first with localStorage fallback for offline use and when
 * the backend dashboard endpoint is unavailable.
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
      }
    });
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  const persist = useCallback(
    (next: Dashboard[]) => {
      setDashboards(next);
      writeStorage(next);
      void saveToBackend(projectId, next);
    },
    [projectId],
  );

  const createDashboard = useCallback(
    (name: string) => {
      const dash: Dashboard = {
        id: newId(),
        name,
        widgets: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      const next = [...dashboards, dash];
      persist(next);
      setActiveId(dash.id);
      return dash;
    },
    [dashboards, persist],
  );

  const deleteDashboard = useCallback(
    (id: string) => {
      const next = dashboards.filter((d) => d.id !== id);
      persist(next);
      if (activeId === id) {
        setActiveId(next.length > 0 ? next[0].id : null);
      }
    },
    [activeId, dashboards, persist],
  );

  const renameDashboard = useCallback(
    (id: string, name: string) => {
      persist(
        dashboards.map((d) =>
          d.id === id ? { ...d, name, updatedAt: Date.now() } : d,
        ),
      );
    },
    [dashboards, persist],
  );

  const addWidget = useCallback(
    (dashId: string, widget: Omit<Widget, "id">) => {
      const w: Widget = { ...widget, id: newWidgetId() };
      persist(
        dashboards.map((d) =>
          d.id === dashId
            ? { ...d, widgets: [...d.widgets, w], updatedAt: Date.now() }
            : d,
        ),
      );
      return w;
    },
    [dashboards, persist],
  );

  const removeWidget = useCallback(
    (dashId: string, widgetId: string) => {
      persist(
        dashboards.map((d) =>
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
    [dashboards, persist],
  );

  const updateWidget = useCallback(
    (dashId: string, widgetId: string, patch: Partial<Widget>) => {
      persist(
        dashboards.map((d) =>
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
    [dashboards, persist],
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
