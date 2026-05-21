/**
 * Eval framework types.
 *
 * Bir EvalCase, deterministic veya LLM-as-judge stratejisiyle bir
 * prompt + provider çıktısının kalite kontrolünü yapar.
 */

import type { CompletionResponse, Message } from "../providers/types";

export interface EvalCase {
  /** Insan-okunabilir benzersiz ID */
  id: string;
  /** Açıklama (regression report için) */
  description?: string;
  /** Bu case için prompt template ID + version (deklaratif iz için) */
  prompt_ref?: { id: string; version?: string };
  /** Modele gönderilecek mesajlar */
  messages: Message[];
  /** Çağrı parametreleri */
  call?: {
    model?: string;
    max_tokens?: number;
    temperature?: number;
  };
  /** Çıktı assertion'ları (AND mantığı — hepsi geçmeli) */
  assertions: Assertion[];
  /** Etiketler (filtering için) */
  tags?: string[];
  /** Skip et + sebep */
  skip?: { reason: string };
}

/** Assertion union — tipsel olarak ayrıştırılır */
export type Assertion =
  | { type: "contains"; value: string; case_insensitive?: boolean }
  | { type: "not_contains"; value: string; case_insensitive?: boolean }
  | { type: "matches"; pattern: string; flags?: string }
  | { type: "json_valid" }
  | { type: "json_has_keys"; keys: string[] }
  | { type: "min_length"; length: number }
  | { type: "max_length"; length: number }
  | { type: "max_tokens"; limit: number }
  | { type: "max_latency_ms"; limit: number }
  | { type: "max_cost_usd"; limit: number }
  | { type: "custom"; name: string; fn: (resp: CompletionResponse) => boolean | string };

export interface AssertionResult {
  pass: boolean;
  assertion: Assertion;
  /** Fail nedeni */
  reason?: string;
}

export interface EvalResult {
  case_id: string;
  description?: string;
  pass: boolean;
  skipped?: boolean;
  skip_reason?: string;
  duration_ms: number;
  response?: CompletionResponse;
  /** Her assertion'ın sonucu */
  assertions: AssertionResult[];
  /** Test-time error (provider throw vs.) */
  error?: string;
}

export interface EvalSummary {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  errors: number;
  pass_rate: number;
  duration_ms: number;
  /** Toplam cost (varsa) */
  total_cost_usd: number;
  results: EvalResult[];
}
