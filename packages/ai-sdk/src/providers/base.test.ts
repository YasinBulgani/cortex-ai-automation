import { describe, it, expect, vi } from "vitest";
import { CircuitBreaker, CircuitOpenError, computeCost, splitSystem } from "./base";

describe("CircuitBreaker", () => {
  it("starts in closed state", () => {
    const cb = new CircuitBreaker();
    expect(cb.currentState).toBe("closed");
  });

  it("opens after threshold failures", () => {
    const cb = new CircuitBreaker({ failure_threshold: 3, reset_timeout_ms: 1000 });
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.currentState).toBe("closed");
    cb.recordFailure();
    expect(cb.currentState).toBe("open");
  });

  it("transitions to half-open after reset timeout", async () => {
    vi.useFakeTimers();
    const cb = new CircuitBreaker({ failure_threshold: 1, reset_timeout_ms: 100 });
    cb.recordFailure();
    expect(cb.currentState).toBe("open");
    vi.advanceTimersByTime(101);
    expect(cb.currentState).toBe("half-open");
    vi.useRealTimers();
  });

  it("closes again after success", () => {
    const cb = new CircuitBreaker({ failure_threshold: 2, reset_timeout_ms: 10 });
    cb.recordFailure();
    cb.recordFailure();
    expect(cb.currentState).toBe("open");
    cb.recordSuccess();
    expect(cb.currentState).toBe("closed");
  });

  it("execute throws CircuitOpenError when open", async () => {
    const cb = new CircuitBreaker({ failure_threshold: 1, reset_timeout_ms: 10_000 });
    cb.recordFailure();
    await expect(cb.execute(async () => "ok")).rejects.toBeInstanceOf(CircuitOpenError);
  });

  it("execute passes through on success", async () => {
    const cb = new CircuitBreaker();
    const result = await cb.execute(async () => "ok");
    expect(result).toBe("ok");
  });

  it("execute records failure when fn throws", async () => {
    const cb = new CircuitBreaker({ failure_threshold: 1, reset_timeout_ms: 10_000 });
    await expect(cb.execute(async () => { throw new Error("boom"); })).rejects.toThrow("boom");
    expect(cb.currentState).toBe("open");
  });
});

describe("computeCost", () => {
  it("calculates total of input + output", () => {
    const cost = computeCost(1_000_000, 1_000_000, {
      input_per_million_usd: 3,
      output_per_million_usd: 15,
    });
    expect(cost).toBeCloseTo(18, 4);
  });

  it("handles zero tokens", () => {
    expect(computeCost(0, 0, { input_per_million_usd: 10, output_per_million_usd: 10 })).toBe(0);
  });

  it("scales fractionally", () => {
    const cost = computeCost(500_000, 500_000, {
      input_per_million_usd: 2,
      output_per_million_usd: 4,
    });
    expect(cost).toBeCloseTo(3, 4);
  });
});

describe("splitSystem", () => {
  it("extracts and joins multiple system messages", () => {
    const { system, rest } = splitSystem([
      { role: "system", content: "S1" },
      { role: "user", content: "U1" },
      { role: "system", content: "S2" },
    ]);
    expect(system).toBe("S1\n\nS2");
    expect(rest).toHaveLength(1);
    expect(rest[0].role).toBe("user");
  });

  it("returns empty system when none present", () => {
    const { system, rest } = splitSystem([{ role: "user", content: "hi" }]);
    expect(system).toBe("");
    expect(rest).toHaveLength(1);
  });
});
