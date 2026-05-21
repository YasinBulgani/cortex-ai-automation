/**
 * Eval Runner — case'leri sırayla çalıştırır, assertion sonuçlarını toplar.
 *
 * Concurrency: opsiyonel paralellik (default 1, provider rate-limit dostu).
 * Caching: aynı (case + provider + model) için sonuç cache'lenebilir
 * (geliştirme döngüsünde tasarruf).
 */

import type { CompletionResponse, Message } from "../providers/types";
import type { EvalCase, EvalResult, EvalSummary } from "./types";
import { evaluateAssertion } from "./assertions";

export interface EvalRunnerOptions {
  /** Aynı anda kaç case (default 1) */
  concurrency?: number;
  /** Belirli tag'leri filtrele */
  tags_include?: string[];
  /** Filtrele tag'leri hariç tut */
  tags_exclude?: string[];
  /** Belirli case ID'leri */
  case_ids?: string[];
  /** Konsola progress yaz (default false) */
  verbose?: boolean;
}

export type CompletionFn = (req: {
  messages: Message[];
  model?: string;
  max_tokens?: number;
  temperature?: number;
}) => Promise<CompletionResponse>;

export class EvalRunner {
  constructor(private complete: CompletionFn) {}

  async run(cases: EvalCase[], opts: EvalRunnerOptions = {}): Promise<EvalSummary> {
    const filtered = this.filter(cases, opts);
    const concurrency = Math.max(1, opts.concurrency ?? 1);
    const start = Date.now();
    const results: EvalResult[] = [];

    const queue = [...filtered];
    const workers = Array.from({ length: concurrency }, async () => {
      while (queue.length > 0) {
        const c = queue.shift();
        if (!c) break;
        const result = await this.runCase(c);
        if (opts.verbose) {
          const tag = result.skipped ? "SKIP" : result.pass ? "PASS" : "FAIL";
          // eslint-disable-next-line no-console
          console.log(`[eval] ${tag}  ${c.id}${result.error ? "  err=" + result.error : ""}`);
        }
        results.push(result);
      }
    });
    await Promise.all(workers);

    // Ordered by input order, not finish order
    const order = new Map(filtered.map((c, i) => [c.id, i] as const));
    results.sort((a, b) => (order.get(a.case_id) ?? 0) - (order.get(b.case_id) ?? 0));

    return this.summarize(results, Date.now() - start);
  }

  private async runCase(c: EvalCase): Promise<EvalResult> {
    if (c.skip) {
      return {
        case_id: c.id,
        description: c.description,
        pass: false,
        skipped: true,
        skip_reason: c.skip.reason,
        duration_ms: 0,
        assertions: [],
      };
    }

    const start = Date.now();
    let response: CompletionResponse;
    try {
      response = await this.complete({
        messages: c.messages,
        model: c.call?.model,
        max_tokens: c.call?.max_tokens,
        temperature: c.call?.temperature,
      });
    } catch (err) {
      return {
        case_id: c.id,
        description: c.description,
        pass: false,
        duration_ms: Date.now() - start,
        assertions: [],
        error: err instanceof Error ? err.message : String(err),
      };
    }

    const assertionResults = c.assertions.map(a => evaluateAssertion(a, response));
    const pass = assertionResults.every(r => r.pass);
    return {
      case_id: c.id,
      description: c.description,
      pass,
      duration_ms: Date.now() - start,
      response,
      assertions: assertionResults,
    };
  }

  private filter(cases: EvalCase[], opts: EvalRunnerOptions): EvalCase[] {
    return cases.filter(c => {
      if (opts.case_ids && !opts.case_ids.includes(c.id)) return false;
      if (opts.tags_include && opts.tags_include.length > 0) {
        const tags = c.tags ?? [];
        if (!opts.tags_include.some(t => tags.includes(t))) return false;
      }
      if (opts.tags_exclude && opts.tags_exclude.length > 0) {
        const tags = c.tags ?? [];
        if (opts.tags_exclude.some(t => tags.includes(t))) return false;
      }
      return true;
    });
  }

  private summarize(results: EvalResult[], duration_ms: number): EvalSummary {
    const passed = results.filter(r => r.pass).length;
    const skipped = results.filter(r => r.skipped).length;
    const errors = results.filter(r => !r.skipped && r.error).length;
    const failed = results.length - passed - skipped - errors;
    const total_cost_usd = results.reduce(
      (sum, r) => sum + (r.response?.cost_usd ?? 0),
      0,
    );
    return {
      total: results.length,
      passed,
      failed,
      skipped,
      errors,
      pass_rate: results.length === 0 ? 1 : passed / (results.length - skipped),
      duration_ms,
      total_cost_usd,
      results,
    };
  }
}
