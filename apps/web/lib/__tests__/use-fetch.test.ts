/** @jest-environment jsdom */
import { renderHook, act, waitFor } from "@testing-library/react";

// Mock @/lib/api so we control apiFetch without real HTTP
jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn(),
}));
import { apiFetch } from "@/lib/api";
import { useFetch, useMutate } from "../useFetch";

const mockApiFetch = apiFetch as jest.Mock;

// Suppress console.error noise from unhandled rejections in test
beforeEach(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  mockApiFetch.mockReset();
});
afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

// ─── useFetch ─────────────────────────────────────────────────────────────────
describe("useFetch", () => {
  it("starts in loading=false when path is null", () => {
    const { result } = renderHook(() => useFetch<string>(null));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it("starts loading when path is provided", async () => {
    // Mock that never resolves to capture loading state
    mockApiFetch.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useFetch<string>("/api/test"));
    expect(result.current.loading).toBe(true);
  });

  it("returns data on successful fetch", async () => {
    mockApiFetch.mockResolvedValue({ id: 1, name: "Test" });
    const { result } = renderHook(() => useFetch<{ id: number; name: string }>("/api/test"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual({ id: 1, name: "Test" });
    expect(result.current.error).toBeNull();
  });

  it("sets error on failed fetch", async () => {
    mockApiFetch.mockRejectedValue(new Error("500 Internal Server Error"));
    const { result } = renderHook(() => useFetch<string>("/api/test"));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("500 Internal Server Error");
    expect(result.current.data).toBeNull();
  });

  it("does not fetch when enabled=false", () => {
    renderHook(() => useFetch<string>("/api/test", { enabled: false }));
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it("refresh() triggers a new fetch", async () => {
    mockApiFetch.mockResolvedValue("result");
    const { result } = renderHook(() => useFetch<string>("/api/test"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockApiFetch).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockApiFetch).toHaveBeenCalledTimes(2);
  });

  it("ignores AbortError when component unmounts", async () => {
    const abortError = new Error("aborted");
    abortError.name = "AbortError";
    mockApiFetch.mockRejectedValue(abortError);

    const { result, unmount } = renderHook(() => useFetch<string>("/api/test"));
    unmount();

    // Should not set error for AbortError
    expect(result.current.error).toBeNull();
  });

  it("returns data as null initially", () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(() => useFetch<string>("/api/test"));
    expect(result.current.data).toBeNull();
  });
});

// ─── useMutate ────────────────────────────────────────────────────────────────
describe("useMutate", () => {
  it("starts with loading=false and no error", () => {
    const { result } = renderHook(() => useMutate("/api/items"));
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets loading=true during mutation", async () => {
    let resolve!: (v: unknown) => void;
    mockApiFetch.mockReturnValue(new Promise(res => { resolve = res; }));
    const { result } = renderHook(() => useMutate("/api/items"));

    act(() => { result.current.mutate({ name: "New" }); });
    expect(result.current.loading).toBe(true);

    await act(async () => { resolve({ id: 1 }); });
  });

  it("returns result on success", async () => {
    mockApiFetch.mockResolvedValue({ id: 42 });
    const { result } = renderHook(() => useMutate<{ name: string }, { id: number }>("/api/items"));

    let response: { id: number } | null = null;
    await act(async () => {
      response = await result.current.mutate({ name: "Item" });
    });

    expect(response).toEqual({ id: 42 });
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets error on failure and returns null", async () => {
    mockApiFetch.mockRejectedValue(new Error("422 Unprocessable Entity"));
    const { result } = renderHook(() => useMutate("/api/items"));

    let response: unknown = "sentinel";
    await act(async () => {
      response = await result.current.mutate({ name: "" });
    });

    expect(response).toBeNull();
    expect(result.current.error).toBe("422 Unprocessable Entity");
  });

  it("calls onSuccess callback with result", async () => {
    mockApiFetch.mockResolvedValue({ id: 10 });
    const onSuccess = jest.fn();
    const { result } = renderHook(() => useMutate<unknown, { id: number }>("/api/items", { onSuccess }));

    await act(async () => { await result.current.mutate({}); });

    expect(onSuccess).toHaveBeenCalledWith({ id: 10 });
  });

  it("calls onError callback with error message", async () => {
    mockApiFetch.mockRejectedValue(new Error("404 Not Found"));
    const onError = jest.fn();
    const { result } = renderHook(() => useMutate("/api/items", { onError }));

    await act(async () => { await result.current.mutate({}); });

    expect(onError).toHaveBeenCalledWith("404 Not Found");
  });

  it("uses PUT method when specified", async () => {
    mockApiFetch.mockResolvedValue({ updated: true });
    const { result } = renderHook(() => useMutate("/api/items/1", { method: "PUT" }));

    await act(async () => { await result.current.mutate({ name: "Updated" }); });

    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/items/1",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("uses DELETE method when specified", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { result } = renderHook(() => useMutate("/api/items/1", { method: "DELETE" }));

    await act(async () => { await result.current.mutate(); });

    expect(mockApiFetch).toHaveBeenCalledWith(
      "/api/items/1",
      expect.objectContaining({ method: "DELETE" })
    );
  });
});
