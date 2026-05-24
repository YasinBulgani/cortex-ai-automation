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

export interface RequirementLink {
  id: string;
  project_id: string;
  case_id: string;
  external_source: string;
  external_key: string;
  title_snapshot: string;
  url?: string | null;
  source_updated_at?: string | null;
  coverage_status: string;
}

export interface DefectLink {
  id: string;
  run_case_id: string;
  step_result_id?: string | null;
  external_source: string;
  external_key: string;
  title: string;
  status: string;
  url?: string | null;
  created_at: string;
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
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
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

const BASE = (projectId: string) => `/api/v1/test-management/projects/${projectId}`;

export const managementKeys = {
  all: ["management"] as const,
  projects: () => [...managementKeys.all, "projects"] as const,
  project: (projectId: string | undefined) => [...managementKeys.projects(), projectId] as const,
  repository: (projectId: string | undefined) => [...managementKeys.project(projectId), "repository"] as const,
  cases: (projectId: string | undefined) => [...managementKeys.project(projectId), "cases"] as const,
  runs: (projectId: string | undefined) => [...managementKeys.project(projectId), "runs"] as const,
  summary: (projectId: string | undefined) => [...managementKeys.project(projectId), "summary"] as const,
  requirements: (projectId: string | undefined) => [...managementKeys.project(projectId), "requirements"] as const,
  defects: (projectId: string | undefined) => [...managementKeys.project(projectId), "defects"] as const,
  imports: (projectId: string | undefined) => [...managementKeys.project(projectId), "imports"] as const,
};

export function useManagementProjects() {
  return useQuery({
    queryKey: managementKeys.projects(),
    queryFn: () => apiFetch<ManagementProject[]>("/api/v1/test-management/projects"),
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

export function useManagementRun(projectId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: [...managementKeys.runs(projectId), runId, "detail"] as const,
    queryFn: () => apiFetch<RunDetail>(`${BASE(projectId!)}/runs/${runId!}`),
    enabled: !!projectId && !!runId,
    staleTime: 15_000,
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

export function useExecutionSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.summary(projectId),
    queryFn: () => apiFetch<ExecutionSummary>(`${BASE(projectId!)}/reports/execution-summary`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementRequirements(projectId: string | undefined, caseId?: string) {
  return useQuery({
    queryKey: [...managementKeys.requirements(projectId), caseId] as const,
    queryFn: () =>
      apiFetch<RequirementLink[]>(
        `${BASE(projectId!)}/requirements${caseId ? `?case_id=${encodeURIComponent(caseId)}` : ""}`,
      ),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useManagementDefects(projectId: string | undefined) {
  return useQuery({
    queryKey: managementKeys.defects(projectId),
    queryFn: () => apiFetch<DefectLink[]>(`${BASE(projectId!)}/defects`),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function exportManagementRepository(projectId: string) {
  return apiFetch<Record<string, unknown>>(`${BASE(projectId)}/export`);
}

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

export function useUpdateManagementStepResult(projectId: string, runCaseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ stepNo, ...payload }: UpdateStepResultInput & { stepNo: number }) =>
      apiFetch(`${BASE(projectId)}/run-cases/${runCaseId}/steps/${stepNo}`, {
        method: "PATCH",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.summary(projectId) });
    },
  });
}

export function useCreateManagementRequirement(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<RequirementLink, "id" | "project_id" | "source_updated_at">) =>
      apiFetch<RequirementLink>(`${BASE(projectId)}/requirements`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: managementKeys.requirements(projectId) });
    },
  });
}

export function useCreateManagementDefect(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Omit<DefectLink, "id" | "created_at">) =>
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
