/**
 * Shared provider helpers — circuit breaker, retry, fetch wrapper.
 * Tüm providerlar bunu kullanır.
 */

import type {
  CompletionRequest,
  CompletionResponse,
  Message,
  Provider,
  ProviderCapabilities,
  ProviderId,
  StreamChunk,
} from "./types";

export interface ProviderConfig {
  api_key?: string;
  base_url?: string;
  timeout_ms?: number;
}

export type CircuitState = "closed" | "open" | "half-open";

export interface CircuitBreakerOptions {
  failure_threshold: number;
  reset_timeout_ms: number;
}

const DEFAULT_BREAKER: CircuitBreakerOptions = {
  failure_threshold: 5,
  reset_timeout_ms: 30_000,
};

export class CircuitBreaker {
  private state: CircuitState = "closed";
  private failures = 0;
  private opened_at = 0;
  private opts: CircuitBreakerOptions;

  constructor(opts: Partial<CircuitBreakerOptions> = {}) {
    this.opts = { ...DEFAULT_BREAKER, ...opts };
  }

  get currentState(): CircuitState {
    if (this.state === "open" && Date.now() - this.opened_at >= this.opts.reset_timeout_ms) {
      this.state = "half-open";
    }
    return this.state;
  }

  recordSuccess(): void {
    this.failures = 0;
    this.state = "closed";
  }

  recordFailure(): void {
    this.failures += 1;
    if (this.failures >= this.opts.failure_threshold) {
      this.state = "open";
      this.opened_at = Date.now();
    }
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.currentState === "open") {
      throw new CircuitOpenError("Circuit breaker is open");
    }
    try {
      const result = await fn();
      this.recordSuccess();
      return result;
    } catch (err) {
      this.recordFailure();
      throw err;
    }
  }
}

export class CircuitOpenError extends Error {
  constructor(msg: string) {
    super(msg);
    this.name = "CircuitOpenError";
  }
}

export class ProviderError extends Error {
  constructor(
    msg: string,
    public readonly provider: ProviderId,
    public readonly status?: number,
    public readonly retriable: boolean = false,
  ) {
    super(msg);
    this.name = "ProviderError";
  }
}

/**
 * Fetch with timeout + JSON body — provider implementations için yardımcı.
 */
export async function fetchJson(
  url: string,
  init: RequestInit & { timeout_ms?: number } = {},
): Promise<Response> {
  const { timeout_ms = 30_000, ...rest } = init;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout_ms);
  try {
    const res = await fetch(url, {
      ...rest,
      signal: rest.signal ?? controller.signal,
      headers: {
        "content-type": "application/json",
        ...(rest.headers ?? {}),
      },
    });
    return res;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Server-Sent Events stream parser — token-by-token akış.
 */
export async function* parseSSE(stream: ReadableStream<Uint8Array>): AsyncIterable<string> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const event = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        for (const line of event.split("\n")) {
          if (line.startsWith("data: ")) {
            yield line.slice(6);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Base provider — common behavior (circuit breaker, error mapping).
 * Concrete providers extend this.
 */
export abstract class BaseProvider implements Provider {
  abstract readonly id: ProviderId;
  abstract readonly capabilities: ProviderCapabilities;
  protected breaker: CircuitBreaker;

  constructor(protected config: ProviderConfig = {}, breakerOpts?: Partial<CircuitBreakerOptions>) {
    this.breaker = new CircuitBreaker(breakerOpts);
  }

  abstract complete(req: CompletionRequest): Promise<CompletionResponse>;

  async health(): Promise<{ healthy: boolean; latency_ms?: number; error?: string }> {
    const start = Date.now();
    if (this.breaker.currentState === "open") {
      return { healthy: false, error: "circuit_open" };
    }
    try {
      // Minimal health check — kısa prompt
      await this.complete({
        messages: [{ role: "user", content: "ping" }],
        max_tokens: 1,
        timeout_ms: 5000,
      });
      return { healthy: true, latency_ms: Date.now() - start };
    } catch (err) {
      return {
        healthy: false,
        latency_ms: Date.now() - start,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }

  protected requireApiKey(): string {
    if (!this.config.api_key) {
      throw new ProviderError(`Missing API key for ${this.id}`, this.id);
    }
    return this.config.api_key;
  }
}

/**
 * Cost helper — input/output token başına maliyet hesabı.
 */
export function computeCost(
  input_tokens: number,
  output_tokens: number,
  rates: { input_per_million_usd: number; output_per_million_usd: number },
): number {
  return (
    (input_tokens / 1_000_000) * rates.input_per_million_usd +
    (output_tokens / 1_000_000) * rates.output_per_million_usd
  );
}

/**
 * System mesajını ayıklayıp diğer mesajları döndürür — Anthropic gibi
 * system'i ayrı parametre alan API'ler için.
 */
export function splitSystem(messages: Message[]): { system: string; rest: Message[] } {
  const system = messages.filter(m => m.role === "system").map(m => m.content).join("\n\n");
  const rest = messages.filter(m => m.role !== "system");
  return { system, rest };
}

export type { Provider, CompletionRequest, CompletionResponse, StreamChunk };
