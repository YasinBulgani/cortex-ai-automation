/**
 * Tools — AI agent'larının çağırabileceği function definition'ları.
 *
 * MCP (Model Context Protocol) uyumlu. Her tool için:
 *   - JSON Schema (input validation)
 *   - Description (LLM seçim için)
 *   - Handler (sunucu tarafında çalışır)
 */

import type { Tool } from "../providers/types";

export interface ToolHandler<TInput = unknown, TOutput = unknown> {
  schema: Tool;
  execute(input: TInput, ctx: ToolContext): Promise<TOutput>;
}

export interface ToolContext {
  tenant_id: string;
  user_id?: string;
  request_id: string;
}

/**
 * Tool registry — AI agentlar buradan keşfedip çağırır.
 */
export class ToolRegistry {
  private tools: Map<string, ToolHandler> = new Map();

  register<TIn, TOut>(name: string, handler: ToolHandler<TIn, TOut>): void {
    this.tools.set(name, handler as ToolHandler);
  }

  get(name: string): ToolHandler | undefined {
    return this.tools.get(name);
  }

  list(): Tool[] {
    return Array.from(this.tools.values()).map(h => h.schema);
  }

  async invoke(name: string, input: unknown, ctx: ToolContext): Promise<unknown> {
    const handler = this.tools.get(name);
    if (!handler) throw new Error(`Tool not found: ${name}`);
    return handler.execute(input, ctx);
  }
}

// ─── Örnek tool tanımı ─────────────────────────────────────────────────

export const searchProjectTool: ToolHandler<{ query: string; limit?: number }, { results: Array<{ id: string; name: string }> }> = {
  schema: {
    type: "function",
    function: {
      name: "search_projects",
      description: "Tenant içindeki projeleri ada göre arar",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "Arama terimi" },
          limit: { type: "integer", description: "Maks sonuç", default: 10 },
        },
        required: ["query"],
      },
    },
  },
  async execute(input, _ctx) {
    // Bu örnek - gerçek backend implementasyonu burada
    return { results: [{ id: "demo", name: `Result for: ${input.query}` }] };
  },
};
