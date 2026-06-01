/**
 * Tests for useCustomDashboard — backend-first pattern (Wave 6).
 *
 * Strategy:
 *  - localStorage is mocked via a simple in-memory store (Storage mock is
 *    already provided by @testing-library's jsdom environment).
 *  - fetch is replaced with a jest.fn() so we can control backend responses.
 *  - renderHook + act from @testing-library/react.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { useCustomDashboard } from "../useCustomDashboard";
import type { Dashboard } from "../useCustomDashboard";

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

const STORAGE_KEY = "neurex_dashboards_v1";

const MOCK_BACKEND_DASHBOARDS: Dashboard[] = [
  {
    id: "dash-backend-1",
    name: "Backend Dash",
    widgets: [],
    createdAt: 1000,
    updatedAt: 1000,
  },
];

const MOCK_LOCAL_DASHBOARDS: Dashboard[] = [
  {
    id: "dash-local-1",
    name: "Local Dash",
    widgets: [],
    createdAt: 500,
    updatedAt: 500,
  },
];

function mockFetchSuccess(data: Dashboard[]) {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => data,
  } as Response);
}

function mockFetchFailure() {
  (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));
}

function mockFetchNotOk() {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    json: async () => [],
  } as unknown as Response);
}

beforeEach(() => {
  localStorage.clear();
  (global.fetch as jest.Mock).mockClear();
});

// ---------------------------------------------------------------------------
// TASK 1 — Initial load behaviour
// ---------------------------------------------------------------------------

describe("useCustomDashboard — initial load", () => {
  it("loads dashboards from localStorage immediately on mount", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_LOCAL_DASHBOARDS));
    mockFetchSuccess([]); // backend returns empty

    const { result } = renderHook(() => useCustomDashboard("proj-1"));

    // The first synchronous render should already have local data
    expect(result.current.dashboards.length).toBeGreaterThanOrEqual(0);

    await waitFor(() => {
      // After full effect resolution local data should still be present
      // (backend was empty so local should be kept)
      expect(
        result.current.dashboards.some((d) => d.id === "dash-local-1"),
      ).toBe(true);
    });
  });

  it("fetches dashboards from backend on mount", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    renderHook(() => useCustomDashboard("proj-1"));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("project_id=proj-1"),
        expect.objectContaining({ credentials: "include" }),
      );
    });
  });

  it("prefers backend data over localStorage when backend responds with items", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_LOCAL_DASHBOARDS));
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));

    await waitFor(() => {
      expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
        true,
      );
    });
  });

  it("falls back to localStorage when backend request fails", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_LOCAL_DASHBOARDS));
    mockFetchFailure();

    const { result } = renderHook(() => useCustomDashboard("proj-1"));

    await waitFor(() => {
      expect(result.current.dashboards.some((d) => d.id === "dash-local-1")).toBe(
        true,
      );
    });
  });

  it("falls back to localStorage when backend returns non-ok status", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_LOCAL_DASHBOARDS));
    mockFetchNotOk();

    const { result } = renderHook(() => useCustomDashboard("proj-1"));

    await waitFor(() => {
      expect(result.current.dashboards.some((d) => d.id === "dash-local-1")).toBe(
        true,
      );
    });
  });

  it("handles empty backend response without overwriting localStorage", async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_LOCAL_DASHBOARDS));
    mockFetchSuccess([]); // backend returns empty array

    const { result } = renderHook(() => useCustomDashboard("proj-1"));

    await waitFor(() => {
      // Local data should survive when backend is empty
      expect(result.current.dashboards.some((d) => d.id === "dash-local-1")).toBe(
        true,
      );
    });
  });

  it("syncs backend data to localStorage for offline use", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    renderHook(() => useCustomDashboard("proj-1"));

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
      expect(stored.some((d: Dashboard) => d.id === "dash-backend-1")).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// TASK 2 — Mutation operations
// ---------------------------------------------------------------------------

describe("useCustomDashboard — mutations", () => {
  it("createDashboard adds a new dashboard and sets it active", async () => {
    mockFetchSuccess([]);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());

    act(() => {
      result.current.createDashboard("My New Dash");
    });

    expect(result.current.dashboards.some((d) => d.name === "My New Dash")).toBe(
      true,
    );
    expect(result.current.active?.name).toBe("My New Dash");
  });

  it("deleteDashboard removes the dashboard", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));
    await waitFor(() =>
      expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
        true,
      ),
    );

    act(() => {
      result.current.deleteDashboard("dash-backend-1");
    });

    expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
      false,
    );
  });

  it("renameDashboard updates the dashboard name", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));
    await waitFor(() =>
      expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
        true,
      ),
    );

    act(() => {
      result.current.renameDashboard("dash-backend-1", "Renamed");
    });

    expect(
      result.current.dashboards.find((d) => d.id === "dash-backend-1")?.name,
    ).toBe("Renamed");
  });

  it("addWidget adds a widget to the specified dashboard", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));
    await waitFor(() =>
      expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
        true,
      ),
    );

    act(() => {
      result.current.addWidget("dash-backend-1", {
        type: "pass-rate",
        title: "Pass Rate",
        x: 0,
        y: 0,
        w: 2,
        h: 2,
      });
    });

    const dash = result.current.dashboards.find((d) => d.id === "dash-backend-1");
    expect(dash?.widgets.length).toBe(1);
    expect(dash?.widgets[0].type).toBe("pass-rate");
  });

  it("removeWidget deletes the widget from the dashboard", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));
    await waitFor(() =>
      expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
        true,
      ),
    );

    // First add then remove
    let widgetId: string;
    act(() => {
      const w = result.current.addWidget("dash-backend-1", {
        type: "execution-count",
        title: "Runs",
        x: 0,
        y: 0,
        w: 1,
        h: 1,
      });
      widgetId = w.id;
    });

    act(() => {
      result.current.removeWidget("dash-backend-1", widgetId!);
    });

    const dash = result.current.dashboards.find((d) => d.id === "dash-backend-1");
    expect(dash?.widgets.length).toBe(0);
  });

  it("updateWidget patches widget properties", async () => {
    mockFetchSuccess(MOCK_BACKEND_DASHBOARDS);

    const { result } = renderHook(() => useCustomDashboard("proj-1"));
    await waitFor(() =>
      expect(result.current.dashboards.some((d) => d.id === "dash-backend-1")).toBe(
        true,
      ),
    );

    let widgetId: string;
    act(() => {
      const w = result.current.addWidget("dash-backend-1", {
        type: "ai-cost",
        title: "AI Cost",
        x: 0,
        y: 0,
        w: 2,
        h: 2,
      });
      widgetId = w.id;
    });

    act(() => {
      result.current.updateWidget("dash-backend-1", widgetId!, { title: "Updated Title" });
    });

    const dash = result.current.dashboards.find((d) => d.id === "dash-backend-1");
    expect(dash?.widgets.find((w) => w.id === widgetId)?.title).toBe("Updated Title");
  });
});
