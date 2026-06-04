"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

export type ManagementStatus = "draft" | "active" | "archived";
export type TestPriority = "P0" | "P1" | "P2" | "P3";
export type TestCaseType = "manual" | "exploratory" | "regression" | "smoke" | "uat";
export type TestRunStatus = "not_run" | "running" | "passed" | "failed" | "blocked" | "skipped";

export interface ManagementProject {
  id: string;
  tenant_id: string;
  tspm_project_id?: string | null;
  key: string;
  name: string;
  description?: string | null;
  status: string;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TestSuite {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  order_index: number;
  status: string;
  created_at: string;
}

export interface TestFolder {
  id: string;
  suite_id: string;
  parent_id?: string | null;
  name: string;
  path: string;
  order_index: number;
  created_at: string;
}

export interface TestCaseStep {
  id: string;
  case_id: string;
  step_no: number;
  action: string;
  expected_result: string;
  test_data: Record<string, unknown>;
  notes?: string | null;
  is_required: boolean;
}

export interface TestCase {
  id: string;
  project_id: string;
  suite_id?: string | null;
  folder_id?: string | null;
  case_key: string;
  title: string;
  objective?: string | null;
  preconditions?: string | null;
  test_data: Record<string, unknown>;
  priority: string;
  severity: string;
  type: string;
  automation_status: string;
  status: string;
  source_type: string;
  source_ref?: string | null;
  tags: string[];
  custom_fields: Record<string, unknown>;
  current_version: number;
  last_run_status?: string | null;
  last_run_at?: string | null;
  owner_id?: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
  steps: TestCaseStep[];
}

export interface TestCaseVersion {
  id: string;
  case_id: string;
  version_no: number;
  snapshot: Record<string, unknown>;
  change_summary?: string | null;
  changed_fields: string[];
  snapshot_size_bytes: number;
  created_by?: string | null;
  created_at: string;
}

export interface Repository {
  suites: TestSuite[];
  folders: TestFolder[];
  cases: TestCase[];
}

export interface ExecutionSummary {
  total: number;
  not_run: number;
  passed: number;
  failed: number;
  blocked: number;
  skipped: number;
  retest: number;
  progress_pct: number;
  pass_rate_pct: number;
}

export interface ReleaseChecklistItem {
  label: string;
  metric: string;
  status: "pass" | "warn" | "fail" | string;
}

export interface ReleaseBlocker {
  label: string;
  value: number;
  detail: string;
}

export interface ReleaseReport {
  project_id: string;
  decision: string;
  generated_at: string;
  progress_pct: number;
  pass_rate_pct: number;
  requirement_coverage_pct: number;
  stale_requirement_count: number;
  uncovered_requirement_count: number;
  open_defect_count: number;
  oldest_open_defect_days: number;
  active_run_count: number;
  blockers: ReleaseBlocker[];
  checklist: ReleaseChecklistItem[];
}

export interface ReleaseSignoff {
  id: string;
  project_id: string;
  release_name?: string | null;
  role?: string | null;
  decision: string;
  status: string;
  comment?: string | null;
  report_snapshot: Record<string, unknown>;
  signed_by?: string | null;
  signed_at: string;
  created_at: string;
}

export interface RequirementLink {
  id: string;
  project_id: string;
  requirement_id?: string | null;
  case_id: string;
  external_source: string;
  external_key: string;
  title_snapshot: string;
  url?: string | null;
  source_updated_at?: string | null;
  coverage_status: string;
}

export interface Requirement {
  id: string;
  project_id: string;
  external_source: string;
  external_key: string;
  title: string;
  description?: string | null;
  priority: string;
  status: string;
  owner_id?: string | null;
  url?: string | null;
  source_updated_at?: string | null;
  version_no: number;
  acceptance_criteria: Record<string, unknown>[];
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface DefectLink {
  id: string;
  run_case_id: string;
  step_result_id?: string | null;
  external_source: string;
  external_key: string;
  title: string;
  status: string;
  severity: string;
  priority: string;
  assignee_id?: string | null;
  root_cause?: string | null;
  retest_status: string;
  url?: string | null;
  resolved_at?: string | null;
  verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDefectInput {
  run_case_id?: string;
  step_result_id?: string | null;
  external_source?: string;
  external_key: string;
  title: string;
  status?: string;
  severity?: string;
  priority?: string;
  assignee_id?: string | null;
  root_cause?: string | null;
  retest_status?: string;
  url?: string | null;
  description?: string;
}

export interface EvidenceFile {
  id: string;
  run_case_id: string;
  step_result_id?: string | null;
  filename: string;
  content_type: string;
  url: string;
  uploaded_at: string;
}

export interface StepResult {
  id: string;
  run_case_id: string;
  step_no: number;
  status: string;
  actual_result?: string | null;
  comment?: string | null;
  executed_at?: string | null;
}

export interface RunCase {
  id: string;
  run_id: string;
  case_id: string;
  case_version_no: number;
  case_snapshot: Record<string, unknown>;
  assigned_to?: string | null;
  status: string;
  actual_result?: string | null;
  execution_notes?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  step_results: StepResult[];
}

export interface TestRun {
  id: string;
  cycle_id: string;
  name: string;
  status: string;
  source_type: string;
  source_ref?: string | null;
  scope_snapshot: Record<string, unknown>;
  environment?: string | null;
  assigned_to?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface TestPlan {
  id: string;
  project_id: string;
  name: string;
  plan_type: string;
  release_name?: string | null;
  status: string;
  scope_summary?: string | null;
  created_by?: string | null;
  created_at: string;
}

export interface TestCycle {
  id: string;
  plan_id: string;
  name: string;
  environment?: string | null;
  build_version?: string | null;
  status: string;
  created_at: string;
}

export interface RegressionSelectionFilter {
  priorities?: string[];
  severities?: string[];
  types?: string[];
  tags?: string[];
  suite_ids?: string[];
  folder_ids?: string[];
  include_last_failed?: boolean;
  include_not_run?: boolean;
  include_without_requirements?: boolean;
  max_cases?: number;
}

export interface RegressionCandidate {
  case_id: string;
  case_key: string;
  title: string;
  priority: string;
  severity: string;
  type: string;
  status: string;
  tags: string[];
  last_run_status?: string | null;
  risk_score: number;
  reasons: string[];
}

export interface RegressionSetCase {
  id: string;
  case_id: string;
  case_version_no: number;
  case_key: string;
  title: string;
  priority: string;
  severity: string;
  type: string;
  last_run_status?: string | null;
  order_index: number;
  risk_score: number;
  reason?: string | null;
  include_mode: string;
}

export interface RegressionSet {
  id: string;
  project_id: string;
  name: string;
  set_type: string;
  description?: string | null;
  source_filters: Record<string, unknown>;
  selection_summary: Record<string, unknown>;
  created_by?: string | null;
  created_at: string;
  cases: RegressionSetCase[];
}

export interface RunDetail extends TestRun {
  run_cases: RunCase[];
}

export interface ImportJobRow {
  id: string;
  job_id: string;
  row_no: number;
  parsed_data: Record<string, unknown>;
  validation_errors: Record<string, unknown>[];
  status: string;
  conflict_key?: string | null;
}

export interface ImportJob {
  id: string;
  project_id: string;
  filename: string;
  status: string;
  mapping: Record<string, unknown>;
  totals: Record<string, unknown>;
  created_by?: string | null;
  created_at: string;
}

export interface ImportJobDetail extends ImportJob {
  rows: ImportJobRow[];
}

export interface ManagementSettings {
  project_id: string;
  permissions: string[];
  workflow_statuses: Record<string, string[]>;
  evidence_retention_days: Record<string, number>;
  aggregation_policy: Record<string, unknown>;
  custom_field_usage: {
    defined_fields: string[];
    case_count: number;
    cases_with_custom_fields: number;
    evidence_count: number;
  };
}

export interface ManagementAuditEvent {
  id: string;
  project_id?: string | null;
  actor_id?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface CreateTestCaseInput {
  suite_id?: string | null;
  folder_id?: string | null;
  case_key?: string | null;
  title: string;
  objective?: string | null;
  preconditions?: string | null;
  test_data?: Record<string, unknown>;
  priority?: string;
  severity?: string;
  type?: string;
  automation_status?: string;
  status?: string;
  source_type?: string;
  source_ref?: string | null;
  tags?: string[];
  custom_fields?: Record<string, unknown>;
  owner_id?: string | null;
  steps?: Array<{
    step_no: number;
    action: string;
    expected_result: string;
    test_data?: Record<string, unknown>;
    notes?: string | null;
    is_required?: boolean;
  }>;
}

export interface UpdateStepResultInput {
  status: TestRunStatus;
  actual_result?: string | null;
  comment?: string | null;
}

export interface UpdateDefectInput {
  defectId: string;
  status?: string;
  title?: string;
  severity?: string;
  priority?: string;
  assignee_id?: string | null;
  root_cause?: string | null;
  retest_status?: string;
  url?: string | null;
}

export interface CreateRunInput {
  cycle_id: string;
  name: string;
  case_ids: string[];
  assigned_to?: string | null;
  source_type?: string;
  source_ref?: string | null;
  scope_snapshot?: Record<string, unknown>;
  environment?: string | null;
}

export interface CreateRegressionSetInput {
  name: string;
  set_type?: string;
  description?: string | null;
  filters?: RegressionSelectionFilter;
  cases?: Array<{
    case_id: string;
    order_index?: number;
    risk_score?: number;
    reason?: string;
    include_mode?: string;
  }>;
}

const BASE = (projectId: string) => `/api/v1/test-management/projects/${projectId}`;

export const managementKeys = {
  all: ["management"] as const,
  projects: () => [...managementKeys.all, "projects"] as const,
  project: (projectId: string | undefined) => [...managementKeys.projects(), projectId] as const,
  repository: (projectId: string | undefined) => [...managementKeys.project(projectId), "repository"] as const,
  cases: (projectId: string | undefined) => [...managementKeys.project(projectId), "cases"] as const,
  case: (projectId: string | undefined, caseId: string | undefined) => [...managementKeys.cases(projectId), caseId] as const,
  caseVersions: (projectId: string | undefined, caseId: string | undefined) =>
    [...managementKeys.case(projectId, caseId), "versions"] as const,
  plans: (projectId: string | undefined) => [...managementKeys.project(projectId), "plans"] as const,
  cycles: (projectId: string | undefined) => [...managementKeys.project(projectId), "cycles"] as const,
  regression: (projectId: string | undefined) => [...managementKeys.project(projectId), "regression"] as const,
  regressionSets: (projectId: string | undefined) => [...managementKeys.regression(projectId), "sets"] as const,
  runs: (projectId: string | undefined) => [...managementKeys.project(projectId), "runs"] as const,
  evidence: (projectId: string | undefined, runId: string | undefined, runCaseId: string | undefined) =>
    [...managementKeys.runs(projectId), runId, "cases", runCaseId, "evidence"] as const,
  summary: (projectId: string | undefined) => [...managementKeys.project(projectId), "summary"] as const,
  releaseReport: (projectId: string | undefined) => [...managementKeys.project(projectId), "release-report"] as const,
  releaseSignoffs: (projectId: string | undefined) => [...managementKeys.releaseReport(projectId), "signoffs"] as const,
  requirements: (projectId: string | undefined) => [...managementKeys.project(projectId), "requirements"] as const,
  requirementCatalog: (projectId: string | undefined) => [...managementKeys.requirements(projectId), "catalog"] as const,
  defects: (projectId: string | undefined) => [...managementKeys.project(projectId), "defects"] as const,
  imports: (projectId: string | undefined) => [...managementKeys.project(projectId), "imports"] as const,
  settings: (projectId: string | undefined) => [...managementKeys.project(projectId), "settings"] as const,
  audit: (projectId: string | undefined) => [...managementKeys.project(projectId), "audit"] as const,
};

export function useManagementProjects() {
  return useQuery({
    queryKey: managementKeys.projects(),
    queryFn: () => apiFetch<ManagementProject[]>("/api/v1/test-management/projects"),
  });
}

export function useEnsureManagementProject(projectId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<ManagementProject>(`/api/v1/test-management/projects/by-tspm/${projectId!}/ensure`, {
        method: "POST",
      }),
    onSuccess: (project) => {
      void qc.invalidateQueries({ queryKey: managementKeys.projects() });
      void qc.invalidateQueries({ queryKey: managementKeys.project(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.project(project.id) });
    },
  });
}

export function useManagementRepository(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.repository(projectId),
    queryFn: () => apiFetch<Repository>(`${BASE(projectId!)}/repository`),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useCreateManagementSuite(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string; order_index?: number }) =>
      apiFetch<TestSuite>(`${BASE(projectId)}/suites`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

export function useCreateManagementFolder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      suite_id: string;
      parent_id?: string | null;
      name: string;
      path: string;
      order_index?: number;
    }) => apiFetch<TestFolder>(`${BASE(projectId)}/folders`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

export function useUpdateManagementSuite(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ suiteId, ...payload }: {
      suiteId: string;
      name?: string;
      description?: string;
      order_index?: number;
      status?: string;
    }) => apiFetch<TestSuite>(`${BASE(projectId)}/suites/${suiteId}`, { method: "PATCH", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

export function useDeleteManagementSuite(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (suiteId: string) =>
      apiFetch<void>(`${BASE(projectId)}/suites/${suiteId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

export function useUpdateManagementFolder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ folderId, ...payload }: {
      folderId: string;
      name?: string;
      path?: string;
      suite_id?: string | null;
      parent_id?: string | null;
      order_index?: number;
    }) => apiFetch<TestFolder>(`${BASE(projectId)}/folders/${folderId}`, { method: "PATCH", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

export function useDeleteManagementFolder(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (folderId: string) =>
      apiFetch<void>(`${BASE(projectId)}/folders/${folderId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

export function useManagementSettings(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.settings(projectId),
    queryFn: () => apiFetch<ManagementSettings>(`${BASE(projectId!)}/settings`),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useManagementAuditEvents(projectId: string | undefined, limit = 50) {
  return useQuery({
    queryKey: [...managementKeys.audit(projectId), limit] as const,
    queryFn: () => apiFetch<ManagementAuditEvent[]>(`${BASE(projectId!)}/audit-events?limit=${limit}`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementCases(projectId: string | undefined, includeArchived = false) {
  return useQuery({
    queryKey: [...managementKeys.cases(projectId), includeArchived] as const,
    queryFn: () =>
      apiFetch<TestCase[]>(
        `${BASE(projectId!)}/cases${includeArchived ? "?include_archived=true" : ""}`,
      ),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementCase(projectId: string | undefined, caseId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.case(projectId, caseId),
    queryFn: () => apiFetch<TestCase>(`${BASE(projectId!)}/cases/${caseId!}`),
    enabled: !!projectId && !!caseId,
    staleTime: 30_000,
  });
}

export function useManagementCaseVersions(projectId: string | undefined, caseId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.caseVersions(projectId, caseId),
    queryFn: () => apiFetch<TestCaseVersion[]>(`${BASE(projectId!)}/cases/${caseId!}/versions`),
    enabled: !!projectId && !!caseId,
    staleTime: 30_000,
  });
}

export function useManagementRun(projectId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: [...managementKeys.runs(projectId), runId, "detail"] as const,
    queryFn: () => apiFetch<RunDetail>(`${BASE(projectId!)}/runs/${runId!}`),
    enabled: !!projectId && !!runId,
    staleTime: 15_000,
  });
}

export function useManagementEvidence(
  projectId: string | undefined,
  runId: string | undefined,
  runCaseId: string | undefined,
) {
  return useQuery({
    queryKey: managementKeys.evidence(projectId, runId, runCaseId),
    queryFn: () =>
      apiFetch<EvidenceFile[]>(
        `${BASE(projectId!)}/runs/${runId!}/cases/${runCaseId!}/evidence`,
      ),
    enabled: !!projectId && !!runId && !!runCaseId,
    staleTime: 15_000,
  });
}

export function useManagementPlans(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.plans(projectId),
    queryFn: () => apiFetch<TestPlan[]>(`${BASE(projectId!)}/plans`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementCycles(projectId: string | undefined, planId?: string) {
  return useQuery({
    queryKey: [...managementKeys.cycles(projectId), planId] as const,
    queryFn: () =>
      apiFetch<TestCycle[]>(`${BASE(projectId!)}/cycles${planId ? `?plan_id=${encodeURIComponent(planId)}` : ""}`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementRuns(projectId: string | undefined, statusFilter?: string) {
  return useQuery({
    queryKey: [...managementKeys.runs(projectId), statusFilter] as const,
    queryFn: () =>
      apiFetch<TestRun[]>(
        `${BASE(projectId!)}/runs${statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ""}`,
      ),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useRegressionSets(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.regressionSets(projectId),
    queryFn: () => apiFetch<RegressionSet[]>(`${BASE(projectId!)}/regression/sets`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useSuggestRegressionCandidates(projectId: string) {
  return useMutation({
    mutationFn: (payload: RegressionSelectionFilter) =>
      apiFetch<RegressionCandidate[]>(`${BASE(projectId)}/regression/suggest`, {
        method: "POST",
        json: payload,
      }),
  });
}

export function useCreateRegressionSet(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateRegressionSetInput) =>
      apiFetch<RegressionSet>(`${BASE(projectId)}/regression/sets`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.regressionSets(projectId) });
    },
  });
}

export function useUpdateRegressionSet(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: string; name?: string; set_type?: string; description?: string }) =>
      apiFetch<RegressionSet>(`${BASE(projectId)}/regression/sets/${id}`, { method: "PATCH", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.regressionSets(projectId) });
    },
  });
}

export function useDeleteRegressionSet(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id }: { id: string }) =>
      apiFetch<void>(`${BASE(projectId)}/regression/sets/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.regressionSets(projectId) });
    },
  });
}

export function useAddCasesToRegressionSet(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ setId, caseIds }: { setId: string; caseIds: string[] }) =>
      apiFetch<RegressionSet>(`${BASE(projectId)}/regression/sets/${setId}/cases`, {
        method: "POST",
        json: { case_ids: caseIds },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.regressionSets(projectId) });
    },
  });
}

export function useRemoveCaseFromRegressionSet(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ setId, caseId }: { setId: string; caseId: string }) =>
      apiFetch<RegressionSet>(`${BASE(projectId)}/regression/sets/${setId}/cases/${caseId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.regressionSets(projectId) });
    },
  });
}

export function useCreateManagementPlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      name: string;
      plan_type?: string;
      release_name?: string | null;
      scope_summary?: string | null;
    }) => apiFetch<TestPlan>(`${BASE(projectId)}/plans`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.plans(projectId) });
    },
  });
}

export function useCreateManagementCycle(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      plan_id: string;
      name: string;
      environment?: string | null;
      build_version?: string | null;
    }) => apiFetch<TestCycle>(`${BASE(projectId)}/cycles`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.cycles(projectId) });
    },
  });
}

export function useCreateManagementRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateRunInput) =>
      apiFetch<TestRun>(`${BASE(projectId)}/runs`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.runs(projectId) });
    },
  });
}

export function useArchiveManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (caseId: string) =>
      apiFetch<TestCase>(`${BASE(projectId)}/cases/${caseId}/archive`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

/** TestRail-style: update the overall status of a test case in a run with one click. */
export function useUpdateManagementRunCase(projectId: string, runId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ runCaseId, status, actual_result, execution_notes }: {
      runCaseId: string;
      status: string;
      actual_result?: string | null;
      execution_notes?: string | null;
    }) =>
      apiFetch<RunCase>(`${BASE(projectId)}/run-cases/${runCaseId}`, {
        method: "PATCH",
        json: { status, actual_result, execution_notes },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.summary(projectId) });
      if (runId) {
        void qc.invalidateQueries({ queryKey: [...managementKeys.runs(projectId), runId, "detail"] as const });
        void qc.invalidateQueries({ queryKey: managementKeys.runs(projectId) });
      }
    },
  });
}

export function useUpdateManagementStepResult(projectId: string, runCaseId: string, runId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stepNo, ...payload }: UpdateStepResultInput & { stepNo: number }) =>
      apiFetch(`${BASE(projectId)}/run-cases/${runCaseId}/steps/${stepNo}`, {
        method: "PATCH",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.summary(projectId) });
      if (runId) {
        void qc.invalidateQueries({ queryKey: [...managementKeys.runs(projectId), runId, "detail"] as const });
        void qc.invalidateQueries({ queryKey: managementKeys.runs(projectId) });
      }
    },
  });
}

export function useCreateManagementRequirement(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<RequirementLink, "id" | "project_id">) =>
      apiFetch<RequirementLink>(`${BASE(projectId)}/requirements`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.requirements(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.requirementCatalog(projectId) });
    },
  });
}

export function useCreateRequirementCatalogItem(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      external_source?: string;
      external_key: string;
      title: string;
      description?: string | null;
      priority?: string;
      status?: string;
      owner_id?: string | null;
      url?: string | null;
      source_updated_at?: string | null;
      version_no?: number;
      acceptance_criteria?: Record<string, unknown>[];
      tags?: string[];
    }) =>
      apiFetch<Requirement>(`${BASE(projectId)}/requirements/catalog`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.requirementCatalog(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.requirements(projectId) });
    },
  });
}

export function useCreateManagementDefect(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDefectInput) =>
      apiFetch<DefectLink>(`${BASE(projectId)}/defects`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.defects(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.summary(projectId) });
    },
  });
}

export function useUpdateManagementDefect(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ defectId, ...payload }: UpdateDefectInput) =>
      apiFetch<DefectLink>(`${BASE(projectId)}/defects/${defectId}`, {
        method: "PATCH",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.defects(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.summary(projectId) });
    },
  });
}

export function useManagementImports(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.imports(projectId),
    queryFn: () => apiFetch<ImportJob[]>(`${BASE(projectId!)}/imports`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementImportDetail(projectId: string | undefined, jobId: string | undefined) {
  return useQuery({
    queryKey: [...managementKeys.imports(projectId), jobId] as const,
    queryFn: () => apiFetch<ImportJobDetail>(`${BASE(projectId!)}/imports/${jobId!}`),
    enabled: !!projectId && !!jobId,
    staleTime: 15_000,
  });
}

export function useCreateManagementImportJob(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { filename: string; mapping?: Record<string, unknown>; rows?: Record<string, unknown>[] }) =>
      apiFetch<ImportJob>(`${BASE(projectId)}/imports`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.imports(projectId) });
    },
  });
}

export function useCommitImportJob(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      apiFetch<ImportJob>(`${BASE(projectId)}/imports/${jobId}/commit`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.imports(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

// ── Semantic search ───────────────────────────────────────────────────────────

export interface SimilarCaseResult {
  case_id: string;
  case_key: string;
  title: string;
  score: number;
  project_id: string;
  tags: string[];
  last_run_status?: string | null;
}

export interface SimilarCaseQuery {
  query: string;
  k?: number;
  min_score?: number;
  exclude_case_id?: string | null;
}

export function useSearchSimilarCases(projectId: string) {
  return useMutation({
    mutationFn: (payload: SimilarCaseQuery) =>
      apiFetch<SimilarCaseResult[]>(`${BASE(projectId)}/cases/search-similar`, {
        method: "POST",
        json: payload,
      }),
  });
}

// ── Defect delete ─────────────────────────────────────────────────────────────

export function useDeleteManagementDefect(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (defectId: string) =>
      apiFetch<void>(`${BASE(projectId)}/defects/${defectId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.defects(projectId) });
    },
  });
}

// ── Defects list ──────────────────────────────────────────────────────────────

export function useManagementDefects(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.defects(projectId),
    queryFn: () => apiFetch<DefectLink[]>(`${BASE(projectId!)}/defects`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

// ── Execution summary ─────────────────────────────────────────────────────────

export function useExecutionSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.summary(projectId),
    queryFn: () => apiFetch<ExecutionSummary>(`${BASE(projectId!)}/reports/execution-summary`),
    enabled: !!projectId,
    staleTime: 15_000,
  });
}

// ── Release report & signoffs ─────────────────────────────────────────────────

export function useReleaseReport(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.releaseReport(projectId),
    queryFn: () => apiFetch<ReleaseReport>(`${BASE(projectId!)}/reports/release`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useReleaseSignoffs(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.releaseSignoffs(projectId),
    queryFn: () => apiFetch<ReleaseSignoff[]>(`${BASE(projectId!)}/reports/release/signoffs`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useCreateReleaseSignoff(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      release_name?: string | null;
      role?: string | null;
      decision: string;
      comment?: string | null;
      report_snapshot?: Record<string, unknown>;
    }) =>
      apiFetch<ReleaseSignoff>(`${BASE(projectId)}/reports/release/signoffs`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.releaseSignoffs(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.releaseReport(projectId) });
    },
  });
}

// ── Requirements ──────────────────────────────────────────────────────────────

export function useManagementRequirements(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.requirements(projectId),
    queryFn: () => apiFetch<RequirementLink[]>(`${BASE(projectId!)}/requirements`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export interface RequirementTraceabilityRow {
  requirement_id: string;
  requirement_key: string;
  external_key: string;
  title: string;
  status: string;
  priority: string;
  source: string;
  covered: boolean;
  stale: boolean;
  coverage_pct: number;
  cases: Array<{
    case_id: string;
    case_key: string;
    title: string;
    last_run_status?: string | null;
    coverage_status: string;
  }>;
}

/** @deprecated Use RequirementTraceabilityRow */
export type TraceabilityRow = RequirementTraceabilityRow;

export function useRequirementCatalog(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.requirementCatalog(projectId),
    queryFn: () => apiFetch<Requirement[]>(`${BASE(projectId!)}/requirements/catalog`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useRequirementTraceability(projectId: string | undefined) {
  return useQuery({
    queryKey: [...managementKeys.requirements(projectId), "traceability"] as const,
    queryFn: () => apiFetch<RequirementTraceabilityRow[]>(`${BASE(projectId!)}/requirements/traceability`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

// ── Test case CRUD ────────────────────────────────────────────────────────────

export function useCreateManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateTestCaseInput) =>
      apiFetch<TestCase>(`${BASE(projectId)}/cases`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

export function useUpdateManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, ...payload }: Partial<CreateTestCaseInput> & { caseId: string }) =>
      apiFetch<TestCase>(`${BASE(projectId)}/cases/${caseId}`, { method: "PATCH", json: payload }),
    onSuccess: (_data, variables) => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.case(projectId, variables.caseId) });
    },
  });
}

export function useMoveManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { caseId: string; suite_id?: string | null; folder_id?: string | null }) =>
      apiFetch<TestCase>(`${BASE(projectId)}/cases/${payload.caseId}/move`, {
        method: "PATCH",
        json: { suite_id: payload.suite_id, folder_id: payload.folder_id },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

export async function exportManagementRepository(projectId: string): Promise<Repository> {
  return apiFetch<Repository>(`${BASE(projectId)}/repository/export`);
}

export function usePromoteCases(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { case_ids: string[]; target_status: string }) =>
      apiFetch<{ updated: number }>(`${BASE(projectId)}/cases/promote`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

// ── Kiwi TCMS integration ──────────────────────────────────────────────
const KIWI_BASE = (projectId: string) => `/api/v1/kiwi-tcms/projects/${projectId}`;

export const kiwiKeys = {
  connection: (projectId: string | undefined) =>
    [...managementKeys.project(projectId), "kiwi", "connection"] as const,
  preview: (projectId: string | undefined) =>
    [...managementKeys.project(projectId), "kiwi", "preview"] as const,
  syncJobs: (projectId: string | undefined) =>
    [...managementKeys.project(projectId), "kiwi", "sync-jobs"] as const,
};

export interface KiwiConnection {
  id: string;
  project_id: string;
  base_url: string;
  username: string;
  has_secret: boolean;
  kiwi_product_id?: number | null;
  verify_ssl: boolean;
  status: string;
  last_error?: string | null;
  last_tested_at?: string | null;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KiwiConnectionInput {
  base_url: string;
  username: string;
  secret?: string;
  kiwi_product_id?: number | null;
  verify_ssl: boolean;
}

export interface KiwiProduct {
  id: number;
  name: string;
}

export interface KiwiTestConnectionResult {
  ok: boolean;
  product_count: number;
  error?: string | null;
  products: KiwiProduct[];
}

export interface KiwiPreview {
  ok: boolean;
  error?: string | null;
  counts: Record<string, number>;
}

export interface KiwiSyncJob {
  id: string;
  connection_id: string;
  project_id: string;
  mode: string;
  status: "queued" | "running" | "succeeded" | "failed";
  dry_run: boolean;
  totals: Record<string, { created: number; updated: number; skipped: number; errors: number }>;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export function useKiwiConnection(projectId: string | undefined) {
  return useQuery({
    queryKey: kiwiKeys.connection(projectId),
    queryFn: () => apiFetch<KiwiConnection | null>(`${KIWI_BASE(projectId!)}/connection`),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

export function useSaveKiwiConnection(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: KiwiConnectionInput) =>
      apiFetch<KiwiConnection>(`${KIWI_BASE(projectId)}/connection`, { method: "PUT", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: kiwiKeys.connection(projectId) });
    },
  });
}

export function useTestKiwiConnection(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<KiwiTestConnectionResult>(`${KIWI_BASE(projectId)}/connection/test`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: kiwiKeys.connection(projectId) });
    },
  });
}

export function useKiwiPreview(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<KiwiPreview>(`${KIWI_BASE(projectId)}/preview`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: kiwiKeys.preview(projectId) });
    },
  });
}

export function useStartKiwiSync(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { dry_run: boolean }) =>
      apiFetch<KiwiSyncJob>(`${KIWI_BASE(projectId)}/sync`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: kiwiKeys.syncJobs(projectId) });
    },
  });
}

export function useKiwiSyncJobs(projectId: string | undefined) {
  return useQuery({
    queryKey: kiwiKeys.syncJobs(projectId),
    queryFn: () => apiFetch<KiwiSyncJob[]>(`${KIWI_BASE(projectId!)}/sync-jobs`),
    enabled: !!projectId,
    refetchInterval: 5_000,
  });
}

// ── Complete Run ──────────────────────────────────────────────────────────────

export function useCompleteRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      apiFetch<TestRun>(`${BASE(projectId)}/runs/${runId}/complete`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.runs(projectId) });
    },
  });
}

// ── Run Progress ─────────────────────────────────────────────────────────────

export interface RunProgressData {
  run_id: string;
  total: number;
  done: number;
  passed: number;
  failed: number;
  blocked: number;
  not_run: number;
  progress_pct: number;
  pass_rate_pct: number;
}

export function useRunProgress(projectId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: [...(projectId ? managementKeys.project(projectId) : []), "runs", runId, "progress"],
    queryFn: () => apiFetch<RunProgressData>(`${BASE(projectId!)}/runs/${runId}/progress`),
    enabled: !!projectId && !!runId,
    refetchInterval: 10_000,
    staleTime: 5_000,
  });
}

// ── Bulk Create Requirements ──────────────────────────────────────────────────

export function useBulkCreateRequirements(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: Array<{
      external_source?: string;
      external_key: string;
      title: string;
      description?: string;
      priority?: string;
      status?: string;
      tags?: string[];
    }>) =>
      apiFetch<{ created: number; total: number }>(`${BASE(projectId)}/requirements/bulk`, {
        method: "POST",
        json: items,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.requirementCatalog(projectId) });
    },
  });
}

// ── Delete Plan ───────────────────────────────────────────────────────────────

export function useDeleteManagementPlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (planId: string) =>
      apiFetch<void>(`${BASE(projectId)}/plans/${planId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.plans(projectId) });
    },
  });
}

// ── Quality Scan ──────────────────────────────────────────────────────────────

export interface QualityScanResult {
  case_id: string;
  case_key: string;
  title: string;
  issues: string[];
  score: number;
  recommendation: string;
}

export interface QualityScanResponse {
  total: number;
  scanned: number;
  issues_found: number;
  results: QualityScanResult[];
}

export function useQualityScan(projectId: string | undefined) {
  return useQuery({
    queryKey: [...(projectId ? managementKeys.project(projectId) : []), "quality-scan"],
    queryFn: () => apiFetch<QualityScanResponse>(`${BASE(projectId!)}/cases/quality-scan?limit=100`),
    enabled: !!projectId,
    staleTime: 120_000,
  });
}

// ── Bulk Update Cases ─────────────────────────────────────────────────────────

export interface BulkUpdateCasesInput {
  case_ids: string[];
  priority?: string;
  type?: string;
  status?: string;
  suite_id?: string | null;
  folder_id?: string | null;
  tags_add?: string[];
  tags_remove?: string[];
}

export function useBulkUpdateCases(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: BulkUpdateCasesInput) =>
      apiFetch<{ updated: number; failed: number }>(`${BASE(projectId)}/cases/bulk-update`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

// ── AI Defect Root Cause ─────────────────────────────────────────────────────

export interface DefectRootCauseResponse {
  root_cause: string;
  suggestions: string[];
  category?: string | null;
}

export function useAnalyzeDefectRootCause(projectId: string) {
  return useMutation({
    mutationFn: (payload: { defect_title: string; defect_status?: string; test_context?: string }) =>
      apiFetch<DefectRootCauseResponse>(`${BASE(projectId)}/defects/analyze-root-cause`, {
        method: "POST",
        json: payload,
      }),
  });
}

// ── AI Plan Generate ─────────────────────────────────────────────────────────

export interface AIPlanGenerateResponse {
  name: string;
  scope_summary: string;
  suggested_suite_ids: string[];
  suggestions: string[];
}

export function useAIGeneratePlan(projectId: string) {
  return useMutation({
    mutationFn: (payload: { release_name: string; goal?: string; plan_type?: string }) =>
      apiFetch<AIPlanGenerateResponse>(`${BASE(projectId)}/plans/ai-generate`, {
        method: "POST",
        json: payload,
      }),
  });
}

// ── AI Case Improve ───────────────────────────────────────────────────────────

export interface ImproveTestCaseResponse {
  title?: string | null;
  objective?: string | null;
  preconditions?: string | null;
  steps?: GeneratedStep[] | null;
  suggestions: string[];
}

export function useImproveManagementCase(projectId: string) {
  return useMutation({
    mutationFn: ({ caseId, focus = "all" }: { caseId: string; focus?: string }) =>
      apiFetch<ImproveTestCaseResponse>(`${BASE(projectId)}/cases/${caseId}/improve`, {
        method: "POST",
        json: { focus },
      }),
  });
}

// ── AI Test Generation ────────────────────────────────────────────────────────

export interface GeneratedStep {
  step_no: number;
  action: string;
  expected_result: string;
  is_required: boolean;
}

export interface GeneratedCase {
  title: string;
  objective: string;
  preconditions: string;
  priority: string;
  tags: string[];
  steps: GeneratedStep[];
  saved_id: string | null;
}

export interface GenerateTestCasesInput {
  prompt: string;
  count?: number;
  suite_id?: string | null;
  folder_id?: string | null;
  priority?: string;
  type?: string;
  save?: boolean;
}

export function useGenerateTestCases(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateTestCasesInput) =>
      apiFetch<{ cases: GeneratedCase[] }>(`${BASE(projectId)}/cases/generate`, {
        method: "POST",
        json: { count: 5, priority: "P1", type: "manual", save: false, ...payload },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
    },
  });
}

// ── Case Clone ────────────────────────────────────────────────────────────────

export function useCloneManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, ...payload }: { caseId: string; title?: string; suite_id?: string | null; folder_id?: string | null }) =>
      apiFetch<TestCase>(`${BASE(projectId)}/cases/${caseId}/clone`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

// ── Standup ───────────────────────────────────────────────────────────────────

export interface StandupAnomaly {
  severity: string;
  title: string;
}

export interface StandupData {
  health_score: number;
  summary_health: "healthy" | "at_risk" | "critical";
  eta_hours: number | null;
  remaining_cases: number;
  total_cases: number;
  completed_cases: number;
  pass_rate: number;
  blocked: number;
  failed: number;
  velocity_per_hour: number;
  anomalies: StandupAnomaly[];
  run_name: string;
  predicted_completion: string | null;
  will_meet_gate: boolean;
  blocking_factors: string[];
}

export function useManagementStandup(projectId: string | undefined, runId?: string) {
  return useQuery({
    queryKey: [...(projectId ? managementKeys.project(projectId) : []), "standup", runId ?? "latest"],
    queryFn: () => {
      const url = runId
        ? `${BASE(projectId!)}/standup?run_id=${runId}`
        : `${BASE(projectId!)}/standup`;
      return apiFetch<StandupData>(url);
    },
    enabled: !!projectId,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

// ── Delete Case (hard delete) ─────────────────────────────────────────────────

export function useDeleteManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (caseId: string) =>
      apiFetch<void>(`${BASE(projectId)}/cases/${caseId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

// ── Unarchive Case ────────────────────────────────────────────────────────────

export function useUnarchiveManagementCase(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (caseId: string) =>
      apiFetch<TestCase>(`${BASE(projectId)}/cases/${caseId}/unarchive`, { method: "POST", json: {} }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.repository(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.cases(projectId) });
    },
  });
}

// ── Plan / Cycle / Run CRUD ──────────────────────────────────────────────────

export interface TestPlanUpdate { name?: string; plan_type?: string; release_name?: string | null; status?: string; scope_summary?: string | null; }
export interface TestCycleUpdate { name?: string; environment?: string | null; build_version?: string | null; status?: string; }
export interface TestRunUpdate { name?: string; environment?: string | null; status?: string; }
export interface RequirementUpdate { title?: string; priority?: string; status?: string; description?: string | null; coverage_status?: string; }

export function useUpdateManagementPlan(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: TestPlanUpdate & { id: string }) =>
      apiFetch<TestPlan>(`${BASE(projectId)}/plans/${id}`, { method: "PATCH", json: payload }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: managementKeys.plans(projectId) }); },
  });
}

export function useUpdateManagementCycle(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: TestCycleUpdate & { id: string }) =>
      apiFetch<TestCycle>(`${BASE(projectId)}/cycles/${id}`, { method: "PATCH", json: payload }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: managementKeys.cycles(projectId) }); },
  });
}

export function useDeleteManagementCycle(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`${BASE(projectId)}/cycles/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.cycles(projectId) });
      void qc.invalidateQueries({ queryKey: managementKeys.plans(projectId) });
    },
  });
}

export function useUpdateManagementRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: TestRunUpdate & { id: string }) =>
      apiFetch<TestRun>(`${BASE(projectId)}/runs/${id}`, { method: "PATCH", json: payload }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: managementKeys.runs(projectId) }); },
  });
}

export function useDeleteManagementRun(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`${BASE(projectId)}/runs/${id}`, { method: "DELETE" }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: managementKeys.runs(projectId) }); },
  });
}

export function useUpdateManagementRequirement(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: RequirementUpdate & { id: string }) =>
      apiFetch<Requirement>(`${BASE(projectId)}/requirements/${id}`, { method: "PATCH", json: payload }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: managementKeys.requirements(projectId) }); },
  });
}

export function useDeleteManagementRequirement(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reqId: string) => apiFetch<void>(`${BASE(projectId)}/requirements/${reqId}`, { method: "DELETE" }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: managementKeys.requirements(projectId) }); },
  });
}

// ── Run Trend ─────────────────────────────────────────────────────────────────

export interface RunTrendPoint { run_id: string; name: string; created_at: string; pass_rate_pct: number; total_cases: number; passed: number; failed: number; }

export function useManagementRunTrend(projectId: string | undefined) {
  return useQuery({
    queryKey: [...managementKeys.project(projectId), "run-trend"],
    queryFn: () => apiFetch<RunTrendPoint[]>(`${BASE(projectId!)}/reports/run-trend`),
    enabled: !!projectId,
    staleTime: 60_000,
  });
}

// ── Aliases ───────────────────────────────────────────────────────────────────
export const useDeleteRequirementCatalogItem = useDeleteManagementRequirement;
