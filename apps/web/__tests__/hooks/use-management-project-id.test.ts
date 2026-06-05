/** @jest-environment jsdom */
/**
 * useManagementProjectId unit tests.
 *
 * ADR-0012 backend-first pattern:
 *   Phase-1 — localStorage cache okunur, UI beklemeden render eder.
 *   Phase-2 — Backend fetch tamamlanır, cache güncellenir ve state set edilir.
 *
 * useEnsureManagementProject mock'lanır: gerçek ağ bağlantısı YOK.
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// --- Mock useEnsureManagementProject before importing the hook under test ---
const mutateAsyncMock = jest.fn();
jest.mock("@/lib/hooks/use-management", () => ({
  useEnsureManagementProject: () => ({ mutateAsync: mutateAsyncMock }),
}));

import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";

const LS_PREFIX = "neurex:mgmt_pid:";
function lsKey(pid: string) {
  return `${LS_PREFIX}${pid}`;
}

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

beforeEach(() => {
  localStorage.clear();
  mutateAsyncMock.mockReset();
  // Default: backend never resolves (simulate inflight to test initial state)
  mutateAsyncMock.mockReturnValue(new Promise(() => {}));
});

// ─── 1. projectId varken mpid döndürür ─────────────────────────────────────
describe("projectId varken", () => {
  test("başlangıçta projectId'yi döndürür (localStorage boşken)", () => {
    const { result } = renderHook(
      () => useManagementProjectId("proj-abc"),
      { wrapper: makeWrapper() },
    );
    // Phase-1: LS boş → projectId fallback
    expect(result.current).toBe("proj-abc");
  });

  test("backend başarılı yanıt verince mpid güncellenir", async () => {
    const backendMpid = "mgmt-999";
    mutateAsyncMock.mockResolvedValue({ id: backendMpid });

    const { result } = renderHook(
      () => useManagementProjectId("proj-abc"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current).toBe(backendMpid));
  });
});

// ─── 2. projectId yokken null/undefined döndürür ───────────────────────────
describe("projectId yokken", () => {
  test("undefined projectId → undefined döner", () => {
    mutateAsyncMock.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(
      () => useManagementProjectId(undefined),
      { wrapper: makeWrapper() },
    );
    expect(result.current).toBeUndefined();
  });

  test("mutateAsync undefined projectId ile çağrılmaz", () => {
    renderHook(
      () => useManagementProjectId(undefined),
      { wrapper: makeWrapper() },
    );
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });
});

// ─── 3. localStorage'dan cached value okunur ───────────────────────────────
describe("localStorage cache", () => {
  test("Phase-1: LS'deki cached mpid anında döner", () => {
    const cachedMpid = "mgmt-cached-111";
    localStorage.setItem(lsKey("proj-ls"), cachedMpid);

    const { result } = renderHook(
      () => useManagementProjectId("proj-ls"),
      { wrapper: makeWrapper() },
    );
    // Backend inflight — ama LS'den hemen geldi
    expect(result.current).toBe(cachedMpid);
  });

  test("LS'de kayıt varken bile backend yanıtı state'i günceller", async () => {
    localStorage.setItem(lsKey("proj-ls"), "mgmt-stale");
    const freshMpid = "mgmt-fresh-222";
    mutateAsyncMock.mockResolvedValue({ id: freshMpid });

    const { result } = renderHook(
      () => useManagementProjectId("proj-ls"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current).toBe(freshMpid));
  });
});

// ─── 4. Backend fetch başarılı → mpid set edilir ───────────────────────────
describe("backend fetch başarılı", () => {
  test("mpid state'i backend'den gelen id ile güncellenir", async () => {
    const backendId = "mgmt-from-backend";
    mutateAsyncMock.mockResolvedValue({ id: backendId });

    const { result } = renderHook(
      () => useManagementProjectId("proj-backend"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current).toBe(backendId));
  });

  test("backend yanıtı localStorage'a yazılır", async () => {
    const backendId = "mgmt-stored";
    mutateAsyncMock.mockResolvedValue({ id: backendId });

    renderHook(
      () => useManagementProjectId("proj-store"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() =>
      expect(localStorage.getItem(lsKey("proj-store"))).toBe(backendId),
    );
  });
});

// ─── 5. Backend fetch başarısız → localStorage fallback ────────────────────
describe("backend fetch başarısız", () => {
  test("LS'de cache varken backend hatası → cached mpid korunur", async () => {
    const cachedMpid = "mgmt-safe-fallback";
    localStorage.setItem(lsKey("proj-fail"), cachedMpid);
    mutateAsyncMock.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(
      () => useManagementProjectId("proj-fail"),
      { wrapper: makeWrapper() },
    );

    // Initial: LS cache
    expect(result.current).toBe(cachedMpid);

    // After rejection: still cached value (not undefined)
    await waitFor(() => expect(result.current).toBe(cachedMpid));
  });

  test("LS boşken backend hatası → projectId fallback döner", async () => {
    mutateAsyncMock.mockRejectedValue(new Error("500 Internal Server Error"));

    const { result } = renderHook(
      () => useManagementProjectId("proj-no-cache"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current).toBe("proj-no-cache"));
  });
});

// ─── 6. Farklı projectId → yeni fetch tetiklenir ───────────────────────────
describe("projectId değişince", () => {
  test("farklı projectId ile yeni mutateAsync çağrısı yapılır", async () => {
    mutateAsyncMock.mockResolvedValue({ id: "mgmt-a" });

    const { result, rerender } = renderHook(
      ({ pid }: { pid: string }) => useManagementProjectId(pid),
      {
        wrapper: makeWrapper(),
        initialProps: { pid: "proj-1" },
      },
    );

    await waitFor(() => expect(result.current).toBe("mgmt-a"));
    const firstCallCount = mutateAsyncMock.mock.calls.length;
    expect(firstCallCount).toBeGreaterThanOrEqual(1);

    mutateAsyncMock.mockResolvedValue({ id: "mgmt-b" });

    await act(async () => {
      rerender({ pid: "proj-2" });
    });

    await waitFor(() => expect(result.current).toBe("mgmt-b"));
    expect(mutateAsyncMock.mock.calls.length).toBeGreaterThan(firstCallCount);
  });

  test("projectId değişince eski projectId'nin LS kaydını etkilemez", async () => {
    localStorage.setItem(lsKey("proj-old"), "mgmt-old-cached");

    // proj-old için backend'in yanıtı da "mgmt-old-cached" döner (LS ile uyumlu)
    mutateAsyncMock
      .mockResolvedValueOnce({ id: "mgmt-old-cached" }) // proj-old fetch
      .mockResolvedValue({ id: "mgmt-new" });            // proj-new fetch

    const { rerender } = renderHook(
      ({ pid }: { pid: string }) => useManagementProjectId(pid),
      {
        wrapper: makeWrapper(),
        initialProps: { pid: "proj-old" },
      },
    );

    // proj-old fetch tamamlanana kadar bekle
    await waitFor(() =>
      expect(localStorage.getItem(lsKey("proj-old"))).toBe("mgmt-old-cached"),
    );

    await act(async () => {
      rerender({ pid: "proj-new" });
    });

    await waitFor(() =>
      expect(localStorage.getItem(lsKey("proj-new"))).toBe("mgmt-new"),
    );

    // Eski key bozulmamış olmalı
    expect(localStorage.getItem(lsKey("proj-old"))).toBe("mgmt-old-cached");
  });
});
