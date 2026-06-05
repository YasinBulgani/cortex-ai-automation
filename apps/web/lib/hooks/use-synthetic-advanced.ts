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

// Module-level cache: fit/train adımındaki sample_data'yı saklar
// (Backend fit+generate'i tek adımda yapar; biz 2-adımlı UI'ı desteklemek için önbellekliyoruz)
const _sampleDataCache = new Map<string, Record<string, unknown>[]>();

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

// Backend BankingDatasetRequest şemasıyla eşleştirildi
export interface BankingDatasetRequest {
  customer_count?: number;
  accounts_per_customer?: number;
  transactions_per_account?: number;
  days?: number;
  generator_type?: "kde" | "ctgan";
}

export interface BankingDatasetResult {
  customers: Record<string, unknown>[];
  accounts: Record<string, unknown>[];
  transactions: Record<string, unknown>[];
  stats: Record<string, unknown>;
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
        `/api/ai/nl-test?project_id=${projectId}`,
        { method: "POST", json: req },
      ),
  });
}

export function useNLBatchGenerate(projectId: string) {
  return useMutation({
    mutationFn: (req: NLBatchRequest) =>
      Promise.all(
        req.items.map(item =>
          apiFetch<NLTestResult>(`/api/ai/nl-test?project_id=${projectId}`, {
            method: "POST",
            json: item,
          }),
        ),
      ).then(results => ({
        results,
        total: results.length,
        succeeded: results.length,
        failed: 0,
      })),
  });
}

export function useNLSuggestions(projectId: string) {
  return useMutation({
    mutationFn: async () => ({
      endpoint_id: projectId,
      endpoint: "local-suggestions",
      suggestions: [
        { text: "Kullanıcı geçerli bilgilerle giriş yaptığında dashboard açılmalı", category: "auth", complexity: "medium" },
        { text: "Zorunlu alan boş bırakıldığında doğrulama mesajı gösterilmeli", category: "validation", complexity: "low" },
        { text: "Yetkisiz kullanıcı yönetim sayfasına erişememeli", category: "rbac", complexity: "high" },
      ] satisfies NLSuggestion[],
    }),
  });
}

// ── KDE / CTGAN Hooks ─────────────────────────────────────────────────
// Backend fit+generate'i tek adımda yapar (POST /synthetic/generate).
// Biz 2-adımlı UI akışını korumak için:
//   - Fit/Train adımında veriyi modül düzeyinde önbellekliyoruz.
//   - Generate adımında önbellekten alıp gerçek isteği gönderiyoruz.

export function useKDEFit(projectId: string) {
  return useMutation({
    mutationFn: async (req: KDEFitRequest) => {
      // Veriyi backend'de doğrula (count=1 ile deneme üretimi)
      await apiFetch<unknown>(
        `/api/v1/synthetic/generate?project_id=${projectId}`,
        { method: "POST", json: { sample_data: req.data, count: 1, generator_type: "kde" } },
      );
      _sampleDataCache.set(`kde_${projectId}`, req.data);
      return { fitted: true, columns: Object.keys(req.data[0] ?? {}), row_count: req.data.length };
    },
  });
}

export function useKDEGenerate(projectId: string) {
  return useMutation({
    mutationFn: async (req: KDEGenerateRequest) => {
      const sampleData = _sampleDataCache.get(`kde_${projectId}`) ?? [];
      const res = await apiFetch<{ records: Record<string, unknown>[]; record_count: number }>(
        `/api/v1/synthetic/generate?project_id=${projectId}`,
        { method: "POST", json: { sample_data: sampleData, count: req.count, seed: req.seed, generator_type: "kde" } },
      );
      return { data: res.records, count: res.record_count };
    },
  });
}

export function useCTGANTrain(projectId: string) {
  return useMutation({
    mutationFn: async (req: CTGANTrainRequest) => {
      await apiFetch<unknown>(
        `/api/v1/synthetic/generate?project_id=${projectId}`,
        { method: "POST", json: { sample_data: req.data, count: 1, generator_type: "ctgan" } },
      );
      _sampleDataCache.set(`ctgan_${projectId}`, req.data);
      return { trained: true, epochs: req.epochs ?? 0, loss_history: [] };
    },
  });
}

export function useCTGANGenerate(projectId: string) {
  return useMutation({
    mutationFn: async (req: CTGANGenerateRequest) => {
      const sampleData = _sampleDataCache.get(`ctgan_${projectId}`) ?? [];
      const res = await apiFetch<{ records: Record<string, unknown>[]; record_count: number }>(
        `/api/v1/synthetic/generate?project_id=${projectId}`,
        { method: "POST", json: { sample_data: sampleData, count: req.count, conditions: req.conditions, generator_type: "ctgan" } },
      );
      return { data: res.records, count: res.record_count };
    },
  });
}

// /quality → /quality-check
export function useSyntheticQuality(projectId: string) {
  return useMutation({
    mutationFn: async (args: { original: Record<string, unknown>[]; synthetic: Record<string, unknown>[] }) => {
      const res = await apiFetch<{
        correlation_preservation: number;
        distribution_similarity: Record<string, number>;
        overall_score: number;
      }>(
        `/api/v1/synthetic/quality-check?project_id=${projectId}`,
        { method: "POST", json: args },
      );
      return {
        statistical_similarity: res.overall_score,
        column_correlations: {},
        distribution_scores: res.distribution_similarity,
        overall_quality: res.overall_score,
        warnings: [],
      } satisfies SyntheticQualityReport;
    },
  });
}

// /banking/generate → /banking-dataset (ve tip şeması güncellendi)
export function useBankingDataset(projectId: string) {
  return useMutation({
    mutationFn: async (req: BankingDatasetRequest) => {
      const res = await apiFetch<BankingDatasetResult>(
        `/api/v1/synthetic/banking-dataset?project_id=${projectId}`,
        { method: "POST", json: req },
      );
      return {
        ...res,
        generation_time_ms: res.generation_time_ms ?? (res as unknown as { duration_ms?: number }).duration_ms ?? 0,
      } satisfies BankingDatasetResult;
    },
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
