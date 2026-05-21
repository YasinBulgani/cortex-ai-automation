import { describe, it, expect } from "vitest";
import { EvalRunner } from "./runner";
import type { CompletionResponse, Message } from "../providers/types";
import type { EvalCase } from "./types";

function stubResponse(content: string, opts: Partial<CompletionResponse> = {}): CompletionResponse {
  return {
    id: "r",
    model: "stub",
    content,
    finish_reason: "stop",
    usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
    cost_usd: 0,
    latency_ms: 10,
    ...opts,
  };
}

describe("EvalRunner", () => {
  it("passes when all assertions pass", async () => {
    const runner = new EvalRunner(async () => stubResponse("hello world"));
    const cases: EvalCase[] = [
      {
        id: "c1",
        messages: [{ role: "user", content: "hi" }],
        assertions: [{ type: "contains", value: "hello" }, { type: "min_length", length: 5 }],
      },
    ];
    const summary = await runner.run(cases);
    expect(summary.passed).toBe(1);
    expect(summary.failed).toBe(0);
    expect(summary.pass_rate).toBe(1);
  });

  it("fails when any assertion fails", async () => {
    const runner = new EvalRunner(async () => stubResponse("hi"));
    const cases: EvalCase[] = [
      {
        id: "c1",
        messages: [{ role: "user", content: "x" }],
        assertions: [{ type: "min_length", length: 100 }],
      },
    ];
    const summary = await runner.run(cases);
    expect(summary.passed).toBe(0);
    expect(summary.failed).toBe(1);
  });

  it("records skips with reason", async () => {
    const runner = new EvalRunner(async () => stubResponse(""));
    const cases: EvalCase[] = [
      {
        id: "skipped",
        skip: { reason: "API key missing" },
        messages: [{ role: "user", content: "x" }],
        assertions: [],
      },
    ];
    const summary = await runner.run(cases);
    expect(summary.skipped).toBe(1);
    expect(summary.passed).toBe(0);
    expect(summary.results[0].skip_reason).toBe("API key missing");
  });

  it("captures provider errors per case", async () => {
    const runner = new EvalRunner(async () => { throw new Error("rate_limit"); });
    const cases: EvalCase[] = [
      { id: "c1", messages: [{ role: "user", content: "x" }], assertions: [{ type: "min_length", length: 1 }] },
    ];
    const summary = await runner.run(cases);
    expect(summary.errors).toBe(1);
    expect(summary.results[0].error).toContain("rate_limit");
  });

  it("filters by case_ids", async () => {
    const runner = new EvalRunner(async () => stubResponse("ok"));
    const cases: EvalCase[] = [
      { id: "a", messages: [{ role: "user", content: "x" }], assertions: [] },
      { id: "b", messages: [{ role: "user", content: "x" }], assertions: [] },
      { id: "c", messages: [{ role: "user", content: "x" }], assertions: [] },
    ];
    const summary = await runner.run(cases, { case_ids: ["b"] });
    expect(summary.total).toBe(1);
    expect(summary.results[0].case_id).toBe("b");
  });

  it("filters by include/exclude tags", async () => {
    const runner = new EvalRunner(async () => stubResponse("ok"));
    const cases: EvalCase[] = [
      { id: "a", tags: ["fast"],        messages: [{ role: "user", content: "x" }], assertions: [] },
      { id: "b", tags: ["slow"],        messages: [{ role: "user", content: "x" }], assertions: [] },
      { id: "c", tags: ["fast", "exp"], messages: [{ role: "user", content: "x" }], assertions: [] },
    ];
    const inc = await runner.run(cases, { tags_include: ["fast"] });
    expect(inc.total).toBe(2);
    const exc = await runner.run(cases, { tags_exclude: ["exp"] });
    expect(exc.results.map(r => r.case_id)).toEqual(["a", "b"]);
  });

  it("aggregates total cost", async () => {
    const runner = new EvalRunner(async () => stubResponse("x", { cost_usd: 0.05 }));
    const cases: EvalCase[] = Array.from({ length: 3 }, (_, i) => ({
      id: `c${i}`,
      messages: [{ role: "user", content: "x" } as Message],
      assertions: [],
    }));
    const summary = await runner.run(cases);
    expect(summary.total_cost_usd).toBeCloseTo(0.15, 4);
  });

  it("respects concurrency without dropping cases", async () => {
    const runner = new EvalRunner(async () => stubResponse("ok"));
    const cases: EvalCase[] = Array.from({ length: 10 }, (_, i) => ({
      id: `c${i}`,
      messages: [{ role: "user", content: "x" } as Message],
      assertions: [],
    }));
    const summary = await runner.run(cases, { concurrency: 4 });
    expect(summary.total).toBe(10);
    expect(summary.results.map(r => r.case_id)).toEqual(cases.map(c => c.id));
  });
});
