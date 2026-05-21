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
      .mockResolvedValueOnce(responseMock(200, { ok: true }))
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
