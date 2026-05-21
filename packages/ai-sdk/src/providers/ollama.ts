/**
 * Ollama provider — local LLM inference.
 * Tenant gizli verisi içeren request'ler için (veri dışarı çıkmaz).
 * Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
 */

import {
  BaseProvider,
  ProviderError,
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

export class OllamaProvider extends BaseProvider {
  readonly id: ProviderId = "ollama";
  readonly capabilities: ProviderCapabilities = {
    id: "ollama",
    models: ["qwen2.5-coder:7b", "llama3.1:8b", "qwen2.5:14b", "mistral-nemo:12b"],
    cost_per_million_tokens: 0, // local
    ttft_p95_ms: 800, // depends on hw
    max_context: 32_000,
    supports_tools: true,
    supports_streaming: true,
    supports_vision: false,
  };

  private readonly base_url: string;

  constructor(config: ProviderConfig = {}) {
    super(config);
    this.base_url = config.base_url ?? "http://localhost:11434";
  }

  async complete(req: CompletionRequest): Promise<CompletionResponse> {
    return this.breaker.execute(async () => {
      const start = Date.now();
      const model = req.model ?? "qwen2.5-coder:7b";

      const body: Record<string, unknown> = {
        model,
        messages: req.messages.map(m => ({
          role: m.role === "tool" ? "user" : m.role,
          content: m.content,
        })),
        stream: false,
        options: {} as Record<string, unknown>,
      };
      if (req.temperature !== undefined) (body.options as Record<string, unknown>).temperature = req.temperature;
      if (req.max_tokens) (body.options as Record<string, unknown>).num_predict = req.max_tokens;

      const res = await fetchJson(`${this.base_url}/api/chat`, {
        method: "POST",
        body: JSON.stringify(body),
        timeout_ms: req.timeout_ms ?? 120_000,
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new ProviderError(
          `Ollama ${res.status}: ${txt.slice(0, 500)}`,
          "ollama",
          res.status,
          res.status >= 500,
        );
      }

      const data = (await res.json()) as OllamaResponse;

      return {
        id: data.created_at ?? "",
        model: data.model ?? model,
        content: data.message?.content ?? "",
        finish_reason: data.done ? "stop" : "length",
        usage: {
          prompt_tokens: data.prompt_eval_count ?? 0,
          completion_tokens: data.eval_count ?? 0,
          total_tokens: (data.prompt_eval_count ?? 0) + (data.eval_count ?? 0),
        },
        cost_usd: 0,
        latency_ms: Date.now() - start,
      };
    });
  }

  async *stream(req: CompletionRequest): AsyncIterable<StreamChunk> {
    const model = req.model ?? "qwen2.5-coder:7b";

    const body: Record<string, unknown> = {
      model,
      messages: req.messages.map(m => ({
        role: m.role === "tool" ? "user" : m.role,
        content: m.content,
      })),
      stream: true,
    };
    if (req.temperature !== undefined || req.max_tokens) {
      const opts: Record<string, unknown> = {};
      if (req.temperature !== undefined) opts.temperature = req.temperature;
      if (req.max_tokens) opts.num_predict = req.max_tokens;
      body.options = opts;
    }

    const res = await fetchJson(`${this.base_url}/api/chat`, {
      method: "POST",
      body: JSON.stringify(body),
      timeout_ms: req.timeout_ms ?? 120_000,
    });
    if (!res.ok || !res.body) {
      throw new ProviderError(`Ollama stream ${res.status}`, "ollama", res.status);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, idx).trim();
          buffer = buffer.slice(idx + 1);
          if (!line) continue;
          try {
            const evt = JSON.parse(line) as OllamaResponse;
            const text = evt.message?.content;
            if (text) yield { delta: text, done: false };
            if (evt.done) {
              yield { delta: "", done: true };
              return;
            }
          } catch {
            // skip
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

interface OllamaResponse {
  created_at?: string;
  model?: string;
  done?: boolean;
  message?: { role?: string; content?: string };
  prompt_eval_count?: number;
  eval_count?: number;
}
