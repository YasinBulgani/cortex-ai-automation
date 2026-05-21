/** @jest-environment jsdom */
import { renderHook, act } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Drain the microtask queue without touching timers.
 * Chains many Promise.resolve() ticks so that deeply nested async state
 * setters (fetch → json → setState) all settle before assertions run.
 */
async function drainMicrotasks(depth = 10): Promise<void> {
  for (let i = 0; i < depth; i++) {
    // eslint-disable-next-line no-await-in-loop
    await Promise.resolve();
  }
}

const flushMicrotasks = () => act(() => drainMicrotasks());

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock("@/lib/useWebSocket", () => ({
  useWebSocket: jest.fn(),
}));

jest.mock("@/lib/api-client", () => ({
  getToken: jest.fn(() => "test-token"),
}));

import { useWebSocket } from "@/lib/useWebSocket";
import { useRealtimeExecution } from "../useRealtimeExecution";
import { useCoreRuntime } from "../core-runtime";
import { useLiveData } from "../use-live-data";

const mockUseWebSocket = useWebSocket as jest.Mock;

// ---------------------------------------------------------------------------
// WebSocket mock factory (for useLiveData tests)
// ---------------------------------------------------------------------------

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 0; // CONNECTING

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = 3; // CLOSED
    this.onclose?.();
  }

  open() {
    this.readyState = 1; // OPEN
    this.onopen?.();
  }

  /** Simulate an error followed by close → triggers WS → polling fallback. */
  triggerError() {
    this.onerror?.();
    this.close();
  }

  receive(data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    this.onmessage?.(event);
  }
}

let OriginalWebSocket: typeof WebSocket;

// ===========================================================================
// useRealtimeExecution
// ===========================================================================

describe("useRealtimeExecution", () => {
  beforeEach(() => {
    mockUseWebSocket.mockReturnValue({ messages: [], connected: false });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("does not call onRefresh when messages is empty", () => {
    const onRefresh = jest.fn();
    mockUseWebSocket.mockReturnValue({ messages: [] });

    renderHook(() => useRealtimeExecution("proj-1", onRefresh));
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("calls onRefresh when execution.completed arrives with matching projectId", () => {
    const onRefresh = jest.fn();
    mockUseWebSocket.mockReturnValue({
      messages: [{ type: "execution.completed", payload: { project_id: "proj-1" } }],
    });

    renderHook(() => useRealtimeExecution("proj-1", onRefresh));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("calls onRefresh when execution.updated arrives with no projectId in payload", () => {
    const onRefresh = jest.fn();
    mockUseWebSocket.mockReturnValue({
      messages: [{ type: "execution.updated", payload: {} }],
    });

    renderHook(() => useRealtimeExecution("proj-1", onRefresh));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("calls onRefresh when execution.failed arrives with matching projectId", () => {
    const onRefresh = jest.fn();
    mockUseWebSocket.mockReturnValue({
      messages: [{ type: "execution.failed", payload: { project_id: "proj-2" } }],
    });

    renderHook(() => useRealtimeExecution("proj-2", onRefresh));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("does NOT call onRefresh for non-execution message types", () => {
    const onRefresh = jest.fn();
    mockUseWebSocket.mockReturnValue({
      messages: [{ type: "test.done", payload: {} }],
    });

    renderHook(() => useRealtimeExecution("proj-1", onRefresh));
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("does NOT call onRefresh when projectId does not match payload.project_id", () => {
    const onRefresh = jest.fn();
    mockUseWebSocket.mockReturnValue({
      messages: [{ type: "execution.completed", payload: { project_id: "other-project" } }],
    });

    renderHook(() => useRealtimeExecution("proj-1", onRefresh));
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it("always uses the latest onRefresh via ref — does not stale-close over old callback", () => {
    const onRefresh1 = jest.fn();
    const onRefresh2 = jest.fn();
    const messages = [{ type: "execution.completed", payload: {} }];
    mockUseWebSocket.mockReturnValue({ messages });

    const { rerender } = renderHook(
      ({ cb }) => useRealtimeExecution("proj-1", cb),
      { initialProps: { cb: onRefresh1 } }
    );

    // First render fires with onRefresh1 (messages same reference → effect ran once).
    expect(onRefresh1).toHaveBeenCalledTimes(1);

    // Rerender with new callback but same messages (no new effect run).
    rerender({ cb: onRefresh2 });
    expect(onRefresh2).not.toHaveBeenCalled();

    // Update messages reference → effect re-runs, should call the *latest* callback.
    const newMessages = [{ type: "execution.updated", payload: {} }];
    mockUseWebSocket.mockReturnValue({ messages: newMessages });
    rerender({ cb: onRefresh2 });
    expect(onRefresh2).toHaveBeenCalledTimes(1);
    // onRefresh1 is NOT called again.
    expect(onRefresh1).toHaveBeenCalledTimes(1);
  });
});

// ===========================================================================
// useCoreRuntime
// ===========================================================================

describe("useCoreRuntime", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        backendReady: true,
        services: [],
        checkedAt: new Date().toISOString(),
      }),
    }) as jest.Mock;
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("starts with loading=true before the fetch resolves", () => {
    const { result } = renderHook(() => useCoreRuntime());
    // Synchronous initial state — fetch hasn't resolved yet.
    expect(result.current.loading).toBe(true);
  });

  it("does not throw when rendered", () => {
    expect(() => {
      renderHook(() => useCoreRuntime());
    }).not.toThrow();
  });

  it("returns an object with all expected shape properties after fetch resolves", async () => {
    const { result } = renderHook(() => useCoreRuntime());
    await flushMicrotasks();

    expect(result.current).toMatchObject({
      loading: expect.any(Boolean),
      backendReady: expect.any(Boolean),
      services: expect.any(Array),
      authState: expect.stringMatching(/^(ready|preparing|missing)$/),
      canQueryProjects: expect.any(Boolean),
      refresh: expect.any(Function),
    });
    expect(
      result.current.checkedAt === null || typeof result.current.checkedAt === "string"
    ).toBe(true);
    expect(
      result.current.blockingReason === null ||
        typeof result.current.blockingReason === "string"
    ).toBe(true);
  });

  it("authState is one of the expected string literals after fetch resolves", async () => {
    const { result } = renderHook(() => useCoreRuntime());
    await flushMicrotasks();

    expect(["ready", "preparing", "missing"]).toContain(result.current.authState);
  });

  it("sets loading=false and backendReady=true after successful fetch", async () => {
    const { result } = renderHook(() => useCoreRuntime());
    await flushMicrotasks();

    expect(result.current.loading).toBe(false);
    expect(result.current.backendReady).toBe(true);
  });

  it("sets loading=false and error when fetch rejects", async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

    const { result } = renderHook(() => useCoreRuntime());
    await flushMicrotasks();

    expect(result.current.loading).toBe(false);
    expect(result.current.backendReady).toBe(false);
    expect(result.current.error).toBe("Network error");
  });

  it("canQueryProjects equals backendReady", async () => {
    const { result } = renderHook(() => useCoreRuntime());
    await flushMicrotasks();

    expect(result.current.canQueryProjects).toBe(result.current.backendReady);
  });

  it("cleans up the polling interval on unmount", () => {
    const clearIntervalSpy = jest.spyOn(window, "clearInterval");
    const { unmount } = renderHook(() => useCoreRuntime());
    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});

// ===========================================================================
// useLiveData
// ===========================================================================

describe("useLiveData", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    MockWebSocket.instances = [];
    OriginalWebSocket = global.WebSocket;
    global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ value: 42 }),
    }) as jest.Mock;
  });

  afterEach(() => {
    global.WebSocket = OriginalWebSocket;
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it("returns status 'connecting' initially when wsUrl is provided and enabled=true", () => {
    const { result } = renderHook(() =>
      useLiveData({ wsUrl: "ws://localhost/ws", pollUrl: "/api/data" })
    );
    // The hook sets "connecting" synchronously in the effect.
    expect(["connecting", "connected"]).toContain(result.current.status);
  });

  it("returns data=null initially", () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data" })
    );
    expect(result.current.data).toBeNull();
  });

  it("pause() is callable and transitions status to 'paused'", async () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data" })
    );

    act(() => { result.current.pause(); });
    await flushMicrotasks();

    expect(result.current.status).toBe("paused");
  });

  it("resume() is callable and transitions status away from 'paused'", async () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data" })
    );

    act(() => { result.current.pause(); });
    await flushMicrotasks();
    expect(result.current.status).toBe("paused");

    act(() => { result.current.resume(); });
    await flushMicrotasks();
    expect(result.current.status).not.toBe("paused");
  });

  it("enabled=false keeps status 'idle' and never fetches", () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data", enabled: false })
    );
    expect(result.current.status).toBe("idle");
    expect(result.current.data).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("falls back to polling when WebSocket errors out", async () => {
    const { result } = renderHook(() =>
      useLiveData({
        wsUrl: "ws://localhost/ws",
        pollUrl: "/api/data",
        interval: 5000,
      })
    );

    // Simulate WS error → close → startPolling()
    act(() => {
      const ws = MockWebSocket.instances[0];
      ws.triggerError();
    });
    await flushMicrotasks();

    expect(result.current.status).toBe("polling");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/data",
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("starts polling directly when no wsUrl is provided", async () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data", interval: 5000 })
    );

    await flushMicrotasks();

    expect(result.current.status).toBe("polling");
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("uses custom fetcher instead of global fetch when provided", async () => {
    const customFetcher = jest.fn().mockResolvedValue({ custom: true });

    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data", fetcher: customFetcher, interval: 5000 })
    );

    await flushMicrotasks();

    expect(customFetcher).toHaveBeenCalledWith("/api/data");
    expect(result.current.data).toEqual({ custom: true });
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("updates data and lastUpdate after a successful poll", async () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data", interval: 5000 })
    );

    await flushMicrotasks();

    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.lastUpdate).toBeInstanceOf(Date);
  });

  it("sets error when fetch rejects", async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("fetch failed"));

    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data", interval: 5000 })
    );

    await flushMicrotasks();

    expect(result.current.error).toBe("fetch failed");
  });

  it("fires additional fetches on each polling interval tick", async () => {
    const { result } = renderHook(() =>
      useLiveData({ pollUrl: "/api/data", interval: 5000 })
    );

    await flushMicrotasks(); // initial poll
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Advance time to trigger the setInterval callback.
    await act(async () => { jest.advanceTimersByTime(5000); });
    await flushMicrotasks(); // second poll
    expect(global.fetch).toHaveBeenCalledTimes(2);

    expect(result.current.status).toBe("polling");
  });
});
