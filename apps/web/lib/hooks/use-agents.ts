"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { AI_AGENTS, type AIAgent } from "@/app/(dashboard)/ai-agents/agents-data";

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

export interface AgentRunV2Response {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  stream_url: string;
  detail_url: string;
}

export interface AgentRunV2ListItem {
  run_id: string;
  project_id: string;
  status: string;
  input_source: string;
  created_at: string;
  completed_at?: string | null;
  cost_usd: number;
  scenario_count: number;
  passed_count: number;
  failed_count: number;
}

export interface AgentRunV2Request {
  project_id: string;
  input_source: "url" | "text" | "swagger" | "manual";
  url?: string;
  text?: string;
  swagger_url?: string;
  extra_context?: string;
}

// ── Query Keys ───────────────────────────────────────────────────────
export const agentKeys = {
  all: ["agents"] as const,
  info: () => [...agentKeys.all, "info"] as const,
  catalog: () => [...agentKeys.all, "catalog"] as const,
  traces: (params?: Record<string, unknown>) =>
    [...agentKeys.all, "traces", params] as const,
  runs: (params?: Record<string, unknown>) =>
    [...agentKeys.all, "runs", params] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Agent bilgilerini getir. */
export function useAgentInfo() {
  return useQuery({
    queryKey: agentKeys.info(),
    queryFn: () => apiFetch<AgentInfo[]>("/api/v1/agents/banking/status"),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Ajan kataloğunu getir.
 * API başarısız olursa statik agents-data.ts verisiyle fallback.
 */
export function useAgentsCatalog(): {
  agents: AIAgent[];
  isLoading: boolean;
  isLive: boolean;
} {
  const query = useQuery({
    queryKey: agentKeys.catalog(),
    queryFn: () => apiFetch<AIAgent[]>("/api/v1/agents/v2/catalog"),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  return {
    agents: (query.data && query.data.length > 0) ? query.data : AI_AGENTS,
    isLoading: query.isLoading,
    isLive: !!query.data,
  };
}

/** Son ajan çalıştırma listesini getir. */
export function useAgentRecentRuns(limit = 10) {
  return useQuery({
    queryKey: agentKeys.runs({ limit }),
    queryFn: () =>
      apiFetch<{ runs: AgentRunV2ListItem[]; total: number }>(
        `/api/v1/agents/v2/runs?limit=${limit}`
      ),
    staleTime: 30 * 1000,
    retry: 1,
  });
}

/** LLM izleme kayıtları (son N kayıt). */
export function useLLMTraces(params?: { limit?: number; agent_name?: string }) {
  const { limit = 50, agent_name } = params ?? {};

  return useQuery({
    queryKey: agentKeys.traces({ limit, agent_name }),
    queryFn: () => {
      const qs = new URLSearchParams();
      qs.set("limit", String(limit));
      if (agent_name) qs.set("agent_name", agent_name);
      return apiFetch<LLMTrace[]>(`/api/v1/ai/llm-traces?${qs}`);
    },
    staleTime: 30 * 1000,
  });
}

/** Nexus Code v2 agent'ını çalıştır. */
export function useRunAgentV2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentRunV2Request) =>
      apiFetch<AgentRunV2Response>("/api/v1/agents/v2/run", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentKeys.runs() });
    },
  });
}
