/** @jest-environment jsdom */
import { renderHook, act } from "@testing-library/react";
import { useWebSocket } from "../useWebSocket";

// ─── WebSocket mock factory ────────────────────────────────────────────────────
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = WebSocket.CONNECTING;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  }

  /** Test helper: simulate connection opening */
  open() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.();
  }

  /** Test helper: simulate receiving a message */
  receive(data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    this.onmessage?.(event);
  }

  /** Test helper: simulate malformed message */
  receiveRaw(data: string) {
    const event = { data } as MessageEvent;
    this.onmessage?.(event);
  }
}

let OriginalWebSocket: typeof WebSocket;

beforeEach(() => {
  MockWebSocket.instances = [];
  OriginalWebSocket = global.WebSocket;
  global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  jest.useFakeTimers();
});

afterEach(() => {
  global.WebSocket = OriginalWebSocket;
  jest.useRealTimers();
  jest.clearAllMocks();
});

describe("useWebSocket", () => {
  it("starts with connected=false and empty messages", () => {
    const { result } = renderHook(() => useWebSocket());
    expect(result.current.connected).toBe(false);
    expect(result.current.messages).toHaveLength(0);
  });

  it("creates a WebSocket on mount", () => {
    renderHook(() => useWebSocket());
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("sets connected=true when WebSocket opens", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      MockWebSocket.instances[0].open();
    });

    expect(result.current.connected).toBe(true);
  });

  it("stores received messages in state (newest first)", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      MockWebSocket.instances[0].open();
      MockWebSocket.instances[0].receive({ type: "test.done", payload: { id: 1 } });
      MockWebSocket.instances[0].receive({ type: "test.fail", payload: { id: 2 } });
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].type).toBe("test.fail"); // newest first
    expect(result.current.messages[1].type).toBe("test.done");
  });

  it("calls onMessage handler when message received", () => {
    const onMessage = jest.fn();
    renderHook(() => useWebSocket(onMessage));

    act(() => {
      MockWebSocket.instances[0].open();
      MockWebSocket.instances[0].receive({ type: "exec.progress", payload: { pct: 50 } });
    });

    expect(onMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: "exec.progress" })
    );
  });

  it("silently ignores malformed messages", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      MockWebSocket.instances[0].open();
      MockWebSocket.instances[0].receiveRaw("not-json-at-all{{{{");
    });

    expect(result.current.messages).toHaveLength(0);
  });

  it("clearMessages empties the messages array", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      MockWebSocket.instances[0].open();
      MockWebSocket.instances[0].receive({ type: "ping", payload: {} });
    });
    expect(result.current.messages).toHaveLength(1);

    act(() => { result.current.clearMessages(); });
    expect(result.current.messages).toHaveLength(0);
  });

  it("sets connected=false when WebSocket closes", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      MockWebSocket.instances[0].open();
    });
    expect(result.current.connected).toBe(true);

    act(() => {
      // Disable reconnect so we don't create more sockets
      // Directly invoke close — which will try to reconnect after a delay
      MockWebSocket.instances[0].readyState = WebSocket.CLOSED;
      MockWebSocket.instances[0].onclose?.();
    });

    expect(result.current.connected).toBe(false);
  });

  it("closes WebSocket and stops reconnect on unmount", () => {
    const { unmount } = renderHook(() => useWebSocket());
    const ws = MockWebSocket.instances[0];

    unmount();

    // After unmount, the WS is closed
    expect(ws.readyState).toBe(WebSocket.CLOSED);
    // No further reconnect timers should fire (reconnectEnabledRef = false)
    // Running timers should not create new WebSocket instances
    const countBefore = MockWebSocket.instances.length;
    act(() => { jest.runAllTimers(); });
    expect(MockWebSocket.instances.length).toBe(countBefore);
  });

  it("caps messages at 50", () => {
    const { result } = renderHook(() => useWebSocket());

    act(() => {
      MockWebSocket.instances[0].open();
      for (let i = 0; i < 60; i++) {
        MockWebSocket.instances[0].receive({ type: `msg.${i}`, payload: {} });
      }
    });

    expect(result.current.messages.length).toBeLessThanOrEqual(50);
  });
});
