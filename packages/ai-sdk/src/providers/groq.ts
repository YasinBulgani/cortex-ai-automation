/**
 * Groq provider — OpenAI-compatible /chat/completions API.
 * Çok hızlı LPU inference, küçük modeller için ucuz.
 */

import {
  BaseProvider,
  ProviderError,
  computeCost,
  fetchJson,
  parseSSE,
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
  "llama-3.1-8b-instant":  { input_per_million_usd: 0.05, output_per_million_usd: 0.08 },
  "llama-3.3-70b-versatile": { input_per_million_usd: 0.59, output_per_million_usd: 0.79 },
  "mixtral-8x7b-32768":    { input_per_million_usd: 0.24, output_per_million_usd: 0.24 },
};

export class GroqProvider extends BaseProvider {
  readonly id: ProviderId = "groq";
  readonly capabilities: ProviderCapabilities = {
    id: "groq",
    models: ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
    cost_per_million_tokens: 0.4,
    ttft_p95_ms: 150, // Groq is very fast
    max_context: 128_000,
    supports_tools: true,
    supports_streaming: true,
    supports_vision: false,
  };

  private readonly base_url: string;

  constructor(config: ProviderConfig = {}) {
    super(config);
    this.base_url = config.base_url ?? "https://api.groq.com/openai/v1";
  }

  async complete(req: CompletionRequest): Promise<CompletionResponse> {
    return this.breaker.execute(async () => {
      const start = Date.now();
      const apiKey = this.requireApiKey();
      const model = req.model ?? "llama-3.1-8b-instant";

      const body: Record<string, unknown> = {
        model,
        messages: req.messages.map(m => ({
          role: m.role,
          content: m.content,
          ...(m.tool_call_id ? { tool_call_id: m.tool_call_id } : {}),
        })),
      };
      if (req.max_tokens) body.max_tokens = req.max_tokens;
      if (req.temperature !== undefined) body.temperature = req.temperature;
      if (req.tools?.length) body.tools = req.tools;

      const res = await fetchJson(`${this.base_url}/chat/completions`, {
        method: "POST",
        headers: { authorization: `Bearer ${apiKey}` },
        body: JSON.stringify(body),
        timeout_ms: req.timeout_ms,
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new ProviderError(
          `Groq ${res.status}: ${txt.slice(0, 500)}`,
          "groq",
          res.status,
          res.status >= 500 || res.status === 429,
        );
      }

      const data = (await res.json()) as OpenAIResponse;
      const choice = data.choices?.[0];
      const usage = {
        prompt_tokens: data.usage?.prompt_tokens ?? 0,
        completion_tokens: data.usage?.completion_tokens ?? 0,
        total_tokens: data.usage?.total_tokens ?? 0,
      };
      const rates = COST_RATES[model];
      const cost_usd = rates ? computeCost(usage.prompt_tokens, usage.completion_tokens, rates) : undefined;

      return {
        id: data.id ?? "",
        model: data.model ?? model,
        content: choice?.message?.content ?? "",
        tool_calls: choice?.message?.tool_calls?.map(tc => ({
          id: tc.id,
          type: "function" as const,
          function: { name: tc.function.name, arguments: tc.function.arguments },
        })),
        finish_reason: mapFinish(choice?.finish_reason),
        usage,
        cost_usd,
        latency_ms: Date.now() - start,
      };
    });
  }

  async *stream(req: CompletionRequest): AsyncIterable<StreamChunk> {
    const apiKey = this.requireApiKey();
    const model = req.model ?? "llama-3.1-8b-instant";
    const body: Record<string, unknown> = {
      model,
      messages: req.messages,
      stream: true,
    };
    if (req.max_tokens) body.max_tokens = req.max_tokens;
    if (req.temperature !== undefined) body.temperature = req.temperature;

    const res = await fetchJson(`${this.base_url}/chat/completions`, {
      method: "POST",
      headers: { authorization: `Bearer ${apiKey}` },
      body: JSON.stringify(body),
      timeout_ms: req.timeout_ms,
    });
    if (!res.ok || !res.body) {
      throw new ProviderError(`Groq stream ${res.status}`, "groq", res.status);
    }

    for await (const raw of parseSSE(res.body)) {
      if (raw === "[DONE]") {
        yield { delta: "", done: true };
        return;
      }
      try {
        const evt = JSON.parse(raw) as OpenAIStreamChunk;
        const delta = evt.choices?.[0]?.delta?.content;
        if (delta) yield { delta, done: false };
      } catch {
        // skip malformed
      }
    }
  }
}

function mapFinish(reason: string | null | undefined): CompletionResponse["finish_reason"] {
  if (!reason) return "stop";
  if (reason === "length") return "length";
  if (reason === "tool_calls") return "tool_calls";
  if (reason === "content_filter") return "content_filter";
  return "stop";
}

interface OpenAIResponse {
  id?: string;
  model?: string;
  choices?: Array<{
    message?: { content?: string; tool_calls?: Array<{ id: string; function: { name: string; arguments: string } }> };
    finish_reason?: string;
  }>;
  usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
}

interface OpenAIStreamChunk {
  choices?: Array<{ delta?: { content?: string } }>;
}
