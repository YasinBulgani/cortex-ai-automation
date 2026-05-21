/** @jest-environment node */

/**
 * Tests for two pure API client modules:
 *   - lib/agents-v2-api
 *   - lib/ai-gateway
 *
 * Neither module is jest.mock()'d — they are imported directly.
 * global.fetch is swapped in/out per test to control responses.
 *
 * NOTE: ai-gateway captures NEXT_PUBLIC_GATEWAY_KEY at module-load time
 * (top-level const), so all ai-gateway tests use jest.resetModules() +
 * dynamic import to guarantee the env var is set before the module evaluates.
 */

// ─── agents-v2-api uses static import (no env-var guard at module level) ──────

import {
  startAgentRun,
  getAgentRun,
  listAgentRuns,
  cancelAgentRun,
  getAgentsV2Health,
  type RunAgentV2Request,
  type RunAgentV2Response,
  type RunV2Status,
  type RunV2ListItem,
} from "@/lib/agents-v2-api";

// ─── Type-only imports for ai-gateway (no value import — all values loaded dynamically) ──

import type {
  AIGatewayRequest,
  AIGatewayResponse,
  ProviderHealth,
} from "@/lib/ai-gateway";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function makeFetchOk(body: unknown): typeof global.fetch {
  return jest.fn().mockResolvedValue({
    ok: true,
    json: async () => body,
    text: async () => JSON.stringify(body),
  }) as unknown as typeof global.fetch;
}

function makeFetchError(status: number, body = "error"): typeof global.fetch {
  return jest.fn().mockResolvedValue({
    ok: false,
    status,
    json: async () => ({ detail: body }),
    text: async () => body,
  }) as unknown as typeof global.fetch;
}

// ─────────────────────────────────────────────────────────────────────────────
// MODULE 1 — agents-v2-api
// ─────────────────────────────────────────────────────────────────────────────

describe("agents-v2-api", () => {
  let savedFetch: typeof global.fetch;

  beforeEach(() => {
    savedFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = savedFetch;
  });

  // 1. startAgentRun — happy path

  it("startAgentRun calls POST /api/v1/agents/v2/run and returns RunAgentV2Response", async () => {
    const mockResponse: RunAgentV2Response = {
      run_id: "run-1",
      status: "queued",
      created_at: "2026-01-01T00:00:00Z",
      stream_url: "/api/v1/agents/v2/runs/run-1/stream",
      detail_url: "/api/v1/agents/v2/runs/run-1",
    };

    global.fetch = makeFetchOk(mockResponse);

    const request: RunAgentV2Request = {
      project_id: "proj-1",
      input_source: "text",
      text: "Login page tests",
    };

    const result = await startAgentRun(request);

    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [url, options] = (global.fetch as jest.Mock).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(url).toContain("/api/v1/agents/v2/run");
    expect(options.method).toBe("POST");
    // Main now passes a Headers instance instead of a plain object; check via .get()
    const hdrs = options.headers as any;
    const contentType = typeof hdrs?.get === "function" ? hdrs.get("Content-Type") : hdrs?.["Content-Type"];
    expect(contentType).toBe("application/json");

    expect(result.run_id).toBe("run-1");
    expect(result.status).toBe("queued");
    expect(typeof result.stream_url).toBe("string");
    expect(typeof result.detail_url).toBe("string");
    expect(typeof result.created_at).toBe("string");
  });

  // 2. getAgentRun — correct URL and returned shape

  it("getAgentRun calls correct URL and returns RunV2Status shape", async () => {
    const mockStatus: RunV2Status = {
      run_id: "run-1",
      status: "completed",
      project_id: "proj-1",
      input_source: "text",
      created_at: "2026-01-01T00:00:00Z",
      completed_at: "2026-01-01T00:01:00Z",
      cost_usd: 0.002,
      tokens_used: 500,
      llm_calls_count: 3,
      errors: [],
      scenarios: [],
    };

    global.fetch = makeFetchOk(mockStatus);

    const result = await getAgentRun("run-1");

    const [url] = (global.fetch as jest.Mock).mock.calls[0] as [string];
    expect(url).toContain("/api/v1/agents/v2/runs/run-1");

    expect(result.run_id).toBe("run-1");
    expect(result.status).toBe("completed");
    expect(result.project_id).toBe("proj-1");
    expect(Array.isArray(result.errors)).toBe(true);
    expect(Array.isArray(result.scenarios)).toBe(true);
    expect(typeof result.cost_usd).toBe("number");
    expect(typeof result.tokens_used).toBe("number");
  });

  // 3. listAgentRuns() without params — returns expected shape

  it("listAgentRuns() returns { runs, total, page, page_size } shape", async () => {
    const mockList = { runs: [] as RunV2ListItem[], total: 0, page: 1, page_size: 20 };

    global.fetch = makeFetchOk(mockList);

    const result = await listAgentRuns();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(Array.isArray(result.runs)).toBe(true);
    expect(typeof result.total).toBe("number");
    expect(typeof result.page).toBe("number");
    expect(typeof result.page_size).toBe("number");
  });

  // 4. listAgentRuns with projectId — includes project_id in query string

  it("listAgentRuns({ projectId }) includes project_id in URL query params", async () => {
    const mockList = { runs: [] as RunV2ListItem[], total: 0, page: 1, page_size: 20 };

    global.fetch = makeFetchOk(mockList);

    await listAgentRuns({ projectId: "proj-1" });

    const [url] = (global.fetch as jest.Mock).mock.calls[0] as [string];
    expect(url).toContain("project_id=proj-1");
  });

  // 5. cancelAgentRun — calls cancel endpoint with POST

  it("cancelAgentRun calls POST to cancel endpoint", async () => {
    global.fetch = makeFetchOk({});

    await cancelAgentRun("run-1");

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (global.fetch as jest.Mock).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(url).toContain("/api/v1/agents/v2/runs/run-1/cancel");
    expect(options.method).toBe("POST");
  });

  // 6. getAgentsV2Health — returns health object with status field

  it("getAgentsV2Health returns health object with status field", async () => {
    const mockHealth = {
      status: "ok",
      langgraph_available: true,
      ai_gateway_reachable: true,
      active_runs: 0,
    };

    global.fetch = makeFetchOk(mockHealth);

    const result = await getAgentsV2Health();

    const [url] = (global.fetch as jest.Mock).mock.calls[0] as [string];
    expect(url).toContain("/api/v1/agents/v2/health");

    expect(typeof result.status).toBe("string");
    expect(typeof result.langgraph_available).toBe("boolean");
    expect(typeof result.ai_gateway_reachable).toBe("boolean");
    expect(typeof result.active_runs).toBe("number");
  });

  // 7. startAgentRun — rejects when fetch returns ok=false

  it("startAgentRun throws when fetch returns ok=false", async () => {
    global.fetch = makeFetchError(422, "Validation error");

    const request: RunAgentV2Request = {
      project_id: "proj-bad",
      input_source: "text",
    };

    await expect(startAgentRun(request)).rejects.toThrow();
  });

  // Bonus: getAgentRun rejects on not-found response

  it("getAgentRun throws when run is not found (ok=false)", async () => {
    global.fetch = makeFetchError(404, "not found");

    await expect(getAgentRun("nonexistent")).rejects.toThrow();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// MODULE 2 — ai-gateway
//
// INTERNAL_KEY and GATEWAY_BASE are top-level consts captured at module-load
// time.  Every test that needs the key must:
//   1. Set the env var
//   2. Call jest.resetModules() to clear the module registry
//   3. Dynamically import ai-gateway so it picks up the env var fresh
// ─────────────────────────────────────────────────────────────────────────────

describe("ai-gateway", () => {
  let savedFetch: typeof global.fetch;
  const savedKey = process.env.NEXT_PUBLIC_GATEWAY_KEY;
  const savedBase = process.env.NEXT_PUBLIC_AI_GATEWAY_BASE;

  const savedInternalKey = process.env.GATEWAY_INTERNAL_KEY;

  beforeEach(() => {
    savedFetch = global.fetch;
    jest.resetModules();
    process.env.NEXT_PUBLIC_GATEWAY_KEY = "test-key";
    process.env.NEXT_PUBLIC_AI_GATEWAY_BASE = "http://localhost:8080";
    // Main switched to a server-side GATEWAY_INTERNAL_KEY check; set it too
    process.env.GATEWAY_INTERNAL_KEY = "test-internal-key";
  });

  afterEach(() => {
    global.fetch = savedFetch;
    if (savedKey !== undefined) {
      process.env.NEXT_PUBLIC_GATEWAY_KEY = savedKey;
    } else {
      delete process.env.NEXT_PUBLIC_GATEWAY_KEY;
    }
    if (savedBase !== undefined) {
      process.env.NEXT_PUBLIC_AI_GATEWAY_BASE = savedBase;
    } else {
      delete process.env.NEXT_PUBLIC_AI_GATEWAY_BASE;
    }
    if (savedInternalKey !== undefined) {
      process.env.GATEWAY_INTERNAL_KEY = savedInternalKey;
    } else {
      delete process.env.GATEWAY_INTERNAL_KEY;
    }
    jest.resetModules();
  });

  const mockGatewayResponse: AIGatewayResponse = {
    content: "response text",
    provider_used: "groq",
    model_used: "llama3",
    latency_ms: 123,
    cached: false,
    tokens_used: 50,
    attempts: [],
  };

  const mockHealthResponse: ProviderHealth = {
    status: "healthy",
    providers: { groq: true },
    version: "1.0.0",
  };

  // 1. aiComplete — sends POST to /ai/complete with messages

  it("aiComplete sends POST to /ai/complete with messages", async () => {
    global.fetch = makeFetchOk(mockGatewayResponse);

    const { aiComplete } = await import("@/lib/ai-gateway");

    const req: AIGatewayRequest = {
      messages: [{ role: "user", content: "Hello" }],
    };

    await aiComplete(req);

    expect(global.fetch).toHaveBeenCalledTimes(1);

    const [url, options] = (global.fetch as jest.Mock).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(url).toContain("/ai/complete");
    expect(options.method).toBe("POST");

    const sentBody = JSON.parse(options.body as string);
    expect(Array.isArray(sentBody.messages)).toBe(true);
    expect(sentBody.messages[0].content).toBe("Hello");
  });

  // 2. aiComplete — includes X-Internal-Key header

  it("aiComplete includes X-Internal-Key header", async () => {
    global.fetch = makeFetchOk(mockGatewayResponse);

    const { aiComplete } = await import("@/lib/ai-gateway");

    await aiComplete({ messages: [{ role: "user", content: "test" }] });

    const [, options] = (global.fetch as jest.Mock).mock.calls[0] as [
      string,
      RequestInit,
    ];
    const headers = options.headers as Record<string, string>;
    // ai-gateway now sources the header from GATEWAY_INTERNAL_KEY rather than NEXT_PUBLIC_GATEWAY_KEY
    expect(headers["X-Internal-Key"]).toBe("test-internal-key");
  });

  // 3. aiComplete — returns AIGatewayResponse shape

  it("aiComplete returns AIGatewayResponse shape", async () => {
    global.fetch = makeFetchOk(mockGatewayResponse);

    const { aiComplete } = await import("@/lib/ai-gateway");

    const result = await aiComplete({
      messages: [{ role: "user", content: "test" }],
    });

    expect(typeof result.content).toBe("string");
    expect(typeof result.provider_used).toBe("string");
    expect(typeof result.model_used).toBe("string");
    expect(typeof result.latency_ms).toBe("number");
    expect(typeof result.cached).toBe("boolean");
    expect(typeof result.tokens_used).toBe("number");
    expect(Array.isArray(result.attempts)).toBe(true);
  });

  // 4. getGatewayHealth — calls /ai/health endpoint

  it("getGatewayHealth calls /ai/health endpoint", async () => {
    global.fetch = makeFetchOk(mockHealthResponse);

    const { getGatewayHealth } = await import("@/lib/ai-gateway");

    await getGatewayHealth();

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url] = (global.fetch as jest.Mock).mock.calls[0] as [string];
    expect(url).toContain("/ai/health");
  });

  // 5. getGatewayHealth — returns ProviderHealth shape

  it("getGatewayHealth returns ProviderHealth shape", async () => {
    global.fetch = makeFetchOk(mockHealthResponse);

    const { getGatewayHealth } = await import("@/lib/ai-gateway");

    const result = await getGatewayHealth();

    expect(result.status).toMatch(/^(healthy|degraded)$/);
    expect(typeof result.providers).toBe("object");
    expect(typeof result.version).toBe("string");
  });

  // 6. analyzeDocument — returns string content from the response

  it("analyzeDocument returns string from AI response content", async () => {
    global.fetch = makeFetchOk({ ...mockGatewayResponse, content: "analysis result" });

    const { analyzeDocument } = await import("@/lib/ai-gateway");

    const result = await analyzeDocument("some doc text", "proj-1");

    expect(typeof result).toBe("string");
    expect(result).toBe("analysis result");
  });

  // 7. generateTestCases — returns string

  it("generateTestCases returns string", async () => {
    global.fetch = makeFetchOk({ ...mockGatewayResponse, content: "TC-1: ..." });

    const { generateTestCases } = await import("@/lib/ai-gateway");

    const result = await generateTestCases("Login module info", "proj-1");

    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  // Additional coverage: generateGherkin — returns string

  it("generateGherkin returns string", async () => {
    global.fetch = makeFetchOk({ ...mockGatewayResponse, content: "Feature: Login\n..." });

    const { generateGherkin } = await import("@/lib/ai-gateway");

    const result = await generateGherkin("TC-1: Login", "Login", "proj-1", "en");

    expect(typeof result).toBe("string");
  });

  // aiComplete — throws on non-ok response from gateway

  it("aiComplete throws when gateway returns ok=false", async () => {
    global.fetch = makeFetchError(500, "Internal Server Error");

    const { aiComplete } = await import("@/lib/ai-gateway");

    await expect(
      aiComplete({ messages: [{ role: "user", content: "test" }] })
    ).rejects.toThrow();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// MODULE 2 — ai-gateway: missing NEXT_PUBLIC_GATEWAY_KEY
// ─────────────────────────────────────────────────────────────────────────────

describe("ai-gateway — when no gateway key", () => {
  const savedKey = process.env.NEXT_PUBLIC_GATEWAY_KEY;
  const savedInternal = process.env.GATEWAY_INTERNAL_KEY;
  let savedFetch: typeof global.fetch;

  beforeEach(() => {
    savedFetch = global.fetch;
    jest.resetModules();
    delete process.env.NEXT_PUBLIC_GATEWAY_KEY;
    delete process.env.GATEWAY_INTERNAL_KEY;
    process.env.NEXT_PUBLIC_AI_GATEWAY_BASE = "http://localhost:8080";
  });

  afterEach(() => {
    global.fetch = savedFetch;
    if (savedKey !== undefined) process.env.NEXT_PUBLIC_GATEWAY_KEY = savedKey;
    if (savedInternal !== undefined) process.env.GATEWAY_INTERNAL_KEY = savedInternal;
    jest.resetModules();
  });

  it("aiComplete throws when gateway key is not set", async () => {
    // Dynamic import re-evaluates the module with no key set
    const { aiComplete: aiCompleteNoKey } = await import("@/lib/ai-gateway");

    // fetch should never be called — gateway access guard throws first
    global.fetch = jest.fn() as unknown as typeof global.fetch;

    // Main now uses GATEWAY_INTERNAL_KEY (with the Turkish message), so accept either
    await expect(
      aiCompleteNoKey({ messages: [{ role: "user", content: "test" }] })
    ).rejects.toThrow(/GATEWAY_INTERNAL_KEY|NEXT_PUBLIC_GATEWAY_KEY/);

    expect(global.fetch).not.toHaveBeenCalled();
  });
});
