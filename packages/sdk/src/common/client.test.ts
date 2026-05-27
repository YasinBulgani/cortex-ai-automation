/**
 * CortexClient unit tests — uses a mock fetch to avoid real HTTP calls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { CortexClient, CortexApiError } from "./client";

function makeFetch(status: number, body: unknown, ok = status < 400) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(String(body)),
  } as unknown as Response);
}

describe("CortexClient", () => {
  let mockFetch: ReturnType<typeof makeFetch>;

  beforeEach(() => {
    mockFetch = makeFetch(200, { hello: "world" });
  });

  it("GETs and returns parsed JSON", async () => {
    const client = new CortexClient({
      baseUrl: "https://api.example.com",
      fetch: mockFetch,
    });

    const result = await client.get("/api/v1/projects");
    expect(result).toEqual({ hello: "world" });
    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.com/api/v1/projects",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("injects Authorization header when apiKey is set", async () => {
    const client = new CortexClient({
      baseUrl: "https://api.example.com",
      apiKey: "test-key-123",
      fetch: mockFetch,
    });

    await client.get("/api/v1/projects");
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Authorization"]).toBe(
      "Bearer test-key-123",
    );
  });

  it("POSTs JSON body with correct Content-Type", async () => {
    const client = new CortexClient({
      baseUrl: "https://api.example.com",
      fetch: mockFetch,
    });

    await client.post("/api/v1/projects", { json: { name: "Test" } });
    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/json",
    );
    expect(init.body).toBe(JSON.stringify({ name: "Test" }));
  });

  it("throws CortexApiError on non-ok response", async () => {
    const errFetch = makeFetch(404, { detail: "Not found" }, false);
    const client = new CortexClient({
      baseUrl: "https://api.example.com",
      fetch: errFetch,
      maxRetries: 0,
    });

    await expect(client.get("/api/v1/projects/missing")).rejects.toThrow(
      CortexApiError,
    );
  });

  it("retries on 500 up to maxRetries times", async () => {
    const errFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: "server error" }),
      text: () => Promise.resolve("server error"),
    } as unknown as Response);

    const client = new CortexClient({
      baseUrl: "https://api.example.com",
      fetch: errFetch,
      maxRetries: 2,
      retryDelayMs: 0, // no sleep in tests
    });

    await expect(client.get("/api/v1/projects")).rejects.toThrow(CortexApiError);
    // Initial attempt + 2 retries = 3 total calls
    expect(errFetch).toHaveBeenCalledTimes(3);
  });

  it("returns undefined for 204 No Content", async () => {
    const noContentFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      statusText: "No Content",
      json: () => Promise.reject(new Error("no body")),
    } as unknown as Response);

    const client = new CortexClient({
      baseUrl: "https://api.example.com",
      fetch: noContentFetch,
    });

    const result = await client.delete("/api/v1/sessions/abc");
    expect(result).toBeUndefined();
  });

  it("strips trailing slash from baseUrl", async () => {
    const client = new CortexClient({
      baseUrl: "https://api.example.com/",
      fetch: mockFetch,
    });

    await client.get("/foo");
    expect(mockFetch.mock.calls[0][0]).toBe("https://api.example.com/foo");
  });
});
