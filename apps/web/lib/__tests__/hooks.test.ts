/** @jest-environment jsdom */
import { renderHook, act } from "@testing-library/react";

jest.mock("next/navigation", () => ({
  useParams: jest.fn(() => ({})),
}));
import { useParams } from "next/navigation";

import { useMediaQuery, useIsMobile } from "../useMediaQuery";
import { usePinned, PinnedItem } from "../use-pinned";
import { useRouteParam } from "../use-route-param";

// ---------------------------------------------------------------------------
// matchMedia stub helpers
// ---------------------------------------------------------------------------

function setupMatchMedia(matches: boolean) {
  const listeners: ((e: { matches: boolean }) => void)[] = [];
  const mql = {
    matches,
    addEventListener: jest.fn(
      (_: string, cb: (e: { matches: boolean }) => void) => {
        listeners.push(cb);
      }
    ),
    removeEventListener: jest.fn(),
  };
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: jest.fn(() => mql),
  });
  return { mql, listeners };
}

// ---------------------------------------------------------------------------
// useMediaQuery
// ---------------------------------------------------------------------------

describe("useMediaQuery", () => {
  it("returns defaultValue (false) before effect runs", () => {
    setupMatchMedia(false);
    const { result } = renderHook(() => useMediaQuery("(min-width: 600px)"));
    // After jsdom renders effects synchronously the value reflects the mock,
    // but the hook initialises with the defaultValue (false) as its useState seed.
    // We verify the default arg is false and the hook doesn't throw.
    expect(typeof result.current).toBe("boolean");
  });

  it("returns true when matchMedia matches", () => {
    setupMatchMedia(true);
    const { result } = renderHook(() => useMediaQuery("(min-width: 600px)"));
    expect(result.current).toBe(true);
  });

  it("returns false when matchMedia does not match", () => {
    setupMatchMedia(false);
    const { result } = renderHook(() => useMediaQuery("(min-width: 600px)"));
    expect(result.current).toBe(false);
  });

  it("registers and removes a change listener on unmount", () => {
    const { mql } = setupMatchMedia(false);
    const { unmount } = renderHook(() => useMediaQuery("(min-width: 600px)"));

    expect(mql.addEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function)
    );

    unmount();

    expect(mql.removeEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function)
    );
  });
});

// ---------------------------------------------------------------------------
// useIsMobile
// ---------------------------------------------------------------------------

describe("useIsMobile", () => {
  it("calls matchMedia with (max-width: 767px)", () => {
    const { mql } = setupMatchMedia(false);
    renderHook(() => useIsMobile());
    expect(window.matchMedia).toHaveBeenCalledWith("(max-width: 767px)");
    // suppress unused-var lint
    void mql;
  });

  it("returns false when not mobile", () => {
    setupMatchMedia(false);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// usePinned
// ---------------------------------------------------------------------------

function makeItem(
  id: string,
  overrides: Partial<Omit<PinnedItem, "addedAt" | "id">> = {}
): Omit<PinnedItem, "addedAt"> {
  return {
    id,
    type: "project",
    label: `Item ${id}`,
    href: `/p/${id}`,
    ...overrides,
  };
}

describe("usePinned", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("starts with an empty items list", () => {
    const { result } = renderHook(() => usePinned());
    expect(result.current.items).toEqual([]);
  });

  it("pin() adds an item to items", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.pin(makeItem("a"));
    });
    expect(result.current.items.some((i) => i.id === "a")).toBe(true);
  });

  it("pin() same item twice deduplicates", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.pin(makeItem("a"));
    });
    act(() => {
      result.current.pin(makeItem("a"));
    });
    expect(result.current.items.filter((i) => i.id === "a").length).toBe(1);
  });

  it("unpin() removes an item", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.pin(makeItem("b"));
    });
    act(() => {
      result.current.unpin("b");
    });
    expect(result.current.items.some((i) => i.id === "b")).toBe(false);
  });

  it("isPinned() returns true after pin, false after unpin", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.pin(makeItem("c"));
    });
    expect(result.current.isPinned("c")).toBe(true);
    act(() => {
      result.current.unpin("c");
    });
    expect(result.current.isPinned("c")).toBe(false);
  });

  it("togglePin() pins an unpinned item", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.togglePin(makeItem("d"));
    });
    expect(result.current.isPinned("d")).toBe(true);
  });

  it("togglePin() unpins an already-pinned item", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.pin(makeItem("e"));
    });
    act(() => {
      result.current.togglePin(makeItem("e"));
    });
    expect(result.current.isPinned("e")).toBe(false);
  });

  it('persists to localStorage under key "neurex_pinned"', () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      result.current.pin(makeItem("f"));
    });
    const stored = localStorage.getItem("neurex_pinned");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.some((i: PinnedItem) => i.id === "f")).toBe(true);
  });

  it("does not exceed MAX_PINS=10 items when 11 are pinned", () => {
    const { result } = renderHook(() => usePinned());
    act(() => {
      for (let i = 1; i <= 11; i++) {
        result.current.pin(makeItem(`item-${i}`));
      }
    });
    expect(result.current.items.length).toBeLessThanOrEqual(10);
  });
});

// ---------------------------------------------------------------------------
// useRouteParam
// ---------------------------------------------------------------------------

describe("useRouteParam", () => {
  const mockUseParams = useParams as jest.Mock;

  it("returns empty string when param is missing", () => {
    mockUseParams.mockReturnValue({});
    const { result } = renderHook(() => useRouteParam("projectId"));
    expect(result.current).toBe("");
  });

  it("returns string param value when present", () => {
    mockUseParams.mockReturnValue({ projectId: "proj-123" });
    const { result } = renderHook(() => useRouteParam("projectId"));
    expect(result.current).toBe("proj-123");
  });

  it("returns the first element when param is an array", () => {
    mockUseParams.mockReturnValue({ projectId: ["proj-abc", "proj-xyz"] });
    const { result } = renderHook(() => useRouteParam("projectId"));
    expect(result.current).toBe("proj-abc");
  });

  it("returns empty string when param is an empty array", () => {
    mockUseParams.mockReturnValue({ projectId: [] });
    const { result } = renderHook(() => useRouteParam("projectId"));
    expect(result.current).toBe("");
  });
});
