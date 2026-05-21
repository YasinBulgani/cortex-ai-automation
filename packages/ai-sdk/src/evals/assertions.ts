/**
 * Assertion evaluation — bir CompletionResponse üzerinde her bir Assertion'ı
 * çalıştırır. Pure function, side-effect yok.
 */

import type { CompletionResponse } from "../providers/types";
import type { Assertion, AssertionResult } from "./types";

export function evaluateAssertion(
  assertion: Assertion,
  response: CompletionResponse,
): AssertionResult {
  const content = response.content ?? "";

  switch (assertion.type) {
    case "contains": {
      const haystack = assertion.case_insensitive ? content.toLowerCase() : content;
      const needle = assertion.case_insensitive ? assertion.value.toLowerCase() : assertion.value;
      const pass = haystack.includes(needle);
      return {
        pass,
        assertion,
        reason: pass ? undefined : `expected to contain ${JSON.stringify(assertion.value)}`,
      };
    }

    case "not_contains": {
      const haystack = assertion.case_insensitive ? content.toLowerCase() : content;
      const needle = assertion.case_insensitive ? assertion.value.toLowerCase() : assertion.value;
      const pass = !haystack.includes(needle);
      return {
        pass,
        assertion,
        reason: pass ? undefined : `should not contain ${JSON.stringify(assertion.value)}`,
      };
    }

    case "matches": {
      let regex: RegExp;
      try {
        regex = new RegExp(assertion.pattern, assertion.flags);
      } catch (err) {
        return { pass: false, assertion, reason: `invalid regex: ${(err as Error).message}` };
      }
      const pass = regex.test(content);
      return {
        pass,
        assertion,
        reason: pass ? undefined : `did not match /${assertion.pattern}/${assertion.flags ?? ""}`,
      };
    }

    case "json_valid": {
      try {
        const trimmed = stripCodeFence(content);
        JSON.parse(trimmed);
        return { pass: true, assertion };
      } catch (err) {
        return { pass: false, assertion, reason: `invalid JSON: ${(err as Error).message}` };
      }
    }

    case "json_has_keys": {
      try {
        const trimmed = stripCodeFence(content);
        const obj = JSON.parse(trimmed) as Record<string, unknown>;
        const missing = assertion.keys.filter(k => !(k in obj));
        if (missing.length > 0) {
          return { pass: false, assertion, reason: `missing keys: ${missing.join(", ")}` };
        }
        return { pass: true, assertion };
      } catch (err) {
        return { pass: false, assertion, reason: `not parseable JSON: ${(err as Error).message}` };
      }
    }

    case "min_length": {
      const pass = content.length >= assertion.length;
      return {
        pass,
        assertion,
        reason: pass ? undefined : `length ${content.length} < ${assertion.length}`,
      };
    }

    case "max_length": {
      const pass = content.length <= assertion.length;
      return {
        pass,
        assertion,
        reason: pass ? undefined : `length ${content.length} > ${assertion.length}`,
      };
    }

    case "max_tokens": {
      const tokens = response.usage?.total_tokens ?? 0;
      const pass = tokens <= assertion.limit;
      return {
        pass,
        assertion,
        reason: pass ? undefined : `tokens ${tokens} > limit ${assertion.limit}`,
      };
    }

    case "max_latency_ms": {
      const pass = response.latency_ms <= assertion.limit;
      return {
        pass,
        assertion,
        reason: pass ? undefined : `latency ${response.latency_ms}ms > ${assertion.limit}ms`,
      };
    }

    case "max_cost_usd": {
      const cost = response.cost_usd ?? 0;
      const pass = cost <= assertion.limit;
      return {
        pass,
        assertion,
        reason: pass ? undefined : `cost $${cost.toFixed(4)} > $${assertion.limit.toFixed(4)}`,
      };
    }

    case "custom": {
      const result = assertion.fn(response);
      const pass = result === true;
      return {
        pass,
        assertion,
        reason: pass ? undefined : typeof result === "string" ? result : `custom '${assertion.name}' failed`,
      };
    }
  }
}

/** ```json ... ``` veya ``` ... ``` blokları içindeki content'i çıkarır */
function stripCodeFence(text: string): string {
  const fenceMatch = text.match(/```(?:json|jsonc)?\s*\n?([\s\S]*?)```/);
  return fenceMatch ? fenceMatch[1].trim() : text.trim();
}
