"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────
export interface LLMTrace {
  id: string;
  agent_name: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  success: boolean;
  error?: string;
  created_at: string;
}

export interface AgentInfo {
  name: string;
  description: string;
  version: string;
  models: string[];
}

// ── Query Keys ───────────────────────────────────────────────────────
export const agentKeys = {
  all: ["agents"] as const,
  info: () => [...agentKeys.all, "info"] as const,
  traces: (params?: Record<string, unknown>) =>
    [...agentKeys.all, "traces", params] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Agent bilgilerini getir. */
export function useAgentInfo() {
  return useQuery({
    queryKey: agentKeys.info(),
    queryFn: () => apiFetch<AgentInfo[]>("/api/v1/agents/banking/agents"),
    staleTime: 5 * 60 * 1000,
  });
}

/** LLM izleme kayitlari (son N kayit). */
export function useLLMTraces(params?: { limit?: number; agent_name?: string }) {
  const { limit = 50, agent_name } = params ?? {};

  return useQuery({
    queryKey: agentKeys.traces({ limit, agent_name }),
    queryFn: () => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      if (agent_name) qs.set("agent_name", agent_name);
      return apiFetch<LLMTrace[]>(`/api/v1/agents/banking/traces?${qs}`);
    },
    staleTime: 30 * 1000,
  });
}
