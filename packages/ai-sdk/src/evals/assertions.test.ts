import { describe, it, expect } from "vitest";
import { evaluateAssertion } from "./assertions";
import type { CompletionResponse } from "../providers/types";

function resp(overrides: Partial<CompletionResponse> = {}): CompletionResponse {
  return {
    id: "x",
    model: "m",
    content: "",
    finish_reason: "stop",
    usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
    latency_ms: 0,
    ...overrides,
  };
}

describe("evaluateAssertion", () => {
  describe("contains", () => {
    it("passes when substring present", () => {
      const r = evaluateAssertion(
        { type: "contains", value: "hello" },
        resp({ content: "well hello there" }),
      );
      expect(r.pass).toBe(true);
    });

    it("fails when missing", () => {
      const r = evaluateAssertion(
        { type: "contains", value: "missing" },
        resp({ content: "well hello there" }),
      );
      expect(r.pass).toBe(false);
    });

    it("respects case_insensitive", () => {
      const r = evaluateAssertion(
        { type: "contains", value: "HELLO", case_insensitive: true },
        resp({ content: "well hello there" }),
      );
      expect(r.pass).toBe(true);
    });
  });

  describe("not_contains", () => {
    it("passes when string absent", () => {
      const r = evaluateAssertion(
        { type: "not_contains", value: "PII" },
        resp({ content: "clean output" }),
      );
      expect(r.pass).toBe(true);
    });

    it("fails when string present", () => {
      const r = evaluateAssertion(
        { type: "not_contains", value: "PII" },
        resp({ content: "leaked PII content" }),
      );
      expect(r.pass).toBe(false);
    });
  });

  describe("matches", () => {
    it("passes for valid regex match", () => {
      const r = evaluateAssertion(
        { type: "matches", pattern: "\\d{3}", flags: "g" },
        resp({ content: "code: 123 and 456" }),
      );
      expect(r.pass).toBe(true);
    });

    it("returns descriptive reason on invalid regex", () => {
      const r = evaluateAssertion(
        { type: "matches", pattern: "[unclosed" },
        resp({ content: "x" }),
      );
      expect(r.pass).toBe(false);
      expect(r.reason).toContain("invalid regex");
    });
  });

  describe("json_valid", () => {
    it("passes on parseable JSON", () => {
      const r = evaluateAssertion({ type: "json_valid" }, resp({ content: '{"a": 1}' }));
      expect(r.pass).toBe(true);
    });

    it("passes on JSON inside ```json fence", () => {
      const r = evaluateAssertion(
        { type: "json_valid" },
        resp({ content: '```json\n{"a": 1}\n```' }),
      );
      expect(r.pass).toBe(true);
    });

    it("fails on invalid JSON", () => {
      const r = evaluateAssertion({ type: "json_valid" }, resp({ content: "not json" }));
      expect(r.pass).toBe(false);
    });
  });

  describe("json_has_keys", () => {
    it("passes when all keys present", () => {
      const r = evaluateAssertion(
        { type: "json_has_keys", keys: ["root_cause", "confidence"] },
        resp({ content: '{"root_cause":"timeout","confidence":0.9}' }),
      );
      expect(r.pass).toBe(true);
    });

    it("fails listing missing keys", () => {
      const r = evaluateAssertion(
        { type: "json_has_keys", keys: ["root_cause", "fix"] },
        resp({ content: '{"root_cause":"x"}' }),
      );
      expect(r.pass).toBe(false);
      expect(r.reason).toContain("fix");
    });
  });

  describe("length", () => {
    it("min_length passes when long enough", () => {
      const r = evaluateAssertion(
        { type: "min_length", length: 5 },
        resp({ content: "hello" }),
      );
      expect(r.pass).toBe(true);
    });

    it("max_length fails when too long", () => {
      const r = evaluateAssertion(
        { type: "max_length", length: 3 },
        resp({ content: "hello" }),
      );
      expect(r.pass).toBe(false);
    });
  });

  describe("perf/cost", () => {
    it("max_latency_ms passes when within limit", () => {
      const r = evaluateAssertion(
        { type: "max_latency_ms", limit: 1000 },
        resp({ latency_ms: 500 }),
      );
      expect(r.pass).toBe(true);
    });

    it("max_cost_usd fails when over", () => {
      const r = evaluateAssertion(
        { type: "max_cost_usd", limit: 0.001 },
        resp({ cost_usd: 0.01 }),
      );
      expect(r.pass).toBe(false);
      expect(r.reason).toContain("$0.0010");
    });

    it("max_tokens uses usage.total_tokens", () => {
      const r = evaluateAssertion(
        { type: "max_tokens", limit: 100 },
        resp({ usage: { prompt_tokens: 50, completion_tokens: 60, total_tokens: 110 } }),
      );
      expect(r.pass).toBe(false);
    });
  });

  describe("custom", () => {
    it("passes when fn returns true", () => {
      const r = evaluateAssertion(
        { type: "custom", name: "starts-with-x", fn: r => r.content.startsWith("x") },
        resp({ content: "x marks the spot" }),
      );
      expect(r.pass).toBe(true);
    });

    it("uses string return as reason", () => {
      const r = evaluateAssertion(
        { type: "custom", name: "n", fn: () => "specific failure" },
        resp(),
      );
      expect(r.pass).toBe(false);
      expect(r.reason).toBe("specific failure");
    });
  });
});
