/**
 * Provider tipleri — sağlayıcı agnostik interface.
 *
 * Hangi LLM olursa olsun (Anthropic, Groq, Gemini, Ollama), aynı
 * şekilde çağrılır. Implementation detayı `providers/{name}.ts` içinde.
 */

export type Role = "system" | "user" | "assistant" | "tool";

export interface Message {
  role: Role;
  content: string;
  /** Tool call results için */
  tool_call_id?: string;
  /** Tool execution çıktıları */
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string; // JSON string
  };
}

export interface Tool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: Record<string, unknown>; // JSON Schema
  };
}

export interface CompletionRequest {
  messages: Message[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  tools?: Tool[];
  stream?: boolean;
  /** Tenant attribution — cost tracking için */
  tenant_id?: string;
  /** User attribution */
  user_id?: string;
  /** İsteğin maksimum bekleme süresi (ms) */
  timeout_ms?: number;
}

export interface CompletionResponse {
  id: string;
  model: string;
  content: string;
  tool_calls?: ToolCall[];
  finish_reason: "stop" | "length" | "tool_calls" | "content_filter" | "error";
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  cost_usd?: number;
  latency_ms: number;
}

export interface StreamChunk {
  delta: string;
  done: boolean;
}

export type ProviderId = "anthropic" | "groq" | "gemini" | "ollama" | "openai" | "g4f" | "vllm";

export interface ProviderCapabilities {
  id: ProviderId;
  models: string[];
  /** Tahmini USD / 1M token (input + output ortalama) */
  cost_per_million_tokens: number;
  /** Tahmini p95 latency ms — ilk token */
  ttft_p95_ms: number;
  /** Maksimum context */
  max_context: number;
  /** Tool calling destekliyor mu */
  supports_tools: boolean;
  /** Streaming destekliyor mu */
  supports_streaming: boolean;
  /** Vision destekliyor mu */
  supports_vision: boolean;
}

export interface Provider {
  readonly id: ProviderId;
  readonly capabilities: ProviderCapabilities;
  complete(req: CompletionRequest): Promise<CompletionResponse>;
  stream?(req: CompletionRequest): AsyncIterable<StreamChunk>;
  health(): Promise<{ healthy: boolean; latency_ms?: number; error?: string }>;
}
