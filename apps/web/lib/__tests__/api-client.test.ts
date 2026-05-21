import {
  ApiError,
  getToken,
  setToken,
  getRefreshToken,
  setRefreshToken,
  clearTokens,
  setTokens,
} from "../api-client";

// ── localStorage mock ─────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v; },
    removeItem: (k: string) => { delete store[k]; },
    clear: () => { store = {}; },
  };
})();
Object.defineProperty(global, "localStorage", { value: localStorageMock });

// ── ApiError ──────────────────────────────────────────────────────────────────

describe("ApiError", () => {
  it("status ve message atanır", () => {
    const err = new ApiError(404, "Not Found");
    expect(err.status).toBe(404);
    expect(err.message).toBe("Not Found");
    expect(err instanceof Error).toBe(true);
    expect(err instanceof ApiError).toBe(true);
  });

  it("name 'ApiError' olarak set edilir", () => {
    expect(new ApiError(500, "Server Error").name).toBe("ApiError");
  });
});

// ── Token storage ─────────────────────────────────────────────────────────────

describe("token yönetimi", () => {
  beforeEach(() => localStorageMock.clear());

  it("getToken — başlangıçta null döner", () => {
    expect(getToken()).toBeNull();
  });

  it("setToken → getToken round-trip (no-op under cookie auth, backwards-compat read via localStorage)", () => {
    // SECURITY: COOKIE_AUTH_ENABLED → setToken is intentionally a no-op
    // so setToken("x") then getToken() returns null. Backwards-compat read
    // still works via direct localStorage write (legacy sessions).
    setToken("mytoken");
    expect(getToken()).toBeNull();

    // Backwards-compat path: when localStorage already has a token
    // (from a pre-cookie-auth session), getToken returns it
    localStorageMock.setItem("tspm_access_token", "legacy_token");
    expect(getToken()).toBe("legacy_token");
  });

  it("getRefreshToken — başlangıçta null döner", () => {
    expect(getRefreshToken()).toBeNull();
  });

  it("setRefreshToken → getRefreshToken (no-op under cookie auth)", () => {
    setRefreshToken("refresh_xyz");
    expect(getRefreshToken()).toBeNull();
  });

  it("clearTokens access ve refresh'i siler", () => {
    // Use direct localStorage writes to simulate legacy tokens
    localStorageMock.setItem("tspm_access_token", "acc");
    localStorageMock.setItem("tspm_refresh_token", "ref");
    clearTokens();
    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("setTokens cookie-auth modunda localStorage'a yazmaz", () => {
    setTokens({ access_token: "a", refresh_token: "r" } as any);
    expect(getToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});

// ── ENGINE_BASE & apiFetch ─────────────────────────────────────────────────────

describe("api-client engine base", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_ENGINE_BASE;
    delete process.env.NEXT_PUBLIC_ENGINE_URL;
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("defaults browser engine calls to the backend proxy", async () => {
    const mod = await import("@/lib/api-client");
    expect(mod.ENGINE_BASE).toBe("/api/v1/automation/proxy");
  });

  it("prefers NEXT_PUBLIC_ENGINE_BASE when explicitly configured", async () => {
    process.env.NEXT_PUBLIC_ENGINE_BASE = "https://example.test/engine/";
    const mod = await import("@/lib/api-client");
    expect(mod.ENGINE_BASE).toBe("https://example.test/engine");
  });
});

describe("apiFetch auth flow", () => {
  const originalEnv = process.env;
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    process.env.NEXT_PUBLIC_API_BASE = "http://127.0.0.1:8000";
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  afterAll(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
  });

  function responseMock(status: number, body: unknown) {
    return {
      status,
      ok: status >= 200 && status < 300,
      statusText: `${status}`,
      json: jest.fn().mockResolvedValue(body),
      text: jest.fn().mockResolvedValue(JSON.stringify(body)),
    };
  }

  it("refreshes once and retries protected requests", async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValueOnce(responseMock(401, { detail: "expired" }))
      // refreshAccessToken requires data.access_token to be present
      .mockResolvedValueOnce(responseMock(200, { access_token: "new_access", refresh_token: "new_refresh", expires_in: 3600 }))
      .mockResolvedValueOnce(responseMock(200, { value: 42 }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const mod = await import("@/lib/api-client");
    const result = await mod.apiFetch<{ value: number }>("/api/v1/secure");

    expect(result.value).toBe(42);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain("/api/v1/auth/refresh");
  });

  it("skips refresh logic for noAuth requests", async () => {
    const fetchMock = jest.fn().mockResolvedValue(responseMock(401, { detail: "invalid credentials" }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const mod = await import("@/lib/api-client");
    await expect(
      mod.apiFetch("/api/v1/auth/login", {
        method: "POST",
        json: { email: "test@example.com", password: "wrong" },
        noAuth: true,
      }),
    ).rejects.toMatchObject({ status: 401 });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/api/v1/auth/login");
  });
});
