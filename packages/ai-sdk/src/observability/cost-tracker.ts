/**
 * Cost tracker — tenant/user başı LLM harcamasını biriktir.
 *
 * In-memory (default); production'da Redis/DB persistence implement et.
 */

import type { AICallRecord, TelemetrySink } from "./telemetry";

export interface CostAggregate {
  total_usd: number;
  total_calls: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  by_provider: Record<string, number>;
  by_model: Record<string, number>;
}

export class CostTracker implements TelemetrySink {
  private byTenant: Map<string, CostAggregate> = new Map();
  private byUser: Map<string, CostAggregate> = new Map();
  private global: CostAggregate = emptyAggregate();

  record(call: AICallRecord): void {
    const cost = call.cost_usd ?? 0;
    this.applyTo(this.global, call, cost);
    if (call.tenant_id) {
      this.applyTo(this.getOrCreate(this.byTenant, call.tenant_id), call, cost);
    }
    if (call.user_id) {
      this.applyTo(this.getOrCreate(this.byUser, call.user_id), call, cost);
    }
  }

  forTenant(tenant_id: string): CostAggregate {
    return this.byTenant.get(tenant_id) ?? emptyAggregate();
  }

  forUser(user_id: string): CostAggregate {
    return this.byUser.get(user_id) ?? emptyAggregate();
  }

  totals(): CostAggregate {
    return this.global;
  }

  reset(): void {
    this.byTenant.clear();
    this.byUser.clear();
    this.global = emptyAggregate();
  }

  /**
   * Tenant'ın budget'i aşıp aşmadığını kontrol et.
   * @returns true = budget aşıldı, AI çağrısı engellenmeli.
   */
  isOverBudget(tenant_id: string, budget_usd: number): boolean {
    return this.forTenant(tenant_id).total_usd >= budget_usd;
  }

  private getOrCreate(map: Map<string, CostAggregate>, key: string): CostAggregate {
    let agg = map.get(key);
    if (!agg) {
      agg = emptyAggregate();
      map.set(key, agg);
    }
    return agg;
  }

  private applyTo(agg: CostAggregate, call: AICallRecord, cost: number): void {
    agg.total_usd += cost;
    agg.total_calls += 1;
    agg.total_prompt_tokens += call.prompt_tokens;
    agg.total_completion_tokens += call.completion_tokens;
    agg.by_provider[call.provider] = (agg.by_provider[call.provider] ?? 0) + cost;
    agg.by_model[call.model] = (agg.by_model[call.model] ?? 0) + cost;
  }
}

function emptyAggregate(): CostAggregate {
  return {
    total_usd: 0,
    total_calls: 0,
    total_prompt_tokens: 0,
    total_completion_tokens: 0,
    by_provider: {},
    by_model: {},
  };
}
