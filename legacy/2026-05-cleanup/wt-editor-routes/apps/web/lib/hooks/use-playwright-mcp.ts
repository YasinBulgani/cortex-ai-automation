"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────

// Health / Sessions
export interface PlaywrightHealthResponse {
  status: "ok" | "unavailable";
  playwright_version?: string;
  browsers?: string[];
  message?: string;
}

export interface PlaywrightSession {
  session_id: string;
  status: "active" | "closed";
  browser: string;
  url?: string;
  title?: string;
  created_at: string;
  closed_at?: string;
}

export interface CreateSessionRequest {
  browser?: "chromium" | "firefox" | "webkit";
  headless?: boolean;
  viewport?: { width: number; height: number };
}

export interface CreateSessionResponse {
  session_id: string;
  status: string;
  browser: string;
  created_at: string;
}

// Navigate
export interface NavigateRequest {
  url: string;
  wait_until?: "load" | "domcontentloaded" | "networkidle";
}

export interface NavigateResponse {
  url: string;
  title: string;
  status: number;
}

// Screenshot
export interface ScreenshotResponse {
  session_id: string;
  image_base64: string;
  format: string;
  timestamp: string;
}

// DOM Snapshot
export interface DOMNode {
  tag: string;
  attributes: Record<string, string>;
  children?: DOMNode[];
  text?: string;
  suggested_selectors?: string[];
}

export interface DOMSnapshotRequest {
  selector?: string;
  max_depth?: number;
}

export interface DOMSnapshotResponse {
  session_id: string;
  root: DOMNode;
  node_count: number;
  timestamp: string;
}

// Selector Validation
export interface SelectorValidationItem {
  selector: string;
  found: boolean;
  count: number;
  visible: boolean;
  tag?: string;
  stability_score: number;
  alternatives?: string[];
}

export interface ValidateSelectorsRequest {
  selectors: string[];
}

export interface ValidateSelectorsResponse {
  session_id: string;
  results: SelectorValidationItem[];
}

// Suggest Selectors
export interface SuggestSelectorsRequest {
  selector: string;
  strategy?: "css" | "xpath" | "text" | "role" | "testid" | "all";
}

export interface SuggestSelectorsResponse {
  original: string;
  suggestions: Array<{
    selector: string;
    type: string;
    confidence: number;
  }>;
}

// Browser Action
export interface BrowserActionRequest {
  action: "click" | "fill" | "hover" | "select" | "check" | "uncheck" | "press";
  selector: string;
  value?: string;
}

export interface BrowserActionResponse {
  action: string;
  selector: string;
  success: boolean;
  error?: string;
  timestamp: string;
}

// Heal Verify
export interface VerifyHealRequest {
  original_selector: string;
  healed_selector: string;
  expected_tag?: string;
  expected_text?: string;
}

export interface VerifyHealResponse {
  original_found: boolean;
  healed_found: boolean;
  matches_expected: boolean;
  confidence: number;
  recommendation: string;
  details?: {
    original_tag?: string;
    healed_tag?: string;
    original_text?: string;
    healed_text?: string;
  };
}

// Heal Pipeline
export interface RunHealPipelineRequest {
  test_case_id: string;
  broken_selectors: Array<{
    selector: string;
    context?: string;
  }>;
  session_id?: string;
}

export interface HealResult {
  original_selector: string;
  healed_selector: string;
  confidence: number;
  strategy: string;
  verified: boolean;
}

export interface RunHealPipelineResponse {
  pipeline_id: string;
  test_case_id: string;
  results: HealResult[];
  total: number;
  healed: number;
  failed: number;
  duration_ms: number;
}

export interface HealHistoryItem {
  pipeline_id: string;
  test_case_id: string;
  healed: number;
  failed: number;
  duration_ms: number;
  created_at: string;
}

export interface HealStatsResponse {
  total_pipelines: number;
  total_selectors_healed: number;
  total_selectors_failed: number;
  avg_confidence: number;
  avg_duration_ms: number;
  by_strategy: Record<string, number>;
}

// ── Query Keys ───────────────────────────────────────────────────────

const KEYS = {
  health: ["playwright-mcp", "health"] as const,
  sessions: ["playwright-mcp", "sessions"] as const,
  screenshot: (sid: string) => ["playwright-mcp", "screenshot", sid] as const,
  domSnapshot: (sid: string) => ["playwright-mcp", "dom-snapshot", sid] as const,
  healHistory: (limit?: number) => ["playwright-mcp", "heal-history", limit] as const,
  healStats: ["playwright-mcp", "heal-stats"] as const,
};

// ── Session Management Hooks ─────────────────────────────────────────

export function usePlaywrightHealth() {
  return useQuery({
    queryKey: KEYS.health,
    queryFn: () =>
      apiFetch<PlaywrightHealthResponse>("/api/v1/playwright-mcp/health"),
    retry: 1,
    refetchInterval: 30_000,
  });
}

export function usePlaywrightSessions() {
  return useQuery({
    queryKey: KEYS.sessions,
    queryFn: () =>
      apiFetch<PlaywrightSession[]>("/api/v1/playwright-mcp/sessions"),
  });
}

export function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req?: CreateSessionRequest) =>
      apiFetch<CreateSessionResponse>("/api/v1/playwright-mcp/sessions", {
        method: "POST",
        json: req ?? {},
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.sessions });
    },
  });
}

export function useCloseSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      apiFetch<{ closed: boolean }>(`/api/v1/playwright-mcp/sessions/${sessionId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.sessions });
    },
  });
}

// ── Browser Action Hooks ─────────────────────────────────────────────

export function useNavigate(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: NavigateRequest) =>
      apiFetch<NavigateResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/navigate`,
        { method: "POST", json: req },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.screenshot(sessionId) });
      void qc.invalidateQueries({ queryKey: KEYS.sessions });
    },
  });
}

export function useScreenshot(sessionId: string) {
  return useQuery({
    queryKey: KEYS.screenshot(sessionId),
    queryFn: () =>
      apiFetch<ScreenshotResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/screenshot`,
      ),
    enabled: !!sessionId,
    refetchOnWindowFocus: false,
  });
}

export function useDOMSnapshot(sessionId: string) {
  return useMutation({
    mutationFn: (req?: DOMSnapshotRequest) =>
      apiFetch<DOMSnapshotResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/dom-snapshot`,
        { method: "POST", json: req ?? {} },
      ),
  });
}

export function useValidateSelectors(sessionId: string) {
  return useMutation({
    mutationFn: (req: ValidateSelectorsRequest) =>
      apiFetch<ValidateSelectorsResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/validate-selectors`,
        { method: "POST", json: req },
      ),
  });
}

export function useSuggestSelectors(sessionId: string) {
  return useMutation({
    mutationFn: (req: SuggestSelectorsRequest) =>
      apiFetch<SuggestSelectorsResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/suggest-selectors`,
        { method: "POST", json: req },
      ),
  });
}

export function useBrowserAction(sessionId: string) {
  return useMutation({
    mutationFn: (req: BrowserActionRequest) =>
      apiFetch<BrowserActionResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/action`,
        { method: "POST", json: req },
      ),
  });
}

export function useVerifyHeal(sessionId: string) {
  return useMutation({
    mutationFn: (req: VerifyHealRequest) =>
      apiFetch<VerifyHealResponse>(
        `/api/v1/playwright-mcp/sessions/${sessionId}/verify-heal`,
        { method: "POST", json: req },
      ),
  });
}

// ── Heal Pipeline Hooks ──────────────────────────────────────────────

export function useRunHealPipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: RunHealPipelineRequest) =>
      apiFetch<RunHealPipelineResponse>("/api/v1/agents/heal/run", {
        method: "POST",
        json: req,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.healHistory() });
      void qc.invalidateQueries({ queryKey: KEYS.healStats });
    },
  });
}

export function useHealHistory(limit?: number) {
  return useQuery({
    queryKey: KEYS.healHistory(limit),
    queryFn: () =>
      apiFetch<HealHistoryItem[]>(
        `/api/v1/agents/heal/history${limit ? `?limit=${limit}` : ""}`,
      ),
  });
}

export function useHealStats() {
  return useQuery({
    queryKey: KEYS.healStats,
    queryFn: () =>
      apiFetch<HealStatsResponse>("/api/v1/agents/heal/stats"),
  });
}
