/**
 * useLearningChecklist hook — 12 unit tests
 *
 * Tests cover:
 *   - initial state (empty completed set)
 *   - localStorage load on mount (instant display)
 *   - backend fetch on mount
 *   - backend data preferred over localStorage
 *   - network-error fallback to localStorage
 *   - non-ok response fallback to localStorage
 *   - localStorage sync after backend success
 *   - markComplete(), markIncomplete(), dismiss()
 *   - progressPct and requiredCompletedAll derived values
 *
 * No real fetch or localStorage is used — both are mocked.
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useLearningChecklist, ChecklistItemId } from "../useLearningChecklist";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

const localStorageData: Record<string, string> = {};
const localStorageMock = {
  getItem: jest.fn((key: string) => localStorageData[key] ?? null),
  setItem: jest.fn((key: string, value: string) => {
    localStorageData[key] = value;
  }),
  removeItem: jest.fn((key: string) => {
    delete localStorageData[key];
  }),
  clear: jest.fn(() => {
    Object.keys(localStorageData).forEach((k) => delete localStorageData[k]);
  }),
};
Object.defineProperty(global, "localStorage", {
  value: localStorageMock,
  writable: true,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "neurex_learning_checklist_v1";
const DISMISSED_KEY = "neurex_checklist_dismissed";

function seedLocalStorage(completedIds: ChecklistItemId[]) {
  localStorageData[STORAGE_KEY] = JSON.stringify(completedIds);
}

function mockBackendSuccess(completedIds: ChecklistItemId[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => completedIds,
  } as Response);
}

function mockBackendNetworkError() {
  mockFetch.mockRejectedValueOnce(new Error("network error"));
}

function mockBackendNonOk() {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Unauthorized" }),
  } as Response);
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorageMock.clear();
  mockFetch.mockClear();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useLearningChecklist", () => {
  // ── 1. Initial state ──────────────────────────────────────────────────────
  it("initializes with an empty completed set when storage and backend are both empty", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useLearningChecklist());

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    expect(result.current.completed.size).toBe(0);
    expect(result.current.totalCompleted).toBe(0);
    expect(result.current.dismissed).toBe(false);
  });

  // ── 2. localStorage load on mount ─────────────────────────────────────────
  it("loads completed ids from localStorage immediately on mount before backend responds", async () => {
    seedLocalStorage(["create_project", "run_first_execution"]);

    // Simulate backend that hasn't responded yet
    let resolveBackend!: (v: unknown) => void;
    mockFetch.mockReturnValueOnce(
      new Promise((res) => {
        resolveBackend = res;
      }),
    );

    const { result } = renderHook(() => useLearningChecklist());

    // Immediately after mount (before backend), localStorage data should be visible
    expect(result.current.completed.has("create_project")).toBe(true);
    expect(result.current.completed.has("run_first_execution")).toBe(true);

    // Cleanup — resolve the pending fetch
    resolveBackend({ ok: true, json: async () => [] });
  });

  // ── 3. Backend fetch on mount ─────────────────────────────────────────────
  it("calls fetch('/api/v1/checklist/progress') on mount", async () => {
    mockBackendSuccess([]);

    renderHook(() => useLearningChecklist());

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/checklist/progress",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  // ── 4. Backend data preferred over localStorage ───────────────────────────
  it("replaces localStorage completed ids with backend data when backend succeeds", async () => {
    seedLocalStorage(["create_project"]);
    const backendIds: ChecklistItemId[] = ["create_project", "create_first_scenario", "run_first_execution"];
    mockBackendSuccess(backendIds);

    const { result } = renderHook(() => useLearningChecklist());

    await waitFor(() => {
      expect(result.current.completed.has("create_first_scenario")).toBe(true);
    });

    expect(result.current.completed.has("run_first_execution")).toBe(true);
    expect(result.current.totalCompleted).toBe(3);
  });

  // ── 5. Network-error fallback to localStorage ─────────────────────────────
  it("falls back to localStorage completed ids when backend throws a network error", async () => {
    seedLocalStorage(["create_project", "run_first_execution"]);
    mockBackendNetworkError();

    const { result } = renderHook(() => useLearningChecklist());

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    expect(result.current.completed.has("create_project")).toBe(true);
    expect(result.current.completed.has("run_first_execution")).toBe(true);
  });

  // ── 6. Non-ok response fallback ───────────────────────────────────────────
  it("falls back to localStorage completed ids when backend returns a non-ok response", async () => {
    seedLocalStorage(["create_project"]);
    mockBackendNonOk();

    const { result } = renderHook(() => useLearningChecklist());

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    expect(result.current.completed.has("create_project")).toBe(true);
  });

  // ── 7. Backend data saved to localStorage ────────────────────────────────
  it("saves backend data to localStorage when backend succeeds", async () => {
    const backendIds: ChecklistItemId[] = ["create_project", "create_first_scenario"];
    mockBackendSuccess(backendIds);

    renderHook(() => useLearningChecklist());

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    const savedRaw = localStorageData[STORAGE_KEY];
    expect(savedRaw).toBeDefined();
    const saved: ChecklistItemId[] = JSON.parse(savedRaw);
    expect(saved).toContain("create_project");
    expect(saved).toContain("create_first_scenario");
  });

  // ── 8. markComplete() adds an id ─────────────────────────────────────────
  it("markComplete() adds the given item id to completed set", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useLearningChecklist());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.markComplete("create_project");
    });

    expect(result.current.completed.has("create_project")).toBe(true);
    expect(result.current.totalCompleted).toBe(1);
  });

  // ── 9. markIncomplete() removes an id ────────────────────────────────────
  it("markIncomplete() removes the given item id from completed set", async () => {
    seedLocalStorage(["create_project", "run_first_execution"]);
    mockBackendSuccess(["create_project", "run_first_execution"]);

    const { result } = renderHook(() => useLearningChecklist());
    await waitFor(() => expect(result.current.totalCompleted).toBe(2));

    act(() => {
      result.current.markIncomplete("create_project");
    });

    expect(result.current.completed.has("create_project")).toBe(false);
    expect(result.current.completed.has("run_first_execution")).toBe(true);
  });

  // ── 10. dismiss() sets dismissed flag ────────────────────────────────────
  it("dismiss() sets dismissed to true and persists to localStorage", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useLearningChecklist());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    expect(result.current.dismissed).toBe(false);

    act(() => {
      result.current.dismiss();
    });

    expect(result.current.dismissed).toBe(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith(DISMISSED_KEY, "1");
  });

  // ── 11. progressPct computed from completedAll ────────────────────────────
  it("progressPct is 0 when nothing is completed", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useLearningChecklist());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    expect(result.current.progressPct).toBe(0);
  });

  // ── 12. requiredCompletedAll is true when all required items are done ─────
  it("requiredCompletedAll is true when all required checklist items are marked complete", async () => {
    // Required items: create_project, create_first_scenario, run_first_execution
    const requiredIds: ChecklistItemId[] = [
      "create_project",
      "create_first_scenario",
      "run_first_execution",
    ];
    mockBackendSuccess(requiredIds);

    const { result } = renderHook(() => useLearningChecklist());

    await waitFor(() => {
      expect(result.current.completed.has("run_first_execution")).toBe(true);
    });

    expect(result.current.requiredCompletedAll).toBe(true);
  });
});
