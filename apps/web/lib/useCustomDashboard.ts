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

function newId(): string {
  return `dash-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function newWidgetId(): string {
  return `w-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

/**
 * Hook for managing user-customised dashboards.
 *
 * Storage: localStorage (per-browser). Cross-device sync would require a
 * backend dashboards table — separate work.
 */
export function useCustomDashboard(projectId: string) {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Initial load
  useEffect(() => {
    const all = readStorage();
    const owned = all.filter((d) => d.id.startsWith("dash-"));
    setDashboards(owned);
    if (owned.length > 0 && activeId === null) {
      setActiveId(owned[0].id);
    }
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
