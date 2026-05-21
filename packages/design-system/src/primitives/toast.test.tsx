import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { ToastProvider, useToast } from "./toast";

function TriggerHarness({ onMount }: { onMount: (api: ReturnType<typeof useToast>) => void }) {
  const api = useToast();
  React.useEffect(() => onMount(api), [api, onMount]);
  return null;
}

// Workaround for missing React import in this scope when using the harness
import * as React from "react";

describe("ToastProvider + useToast", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("renders nothing initially", () => {
    render(
      <ToastProvider>
        <div>app</div>
      </ToastProvider>,
    );
    expect(screen.getByTestId("toast-container").children.length).toBe(0);
  });

  it("opens info toast via toast(string) shorthand", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => { api.toast("hello"); });
    expect(screen.getByText("hello")).toBeInTheDocument();
    expect(screen.getByTestId("toast-info")).toBeInTheDocument();
  });

  it("variant helpers create proper role + variant", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => { api.error("bad"); });
    expect(screen.getByRole("alert")).toHaveTextContent("bad");
    expect(screen.getByTestId("toast-danger")).toBeInTheDocument();
  });

  it("auto-dismisses after duration_ms", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => { api.toast({ message: "tmp", duration_ms: 500 }); });
    expect(screen.getByText("tmp")).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(500); });
    expect(screen.queryByText("tmp")).not.toBeInTheDocument();
  });

  it("duration_ms=0 keeps toast visible", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => { api.toast({ message: "sticky", duration_ms: 0 }); });
    act(() => { vi.advanceTimersByTime(60_000); });
    expect(screen.getByText("sticky")).toBeInTheDocument();
  });

  it("dismiss(id) removes specific toast", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    let id1 = 0, id2 = 0;
    act(() => {
      id1 = api.toast({ message: "first", duration_ms: 0 });
      id2 = api.toast({ message: "second", duration_ms: 0 });
    });
    act(() => { api.dismiss(id1); });
    expect(screen.queryByText("first")).not.toBeInTheDocument();
    expect(screen.getByText("second")).toBeInTheDocument();
    expect(id2).toBeGreaterThan(id1);
  });

  it("dismissAll clears all toasts", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => {
      api.toast({ message: "a", duration_ms: 0 });
      api.toast({ message: "b", duration_ms: 0 });
      api.toast({ message: "c", duration_ms: 0 });
    });
    expect(screen.getByTestId("toast-container").children.length).toBe(3);
    act(() => { api.dismissAll(); });
    expect(screen.getByTestId("toast-container").children.length).toBe(0);
  });

  it("respects max — older toasts drop off", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider max={2}>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => {
      api.toast({ message: "1", duration_ms: 0 });
      api.toast({ message: "2", duration_ms: 0 });
      api.toast({ message: "3", duration_ms: 0 });
    });
    expect(screen.queryByText("1")).not.toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("close button dismisses toast", () => {
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => { api.toast({ message: "click me", duration_ms: 0 }); });
    act(() => { fireEvent.click(screen.getByRole("button", { name: "Kapat" })); });
    expect(screen.queryByText("click me")).not.toBeInTheDocument();
  });

  it("action button calls handler", () => {
    const onAction = vi.fn();
    let api!: ReturnType<typeof useToast>;
    render(
      <ToastProvider>
        <TriggerHarness onMount={x => { api = x; }} />
      </ToastProvider>,
    );
    act(() => {
      api.toast({
        message: "Saved",
        duration_ms: 0,
        action: { label: "Undo", onClick: onAction },
      });
    });
    act(() => { fireEvent.click(screen.getByRole("button", { name: "Undo" })); });
    expect(onAction).toHaveBeenCalledOnce();
  });

  it("throws when useToast called outside provider", () => {
    // Suppress React error log
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    try {
      expect(() => render(<TriggerHarness onMount={() => {}} />)).toThrow(/ToastProvider/);
    } finally {
      spy.mockRestore();
    }
  });
});
