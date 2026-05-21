describe("ai-gateway browser client", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.resetModules();
    global.fetch = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  function okJson(body: unknown) {
    return {
      ok: true,
      status: 200,
      json: jest.fn().mockResolvedValue(body),
      text: jest.fn().mockResolvedValue(JSON.stringify(body)),
    };
  }

  it("routes completions through the same-origin proxy without exposing the internal key", async () => {
    const fetchMock = global.fetch as jest.Mock;
    fetchMock.mockResolvedValueOnce(okJson({
      content: "ok",
      provider_used: "ollama",
      model_used: "llama3.1:8b",
      latency_ms: 12,
      cached: false,
      tokens_used: 3,
      attempts: [],
    }));

    const { aiComplete } = await import("@/lib/ai-gateway");
    await aiComplete({
      messages: [{ role: "user", content: "Merhaba" }],
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ai/complete",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );
    expect(fetchMock.mock.calls[0]?.[1]?.headers?.["X-Internal-Key"]).toBeUndefined();
  });

  it("reads health through the same-origin proxy", async () => {
    const fetchMock = global.fetch as jest.Mock;
    fetchMock.mockResolvedValueOnce(okJson({
      status: "healthy",
      providers: { ollama: true },
      version: "test",
    }));

    const { getGatewayHealth } = await import("@/lib/ai-gateway");
    const health = await getGatewayHealth();

    expect(fetchMock).toHaveBeenCalledWith("/api/ai/health");
    expect(health.providers.ollama).toBe(true);
  });
});
