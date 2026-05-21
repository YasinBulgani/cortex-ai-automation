/**
 * Eval cases — analysis.test-failure promptu için.
 * Output JSON formatı zorunlu, belirli anahtarlar beklenir.
 */

import { renderPrompt } from "../../prompts/registry";
import { analyzeTestFailure } from "../../prompts/library";
import type { EvalCase } from "../types";

export const analyzeTestFailureCases: EvalCase[] = [
  {
    id: "analysis.test-failure.timeout",
    description: "Timeout hatası → JSON root-cause analizi",
    prompt_ref: { id: analyzeTestFailure.id, version: analyzeTestFailure.version },
    tags: ["analysis", "json-output"],
    messages: [
      {
        role: "user",
        content: renderPrompt(analyzeTestFailure, {
          test_name: "login_with_valid_credentials",
          error_message: "Timeout 30000ms exceeded waiting for selector '#dashboard'",
          stack_trace: "at Page.waitForSelector (lib/page.ts:142:11)\n  at LoginFlow.assertDashboard (steps/login.ts:88:5)",
          recent_changes: "feat(auth): added 2FA challenge step",
        }),
      },
    ],
    call: { max_tokens: 800 },
    assertions: [
      { type: "json_valid" },
      { type: "json_has_keys", keys: ["root_cause", "confidence", "fix_suggestion"] },
      { type: "max_latency_ms", limit: 20_000 },
    ],
  },
];
