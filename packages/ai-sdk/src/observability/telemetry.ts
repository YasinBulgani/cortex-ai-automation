/**
 * AI Telemetry — her LLM çağrısı için trace + cost attribution.
 *
 * Sink pluggable: console (dev), OpenTelemetry (prod), datadog vb.
 * Critical: PII'yi `redact()` ile temizleyerek gönder.
 */

import type { CompletionRequest, CompletionResponse, ProviderId } from "../providers/types";

export interface AICallRecord {
  request_id: string;
  tenant_id?: string;
  user_id?: string;
  provider: ProviderId;
  model: string;
  intent?: string;
  prompt_id?: string;
  prompt_version?: string;
  timestamp_ms: number;
  duration_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd?: number;
  success: boolean;
  error?: string;
  /** PII-redacted preview, ilk 200 karakter */
  request_preview?: string;
  response_preview?: string;
}

export interface TelemetrySink {
  record(call: AICallRecord): void | Promise<void>;
}

/**
 * Console-based sink — dev/test için.
 */
export class ConsoleSink implements TelemetrySink {
  constructor(private level: "debug" | "info" | "warn" = "info") {}
  record(call: AICallRecord): void {
    const line = `[ai] ${call.provider}/${call.model} ${call.duration_ms}ms tokens=${call.prompt_tokens}+${call.completion_tokens} cost=$${(call.cost_usd ?? 0).toFixed(4)} ${call.success ? "OK" : "FAIL"}`;
    if (this.level === "debug") {
      // eslint-disable-next-line no-console
      console.debug(line, { request_id: call.request_id, tenant: call.tenant_id });
    } else if (this.level === "warn" && !call.success) {
      // eslint-disable-next-line no-console
      console.warn(line, call.error);
    } else {
      // eslint-disable-next-line no-console
      console.info(line);
    }
  }
}

/**
 * In-memory buffer sink — testler için.
 */
export class BufferSink implements TelemetrySink {
  public readonly calls: AICallRecord[] = [];
  record(call: AICallRecord): void {
    this.calls.push(call);
  }
  clear(): void {
    this.calls.length = 0;
  }
}

/**
 * Telemetry registry — birden çok sink'e fan-out.
 */
export class TelemetryRegistry {
  private sinks: TelemetrySink[] = [];

  add(sink: TelemetrySink): void {
    this.sinks.push(sink);
  }

  remove(sink: TelemetrySink): void {
    this.sinks = this.sinks.filter(s => s !== sink);
  }

  async record(call: AICallRecord): Promise<void> {
    await Promise.all(this.sinks.map(s => Promise.resolve(s.record(call))));
  }
}

export const defaultTelemetry = new TelemetryRegistry();

/**
 * Helper — provider çağrısını telemetry'e bağlar.
 */
export async function withTelemetry<T extends CompletionResponse>(
  ctx: {
    provider: ProviderId;
    model?: string;
    tenant_id?: string;
    user_id?: string;
    intent?: string;
    prompt_id?: string;
    request_id?: string;
    request_messages?: CompletionRequest["messages"];
    registry?: TelemetryRegistry;
  },
  fn: () => Promise<T>,
): Promise<T> {
  const start = Date.now();
  const request_id = ctx.request_id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const registry = ctx.registry ?? defaultTelemetry;

  try {
    const response = await fn();
    await registry.record({
      request_id,
      tenant_id: ctx.tenant_id,
      user_id: ctx.user_id,
      provider: ctx.provider,
      model: ctx.model ?? response.model,
      intent: ctx.intent,
      prompt_id: ctx.prompt_id,
      timestamp_ms: start,
      duration_ms: Date.now() - start,
      prompt_tokens: response.usage.prompt_tokens,
      completion_tokens: response.usage.completion_tokens,
      cost_usd: response.cost_usd,
      success: true,
      request_preview: previewMessages(ctx.request_messages),
      response_preview: response.content.slice(0, 200),
    });
    return response;
  } catch (err) {
    await registry.record({
      request_id,
      tenant_id: ctx.tenant_id,
      user_id: ctx.user_id,
      provider: ctx.provider,
      model: ctx.model ?? "unknown",
      intent: ctx.intent,
      prompt_id: ctx.prompt_id,
      timestamp_ms: start,
      duration_ms: Date.now() - start,
      prompt_tokens: 0,
      completion_tokens: 0,
      success: false,
      error: err instanceof Error ? err.message : String(err),
      request_preview: previewMessages(ctx.request_messages),
    });
    throw err;
  }
}

function previewMessages(messages?: CompletionRequest["messages"]): string | undefined {
  if (!messages || messages.length === 0) return undefined;
  const last = messages[messages.length - 1];
  return last.content.slice(0, 200);
}
