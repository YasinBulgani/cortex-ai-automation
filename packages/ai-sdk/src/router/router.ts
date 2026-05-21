/**
 * Intelligent Router — maliyet + latency + kalite optimum seçim.
 *
 * Task tipine ve constraintlere göre en uygun sağlayıcıyı seçer.
 * Fallback chain destekler: birincil başarısız olursa ikinciye düşer.
 *
 * Kullanım:
 *   const router = new IntelligentRouter([anthropic, groq, gemini, ollama]);
 *   const result = await router.complete({
 *     intent: "code_generation",
 *     messages: [{ role: "user", content: "Yaz bir BDD senaryosu..." }],
 *     latency_sla_ms: 5000,
 *     quality_preference: "high",
 *   });
 */

import type {
  Provider,
  ProviderId,
  CompletionRequest,
  CompletionResponse,
} from "../providers/types";

export type Intent =
  | "intent_classification"
  | "form_autocomplete"
  | "test_step_suggestion"
  | "scenario_generation"
  | "code_generation"
  | "bug_root_cause"
  | "vision_analysis"
  | "general";

export type QualityPreference = "fastest" | "balanced" | "high";

export interface RouterRequest extends CompletionRequest {
  intent: Intent;
  latency_sla_ms?: number;
  quality_preference?: QualityPreference;
  /** Tenant cost budget — null = unlimited */
  cost_budget_usd?: number;
}

/**
 * Intent → provider tier mapping
 *
 * Tier 1: cheap & fast (Groq Llama 8B)
 * Tier 2: balanced (Gemini Flash, Claude Haiku)
 * Tier 3: high quality (Claude Sonnet, Claude Opus)
 */
const INTENT_TIER_MAP: Record<Intent, ProviderId[]> = {
  intent_classification: ["groq", "ollama"],
  form_autocomplete:     ["groq", "gemini", "ollama"],
  test_step_suggestion:  ["gemini", "anthropic", "groq"],
  scenario_generation:   ["anthropic", "gemini"],
  code_generation:       ["anthropic", "ollama"],
  bug_root_cause:        ["anthropic"],
  vision_analysis:       ["anthropic", "gemini"],
  general:               ["gemini", "anthropic", "ollama"],
};

export class IntelligentRouter {
  private providers: Map<ProviderId, Provider> = new Map();

  constructor(providers: Provider[]) {
    for (const p of providers) this.providers.set(p.id, p);
  }

  /**
   * Verilen istek için en uygun sağlayıcıyı seç + çalıştır.
   * Fallback chain ile başarısızlık halinde alternatif denenir.
   */
  async complete(req: RouterRequest): Promise<CompletionResponse> {
    const candidates = this.rank(req);

    if (candidates.length === 0) {
      throw new Error(`No provider available for intent: ${req.intent}`);
    }

    let lastError: Error | null = null;
    for (const provider of candidates) {
      try {
        return await provider.complete(req);
      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));
        // Continue to next candidate
      }
    }

    throw new Error(`All providers failed. Last: ${lastError?.message}`);
  }

  /**
   * Stream completion — async iterable döndürür.
   * İlk başarılı sağlayıcıdan akış başlar.
   */
  async *stream(req: RouterRequest) {
    const candidates = this.rank(req).filter(p => p.stream);

    if (candidates.length === 0) {
      throw new Error("No streaming provider available");
    }

    for (const provider of candidates) {
      if (!provider.stream) continue;
      try {
        for await (const chunk of provider.stream(req)) {
          yield chunk;
        }
        return;
      } catch {
        // Try next
        continue;
      }
    }

    throw new Error("All streaming providers failed");
  }

  /**
   * Sağlayıcıları intent + constraint'lere göre sırala.
   * Sıradaki ilk eleman = primary choice.
   */
  private rank(req: RouterRequest): Provider[] {
    const tier = INTENT_TIER_MAP[req.intent] ?? INTENT_TIER_MAP.general;
    const candidates: Provider[] = [];

    // Quality preference override
    const orderedTier = req.quality_preference === "fastest"
      ? [...tier].reverse()   // Hızlı = cheap tier'lar önce
      : req.quality_preference === "high"
        ? tier                // High = premium önce (intent map zaten doğru sırada)
        : tier;               // Balanced = default

    for (const id of orderedTier) {
      const p = this.providers.get(id);
      if (!p) continue;

      // Latency SLA filter
      if (req.latency_sla_ms && p.capabilities.ttft_p95_ms > req.latency_sla_ms) {
        continue;
      }

      candidates.push(p);
    }

    return candidates;
  }

  /**
   * Tüm sağlayıcıların sağlık durumu.
   */
  async healthCheck(): Promise<Record<ProviderId, { healthy: boolean; latency_ms?: number; error?: string }>> {
    const entries = await Promise.all(
      Array.from(this.providers.values()).map(async p => {
        try {
          return [p.id, await p.health()] as const;
        } catch (err) {
          return [p.id, { healthy: false, error: err instanceof Error ? err.message : String(err) }] as const;
        }
      })
    );
    return Object.fromEntries(entries) as Record<ProviderId, { healthy: boolean; latency_ms?: number; error?: string }>;
  }

  /**
   * Maliyet tahmini — gerçek çağrı yapmadan.
   */
  estimateCost(req: RouterRequest, estimated_tokens: number): { provider: ProviderId; cost_usd: number } | null {
    const candidates = this.rank(req);
    if (candidates.length === 0) return null;
    const primary = candidates[0];
    return {
      provider: primary.id,
      cost_usd: (estimated_tokens / 1_000_000) * primary.capabilities.cost_per_million_tokens,
    };
  }
}
