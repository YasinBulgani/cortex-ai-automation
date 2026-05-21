/**
 * Anthropic Claude provider — Messages API v1.
 * Docs: https://docs.anthropic.com/en/api/messages
 */

import {
  BaseProvider,
  ProviderError,
  computeCost,
  fetchJson,
  parseSSE,
  splitSystem,
  type ProviderConfig,
} from "./base";
import type {
  CompletionRequest,
  CompletionResponse,
  ProviderCapabilities,
  ProviderId,
  StreamChunk,
} from "./types";

const COST_RATES: Record<string, { input_per_million_usd: number; output_per_million_usd: number }> = {
  "claude-opus-4-7":        { input_per_million_usd: 15,  output_per_million_usd: 75 },
  "claude-sonnet-4-6":      { input_per_million_usd: 3,   output_per_million_usd: 15 },
  "claude-haiku-4-5":       { input_per_million_usd: 0.8, output_per_million_usd: 4 },
  "claude-3-5-sonnet-latest": { input_per_million_usd: 3, output_per_million_usd: 15 },
  "claude-3-5-haiku-latest":  { input_per_million_usd: 0.8, output_per_million_usd: 4 },
};

export class AnthropicProvider extends BaseProvider {
  readonly id: ProviderId = "anthropic";
  readonly capabilities: ProviderCapabilities = {
    id: "anthropic",
    models: ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
    cost_per_million_tokens: 9, // weighted avg
    ttft_p95_ms: 1200,
    max_context: 200_000,
    supports_tools: true,
    supports_streaming: true,
    supports_vision: true,
  };

  private readonly base_url: string;

  constructor(config: ProviderConfig = {}) {
    super(config);
    this.base_url = config.base_url ?? "https://api.anthropic.com/v1";
  }

  async complete(req: CompletionRequest): Promise<CompletionResponse> {
    return this.breaker.execute(async () => {
      const start = Date.now();
      const apiKey = this.requireApiKey();
      const model = req.model ?? "claude-sonnet-4-6";
      const { system, rest } = splitSystem(req.messages);

      const body: Record<string, unknown> = {
        model,
        max_tokens: req.max_tokens ?? 1024,
        messages: rest.map(m => ({
          role: m.role === "tool" ? "user" : m.role,
          content: m.content,
        })),
      };
      if (system) body.system = system;
      if (req.temperature !== undefined) body.temperature = req.temperature;
      if (req.tools?.length) {
        body.tools = req.tools.map(t => ({
          name: t.function.name,
          description: t.function.description,
          input_schema: t.function.parameters,
        }));
      }

      const res = await fetchJson(`${this.base_url}/messages`, {
        method: "POST",
        headers: {
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify(body),
        timeout_ms: req.timeout_ms,
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new ProviderError(
          `Anthropic ${res.status}: ${txt.slice(0, 500)}`,
          "anthropic",
          res.status,
          res.status >= 500 || res.status === 429,
        );
      }

      const data = (await res.json()) as AnthropicResponse;
      const content = (data.content ?? [])
        .filter(b => b.type === "text")
        .map(b => b.text ?? "")
        .join("");

      const usage = {
        prompt_tokens: data.usage?.input_tokens ?? 0,
        completion_tokens: data.usage?.output_tokens ?? 0,
        total_tokens:
          (data.usage?.input_tokens ?? 0) + (data.usage?.output_tokens ?? 0),
      };
      const rates = COST_RATES[model];
      const cost_usd = rates ? computeCost(usage.prompt_tokens, usage.completion_tokens, rates) : undefined;

      return {
        id: data.id,
        model: data.model,
        content,
        tool_calls: (data.content ?? [])
          .filter(b => b.type === "tool_use")
          .map(b => ({
            id: b.id ?? "",
            type: "function" as const,
            function: {
              name: b.name ?? "",
              arguments: JSON.stringify(b.input ?? {}),
            },
          })),
        finish_reason: mapFinishReason(data.stop_reason),
        usage,
        cost_usd,
        latency_ms: Date.now() - start,
      };
    });
  }

  async *stream(req: CompletionRequest): AsyncIterable<StreamChunk> {
    const apiKey = this.requireApiKey();
    const model = req.model ?? "claude-sonnet-4-6";
    const { system, rest } = splitSystem(req.messages);

    const body: Record<string, unknown> = {
      model,
      max_tokens: req.max_tokens ?? 1024,
      messages: rest.map(m => ({
        role: m.role === "tool" ? "user" : m.role,
        content: m.content,
      })),
      stream: true,
    };
    if (system) body.system = system;
    if (req.temperature !== undefined) body.temperature = req.temperature;

    const res = await fetchJson(`${this.base_url}/messages`, {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(body),
      timeout_ms: req.timeout_ms,
    });

    if (!res.ok || !res.body) {
      throw new ProviderError(`Anthropic stream ${res.status}`, "anthropic", res.status);
    }

    for await (const raw of parseSSE(res.body)) {
      try {
        const evt = JSON.parse(raw) as AnthropicStreamEvent;
        if (evt.type === "content_block_delta" && evt.delta?.text) {
          yield { delta: evt.delta.text, done: false };
        }
        if (evt.type === "message_stop") {
          yield { delta: "", done: true };
        }
      } catch {
        // ignore malformed event
      }
    }
  }
}

function mapFinishReason(stop: string | null | undefined): CompletionResponse["finish_reason"] {
  switch (stop) {
    case "end_turn": return "stop";
    case "max_tokens": return "length";
    case "tool_use": return "tool_calls";
    case "stop_sequence": return "stop";
    default: return "stop";
  }
}

interface AnthropicResponse {
  id: string;
  model: string;
  stop_reason?: string;
  content?: Array<{ type: string; text?: string; id?: string; name?: string; input?: unknown }>;
  usage?: { input_tokens?: number; output_tokens?: number };
}

interface AnthropicStreamEvent {
  type: string;
  delta?: { text?: string };
}
