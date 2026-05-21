"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────
export interface ApiEnvironment {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  variables: Record<string, string>;
  sensitive_keys: string[];
  is_default: boolean;
  created_at?: string;
}

export interface ApiSpec {
  id: string;
  project_id: string;
  name: string;
  version?: string;
  spec_format: string;
  endpoint_count: number;
  schema_count: number;
  ai_analysis?: Record<string, unknown>;
  source_url?: string;
  created_at?: string;
}

export interface ApiEndpoint {
  id: string;
  spec_id: string;
  method: string;
  path: string;
  operation_id?: string;
  summary?: string;
  description?: string;
  tags: string[];
  parameters: Record<string, unknown>[];
  request_body_schema?: Record<string, unknown>;
  response_schemas: Record<string, unknown>;
  auth_required: boolean;
  risk_level: string;
  has_pii: boolean;
  has_financial: boolean;
  compliance_tags: string[];
  test_case_count: number;
}

export interface ApiTestCase {
  id: string;
  project_id: string;
  endpoint_id?: string;
  title: string;
  description?: string;
  test_type: string;
  priority: string;
  owasp_category?: string;
  regulation?: string;
  request_method: string;
  request_path: string;
  request_headers: Record<string, string>;
  request_body?: Record<string, unknown>;
  assertions: Record<string, unknown>[];
  ai_generated: boolean;
  ai_reasoning?: string;
  review_status: string;
  last_run_status?: string;
  last_run_at?: string;
  run_count: number;
  pass_count: number;
  fail_count: number;
  created_at?: string;
}

export interface ApiTestingStats {
  specs: number;
  endpoints: number;
  test_cases: number;
  ai_generated: number;
  chains: number;
  environments: number;
  test_type_distribution: Record<string, number>;
  review_status_distribution: Record<string, number>;
  last_run: { passed: number; failed: number; pass_rate: number };
}

export interface ExecutionResult {
  method: string;
  url: string;
  status_code?: number;
  response_size_bytes: number;
  total_ms: number;
  passed: boolean;
  error?: string;
  assertion_results: Array<{
    index: number;
    type: string;
    passed: boolean;
    expected: unknown;
    actual: unknown;
    message: string;
  }>;
  response_body?: string;
  response_headers: Record<string, string>;
}

// ── Execution History Types ─────────────────────────────────────────
export interface ExecutionHistoryItem {
  run_id: string;
  timestamp?: string;
  total: number;
  passed: number;
  failed: number;
  duration_ms: number;
  pass_rate: number;
  status: "passed" | "failed" | "mixed";
  test_types: string[];
}

export interface ExecutionHistoryResponse {
  items: ExecutionHistoryItem[];
  total_count: number;
  page: number;
  per_page: number;
}

export interface ExecutionDetailItem {
  id: string;
  test_case_id?: string;
  test_case_title?: string;
  actual_method: string;
  actual_url: string;
  status_code?: number;
  total_ms: number;
  passed: boolean;
  error_message?: string;
  assertion_results: Array<Record<string, unknown>>;
  schema_valid?: boolean;
  executed_at?: string;
}

export interface ExecutionRunDetailResponse {
  run_id: string;
  timestamp?: string;
  total: number;
  passed: number;
  failed: number;
  duration_ms: number;
  pass_rate: number;
  status: "passed" | "failed" | "mixed";
  details: ExecutionDetailItem[];
}

export interface TrendDayData {
  date: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_response_ms: number;
  run_count: number;
}

export interface TestTypeTrendItem {
  test_type: string;
  count: number;
  passed: number;
  failed: number;
}

export interface TrendResponse {
  days: TrendDayData[];
  total_runs: number;
  avg_pass_rate: number;
  avg_response_ms: number;
  most_failed_test_type?: string;
  test_type_distribution: TestTypeTrendItem[];
}

// ── Query Keys ───────────────────────────────────────────────────────
const BASE = (pid: string) => `/api/v1/api-testing/projects/${pid}`;

export const apiTestingKeys = {
  all: (pid: string) => ["api-testing", pid] as const,
  stats: (pid: string) => [...apiTestingKeys.all(pid), "stats"] as const,
  environments: (pid: string) => [...apiTestingKeys.all(pid), "environments"] as const,
  specs: (pid: string) => [...apiTestingKeys.all(pid), "specs"] as const,
  specDetail: (pid: string, sid: string) => [...apiTestingKeys.specs(pid), sid] as const,
  endpoints: (pid: string, filters?: Record<string, unknown>) =>
    [...apiTestingKeys.all(pid), "endpoints", filters] as const,
  testCases: (pid: string, filters?: Record<string, unknown>) =>
    [...apiTestingKeys.all(pid), "test-cases", filters] as const,
  chains: (pid: string) => [...apiTestingKeys.all(pid), "chains"] as const,
  executionHistory: (pid: string, filters?: Record<string, unknown>) =>
    [...apiTestingKeys.all(pid), "execution-history", filters] as const,
  executionDetail: (pid: string, runId: string) =>
    [...apiTestingKeys.all(pid), "execution-detail", runId] as const,
  trends: (pid: string, days?: number) =>
    [...apiTestingKeys.all(pid), "trends", days] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────

export function useApiTestingStats(projectId: string | undefined) {
  return useQuery({
    queryKey: apiTestingKeys.stats(projectId!),
    queryFn: () => apiFetch<ApiTestingStats>(`${BASE(projectId!)}/stats`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useEnvironments(projectId: string | undefined) {
  return useQuery({
    queryKey: apiTestingKeys.environments(projectId!),
    queryFn: () => apiFetch<ApiEnvironment[]>(`${BASE(projectId!)}/environments`),
    enabled: !!projectId,
  });
}

export function useApiSpecs(projectId: string | undefined) {
  return useQuery({
    queryKey: apiTestingKeys.specs(projectId!),
    queryFn: () => apiFetch<ApiSpec[]>(`${BASE(projectId!)}/specs`),
    enabled: !!projectId,
  });
}

export function useApiEndpoints(
  projectId: string | undefined,
  filters?: { spec_id?: string; risk_level?: string; has_pii?: boolean },
) {
  return useQuery({
    queryKey: apiTestingKeys.endpoints(projectId!, filters),
    queryFn: () => {
      const qs = new URLSearchParams();
      if (filters?.spec_id) qs.set("spec_id", filters.spec_id);
      if (filters?.risk_level) qs.set("risk_level", filters.risk_level);
      if (filters?.has_pii !== undefined) qs.set("has_pii", String(filters.has_pii));
      const query = qs.toString();
      return apiFetch<ApiEndpoint[]>(`${BASE(projectId!)}/endpoints${query ? `?${query}` : ""}`);
    },
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useApiTestCases(
  projectId: string | undefined,
  filters?: { endpoint_id?: string; test_type?: string; review_status?: string },
) {
  return useQuery({
    queryKey: apiTestingKeys.testCases(projectId!, filters),
    queryFn: () => {
      const qs = new URLSearchParams();
      if (filters?.endpoint_id) qs.set("endpoint_id", filters.endpoint_id);
      if (filters?.test_type) qs.set("test_type", filters.test_type);
      if (filters?.review_status) qs.set("review_status", filters.review_status);
      const query = qs.toString();
      return apiFetch<ApiTestCase[]>(`${BASE(projectId!)}/test-cases${query ? `?${query}` : ""}`);
    },
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useImportSpec(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { source_url?: string; content?: string; name?: string }) =>
      apiFetch<ApiSpec>(`${BASE(projectId)}/specs/import`, { method: "POST", json: body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.specs(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

export function useAiGenerate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      mode: string;
      spec_id?: string;
      endpoint_ids?: string[];
      regulations?: string[];
      test_types?: string[];
      max_tests_per_endpoint?: number;
    }) => apiFetch<{
      mode: string;
      generated_count: number;
      test_cases: ApiTestCase[];
      warnings: string[];
      ai_model?: string;
      duration_ms: number;
    }>(`${BASE(projectId)}/ai/generate`, { method: "POST", json: body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.testCases(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

export function useExecuteSingle(projectId: string) {
  return useMutation({
    mutationFn: (body: {
      method: string;
      url: string;
      headers?: Record<string, string>;
      params?: Record<string, string>;
      body?: unknown;
      environment_id?: string;
      assertions?: Record<string, unknown>[];
      timeout?: number;
    }) => apiFetch<ExecutionResult>(`${BASE(projectId)}/execute/single`, {
      method: "POST",
      json: body,
    }),
  });
}

export function useExecuteTestCases(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { test_case_ids: string[]; environment_id?: string }) =>
      apiFetch<{
        run_id: string;
        total: number;
        passed: number;
        failed: number;
        errors: number;
        duration_ms: number;
        results: ExecutionResult[];
      }>(`${BASE(projectId)}/execute/test-cases`, { method: "POST", json: body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.testCases(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

export function useCreateEnvironment(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; variables: Record<string, string>; is_default?: boolean }) =>
      apiFetch<ApiEnvironment>(`${BASE(projectId)}/environments`, { method: "POST", json: body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: apiTestingKeys.environments(projectId) }),
  });
}

export function useUpdateEnvironment(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ envId, ...body }: {
      envId: string;
      name?: string;
      description?: string;
      variables?: Record<string, string>;
      sensitive_keys?: string[];
      is_default?: boolean;
    }) =>
      apiFetch<ApiEnvironment>(`${BASE(projectId)}/environments/${envId}`, { method: "PUT", json: body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.environments(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

export function useDeleteEnvironment(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (envId: string) =>
      apiFetch<void>(`${BASE(projectId)}/environments/${envId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.environments(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

// ── Chain Types ─────────────────────────────────────────────────────
export interface ApiChain {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  global_variables: Record<string, string>;
  ai_generated: boolean;
  stop_on_failure: boolean;
  created_at?: string;
}

interface ChainCreatePayload {
  name: string;
  description?: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  global_variables?: Record<string, string>;
  stop_on_failure?: boolean;
  max_retries?: number;
  delay_between_ms?: number;
}

// ── Chain Hooks ─────────────────────────────────────────────────────

export function useChains(projectId: string | undefined) {
  return useQuery({
    queryKey: apiTestingKeys.chains(projectId!),
    queryFn: () => apiFetch<ApiChain[]>(`${BASE(projectId!)}/chains`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useCreateChain(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ChainCreatePayload) =>
      apiFetch<ApiChain>(`${BASE(projectId)}/chains`, { method: "POST", json: body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.chains(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

export function useDeleteChain(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (chainId: string) =>
      apiFetch<void>(`${BASE(projectId)}/chains/${chainId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: apiTestingKeys.chains(projectId) });
      qc.invalidateQueries({ queryKey: apiTestingKeys.stats(projectId) });
    },
  });
}

// ── Execution History & Trends Hooks ────────────────────────────────

export interface ExecutionHistoryFilters {
  page?: number;
  per_page?: number;
  test_type?: string;
  status?: string;
}

export function useExecutionHistory(
  projectId: string | undefined,
  filters?: ExecutionHistoryFilters,
) {
  return useQuery({
    queryKey: apiTestingKeys.executionHistory(projectId!, filters as Record<string, unknown>),
    queryFn: () => {
      const qs = new URLSearchParams();
      if (filters?.page) qs.set("page", String(filters.page));
      if (filters?.per_page) qs.set("per_page", String(filters.per_page));
      if (filters?.test_type) qs.set("test_type", filters.test_type);
      if (filters?.status) qs.set("status", filters.status);
      const query = qs.toString();
      return apiFetch<ExecutionHistoryResponse>(
        `${BASE(projectId!)}/executions${query ? `?${query}` : ""}`,
      );
    },
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

export function useExecutionDetail(
  projectId: string | undefined,
  runId: string | undefined,
) {
  return useQuery({
    queryKey: apiTestingKeys.executionDetail(projectId!, runId!),
    queryFn: () =>
      apiFetch<ExecutionRunDetailResponse>(
        `${BASE(projectId!)}/executions/${runId!}`,
      ),
    enabled: !!projectId && !!runId,
    staleTime: 60_000,
  });
}

export function useTestTrends(
  projectId: string | undefined,
  days?: number,
) {
  return useQuery({
    queryKey: apiTestingKeys.trends(projectId!, days),
    queryFn: () => {
      const qs = days ? `?days=${days}` : "";
      return apiFetch<TrendResponse>(`${BASE(projectId!)}/trends${qs}`);
    },
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FLAKY TEST DETECTION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface FlakyTest {
  test_case_id: string;
  title: string;
  test_type: string;
  flaky_score: number;
  run_count: number;
  pass_rate: number;
  fail_rate: number;
  alternation_count: number;
  last_status: string;
  avg_duration_ms: number;
  recommendation: "quarantine" | "investigate" | "stable";
}

export interface FlakyTrend {
  date: string;
  total_tests: number;
  flaky_count: number;
  quarantined_count: number;
}

export interface QuarantinedTest {
  id: string;
  title: string;
  test_type: string;
  quarantined: boolean;
  quarantine_reason?: string;
  flaky_score?: number;
  run_count: number;
  pass_rate: number;
}

export function useFlakyTests(projectId: string | undefined, windowDays = 30) {
  return useQuery({
    queryKey: ["api-testing", projectId, "flaky", windowDays],
    queryFn: () =>
      apiFetch<FlakyTest[]>(
        `${BASE(projectId!)}/flaky?window_days=${windowDays}`,
      ),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useFlakyTrends(projectId: string | undefined, days = 30) {
  return useQuery({
    queryKey: ["api-testing", projectId, "flaky-trends", days],
    queryFn: () =>
      apiFetch<FlakyTrend[]>(
        `${BASE(projectId!)}/flaky/trends?days=${days}`,
      ),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useQuarantineList(projectId: string | undefined) {
  return useQuery({
    queryKey: ["api-testing", projectId, "quarantine"],
    queryFn: () =>
      apiFetch<QuarantinedTest[]>(
        `${BASE(projectId!)}/quarantine`,
      ),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useQuarantineTest(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { testCaseId: string; reason: string }) =>
      apiFetch<void>(
        `${BASE(projectId)}/flaky/${args.testCaseId}/quarantine`,
        { method: "POST", json: { reason: args.reason } },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-testing", projectId, "flaky"] });
      qc.invalidateQueries({ queryKey: ["api-testing", projectId, "quarantine"] });
    },
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// COVERAGE GAP ANALYSIS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface CoverageGap {
  endpoint_id: string;
  method: string;
  path: string;
  risk_level: string;
  has_pii: boolean;
  has_financial: boolean;
  test_count: number;
  test_types_present: string[];
  test_types_missing: string[];
  gap_severity: "critical" | "high" | "medium" | "low";
  recommendation: string;
}

export interface CoverageSummary {
  total_endpoints: number;
  covered_endpoints: number;
  uncovered_endpoints: number;
  coverage_rate: number;
  critical_uncovered: number;
}

export interface CoverageByRisk {
  total: number;
  covered: number;
  rate: number;
}

export interface CoverageAnalysis {
  summary: CoverageSummary;
  gaps: CoverageGap[];
  by_risk_level: Record<string, CoverageByRisk>;
  by_test_type: Record<string, { count: number; endpoints_covered: number }>;
}

export interface CoverageGapSuggestion {
  endpoint: string;
  gap_severity: string;
  missing_types: string[];
  suggestion: string;
}

export function useCoverageAnalysis(projectId: string | undefined, specId?: string) {
  return useQuery({
    queryKey: ["api-testing", projectId, "coverage-analysis", specId],
    queryFn: () => {
      const qs = specId ? `?spec_id=${specId}` : "";
      return apiFetch<CoverageAnalysis>(
        `${BASE(projectId!)}/coverage-analysis${qs}`,
      );
    },
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useCoverageGaps(projectId: string | undefined) {
  return useQuery({
    queryKey: ["api-testing", projectId, "coverage-gaps"],
    queryFn: () =>
      apiFetch<CoverageGap[]>(
        `${BASE(projectId!)}/coverage-gaps`,
      ),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useCoverageGapSuggestions(projectId: string) {
  return useMutation({
    mutationFn: (maxGaps?: number) =>
      apiFetch<CoverageGapSuggestion[]>(
        `${BASE(projectId)}/coverage-gaps/suggest`,
        { method: "POST", json: { max_gaps: maxGaps ?? 5 } },
      ),
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TEST PRIORITIZATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface PriorityBreakdown {
  failure: number;
  risk: number;
  recency: number;
  sensitivity: number;
  change_impact: number;
}

export interface PrioritizedTest {
  test_case_id: string;
  title: string;
  test_type: string;
  priority_score: number;
  breakdown: PriorityBreakdown;
  endpoint_method: string;
  endpoint_path: string;
  risk_level: string;
  last_run_status?: string;
  estimated_duration_ms: number;
}

export interface PrioritizationStats {
  total_tests: number;
  quarantined_skipped: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  avg_score: number;
  risk_distribution: Record<string, number>;
  estimated_total_duration_ms: number;
}

export interface OptimalSuiteResult {
  selected_ids: string[];
  total_count: number;
  total_duration_ms: number;
  coverage_summary: string;
}

export function usePrioritizedTests(projectId: string | undefined, maxTests?: number) {
  return useQuery({
    queryKey: ["api-testing", projectId, "prioritize", maxTests],
    queryFn: () => {
      const qs = maxTests ? `?max_tests=${maxTests}` : "";
      return apiFetch<{ items: PrioritizedTest[]; total_count: number }>(
        `${BASE(projectId!)}/prioritize${qs}`,
      );
    },
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function usePrioritizationStats(projectId: string | undefined) {
  return useQuery({
    queryKey: ["api-testing", projectId, "prioritize-stats"],
    queryFn: () =>
      apiFetch<PrioritizationStats>(`${BASE(projectId!)}/prioritize/stats`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useOptimalSuite(projectId: string) {
  return useMutation({
    mutationFn: (args: { time_budget_ms?: number; changed_paths?: string[] }) =>
      apiFetch<OptimalSuiteResult>(
        `${BASE(projectId)}/prioritize/optimal-suite`,
        { method: "POST", json: args },
      ),
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ASSERTION SUGGESTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface AssertionSuggestion {
  type: string;
  field: string;
  operator: string;
  expected: unknown;
  reason: string;
  priority: string;
  category: string;
}

export interface AssertionSuggestionsResponse {
  test_case_id: string;
  current_assertion_count: number;
  suggestions: AssertionSuggestion[];
  coverage_improvement: string;
}

export interface AssertionStats {
  total_tests: number;
  total_assertions: number;
  avg_assertions_per_test: number;
  tests_with_no_assertions: number;
  tests_below_threshold: number;
  assertion_type_distribution: Record<string, number>;
  suggestion_potential: number;
}

export function useAssertionSuggestions(projectId: string) {
  return useMutation({
    mutationFn: (testCaseId: string) =>
      apiFetch<AssertionSuggestionsResponse>(
        `${BASE(projectId)}/assertions/${testCaseId}/suggest`,
      ),
  });
}

export function useBulkAssertionSuggestions(projectId: string) {
  return useMutation({
    mutationFn: (args: { test_case_ids?: string[]; test_type?: string }) =>
      apiFetch<{ total_suggestions: number; results: AssertionSuggestionsResponse[] }>(
        `${BASE(projectId)}/assertions/bulk-suggest`,
        { method: "POST", json: args },
      ),
  });
}

export function useAssertionStats(projectId: string | undefined) {
  return useQuery({
    queryKey: ["api-testing", projectId, "assertion-stats"],
    queryFn: () =>
      apiFetch<AssertionStats>(`${BASE(projectId!)}/assertions/stats`),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SELF-HEALING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export interface HealingDetail {
  test_case_id: string;
  title: string;
  failure_category: string;
  strategy: string;
  retries_attempted: number;
  healed: boolean;
  final_status: string;
  healing_time_ms: number;
}

export interface HealAndRetryResult {
  run_id: string;
  total_failures: number;
  healed: number;
  still_failing: number;
  quarantined: number;
  skipped: number;
  healing_details: HealingDetail[];
  total_healing_time_ms: number;
}

export interface HealingCategoryStats {
  attempts: number;
  healed: number;
  rate: number;
}

export interface HealingStats {
  total_healing_attempts: number;
  success_rate: number;
  by_category: Record<string, HealingCategoryStats>;
  avg_retries_needed: number;
  avg_healing_time_ms: number;
  top_healed_tests: Array<{ test_case_id: string; title: string; heal_count: number }>;
  saved_ci_time_ms: number;
}

export function useHealRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      apiFetch<HealAndRetryResult>(
        `${BASE(projectId)}/healing/${runId}/heal`,
        { method: "POST" },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api-testing", projectId] });
    },
  });
}

export function useHealingStats(projectId: string | undefined, days = 30) {
  return useQuery({
    queryKey: ["api-testing", projectId, "healing-stats", days],
    queryFn: () =>
      apiFetch<HealingStats>(
        `${BASE(projectId!)}/healing/stats?days=${days}`,
      ),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useHealingLog(projectId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: ["api-testing", projectId, "healing-log", runId],
    queryFn: () =>
      apiFetch<HealingDetail[]>(
        `${BASE(projectId!)}/healing/${runId!}/log`,
      ),
    enabled: !!projectId && !!runId,
    staleTime: 60_000,
  });
}
