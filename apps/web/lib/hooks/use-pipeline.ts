"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────
export interface PipelineSnapshot {
  run_id: string;
  phase: string;
  progress: number;
  running: boolean;
  current_cycle: number;
  total_cycles: number;
  elapsed_seconds: number;
  error: string | null;
  warnings: string[];
  project_id: string | null;
  scenario_count: number;
  quality_score: number;
  test_results: {
    passed: number;
    failed: number;
  };
}

export interface PipelineStartRequest {
  project_name: string;
  target_url?: string;
  description?: string;
  cycles?: number;
  regulations?: string[];
}

export interface BankingHealth {
  backend: string;
  ollama: string;
  models: string[];
  pipeline: {
    running: boolean;
    phase: string;
    last_run: string | null;
  };
  scheduler: string;
  circuit_breaker: {
    state: string;
    failures: number;
  };
  status: string;
}

// ── Query Keys ───────────────────────────────────────────────────────
export const pipelineKeys = {
  all: ["pipeline"] as const,
  health: () => [...pipelineKeys.all, "health"] as const,
  status: () => [...pipelineKeys.all, "status"] as const,
  history: () => [...pipelineKeys.all, "history"] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

/** Banking AI agent saglik durumu. */
export function useBankingHealth() {
  return useQuery({
    queryKey: pipelineKeys.health(),
    queryFn: () => apiFetch<BankingHealth>("/api/v1/agents/banking/health"),
    staleTime: 30 * 1000, // 30 sn — saglik durumu sik değişir
    refetchInterval: 60 * 1000, // Her 1 dk'da bir otomatik kontrol
  });
}

/** Pipeline mevcut durum (polling ile). */
export function usePipelineStatus(enabled = true) {
  return useQuery({
    queryKey: pipelineKeys.status(),
    queryFn: () =>
      apiFetch<PipelineSnapshot>("/api/v1/agents/pipeline/status"),
    enabled,
    refetchInterval: (query) => {
      // Pipeline çalışmiyorsa polling'i yavaslat
      const data = query.state.data;
      if (data?.running) return 2000; // 2 sn — aktif pipeline
      return 30 * 1000; // 30 sn — bosta
    },
    staleTime: 1000,
  });
}

/** Pipeline başlat. */
export function useStartPipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PipelineStartRequest) =>
      apiFetch("/api/v1/agents/pipeline/start", {
        method: "POST",
        json: data,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.status() });
    },
  });
}

/** Pipeline iptal et. */
export function useCancelPipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/agents/pipeline/cancel", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.status() });
    },
  });
}
