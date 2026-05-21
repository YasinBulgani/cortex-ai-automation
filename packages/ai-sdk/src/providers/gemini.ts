/**
 * Google Gemini provider — generateContent API.
 * Docs: https://ai.google.dev/gemini-api/docs
 */

import {
  BaseProvider,
  ProviderError,
  computeCost,
  fetchJson,
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
  "gemini-2.0-flash":      { input_per_million_usd: 0.1, output_per_million_usd: 0.4 },
  "gemini-2.5-pro":        { input_per_million_usd: 1.25, output_per_million_usd: 5.0 },
  "gemini-2.5-flash":      { input_per_million_usd: 0.075, output_per_million_usd: 0.3 },
  "gemini-1.5-flash":      { input_per_million_usd: 0.075, output_per_million_usd: 0.3 },
};

export class GeminiProvider extends BaseProvider {
  readonly id: ProviderId = "gemini";
  readonly capabilities: ProviderCapabilities = {
    id: "gemini",
    models: ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    cost_per_million_tokens: 0.5,
    ttft_p95_ms: 600,
    max_context: 1_000_000,
    supports_tools: true,
    supports_streaming: true,
    supports_vision: true,
  };

  private readonly base_url: string;

  constructor(config: ProviderConfig = {}) {
    super(config);
    this.base_url = config.base_url ?? "https://generativelanguage.googleapis.com/v1beta";
  }

  async complete(req: CompletionRequest): Promise<CompletionResponse> {
    return this.breaker.execute(async () => {
      const start = Date.now();
      const apiKey = this.requireApiKey();
      const model = req.model ?? "gemini-2.5-flash";
      const url = `${this.base_url}/models/${model}:generateContent?key=${apiKey}`;
      const body = this.buildBody(req);

      const res = await fetchJson(url, {
        method: "POST",
        body: JSON.stringify(body),
        timeout_ms: req.timeout_ms,
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new ProviderError(
          `Gemini ${res.status}: ${txt.slice(0, 500)}`,
          "gemini",
          res.status,
          res.status >= 500 || res.status === 429,
        );
      }

      const data = (await res.json()) as GeminiResponse;
      const cand = data.candidates?.[0];
      const content = (cand?.content?.parts ?? [])
        .map(p => p.text ?? "")
        .join("");

      const usage = {
        prompt_tokens: data.usageMetadata?.promptTokenCount ?? 0,
        completion_tokens: data.usageMetadata?.candidatesTokenCount ?? 0,
        total_tokens: data.usageMetadata?.totalTokenCount ?? 0,
      };
      const rates = COST_RATES[model];
      const cost_usd = rates
        ? computeCost(usage.prompt_tokens, usage.completion_tokens, rates)
        : undefined;

      return {
        id: data.responseId ?? "",
        model,
        content,
        finish_reason: mapFinish(cand?.finishReason),
        usage,
        cost_usd,
        latency_ms: Date.now() - start,
      };
    });
  }

  async *stream(req: CompletionRequest): AsyncIterable<StreamChunk> {
    const apiKey = this.requireApiKey();
    const model = req.model ?? "gemini-2.5-flash";
    const url = `${this.base_url}/models/${model}:streamGenerateContent?alt=sse&key=${apiKey}`;
    const body = this.buildBody(req);

    const res = await fetchJson(url, {
      method: "POST",
      body: JSON.stringify(body),
      timeout_ms: req.timeout_ms,
    });
    if (!res.ok || !res.body) {
      throw new ProviderError(`Gemini stream ${res.status}`, "gemini", res.status);
    }

    const { parseSSE } = await import("./base");
    for await (const raw of parseSSE(res.body)) {
      try {
        const evt = JSON.parse(raw) as GeminiResponse;
        const text = evt.candidates?.[0]?.content?.parts?.[0]?.text;
        if (text) yield { delta: text, done: false };
      } catch {
        // skip
      }
    }
    yield { delta: "", done: true };
  }

  private buildBody(req: CompletionRequest): Record<string, unknown> {
    const contents = req.messages
      .filter(m => m.role !== "system")
      .map(m => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      }));
    const systemContent = req.messages.filter(m => m.role === "system").map(m => m.content).join("\n\n");

    const body: Record<string, unknown> = { contents };
    if (systemContent) {
      body.systemInstruction = { parts: [{ text: systemContent }] };
    }
    const genConfig: Record<string, unknown> = {};
    if (req.max_tokens) genConfig.maxOutputTokens = req.max_tokens;
    if (req.temperature !== undefined) genConfig.temperature = req.temperature;
    if (Object.keys(genConfig).length) body.generationConfig = genConfig;

    return body;
  }
}

function mapFinish(reason: string | null | undefined): CompletionResponse["finish_reason"] {
  switch (reason) {
    case "STOP": return "stop";
    case "MAX_TOKENS": return "length";
    case "SAFETY": return "content_filter";
    case "RECITATION": return "content_filter";
    default: return "stop";
  }
}

interface GeminiResponse {
  responseId?: string;
  candidates?: Array<{
    content?: { parts?: Array<{ text?: string }> };
    finishReason?: string;
  }>;
  usageMetadata?: {
    promptTokenCount?: number;
    candidatesTokenCount?: number;
    totalTokenCount?: number;
  };
}
