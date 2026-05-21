import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebounce } from "./use-debounce";
import { useLocalStorage } from "./use-local-storage";
import { useCopyToClipboard } from "./use-copy-to-clipboard";
import { useClickOutside } from "./use-click-outside";

describe("useDebounce", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("returns initial value immediately", () => {
    const { result } = renderHook(() => useDebounce("hello", 100));
    expect(result.current).toBe("hello");
  });

  it("delays new value until delay elapses", () => {
    const { result, rerender } = renderHook(({ v }) => useDebounce(v, 100), {
      initialProps: { v: "a" },
    });
    rerender({ v: "b" });
    expect(result.current).toBe("a");
    act(() => { vi.advanceTimersByTime(99); });
    expect(result.current).toBe("a");
    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current).toBe("b");
  });

  it("resets timer on rapid changes", () => {
    const { result, rerender } = renderHook(({ v }) => useDebounce(v, 100), {
      initialProps: { v: "a" },
    });
    rerender({ v: "b" });
    act(() => { vi.advanceTimersByTime(50); });
    rerender({ v: "c" });
    act(() => { vi.advanceTimersByTime(99); });
    expect(result.current).toBe("a");
    act(() => { vi.advanceTimersByTime(1); });
    expect(result.current).toBe("c");
  });
});

describe("useLocalStorage", () => {
  beforeEach(() => {
    // jsdom localStorage may be partial — install a minimal in-memory shim
    const store: Record<string, string> = {};
    const mock: Storage = {
      get length() { return Object.keys(store).length; },
      clear: () => { for (const k of Object.keys(store)) delete store[k]; },
      getItem: (k: string) => (k in store ? store[k] : null),
      key: (i: number) => Object.keys(store)[i] ?? null,
      removeItem: (k: string) => { delete store[k]; },
      setItem: (k: string, v: string) => { store[k] = String(v); },
    };
    Object.defineProperty(window, "localStorage", { configurable: true, value: mock });
  });

  it("returns initial value when storage empty", () => {
    const { result } = renderHook(() => useLocalStorage("k1", "init"));
    expect(result.current[0]).toBe("init");
  });

  it("persists value to localStorage", () => {
    const { result } = renderHook(() => useLocalStorage("k2", 0));
    act(() => { result.current[1](42); });
    expect(result.current[0]).toBe(42);
    expect(JSON.parse(window.localStorage.getItem("k2")!)).toBe(42);
  });

  it("supports functional updater", () => {
    const { result } = renderHook(() => useLocalStorage("k3", 1));
    act(() => { result.current[1](prev => prev + 10); });
    expect(result.current[0]).toBe(11);
  });

  it("remove() clears storage and resets value", () => {
    const { result } = renderHook(() => useLocalStorage("k4", "init"));
    act(() => { result.current[1]("changed"); });
    act(() => { result.current[2](); });
    expect(result.current[0]).toBe("init");
    expect(window.localStorage.getItem("k4")).toBeNull();
  });

  it("reads existing value from storage on mount", () => {
    window.localStorage.setItem("k5", JSON.stringify({ a: 1 }));
    const { result } = renderHook(() => useLocalStorage("k5", { a: 0 }));
    expect(result.current[0]).toEqual({ a: 1 });
  });
});

describe("useCopyToClipboard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });
  afterEach(() => vi.useRealTimers());

  it("starts uncopied with no error", () => {
    const { result } = renderHook(() => useCopyToClipboard());
    expect(result.current.copied).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets copied=true after successful copy", async () => {
    const { result } = renderHook(() => useCopyToClipboard(1000));
    await act(async () => {
      await result.current.copy("hello");
    });
    expect(result.current.copied).toBe(true);
  });

  it("resets copied after timeout", async () => {
    const { result } = renderHook(() => useCopyToClipboard(500));
    await act(async () => { await result.current.copy("x"); });
    expect(result.current.copied).toBe(true);
    act(() => { vi.advanceTimersByTime(500); });
    expect(result.current.copied).toBe(false);
  });

  it("sets error when writeText throws", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    const { result } = renderHook(() => useCopyToClipboard());
    await act(async () => { await result.current.copy("x"); });
    expect(result.current.error?.message).toBe("denied");
    expect(result.current.copied).toBe(false);
  });
});

describe("useClickOutside", () => {
  it("calls callback when clicking outside ref element", () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useClickOutside<HTMLDivElement>(fn));
    const inside = document.createElement("div");
    const outside = document.createElement("button");
    document.body.appendChild(inside);
    document.body.appendChild(outside);
    (result.current as { current: HTMLDivElement | null }).current = inside;

    outside.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(fn).toHaveBeenCalled();

    fn.mockClear();
    inside.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(fn).not.toHaveBeenCalled();

    document.body.removeChild(inside);
    document.body.removeChild(outside);
  });

  it("respects enabled=false", () => {
    const fn = vi.fn();
    const { result } = renderHook(() => useClickOutside<HTMLDivElement>(fn, false));
    const inside = document.createElement("div");
    const outside = document.createElement("button");
    document.body.appendChild(inside);
    document.body.appendChild(outside);
    (result.current as { current: HTMLDivElement | null }).current = inside;
    outside.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(fn).not.toHaveBeenCalled();
    document.body.removeChild(inside);
    document.body.removeChild(outside);
  });
});
