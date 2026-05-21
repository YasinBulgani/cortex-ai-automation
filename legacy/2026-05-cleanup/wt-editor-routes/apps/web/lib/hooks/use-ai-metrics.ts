"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Quality Metrics Types ───────────────────────────────────────────

export interface MetricsOverview {
  total_calls: number;
  success_rate: number;
  json_parse_rate: number;
  avg_latency_ms: number;
  unique_agents: number;
  unique_models: number;
}

export interface AgentMetrics {
  agent: string;
  calls: number;
  success_rate: number;
  json_parse_rate: number;
  avg_latency_ms: number;
  error_count: number;
}

export interface ModelMetrics {
  model: string;
  calls: number;
  success_rate: number;
  json_parse_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
}

export interface DailyTrend {
  date: string;
  calls: number;
  success_rate: number;
  avg_latency_ms: number;
}

export interface ErrorDistribution {
  timeout: number;
  connection_error: number;
  json_parse_failure: number;
  rate_limit: number;
  unknown: number;
}

export interface MetricsPeriod {
  start: string;
  end: string;
  days: number;
}

export interface QualityMetrics {
  period: MetricsPeriod;
  overview: MetricsOverview;
  by_agent: AgentMetrics[];
  by_model: ModelMetrics[];
  daily_trend: DailyTrend[];
  error_distribution: ErrorDistribution;
  recommendations: string[];
}

// ── LLM Trace Types ────────────────────────────────────────────────

export interface LlmTrace {
  id: string;
  run_id: string;
  agent_name: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost_usd: number;
  status: "success" | "error" | "timeout";
  error_message?: string;
  quality_score?: number;
  input_preview?: string;
  output_preview?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface TraceStats {
  total_traces: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  success_count: number;
  error_count: number;
  timeout_count: number;
  traces_by_agent: Record<string, number>;
  traces_by_model: Record<string, number>;
  traces_by_status: Record<string, number>;
}

// ── Model Router Types ─────────────────────────────────────────────

export interface ModelRouterStats {
  default_model: string;
  available_models: string[];
  routing_rules: Array<{
    agent_name?: string;
    task_type?: string;
    model: string;
    priority: number;
  }>;
  model_usage: Record<string, number>;
  total_routed: number;
  fallback_count: number;
}

// ── Cross-Agent Memory Types ───────────────────────────────────────

export interface CrossAgentMemoryStats {
  total_entries: number;
  by_event_type: Record<string, number>;
  by_agent: Record<string, number>;
  top_tags: Record<string, number>;
  run_id?: string | null;
}

export interface CrossAgentEntry {
  id: string;
  event_type: string;
  agent_name: string;
  source_agent?: string;
  content: string;
  metadata?: Record<string, unknown>;
  relevance_score?: number;
  created_at: string;
  expires_at?: string;
}

// ── Few-Shot Bank Types ────────────────────────────────────────────

export interface FewShotBankStats {
  categories: Record<string, number>;
  counts: {
    total: number;
    active: number;
    archived: number;
    by_quality: Record<string, number>;
  };
}

// ── Query Keys ──────────────────────────────────────────────────────

export const aiMetricsKeys = {
  all: ["ai"] as const,
  qualityMetrics: (projectId: string | undefined, days: number, agentName?: string, model?: string) =>
    ["ai", "quality-metrics", projectId, days, agentName, model] as const,
  llmTraces: (projectId: string | undefined, runId?: string, agentName?: string, limit?: number) =>
    ["ai", "llm-traces", projectId, runId, agentName, limit] as const,
  llmTraceStats: (projectId: string | undefined) => ["ai", "llm-traces", "stats", projectId] as const,
  modelRouterStats: () => ["ai", "model-router", "stats"] as const,
  crossAgentMemoryStats: () => ["ai", "cross-agent-memory", "stats"] as const,
  crossAgentMemoryEntries: (eventType?: string, agentName?: string, limit?: number) =>
    ["ai", "cross-agent-memory", "entries", eventType, agentName, limit] as const,
  fewShotBankStats: () => ["ai", "few-shot-bank", "stats"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────

/**
 * Fetch aggregated LLM quality metrics with optional filters.
 */
export function useQualityMetrics(
  projectId: string | undefined,
  days = 30,
  agentName?: string,
  model?: string,
) {
  return useQuery({
    queryKey: aiMetricsKeys.qualityMetrics(projectId, days, agentName, model),
    queryFn: () => {
      if (!projectId) {
        throw new Error("Proje secimi olmadan LLM metrikleri yuklenemez.");
      }
      const params = new URLSearchParams();
      params.set("days", String(days));
      params.set("project_id", projectId);
      if (agentName) params.set("agent_name", agentName);
      if (model) params.set("model", model);
      return apiFetch<QualityMetrics>(`/api/v1/ai/quality-metrics?${params}`);
    },
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });
}

/**
 * Fetch LLM trace records, optionally filtered by run_id, agent_name, and limit.
 */
export function useLlmTraces(
  projectId: string | undefined,
  runId?: string,
  agentName?: string,
  limit?: number,
) {
  return useQuery({
    queryKey: aiMetricsKeys.llmTraces(projectId, runId, agentName, limit),
    queryFn: () => {
      if (!projectId) {
        throw new Error("Proje secimi olmadan LLM trace kayitlari yuklenemez.");
      }
      const params = new URLSearchParams();
      params.set("project_id", projectId);
      if (runId) params.set("run_id", runId);
      if (agentName) params.set("agent_name", agentName);
      if (limit !== undefined) params.set("limit", String(limit));
      const qs = params.toString();
      return apiFetch<{ traces: LlmTrace[] }>(
        `/api/v1/ai/llm-traces${qs ? `?${qs}` : ""}`,
      );
    },
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });
}

/**
 * Fetch summary statistics for all LLM traces.
 */
export function useLlmTraceStats(projectId: string | undefined) {
  return useQuery({
    queryKey: aiMetricsKeys.llmTraceStats(projectId),
    queryFn: () => {
      if (!projectId) {
        throw new Error("Proje secimi olmadan LLM trace istatistikleri yuklenemez.");
      }
      return apiFetch<TraceStats>(`/api/v1/ai/llm-traces/stats?project_id=${encodeURIComponent(projectId)}`);
    },
    enabled: Boolean(projectId),
    staleTime: 60_000,
  });
}

/**
 * Fetch model router configuration and usage stats.
 */
export function useModelRouterStats() {
  return useQuery({
    queryKey: aiMetricsKeys.modelRouterStats(),
    queryFn: () => apiFetch<ModelRouterStats>("/api/v1/ai/model-router/stats"),
    staleTime: 60_000,
  });
}

/**
 * Fetch cross-agent memory statistics.
 */
export function useCrossAgentMemoryStats() {
  return useQuery({
    queryKey: aiMetricsKeys.crossAgentMemoryStats(),
    queryFn: () =>
      apiFetch<CrossAgentMemoryStats>("/api/v1/ai/cross-agent-memory/stats"),
    staleTime: 60_000,
  });
}

/**
 * Fetch cross-agent memory entries with optional filters.
 */
export function useCrossAgentMemoryEntries(
  eventType?: string,
  agentName?: string,
  limit?: number,
) {
  return useQuery({
    queryKey: aiMetricsKeys.crossAgentMemoryEntries(eventType, agentName, limit),
    queryFn: () => {
      const params = new URLSearchParams();
      if (eventType) params.set("event_type", eventType);
      if (agentName) params.set("agent_name", agentName);
      if (limit !== undefined) params.set("limit", String(limit));
      const qs = params.toString();
      return apiFetch<{ entries: CrossAgentEntry[] }>(
        `/api/v1/ai/cross-agent-memory/entries${qs ? `?${qs}` : ""}`,
      );
    },
    staleTime: 30_000,
  });
}

/**
 * Fetch few-shot example bank statistics.
 */
export function useFewShotBankStats() {
  return useQuery({
    queryKey: aiMetricsKeys.fewShotBankStats(),
    queryFn: () => apiFetch<FewShotBankStats>("/api/v1/ai/few-shot-bank/stats"),
    staleTime: 60_000,
  });
}
