import { describe, it, expect, vi } from "vitest";
import { IntelligentRouter } from "./router";
import type {
  Provider,
  ProviderCapabilities,
  CompletionRequest,
  CompletionResponse,
  ProviderId,
} from "../providers/types";

function mockProvider(
  id: ProviderId,
  opts: Partial<ProviderCapabilities> = {},
  behavior: { fail?: boolean; latency_ms?: number; content?: string } = {},
): Provider {
  return {
    id,
    capabilities: {
      id,
      models: [`${id}-default`],
      cost_per_million_tokens: 1,
      ttft_p95_ms: opts.ttft_p95_ms ?? 500,
      max_context: 100_000,
      supports_tools: true,
      supports_streaming: true,
      supports_vision: false,
      ...opts,
    },
    async complete(req: CompletionRequest): Promise<CompletionResponse> {
      if (behavior.fail) throw new Error(`${id} fail`);
      return {
        id: `${id}-resp`,
        model: req.model ?? `${id}-default`,
        content: behavior.content ?? `from ${id}`,
        finish_reason: "stop",
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
        latency_ms: behavior.latency_ms ?? 100,
      };
    },
    async health() {
      return { healthy: !behavior.fail };
    },
  };
}

describe("IntelligentRouter", () => {
  it("picks primary provider for an intent", async () => {
    const anthropic = mockProvider("anthropic", {}, { content: "anthropic-result" });
    const gemini = mockProvider("gemini", {}, { content: "gemini-result" });
    const router = new IntelligentRouter([anthropic, gemini]);

    const res = await router.complete({
      intent: "scenario_generation",
      messages: [{ role: "user", content: "test" }],
    });
    // scenario_generation tier = ["anthropic", "gemini"]
    expect(res.content).toBe("anthropic-result");
  });

  it("falls back to secondary when primary fails", async () => {
    const anthropic = mockProvider("anthropic", {}, { fail: true });
    const gemini = mockProvider("gemini", {}, { content: "gemini-fallback" });
    const router = new IntelligentRouter([anthropic, gemini]);

    const res = await router.complete({
      intent: "scenario_generation",
      messages: [{ role: "user", content: "test" }],
    });
    expect(res.content).toBe("gemini-fallback");
  });

  it("throws when all providers fail", async () => {
    const anthropic = mockProvider("anthropic", {}, { fail: true });
    const gemini = mockProvider("gemini", {}, { fail: true });
    const router = new IntelligentRouter([anthropic, gemini]);

    await expect(
      router.complete({
        intent: "scenario_generation",
        messages: [{ role: "user", content: "test" }],
      }),
    ).rejects.toThrow(/All providers failed/);
  });

  it("throws when no provider matches intent", async () => {
    const router = new IntelligentRouter([]);
    await expect(
      router.complete({
        intent: "general",
        messages: [{ role: "user", content: "hi" }],
      }),
    ).rejects.toThrow(/No provider available/);
  });

  it("filters providers exceeding latency SLA", async () => {
    const slow = mockProvider("anthropic", { ttft_p95_ms: 2000 });
    const fast = mockProvider("groq", { ttft_p95_ms: 100 }, { content: "fast-result" });
    const router = new IntelligentRouter([slow, fast]);

    const res = await router.complete({
      intent: "intent_classification",
      messages: [{ role: "user", content: "hi" }],
      latency_sla_ms: 500,
    });
    expect(res.content).toBe("fast-result");
  });

  it("reverses order when quality_preference is fastest", async () => {
    const a = mockProvider("anthropic", {}, { content: "anthropic" });
    const g = mockProvider("groq", {}, { content: "groq" });
    const o = mockProvider("ollama", {}, { content: "ollama" });
    const router = new IntelligentRouter([a, g, o]);

    // code_generation tier = ["anthropic", "ollama"] → reversed = ["ollama", "anthropic"]
    const res = await router.complete({
      intent: "code_generation",
      messages: [{ role: "user", content: "x" }],
      quality_preference: "fastest",
    });
    expect(res.content).toBe("ollama");
  });

  it("estimates cost without making a call", () => {
    const a = mockProvider("anthropic", { cost_per_million_tokens: 9 });
    const router = new IntelligentRouter([a]);
    const est = router.estimateCost(
      { intent: "scenario_generation", messages: [{ role: "user", content: "x" }] },
      1_000_000,
    );
    expect(est).not.toBeNull();
    expect(est?.cost_usd).toBeCloseTo(9, 4);
  });

  it("estimateCost returns null when no candidate", () => {
    const router = new IntelligentRouter([]);
    expect(
      router.estimateCost(
        { intent: "general", messages: [{ role: "user", content: "x" }] },
        100,
      ),
    ).toBeNull();
  });

  it("healthCheck aggregates per-provider status", async () => {
    const a = mockProvider("anthropic", {}, { content: "ok" });
    const failing = mockProvider("groq", {}, { fail: true });
    const router = new IntelligentRouter([a, failing]);
    const health = await router.healthCheck();
    expect(health.anthropic.healthy).toBe(true);
    expect(health.groq.healthy).toBe(false);
  });

  it("complete attempts providers in declared order", async () => {
    const spy1 = vi.fn().mockRejectedValue(new Error("nope"));
    const spy2 = vi.fn().mockResolvedValue({
      id: "x",
      model: "m",
      content: "hi",
      finish_reason: "stop",
      usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      latency_ms: 1,
    });
    const a: Provider = {
      id: "anthropic",
      capabilities: {
        id: "anthropic", models: [], cost_per_million_tokens: 1, ttft_p95_ms: 1,
        max_context: 1, supports_tools: false, supports_streaming: false, supports_vision: false,
      },
      complete: spy1, health: async () => ({ healthy: true }),
    };
    const g: Provider = {
      id: "gemini",
      capabilities: {
        id: "gemini", models: [], cost_per_million_tokens: 1, ttft_p95_ms: 1,
        max_context: 1, supports_tools: false, supports_streaming: false, supports_vision: false,
      },
      complete: spy2, health: async () => ({ healthy: true }),
    };
    const router = new IntelligentRouter([a, g]);
    await router.complete({
      intent: "scenario_generation",
      messages: [{ role: "user", content: "x" }],
    });
    expect(spy1).toHaveBeenCalledOnce();
    expect(spy2).toHaveBeenCalledOnce();
  });
});
