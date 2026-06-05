"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";

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
  created_at: string;
  updated_at: string;
};

const STORAGE_KEY = "neurex_dashboards_v1";
const API_BASE = (mpid: string) =>
  `/api/v1/test-management/projects/${mpid}/dashboards`;

function readStorage(projectId: string): Dashboard[] {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY}_${projectId}`);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeStorage(projectId: string, items: Dashboard[]) {
  try {
    localStorage.setItem(`${STORAGE_KEY}_${projectId}`, JSON.stringify(items));
  } catch {
    /* ignore */
  }
}

function nowIso() {
  return new globalThis.Date().toISOString();
}

function newWidgetId() {
  return `w-${Math.floor(Math.random() * 1e9).toString(36)}`;
}

function localId() {
  return `dash-local-${Math.floor(Math.random() * 1e9).toString(36)}`;
}

/**
 * Backend-first custom dashboard hook.
 * Reads from and writes to test-management project settings_data.
 * Falls back to localStorage when mpid is absent or backend unreachable.
 */
export function useCustomDashboard(projectId: string, mpid?: string | null) {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const local = readStorage(projectId);
    if (local.length > 0) {
      setDashboards(local);
      setActiveId((prev) => (prev === null ? (local[0]?.id ?? null) : prev));
    }

    if (!mpid) {
      setLoading(false);
      return;
    }

    apiFetch<Dashboard[]>(API_BASE(mpid))
      .then((data) => {
        if (data && data.length > 0) {
          setDashboards(data);
          writeStorage(projectId, data);
          setActiveId((prev) => (prev === null ? (data[0]?.id ?? null) : prev));
        } else if (local.length === 0) {
          setDashboards([]);
        }
      })
      .catch(() => { /* keep localStorage */ })
      .finally(() => setLoading(false));
  }, [projectId, mpid]); // eslint-disable-line react-hooks/exhaustive-deps

  const syncState = useCallback(
    (next: Dashboard[]) => {
      setDashboards(next);
      writeStorage(projectId, next);
    },
    [projectId],
  );

  const createDashboard = useCallback(
    async (name: string): Promise<Dashboard> => {
      if (mpid) {
        try {
          const created = await apiFetch<Dashboard>(API_BASE(mpid), {
            method: "POST",
            json: { name, widgets: [] },
          });
          syncState([...readStorage(projectId), created]);
          setActiveId(created.id);
          return created;
        } catch { /* fall through */ }
      }
      const d: Dashboard = {
        id: localId(),
        name,
        widgets: [],
        created_at: nowIso(),
        updated_at: nowIso(),
      };
      syncState([...readStorage(projectId), d]);
      setActiveId(d.id);
      return d;
    },
    [projectId, mpid, syncState],
  );

  const deleteDashboard = useCallback(
    async (id: string): Promise<void> => {
      if (mpid) {
        try { await apiFetch<void>(`${API_BASE(mpid)}/${id}`, { method: "DELETE" }); }
        catch { /* fall through */ }
      }
      const next = readStorage(projectId).filter((d) => d.id !== id);
      syncState(next);
      setActiveId((prev) => {
        if (prev !== id) return prev;
        return next.length > 0 ? (next[0]?.id ?? null) : null;
      });
    },
    [projectId, mpid, syncState],
  );

  const _pushUpdate = useCallback(
    async (updated: Dashboard): Promise<void> => {
      syncState(readStorage(projectId).map((d) => (d.id === updated.id ? updated : d)));
      if (mpid) {
        try {
          await apiFetch<Dashboard>(`${API_BASE(mpid)}/${updated.id}`, {
            method: "PUT",
            json: { name: updated.name, widgets: updated.widgets },
          });
        } catch { /* localStorage already updated */ }
      }
    },
    [projectId, mpid, syncState],
  );

  const renameDashboard = useCallback(
    async (id: string, name: string): Promise<void> => {
      const cur = readStorage(projectId).find((d) => d.id === id);
      if (cur) await _pushUpdate({ ...cur, name, updated_at: nowIso() });
    },
    [projectId, _pushUpdate],
  );

  const addWidget = useCallback(
    async (dashId: string, widget: Omit<Widget, "id">): Promise<Widget> => {
      const w: Widget = { ...widget, id: newWidgetId() };
      const cur = readStorage(projectId).find((d) => d.id === dashId);
      if (cur) await _pushUpdate({ ...cur, widgets: [...cur.widgets, w], updated_at: nowIso() });
      return w;
    },
    [projectId, _pushUpdate],
  );

  const removeWidget = useCallback(
    async (dashId: string, widgetId: string): Promise<void> => {
      const cur = readStorage(projectId).find((d) => d.id === dashId);
      if (cur) {
        await _pushUpdate({
          ...cur,
          widgets: cur.widgets.filter((w) => w.id !== widgetId),
          updated_at: nowIso(),
        });
      }
    },
    [projectId, _pushUpdate],
  );

  const updateWidget = useCallback(
    async (dashId: string, widgetId: string, patch: Partial<Widget>): Promise<void> => {
      const cur = readStorage(projectId).find((d) => d.id === dashId);
      if (cur) {
        await _pushUpdate({
          ...cur,
          widgets: cur.widgets.map((w) => (w.id === widgetId ? { ...w, ...patch } : w)),
          updated_at: nowIso(),
        });
      }
    },
    [projectId, _pushUpdate],
  );

  return {
    dashboards,
    active: dashboards.find((d) => d.id === activeId) ?? null,
    activeId,
    loading,
    setActiveId,
    createDashboard,
    deleteDashboard,
    renameDashboard,
    addWidget,
    removeWidget,
    updateWidget,
  };
}
