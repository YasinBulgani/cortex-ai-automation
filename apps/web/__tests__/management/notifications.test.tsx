/** @jest-environment jsdom */
/**
 * M-45 Notification Inbox frontend tests.
 *
 * Covers the `<NotificationBell>` component and the SSE-event reaction
 * inside `useNotificationStream`. Network is fully mocked.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, render, screen, fireEvent, waitFor, act } from "@testing-library/react";

const apiFetchMock = jest.fn();
jest.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

jest.mock("next/link", () => {
  const MockLink = ({ href, children, ...rest }: any) => (
    <a href={href} {...rest}>{children}</a>
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

import {
  NotificationBell,
} from "@/app/(dashboard)/p/[projectId]/management/_components/NotificationBell";
import {
  type MgmtNotification,
  useNotificationStream,
  notificationKeys,
} from "@/lib/hooks/use-mgmt-notifications";

const TENANT = "00000000-0000-0000-0000-000000000001";
const BOB = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

function makeNotif(over: Partial<MgmtNotification> = {}): MgmtNotification {
  return {
    id: over.id ?? "n-1",
    tenant_id: TENANT,
    user_id: BOB,
    project_id: null,
    kind: "system",
    title: "Hello",
    body: "world",
    link_path: null,
    severity: "info",
    source_trace: {},
    read_at: null,
    archived_at: null,
    created_at: "2026-05-27T10:00:00Z",
    ...over,
  };
}

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
}

function withQc(qc: QueryClient, children: React.ReactNode) {
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ----- EventSource mock so useNotificationStream doesn't blow up -----

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  listeners: Record<string, ((ev: MessageEvent) => void)[]> = {};
  onerror: (() => void) | null = null;
  close = jest.fn();
  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  addEventListener(name: string, cb: (ev: MessageEvent) => void) {
    (this.listeners[name] ??= []).push(cb);
  }
  emit(name: string, data: unknown) {
    for (const cb of this.listeners[name] ?? []) {
      cb({ data: JSON.stringify(data) } as MessageEvent);
    }
  }
}

beforeEach(() => {
  apiFetchMock.mockReset();
  MockEventSource.instances = [];
  // @ts-expect-error stub the global
  global.EventSource = MockEventSource;
});

// Route every API path returned by the hooks to a small deterministic stub.
function defaultApiRouter(
  state: { notifications: MgmtNotification[]; unread: number } = {
    notifications: [makeNotif({ id: "n1", title: "Unread one" })],
    unread: 1,
  },
) {
  apiFetchMock.mockImplementation((url: string, init?: any) => {
    if (typeof url !== "string") return Promise.resolve(null);
    if (url.includes("/unread-count")) {
      return Promise.resolve({ unread: state.unread, total: state.notifications.length });
    }
    if (url.includes("/read-all") && init?.method === "POST") {
      state.notifications = state.notifications.map((n) => ({
        ...n,
        read_at: n.read_at ?? new Date().toISOString(),
      }));
      state.unread = 0;
      return Promise.resolve({ updated: state.notifications.length });
    }
    if (/\/read$/.test(url) && init?.method === "POST") {
      return Promise.resolve(state.notifications[0]);
    }
    if (/\/archive$/.test(url)) {
      return Promise.resolve(state.notifications[0]);
    }
    if (url.startsWith("/api/v1/test-management/notifications")) {
      const unreadOnly = url.includes("unread_only=true");
      const list = unreadOnly
        ? state.notifications.filter((n) => n.read_at == null)
        : state.notifications;
      return Promise.resolve(list);
    }
    return Promise.resolve(null);
  });
  return state;
}

describe("<NotificationBell>", () => {
  it("renders bell with unread badge", async () => {
    defaultApiRouter({ notifications: [makeNotif()], unread: 3 });
    const qc = makeQc();
    await act(async () => {
      render(withQc(qc, <NotificationBell />));
    });
    await waitFor(() => expect(screen.getByText("3")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /3 unread/i })).toBeInTheDocument();
  });

  it("clicking the bell opens the dropdown and lists notifications", async () => {
    defaultApiRouter({
      notifications: [makeNotif({ id: "n1", title: "Welcome aboard" })],
      unread: 1,
    });
    const qc = makeQc();
    await act(async () => {
      render(withQc(qc, <NotificationBell />));
    });
    await waitFor(() => expect(screen.getByRole("button", { name: /Notifications/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Notifications/i }));
    await waitFor(() =>
      expect(screen.getByText("Welcome aboard")).toBeInTheDocument(),
    );
  });

  it('"Mark all read" button calls /read-all', async () => {
    defaultApiRouter({
      notifications: [makeNotif({ id: "n1", title: "A" })],
      unread: 1,
    });
    const qc = makeQc();
    await act(async () => {
      render(withQc(qc, <NotificationBell />));
    });
    await waitFor(() => expect(screen.getByText("1")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Notifications/i }));
    await waitFor(() => expect(screen.getByText("A")).toBeInTheDocument());

    const markAll = screen.getByRole("button", { name: /Mark all read/i });
    await act(async () => {
      fireEvent.click(markAll);
    });
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/api/v1/test-management/notifications/read-all",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("unread-only toggle filters network calls", async () => {
    defaultApiRouter({
      notifications: [
        makeNotif({ id: "n1", title: "Unread", read_at: null }),
        makeNotif({ id: "n2", title: "Already read", read_at: "2026-05-26T10:00:00Z" }),
      ],
      unread: 1,
    });
    const qc = makeQc();
    await act(async () => {
      render(withQc(qc, <NotificationBell />));
    });
    fireEvent.click(screen.getByRole("button", { name: /Notifications/i }));
    await waitFor(() => expect(screen.getByText("Unread")).toBeInTheDocument());
    expect(screen.getByText("Already read")).toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: /Show unread only/i });
    await act(async () => {
      fireEvent.click(toggle);
    });
    await waitFor(() => {
      const calls = apiFetchMock.mock.calls.filter(
        (c) => typeof c[0] === "string" && c[0].includes("unread_only=true"),
      );
      expect(calls.length).toBeGreaterThan(0);
    });
  });

  it("renders empty state when no notifications", async () => {
    defaultApiRouter({ notifications: [], unread: 0 });
    const qc = makeQc();
    await act(async () => {
      render(withQc(qc, <NotificationBell />));
    });
    fireEvent.click(screen.getByRole("button", { name: /Notifications/ }));
    await waitFor(() => expect(screen.getByText(/Nothing here yet/i)).toBeInTheDocument());
  });
});

describe("useNotificationStream", () => {
  it("opens an EventSource and reacts to a 'notification' event", async () => {
    apiFetchMock.mockResolvedValue([]);
    const qc = makeQc();
    const invalidateSpy = jest.spyOn(qc, "invalidateQueries");

    const wrapper = ({ children }: { children: React.ReactNode }) => withQc(qc, children);
    const { result } = renderHook(() => useNotificationStream(true), { wrapper });

    expect(MockEventSource.instances).toHaveLength(1);
    const es = MockEventSource.instances[0];
    expect(es.url).toMatch(/\/api\/v1\/test-management\/notifications\/stream$/);

    const payload = makeNotif({ id: "live-1", title: "Live!" });
    await act(async () => {
      es.emit("notification", payload);
    });

    await waitFor(() => expect(result.current?.id).toBe("live-1"));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: notificationKeys.all }),
    );
  });

  it("noop when disabled", () => {
    apiFetchMock.mockResolvedValue([]);
    const qc = makeQc();
    const wrapper = ({ children }: { children: React.ReactNode }) => withQc(qc, children);
    renderHook(() => useNotificationStream(false), { wrapper });
    expect(MockEventSource.instances).toHaveLength(0);
  });
});

describe("useNotificationStream backoff", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  function triggerError(es: MockEventSource) {
    // The hook assigns es.onerror after construction; invoke it manually.
    es.onerror?.();
  }

  it("schedules reconnect with exponential backoff: 1s → 2s → 4s, capped at 30s", () => {
    apiFetchMock.mockResolvedValue([]);
    const qc = makeQc();
    const wrapper = ({ children }: { children: React.ReactNode }) => withQc(qc, children);
    renderHook(() => useNotificationStream(true), { wrapper });

    const setTimeoutSpy = jest.spyOn(global, "setTimeout");

    expect(MockEventSource.instances).toHaveLength(1);
    // 1st error → 1s delay
    act(() => triggerError(MockEventSource.instances[0]));
    expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 1_000);

    // Advance — new EventSource is constructed.
    act(() => {
      jest.advanceTimersByTime(1_000);
    });
    expect(MockEventSource.instances).toHaveLength(2);

    // 2nd error → 2s delay
    act(() => triggerError(MockEventSource.instances[1]));
    expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 2_000);

    act(() => {
      jest.advanceTimersByTime(2_000);
    });
    expect(MockEventSource.instances).toHaveLength(3);

    // 3rd error → 4s delay
    act(() => triggerError(MockEventSource.instances[2]));
    expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 4_000);

    setTimeoutSpy.mockRestore();
  });

  it("resets backoff after a successful 'open' event", () => {
    apiFetchMock.mockResolvedValue([]);
    const qc = makeQc();
    const wrapper = ({ children }: { children: React.ReactNode }) => withQc(qc, children);
    renderHook(() => useNotificationStream(true), { wrapper });
    const setTimeoutSpy = jest.spyOn(global, "setTimeout");

    // First failure → 1s
    act(() => triggerError(MockEventSource.instances[0]));
    expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 1_000);
    act(() => {
      jest.advanceTimersByTime(1_000);
    });
    // Second failure → 2s
    act(() => triggerError(MockEventSource.instances[1]));
    expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 2_000);
    act(() => {
      jest.advanceTimersByTime(2_000);
    });
    // Now simulate a successful open on the 3rd connection.
    const es3 = MockEventSource.instances[2];
    act(() => {
      es3.listeners["open"]?.forEach((cb) => cb({} as MessageEvent));
    });
    // Next error should restart at 1s.
    act(() => triggerError(es3));
    expect(setTimeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 1_000);

    setTimeoutSpy.mockRestore();
  });

  it("caps backoff delay at 30s after many failures", () => {
    apiFetchMock.mockResolvedValue([]);
    const qc = makeQc();
    const wrapper = ({ children }: { children: React.ReactNode }) => withQc(qc, children);
    renderHook(() => useNotificationStream(true), { wrapper });
    const setTimeoutSpy = jest.spyOn(global, "setTimeout");

    // Storm of errors — each must yield a delay ≤ 30_000.
    let lastIdx = 0;
    for (let i = 0; i < 10; i += 1) {
      const es = MockEventSource.instances[lastIdx];
      act(() => triggerError(es));
      const lastDelay = setTimeoutSpy.mock.calls[setTimeoutSpy.mock.calls.length - 1][1] as number;
      expect(lastDelay).toBeLessThanOrEqual(30_000);
      act(() => {
        jest.advanceTimersByTime(lastDelay);
      });
      lastIdx += 1;
    }

    setTimeoutSpy.mockRestore();
  });
});

describe("LLM digest button in <NotificationBell>", () => {
  it("clicking AI Özet toggles the digest panel and fetches /digest", async () => {
    const digestPayload = {
      window: "24h",
      generated_at: "2026-05-28T00:00:00Z",
      source: "llm",
      total_items: 5,
      groups: [
        { theme: "Mentions", count: 3, oneLine: "You were mentioned 3x" },
        { theme: "System", count: 2, oneLine: "Two system alerts" },
      ],
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (typeof url !== "string") return Promise.resolve(null);
      if (url.includes("/notifications/digest")) {
        return Promise.resolve(digestPayload);
      }
      if (url.includes("/unread-count")) {
        return Promise.resolve({ unread: 0, total: 0 });
      }
      if (url.includes("/test-management/notifications")) {
        return Promise.resolve([]);
      }
      return Promise.resolve(null);
    });

    const qc = makeQc();
    await act(async () => {
      render(withQc(qc, <NotificationBell />));
    });
    // Open the dropdown.
    fireEvent.click(screen.getByRole("button", { name: /Notifications/i }));
    const digestBtn = await screen.findByRole("button", { name: /AI Özet/i });

    await act(async () => {
      fireEvent.click(digestBtn);
    });

    await waitFor(() => {
      const calls = apiFetchMock.mock.calls.filter(
        (c) => typeof c[0] === "string" && c[0].includes("/notifications/digest"),
      );
      expect(calls.length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      expect(screen.getByText(/Mentions/)).toBeInTheDocument();
    });
    expect(screen.getByText(/You were mentioned 3x/)).toBeInTheDocument();
  });
});
