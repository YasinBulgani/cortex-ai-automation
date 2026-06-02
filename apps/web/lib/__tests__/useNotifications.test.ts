/**
 * useNotifications hook — 13 unit tests
 *
 * Tests cover:
 *   - initial state (empty)
 *   - localStorage load on mount (instant display)
 *   - backend fetch on mount
 *   - backend data preferred over localStorage
 *   - network-error fallback to localStorage
 *   - non-ok response fallback to localStorage
 *   - localStorage sync after backend success
 *   - add(), markRead(), markAllRead(), remove(), clear()
 *   - unreadCount derived value
 *
 * No real fetch or localStorage is used — both are mocked.
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { useNotifications, Notification } from "../useNotifications";

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

const STORAGE_KEY = "neurex_notifications_v1";

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: `n-${Date.now()}-test`,
    level: "info",
    title: "Test Notification",
    body: "Test body",
    timestamp: 1700000000000,
    read: false,
    ...overrides,
  };
}

function seedLocalStorage(notifications: Notification[]) {
  localStorageData[STORAGE_KEY] = JSON.stringify(notifications);
}

function mockBackendSuccess(notifications: Notification[]) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => notifications,
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
  // Prevent window.addEventListener errors in jsdom for storage events
  jest.spyOn(window, "addEventListener").mockImplementation(() => {});
  jest.spyOn(window, "removeEventListener").mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useNotifications", () => {
  // ── 1. Initial state ──────────────────────────────────────────────────────
  it("initializes with an empty items array when storage and backend are both empty", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.unreadCount).toBe(0);
  });

  // ── 2. localStorage load on mount ─────────────────────────────────────────
  it("loads notifications from localStorage immediately on mount before backend responds", async () => {
    const stored = [makeNotification({ id: "local-1", title: "Stored Notification" })];
    seedLocalStorage(stored);

    // Simulate backend that hasn't responded yet
    let resolveBackend!: (v: unknown) => void;
    mockFetch.mockReturnValueOnce(
      new Promise((res) => {
        resolveBackend = res;
      }),
    );

    const { result } = renderHook(() => useNotifications());

    // Immediately after mount (before backend), localStorage data should be visible
    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].title).toBe("Stored Notification");

    // Cleanup — resolve the pending fetch
    resolveBackend({ ok: true, json: async () => [] });
  });

  // ── 3. Backend fetch on mount ─────────────────────────────────────────────
  it("calls fetch('/api/v1/notifications') on mount", async () => {
    mockBackendSuccess([]);

    renderHook(() => useNotifications());

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/notifications",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  // ── 4. Backend data preferred over localStorage ───────────────────────────
  it("replaces localStorage notifications with backend data when backend succeeds", async () => {
    seedLocalStorage([makeNotification({ id: "local-1", title: "Local" })]);
    const backendItems = [makeNotification({ id: "backend-1", title: "Backend" })];
    mockBackendSuccess(backendItems);

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.items.some((n) => n.id === "backend-1")).toBe(true);
    });

    expect(result.current.items.some((n) => n.id === "local-1")).toBe(false);
  });

  // ── 5. Network-error fallback to localStorage ─────────────────────────────
  it("falls back to localStorage notifications when backend throws a network error", async () => {
    const stored = [makeNotification({ id: "local-1", title: "Offline Notification" })];
    seedLocalStorage(stored);
    mockBackendNetworkError();

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].title).toBe("Offline Notification");
  });

  // ── 6. Non-ok response fallback ───────────────────────────────────────────
  it("falls back to localStorage notifications when backend returns a non-ok response", async () => {
    const stored = [makeNotification({ id: "local-2", title: "Auth Fallback" })];
    seedLocalStorage(stored);
    mockBackendNonOk();

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    expect(result.current.items.some((n) => n.id === "local-2")).toBe(true);
  });

  // ── 7. Backend data saved to localStorage ────────────────────────────────
  it("saves backend data to localStorage when backend succeeds", async () => {
    const backendItems = [makeNotification({ id: "b1", title: "From Backend" })];
    mockBackendSuccess(backendItems);

    renderHook(() => useNotifications());

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    const savedRaw = localStorageData[STORAGE_KEY];
    expect(savedRaw).toBeDefined();
    const saved: Notification[] = JSON.parse(savedRaw);
    expect(saved.some((n) => n.id === "b1")).toBe(true);
  });

  // ── 8. add() creates a notification ──────────────────────────────────────
  it("add() prepends a new notification to the items list", async () => {
    mockBackendSuccess([]);

    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.add({ level: "error", title: "New Error", source: "CI" });
    });

    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0].title).toBe("New Error");
    expect(result.current.items[0].level).toBe("error");
    expect(result.current.items[0].read).toBe(false);
  });

  // ── 9. unreadCount reflects unread items ─────────────────────────────────
  it("unreadCount returns the number of unread notifications", async () => {
    const items = [
      makeNotification({ id: "n1", read: false }),
      makeNotification({ id: "n2", read: true }),
      makeNotification({ id: "n3", read: false }),
    ];
    mockBackendSuccess(items);

    const { result } = renderHook(() => useNotifications());

    await waitFor(() => {
      expect(result.current.items).toHaveLength(3);
    });

    expect(result.current.unreadCount).toBe(2);
  });

  // ── 10. markRead() marks one notification read ────────────────────────────
  it("markRead() marks a single notification as read", async () => {
    const items = [makeNotification({ id: "r1", read: false })];
    seedLocalStorage(items);
    mockBackendSuccess(items);

    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.markRead("r1");
    });

    const marked = result.current.items.find((n) => n.id === "r1");
    expect(marked?.read).toBe(true);
    expect(result.current.unreadCount).toBe(0);
  });

  // ── 11. markAllRead() marks all notifications read ────────────────────────
  it("markAllRead() sets read=true on every notification", async () => {
    const items = [
      makeNotification({ id: "m1", read: false }),
      makeNotification({ id: "m2", read: false }),
    ];
    seedLocalStorage(items);
    mockBackendSuccess(items);

    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.markAllRead();
    });

    expect(result.current.unreadCount).toBe(0);
    expect(result.current.items.every((n) => n.read)).toBe(true);
  });

  // ── 12. remove() deletes a notification ──────────────────────────────────
  it("remove() deletes the notification with the given id", async () => {
    const n1 = makeNotification({ id: "d1", title: "To Delete" });
    const n2 = makeNotification({ id: "d2", title: "Keep" });
    seedLocalStorage([n1, n2]);
    mockBackendSuccess([n1, n2]);

    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.remove("d1");
    });

    expect(result.current.items.some((n) => n.id === "d1")).toBe(false);
    expect(result.current.items.some((n) => n.id === "d2")).toBe(true);
  });

  // ── 13. clear() removes all notifications ────────────────────────────────
  it("clear() empties the notifications list", async () => {
    const items = [
      makeNotification({ id: "c1" }),
      makeNotification({ id: "c2" }),
    ];
    seedLocalStorage(items);
    mockBackendSuccess(items);

    const { result } = renderHook(() => useNotifications());
    await waitFor(() => expect(result.current.items).toHaveLength(2));

    act(() => {
      result.current.clear();
    });

    expect(result.current.items).toHaveLength(0);
    expect(result.current.unreadCount).toBe(0);
  });
});
