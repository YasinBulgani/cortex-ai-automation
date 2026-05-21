import { describe, it, expect } from "vitest";
import { BufferSink, TelemetryRegistry, withTelemetry, type AICallRecord } from "./telemetry";
import { CostTracker } from "./cost-tracker";

describe("BufferSink + TelemetryRegistry", () => {
  it("collects calls", async () => {
    const reg = new TelemetryRegistry();
    const sink = new BufferSink();
    reg.add(sink);
    await reg.record(stub("anthropic"));
    await reg.record(stub("groq"));
    expect(sink.calls).toHaveLength(2);
  });

  it("withTelemetry records success", async () => {
    const reg = new TelemetryRegistry();
    const sink = new BufferSink();
    reg.add(sink);
    const result = await withTelemetry(
      {
        provider: "anthropic",
        tenant_id: "t1",
        registry: reg,
        request_messages: [{ role: "user", content: "hi" }],
      },
      async () => ({
        id: "x",
        model: "claude",
        content: "ok",
        finish_reason: "stop" as const,
        usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
        cost_usd: 0.001,
        latency_ms: 50,
      }),
    );
    expect(result.content).toBe("ok");
    expect(sink.calls).toHaveLength(1);
    expect(sink.calls[0].success).toBe(true);
    expect(sink.calls[0].tenant_id).toBe("t1");
  });

  it("withTelemetry records failure and rethrows", async () => {
    const reg = new TelemetryRegistry();
    const sink = new BufferSink();
    reg.add(sink);
    await expect(
      withTelemetry(
        { provider: "anthropic", registry: reg },
        async () => { throw new Error("boom"); },
      ),
    ).rejects.toThrow("boom");
    expect(sink.calls).toHaveLength(1);
    expect(sink.calls[0].success).toBe(false);
    expect(sink.calls[0].error).toContain("boom");
  });
});

describe("CostTracker", () => {
  it("aggregates global, tenant, user totals", () => {
    const tracker = new CostTracker();
    tracker.record(stub("anthropic", { tenant_id: "t1", user_id: "u1", cost_usd: 0.5 }));
    tracker.record(stub("groq", { tenant_id: "t1", user_id: "u2", cost_usd: 0.1 }));
    tracker.record(stub("anthropic", { tenant_id: "t2", user_id: "u1", cost_usd: 0.2 }));

    expect(tracker.totals().total_usd).toBeCloseTo(0.8, 4);
    expect(tracker.forTenant("t1").total_usd).toBeCloseTo(0.6, 4);
    expect(tracker.forTenant("t2").total_usd).toBeCloseTo(0.2, 4);
    expect(tracker.forUser("u1").total_usd).toBeCloseTo(0.7, 4);
  });

  it("isOverBudget true once tenant exceeds limit", () => {
    const tracker = new CostTracker();
    tracker.record(stub("anthropic", { tenant_id: "t1", cost_usd: 5.0 }));
    expect(tracker.isOverBudget("t1", 4)).toBe(true);
    expect(tracker.isOverBudget("t1", 10)).toBe(false);
  });

  it("aggregates by provider and model", () => {
    const tracker = new CostTracker();
    tracker.record(stub("anthropic", { tenant_id: "t1", cost_usd: 0.5 }));
    tracker.record(stub("anthropic", { tenant_id: "t1", cost_usd: 0.3 }));
    tracker.record(stub("groq", { tenant_id: "t1", cost_usd: 0.05 }));
    const t1 = tracker.forTenant("t1");
    expect(t1.by_provider.anthropic).toBeCloseTo(0.8, 4);
    expect(t1.by_provider.groq).toBeCloseTo(0.05, 4);
  });

  it("reset clears all aggregates", () => {
    const tracker = new CostTracker();
    tracker.record(stub("anthropic", { tenant_id: "t1", cost_usd: 1 }));
    tracker.reset();
    expect(tracker.totals().total_usd).toBe(0);
    expect(tracker.forTenant("t1").total_usd).toBe(0);
  });
});

function stub(
  provider: AICallRecord["provider"],
  overrides: Partial<AICallRecord> = {},
): AICallRecord {
  return {
    request_id: "r",
    provider,
    model: `${provider}-default`,
    timestamp_ms: Date.now(),
    duration_ms: 10,
    prompt_tokens: 5,
    completion_tokens: 5,
    success: true,
    ...overrides,
  };
}
