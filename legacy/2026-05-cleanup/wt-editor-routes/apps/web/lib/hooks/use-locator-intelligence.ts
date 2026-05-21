"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────

export interface LocatorEntry {
  id?: string;
  name: string;
  selector: string;
  type: string;
  page: string;
  status: string;
}

export interface FallbackResult {
  strategy: string;
  selector: string;
  confidence: number;
  stability_score: number;
  found: boolean;
  reason: string;
  latency_ms: number;
}

export interface FallbackResponse {
  success: boolean;
  best_selector?: string;
  best_strategy?: string;
  best_confidence: number;
  best_stability: number;
  original_selector: string;
  strategies_tried: number;
  total_latency_ms: number;
  all_results: FallbackResult[];
}

export interface StabilityDetail {
  selector: string;
  name: string;
  score: number;
  risk_level: string;
  reasons: string[];
  suggestion?: string;
}

export interface StabilityResponse {
  total_locators: number;
  healthy: number;
  warning: number;
  critical: number;
  avg_score: number;
  details: StabilityDetail[];
  improvements: Record<string, unknown>[];
}

export interface ImproveSuggestion {
  original_selector: string;
  original_score: number;
  suggested_selector: string;
  suggested_score: number;
  improvement_reason: string;
  confidence: number;
}

export interface POMResponse {
  page_name: string;
  language: string;
  code: string;
  element_count: number;
  file_name: string;
}

export interface BreakagePrediction {
  selector: string;
  name: string;
  risk_score: number;
  risk_factors: string[];
  recommendation: string;
}

export interface TrendResponse {
  total_heals: number;
  by_strategy: Record<string, number>;
  by_tier: Record<string, number>;
  most_broken_selectors: Record<string, unknown>[];
  avg_confidence: number;
  trend: string;
}

// ── Request Types ───────────────────────────────────────────────────

export interface FallbackResolveRequest {
  broken_selector: string;
  dom_snippet?: string;
  page_url?: string;
  error_message?: string;
  session_id?: string;
}

export interface StabilityAnalysisRequest {
  locators: LocatorEntry[];
}

export interface ImproveRequest {
  locators: LocatorEntry[];
}

export interface POMGenerateRequest {
  page_name: string;
  language: "typescript" | "python";
  elements?: LocatorEntry[];
  session_id?: string;
}

export interface BreakagePredictionRequest {
  locators: LocatorEntry[];
  recent_changes?: string;
}

// ── Query Keys ──────────────────────────────────────────────────────

const KEYS = {
  trends: ["locator-intelligence", "trends"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────

/** POST /api/v1/agents/locator/resolve — Fallback zinciri ile kirik selector cozumleme */
export function useFallbackResolve() {
  return useMutation({
    mutationFn: (req: FallbackResolveRequest) =>
      apiFetch<FallbackResponse>("/api/v1/agents/locator/resolve", {
        method: "POST",
        json: req,
      }),
  });
}

/** POST /api/v1/agents/locator/stability — Locator stabilite analizi */
export function useStabilityAnalysis() {
  return useMutation({
    mutationFn: (req: StabilityAnalysisRequest) =>
      apiFetch<StabilityResponse>("/api/v1/agents/locator/stability", {
        method: "POST",
        json: req,
      }),
  });
}

/** POST /api/v1/agents/locator/improve — Locator iyilestirme onerileri */
export function useImproveSuggestions() {
  return useMutation({
    mutationFn: (req: ImproveRequest) =>
      apiFetch<ImproveSuggestion[]>("/api/v1/agents/locator/improve", {
        method: "POST",
        json: req,
      }),
  });
}

/** POST /api/v1/agents/locator/pom/generate — Page Object Model uretimi */
export function usePOMGenerate() {
  return useMutation({
    mutationFn: (req: POMGenerateRequest) =>
      apiFetch<POMResponse>("/api/v1/agents/locator/pom/generate", {
        method: "POST",
        json: req,
      }),
  });
}

/** POST /api/v1/agents/locator/predict — Kirilma tahmini */
export function useBreakagePrediction() {
  return useMutation({
    mutationFn: (req: BreakagePredictionRequest) =>
      apiFetch<BreakagePrediction[]>("/api/v1/agents/locator/predict", {
        method: "POST",
        json: req,
      }),
  });
}

/** GET /api/v1/agents/locator/trends — Locator trend istatistikleri */
export function useLocatorTrends() {
  return useQuery({
    queryKey: KEYS.trends,
    queryFn: () =>
      apiFetch<TrendResponse>("/api/v1/agents/locator/trends"),
    retry: 1,
    refetchInterval: 60_000,
  });
}
