"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────────────

export type DesignTechnique = "BVA" | "EQ" | "DT" | "STD" | "PAIRWISE" | "CEG";
export type DesignDataType = "int" | "float" | "string" | "date" | "bool" | "enum";

export interface DesignFieldSpec {
  name: string;
  data_type: DesignDataType;
  min_value?: string | null;
  max_value?: string | null;
  allowed_set?: unknown[] | null;
  nullable?: boolean;
}

export interface GeneratedCaseDraft {
  name: string;
  inputs: Record<string, unknown>;
  expected: string;
  boundary_type?: string | null;
  rationale?: string | null;
  partition_label?: string | null;
  field_name?: string | null;
}

export interface DesignPartition {
  id: string;
  field_id: string;
  partition_label: string;
  is_valid: boolean;
  sample_value?: string | null;
}

export interface DesignRun {
  id: string;
  tenant_id: string;
  project_id?: string | null;
  requirement_id?: string | null;
  technique: DesignTechnique;
  input_spec: Record<string, unknown>;
  generated_cases: GeneratedCaseDraft[];
  source: "llm" | "manual" | "fallback";
  llm_trace_id?: string | null;
  created_by?: string | null;
  created_at: string;
  partitions: DesignPartition[];
}

export interface CreateDesignRunInput {
  project_id?: string | null;
  requirement_id?: string | null;
  fields?: DesignFieldSpec[];
  requirement_text?: string;
  conditions?: string[];
  actions?: string[];
  [key: string]: unknown;
}

export interface PromoteCasesInput {
  case_indexes: number[];
  suite_id?: string | null;
  folder_id?: string | null;
}

export interface PromoteCasesResponse {
  case_ids: string[];
}

export interface CaseParamSet {
  id: string;
  tenant_id: string;
  case_id: string;
  schema_json: { fields: Array<{ name: string; type: string; required: boolean }> };
  created_by?: string | null;
  created_at: string;
}

export interface CaseDataRow {
  id: string;
  param_set_id: string;
  values: Record<string, unknown>;
  expected: Record<string, unknown>;
  source_type: "manual" | "csv" | "llm";
  category?: string | null;
  created_at: string;
}

export interface GenerateDataRowsInput {
  param_set_id: string;
  source: "llm" | "csv";
  count?: number;
  csv_content?: string;
}

export interface ExpandCaseResponse {
  execution_ids: string[];
  run_case_ids: string[];
}

// ── Keys & base ──────────────────────────────────────────────────────────────

const BASE = "/api/v1/test-management";

export const designKeys = {
  all: ["mgmt-design"] as const,
  run: (id: string | undefined) => ["mgmt-design", "run", id] as const,
  runs: (technique?: string, requirementId?: string, projectId?: string) =>
    ["mgmt-design", "runs", technique ?? "", requirementId ?? "", projectId ?? ""] as const,
  paramSets: (caseId: string | undefined) => ["mgmt-design", "params", caseId] as const,
  dataRows: (paramSetId: string | undefined) => ["mgmt-design", "rows", paramSetId] as const,
};

// ── Mutations ────────────────────────────────────────────────────────────────

export function useCreateBvaRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDesignRunInput) =>
      apiFetch<DesignRun>(`${BASE}/design/bva`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.all });
    },
  });
}

export function useCreateEqRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDesignRunInput) =>
      apiFetch<DesignRun>(`${BASE}/design/eq`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.all });
    },
  });
}

export function useCreateDtRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDesignRunInput) =>
      apiFetch<DesignRun>(`${BASE}/design/dt`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.all });
    },
  });
}

export function useCreatePairwiseRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDesignRunInput) =>
      apiFetch<DesignRun>(`${BASE}/design/pairwise`, { method: "POST", json: payload }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.all });
    },
  });
}

export function useDesignRun(runId: string | undefined) {
  return useQuery({
    queryKey: designKeys.run(runId),
    queryFn: () => apiFetch<DesignRun>(`${BASE}/design/runs/${runId!}`),
    enabled: !!runId,
    staleTime: 10_000,
  });
}

export function useDesignRuns(filters: { technique?: DesignTechnique; requirementId?: string; projectId?: string } = {}) {
  const params = new URLSearchParams();
  if (filters.technique) params.set("technique", filters.technique);
  if (filters.requirementId) params.set("requirement_id", filters.requirementId);
  if (filters.projectId) params.set("project_id", filters.projectId);
  return useQuery({
    queryKey: designKeys.runs(filters.technique, filters.requirementId, filters.projectId),
    queryFn: () => apiFetch<DesignRun[]>(`${BASE}/design/runs?${params.toString()}`),
    staleTime: 30_000,
  });
}

export function usePromoteCases(runId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromoteCasesInput) =>
      apiFetch<PromoteCasesResponse>(`${BASE}/design/runs/${runId!}/promote`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.run(runId) });
    },
  });
}

export function useCaseParamSets(caseId: string | undefined) {
  return useQuery({
    queryKey: designKeys.paramSets(caseId),
    queryFn: () => apiFetch<CaseParamSet[]>(`${BASE}/cases/${caseId!}/params`),
    enabled: !!caseId,
    staleTime: 30_000,
  });
}

export function useCreateParamSet(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (schemaJson: CaseParamSet["schema_json"]) =>
      apiFetch<CaseParamSet>(`${BASE}/cases/${caseId}/params`, {
        method: "POST",
        json: { case_id: caseId, schema_json: schemaJson },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.paramSets(caseId) });
    },
  });
}

export function useDataRows(caseId: string | undefined, paramSetId: string | undefined) {
  return useQuery({
    queryKey: designKeys.dataRows(paramSetId),
    queryFn: () =>
      apiFetch<CaseDataRow[]>(`${BASE}/cases/${caseId!}/params/${paramSetId!}/data`),
    enabled: !!caseId && !!paramSetId,
    staleTime: 10_000,
  });
}

export function useGenerateDataRows(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: GenerateDataRowsInput) =>
      apiFetch<CaseDataRow[]>(`${BASE}/cases/${caseId}/data`, {
        method: "POST",
        json: payload,
      }),
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: designKeys.dataRows(vars.param_set_id) });
    },
  });
}

export function useAddManualRows(caseId: string, paramSetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rows: Array<Pick<CaseDataRow, "values" | "expected" | "category" | "source_type">>) =>
      apiFetch<CaseDataRow[]>(`${BASE}/cases/${caseId}/params/${paramSetId}/rows`, {
        method: "POST",
        json: rows,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: designKeys.dataRows(paramSetId) });
    },
  });
}

export function useExpandCase(caseId: string) {
  return useMutation({
    mutationFn: () =>
      apiFetch<ExpandCaseResponse>(`${BASE}/cases/${caseId}/expand`, { method: "POST" }),
  });
}
