"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";

// ── Types ────────────────────────────────────────────────────────────

export interface FileCoverage {
  file_path: string;
  total_lines: number;
  covered_lines: number;
  missed_lines: number;
  line_rate: number;
  branch_rate: number;
  total_branches: number;
  covered_branches: number;
  total_functions: number;
  covered_functions: number;
  missed_line_numbers: number[];
  uncovered_functions: string[];
  complexity?: number;
}

export interface CoverageSummary {
  total_files: number;
  total_lines: number;
  covered_lines: number;
  missed_lines: number;
  line_rate: number;
  branch_rate: number;
  function_rate: number;
  total_functions: number;
  covered_functions: number;
}

export interface CoverageReport {
  report_id: string;
  project_name: string;
  commit_sha: string;
  branch: string;
  format: string;
  created_at: string;
  summary: CoverageSummary;
  files: FileCoverage[];
}

export interface CoverageGapTarget {
  file_path: string;
  function_name?: string;
  start_line: number;
  end_line: number;
  gap_type: string;
  risk_score: number;
  risk_factors: string[];
  code_snippet: string;
  suggestion: string;
}

export interface GeneratedTest {
  target_file: string;
  target_function?: string;
  test_file_path: string;
  test_code: string;
  test_framework: string;
  estimated_coverage_gain: number;
  lines_targeted: number[];
}

export interface TrendPoint {
  report_id: string;
  commit_sha: string;
  created_at: string;
  line_rate: number;
  branch_rate: number;
  function_rate: number;
}

// ── Query Keys ──────────────────────────────────────────────────────

const KEYS = {
  reports: ["coverup", "reports"] as const,
  report: (id: string) => ["coverup", "reports", id] as const,
  trends: ["coverup", "trends"] as const,
};

// ── Upload Coverage ─────────────────────────────────────────────────

export interface UploadCoverageRequest {
  file: File;
  format: string;
  project_name: string;
  commit_sha?: string;
  branch?: string;
}

export function useUploadCoverage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: UploadCoverageRequest) => {
      const formData = new FormData();
      formData.append("file", req.file);
      formData.append("format", req.format);
      formData.append("project_name", req.project_name);
      if (req.commit_sha) formData.append("commit_sha", req.commit_sha);
      if (req.branch) formData.append("branch", req.branch);
      return apiFetch<CoverageReport>("/api/v1/coverup/upload", {
        method: "POST",
        body: formData,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEYS.reports });
      void qc.invalidateQueries({ queryKey: KEYS.trends });
    },
  });
}

// ── Analyze Coverage ────────────────────────────────────────────────

export interface AnalyzeCoverageRequest {
  report_id: string;
  min_risk_score?: number;
  banking_context?: boolean;
}

export function useAnalyzeCoverage() {
  return useMutation({
    mutationFn: (req: AnalyzeCoverageRequest) =>
      apiFetch<CoverageGapTarget[]>("/api/v1/coverup/analyze", {
        method: "POST",
        json: req,
      }),
  });
}

// ── Generate Tests ──────────────────────────────────────────────────

export interface GenerateTestsRequest {
  report_id: string;
  targets: Array<{
    file_path: string;
    function_name?: string;
    start_line: number;
    end_line: number;
  }>;
  framework: string;
  language: string;
  banking_context?: boolean;
}

export function useGenerateTests() {
  return useMutation({
    mutationFn: (req: GenerateTestsRequest) =>
      apiFetch<GeneratedTest[]>("/api/v1/coverup/generate", {
        method: "POST",
        json: req,
      }),
  });
}

// ── Coverage Reports ────────────────────────────────────────────────

export function useCoverageReports() {
  return useQuery({
    queryKey: KEYS.reports,
    queryFn: () =>
      apiFetch<CoverageReport[]>("/api/v1/coverup/reports"),
  });
}

export function useCoverageReport(reportId: string) {
  return useQuery({
    queryKey: KEYS.report(reportId),
    queryFn: () =>
      apiFetch<CoverageReport>(`/api/v1/coverup/reports/${reportId}`),
    enabled: !!reportId,
  });
}

// ── Trends ──────────────────────────────────────────────────────────

export function useCoverageTrends() {
  return useQuery({
    queryKey: KEYS.trends,
    queryFn: () =>
      apiFetch<TrendPoint[]>("/api/v1/coverup/trends"),
  });
}

// ── Banking Targets ─────────────────────────────────────────────────

export interface BankingTargetsRequest {
  report_id: string;
  max_targets?: number;
}

export function useBankingTargets() {
  return useMutation({
    mutationFn: (req: BankingTargetsRequest) =>
      apiFetch<CoverageGapTarget[]>("/api/v1/coverup/targets", {
        method: "POST",
        json: req,
      }),
  });
}
