"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────

// NL Test Generation
export interface NLTestRequest {
  text: string;
  format: "pytest" | "playwright" | "cypress" | "gherkin";
  language: "python" | "typescript" | "javascript";
  framework_hints?: string[];
}

export interface NLTestStep {
  step_number: number;
  action: string;
  selector?: string;
  value?: string;
  assertion?: string;
}

export interface NLTestResult {
  test_id: string;
  original_text: string;
  test_name: string;
  test_code: string;
  format: string;
  language: string;
  steps: NLTestStep[];
  confidence: number;
  warnings: string[];
  generated_at: string;
}

export interface NLBatchRequest {
  items: NLTestRequest[];
}

export interface NLBatchResult {
  results: NLTestResult[];
  total: number;
  succeeded: number;
  failed: number;
}

export interface NLSuggestion {
  text: string;
  category: string;
  complexity: string;
}

// KDE + CTGAN Synthetic Data
export interface KDEFitRequest {
  data: Record<string, unknown>[];
  columns?: string[];
}

export interface KDEGenerateRequest {
  count: number;
  seed?: number;
}

export interface CTGANTrainRequest {
  data: Record<string, unknown>[];
  epochs?: number;
  batch_size?: number;
  discrete_columns?: string[];
}

export interface CTGANGenerateRequest {
  count: number;
  conditions?: Record<string, unknown>;
}

export interface SyntheticQualityReport {
  statistical_similarity: number;
  column_correlations: Record<string, number>;
  distribution_scores: Record<string, number>;
  overall_quality: number;
  warnings: string[];
}

export interface BankingDatasetRequest {
  dataset_type: "accounts" | "transactions" | "customers" | "loans" | "cards";
  count: number;
  locale?: string;
  realistic_distributions?: boolean;
}

export interface BankingDatasetResult {
  dataset_type: string;
  count: number;
  data: Record<string, unknown>[];
  schema: Record<string, string>;
  generation_time_ms: number;
}

// Differential Privacy
export interface PrivacyConfig {
  epsilon: number;
  delta?: number;
  mechanism: "laplace" | "gaussian" | "exponential";
  sensitivity?: number;
}

export interface AnonymizationRequest {
  data: Record<string, unknown>[];
  quasi_identifiers: string[];
  sensitive_columns: string[];
  k_anonymity?: number;
  l_diversity?: number;
}

export interface AnonymizationResult {
  anonymized_data: Record<string, unknown>[];
  original_count: number;
  output_count: number;
  suppressed_count: number;
  k_achieved: number;
  l_achieved: number;
  information_loss: number;
}

export interface PrivacyAuditResult {
  dataset_name: string;
  total_records: number;
  pii_columns_detected: string[];
  quasi_identifier_risk: Record<string, number>;
  re_identification_risk: number;
  compliance: {
    kvkk: { compliant: boolean; issues: string[] };
    gdpr: { compliant: boolean; issues: string[] };
    pci_dss: { compliant: boolean; issues: string[] };
  };
  recommendations: string[];
}

export interface DPNoiseResult {
  original_value: number;
  noisy_value: number;
  noise_added: number;
  epsilon_used: number;
  mechanism: string;
}

// ── NL Test Generation Hooks ──────────────────────────────────────────

export function useNLGenerate(projectId: string) {
  return useMutation({
    mutationFn: (req: NLTestRequest) =>
      apiFetch<NLTestResult>(
        `/api/v1/ai/nl-test/generate?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useNLBatchGenerate(projectId: string) {
  return useMutation({
    mutationFn: (req: NLBatchRequest) =>
      apiFetch<NLBatchResult>(
        `/api/v1/ai/nl-test/batch?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useNLSuggestions(projectId: string) {
  return useQuery({
    queryKey: ["nl-suggestions", projectId],
    queryFn: () =>
      apiFetch<NLSuggestion[]>(
        `/api/v1/ai/nl-test/suggestions?project_id=${projectId}`,
      ),
    enabled: !!projectId,
  });
}

// ── KDE / CTGAN Hooks ─────────────────────────────────────────────────

export function useKDEFit(projectId: string) {
  return useMutation({
    mutationFn: (req: KDEFitRequest) =>
      apiFetch<{ fitted: boolean; columns: string[]; row_count: number }>(
        `/api/v1/synthetic/kde/fit?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useKDEGenerate(projectId: string) {
  return useMutation({
    mutationFn: (req: KDEGenerateRequest) =>
      apiFetch<{ data: Record<string, unknown>[]; count: number }>(
        `/api/v1/synthetic/kde/generate?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useCTGANTrain(projectId: string) {
  return useMutation({
    mutationFn: (req: CTGANTrainRequest) =>
      apiFetch<{ trained: boolean; epochs: number; loss_history: number[] }>(
        `/api/v1/synthetic/ctgan/train?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useCTGANGenerate(projectId: string) {
  return useMutation({
    mutationFn: (req: CTGANGenerateRequest) =>
      apiFetch<{ data: Record<string, unknown>[]; count: number }>(
        `/api/v1/synthetic/ctgan/generate?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useSyntheticQuality(projectId: string) {
  return useMutation({
    mutationFn: (args: { original: Record<string, unknown>[]; synthetic: Record<string, unknown>[] }) =>
      apiFetch<SyntheticQualityReport>(
        `/api/v1/synthetic/quality?project_id=${projectId}`,
        { method: "POST", json: args },
      ),
  });
}

export function useBankingDataset(projectId: string) {
  return useMutation({
    mutationFn: (req: BankingDatasetRequest) =>
      apiFetch<BankingDatasetResult>(
        `/api/v1/synthetic/banking/generate?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

// ── Differential Privacy Hooks ────────────────────────────────────────

export function usePrivacyAudit(projectId: string) {
  return useMutation({
    mutationFn: (args: { data: Record<string, unknown>[]; dataset_name?: string }) =>
      apiFetch<PrivacyAuditResult>(
        `/api/v1/synthetic/privacy/audit?project_id=${projectId}`,
        { method: "POST", json: args },
      ),
  });
}

export function useAnonymize(projectId: string) {
  return useMutation({
    mutationFn: (req: AnonymizationRequest) =>
      apiFetch<AnonymizationResult>(
        `/api/v1/synthetic/privacy/anonymize?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useAddNoise(projectId: string) {
  return useMutation({
    mutationFn: (args: { value: number; config: PrivacyConfig }) =>
      apiFetch<DPNoiseResult>(
        `/api/v1/synthetic/privacy/noise?project_id=${projectId}`,
        { method: "POST", json: args },
      ),
  });
}

export function usePrivacyReport(projectId: string) {
  return useQuery({
    queryKey: ["privacy-report", projectId],
    queryFn: () =>
      apiFetch<PrivacyAuditResult>(
        `/api/v1/synthetic/privacy/report?project_id=${projectId}`,
      ),
    enabled: !!projectId,
  });
}
