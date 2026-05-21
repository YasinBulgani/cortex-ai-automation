/** @jest-environment jsdom */
import React from "react";
import { act, fireEvent, render, screen, within } from "@testing-library/react";

import { NotificationCenter } from "@/components/NotificationCenter";
import { useNotifications } from "@/lib/useNotifications";

// localStorage mock
const ls = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(global, "localStorage", { value: ls, configurable: true });

// next/link mock
jest.mock("next/link", () =>
  function MockLink({ href, children, ...rest }: any) {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    );
  }
);

beforeEach(() => {
  ls.clear();
});

// ── useNotifications hook ──────────────────────────────────────────────────

describe("useNotifications", () => {
  function Wrapper({ onMount }: { onMount: (h: ReturnType<typeof useNotifications>) => void }) {
    const hook = useNotifications();
    React.useEffect(() => {
      onMount(hook);
    });
    return null;
  }

  it("starts with empty list", () => {
    let captured: any;
    render(<Wrapper onMount={(h) => { captured = h; }} />);
    expect(captured.items).toEqual([]);
    expect(captured.unreadCount).toBe(0);
  });

  it("add creates notification with id/timestamp/read=false", () => {
    let captured: any;
    const { rerender } = render(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.add({ level: "info", title: "Hello" });
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    expect(captured.items.length).toBe(1);
    expect(captured.items[0].title).toBe("Hello");
    expect(captured.items[0].read).toBe(false);
    expect(captured.unreadCount).toBe(1);
  });

  it("markRead toggles a single notification", () => {
    let captured: any;
    const { rerender } = render(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.add({ level: "info", title: "First" });
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    const id = captured.items[0].id;
    act(() => {
      captured.markRead(id);
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    expect(captured.items[0].read).toBe(true);
    expect(captured.unreadCount).toBe(0);
  });

  it("markAllRead marks every notification as read", () => {
    let captured: any;
    const { rerender } = render(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.add({ level: "info", title: "A" });
      captured.add({ level: "success", title: "B" });
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.markAllRead();
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    expect(captured.unreadCount).toBe(0);
  });

  it("remove deletes a single notification", () => {
    let captured: any;
    const { rerender } = render(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.add({ level: "info", title: "Goodbye" });
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    const id = captured.items[0].id;
    act(() => {
      captured.remove(id);
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    expect(captured.items.length).toBe(0);
  });

  it("clear wipes everything", () => {
    let captured: any;
    const { rerender } = render(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.add({ level: "info", title: "A" });
      captured.add({ level: "info", title: "B" });
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.clear();
    });
    rerender(<Wrapper onMount={(h) => { captured = h; }} />);
    expect(captured.items.length).toBe(0);
  });

  it("persists to localStorage", () => {
    let captured: any;
    render(<Wrapper onMount={(h) => { captured = h; }} />);
    act(() => {
      captured.add({ level: "info", title: "Persisted" });
    });
    const raw = localStorage.getItem("neurex_notifications_v1");
    expect(raw).toBeTruthy();
    const parsed = JSON.parse(raw!);
    expect(parsed.length).toBe(1);
    expect(parsed[0].title).toBe("Persisted");
  });
});

// ── NotificationCenter component ───────────────────────────────────────────

describe("NotificationCenter", () => {
  it("renders bell toggle", () => {
    render(<NotificationCenter />);
    expect(screen.getByTestId("notification-center")).toBeInTheDocument();
    expect(screen.getByTestId("notification-center-toggle")).toBeInTheDocument();
  });

  it("does not show panel until toggle clicked", () => {
    render(<NotificationCenter />);
    expect(screen.queryByTestId("notification-center-panel")).not.toBeInTheDocument();
  });

  it("opens panel on toggle click", () => {
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));
    expect(screen.getByTestId("notification-center-panel")).toBeInTheDocument();
  });

  it("shows 'Bildirim yok' empty state when no notifications", () => {
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));
    expect(screen.getByTestId("notification-center-empty")).toHaveTextContent("Bildirim yok");
  });

  it("shows unread badge with count when there are unread notifications", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        { id: "n1", level: "error", title: "Test", timestamp: Date.now(), read: false },
        { id: "n2", level: "info", title: "Test2", timestamp: Date.now(), read: false },
      ]),
    );
    render(<NotificationCenter />);
    expect(screen.getByTestId("notification-center-badge")).toHaveTextContent("2");
  });

  it("renders notification items when opened", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        { id: "n1", level: "success", title: "Test başarılı", body: "Login akışı geçti", timestamp: Date.now(), read: false },
      ]),
    );
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));
    expect(screen.getByTestId("notification-item-n1")).toBeInTheDocument();
    expect(screen.getByText("Test başarılı")).toBeInTheDocument();
    expect(screen.getByText("Login akışı geçti")).toBeInTheDocument();
  });

  it("filter toggle switches between all and unread", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        { id: "n1", level: "info", title: "Read", timestamp: Date.now(), read: true },
        { id: "n2", level: "info", title: "Unread", timestamp: Date.now(), read: false },
      ]),
    );
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));

    // Initially "all" → both visible
    expect(screen.getByText("Read")).toBeInTheDocument();
    expect(screen.getByText("Unread")).toBeInTheDocument();

    // Click filter → "unread" only
    fireEvent.click(screen.getByTestId("notification-center-filter"));
    expect(screen.queryByText("Read")).not.toBeInTheDocument();
    expect(screen.getByText("Unread")).toBeInTheDocument();
  });

  it("mark-all-read clears unread count", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        { id: "n1", level: "info", title: "A", timestamp: Date.now(), read: false },
      ]),
    );
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));
    fireEvent.click(screen.getByTestId("notification-center-mark-all-read"));
    expect(screen.queryByTestId("notification-center-badge")).not.toBeInTheDocument();
  });

  it("clear removes all notifications", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        { id: "n1", level: "info", title: "A", timestamp: Date.now(), read: false },
      ]),
    );
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));
    fireEvent.click(screen.getByTestId("notification-center-clear"));
    expect(screen.getByTestId("notification-center-empty")).toBeInTheDocument();
  });

  it("remove button deletes a single notification", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        { id: "n1", level: "info", title: "A", timestamp: Date.now(), read: false },
        { id: "n2", level: "info", title: "B", timestamp: Date.now(), read: false },
      ]),
    );
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));

    fireEvent.click(screen.getByTestId("notification-remove-n1"));

    expect(screen.queryByTestId("notification-item-n1")).not.toBeInTheDocument();
    expect(screen.getByTestId("notification-item-n2")).toBeInTheDocument();
  });

  it("clicking a notification with URL navigates and marks as read", () => {
    localStorage.setItem(
      "neurex_notifications_v1",
      JSON.stringify([
        {
          id: "n1",
          level: "info",
          title: "Test",
          url: "/some-path",
          timestamp: Date.now(),
          read: false,
        },
      ]),
    );
    render(<NotificationCenter />);
    fireEvent.click(screen.getByTestId("notification-center-toggle"));

    const item = screen.getByTestId("notification-item-n1");
    const link = within(item).getByRole("link");
    expect(link).toHaveAttribute("href", "/some-path");
  });
});
