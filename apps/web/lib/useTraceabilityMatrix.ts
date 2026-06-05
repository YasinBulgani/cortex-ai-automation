"use client";

/**
 * Requirement traceability matrix — F3.
 *
 * Backend'den feature × test coverage matrix data çeker; UI'da heatmap
 * gösterimi için pre-aggregated cell'ler oluşturur.
 */

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

export type TraceabilityCell = {
  feature_id: string;
  feature_name: string;
  test_count: number;
  passed_count: number;
  failed_count: number;
  flaky_count: number;
  coverage_pct: number;
};

export type TraceabilityMatrix = {
  features: TraceabilityCell[];
  total_tests: number;
  overall_coverage_pct: number;
};

type RequirementTraceabilityRow = {
  requirement_id?: string | null;
  requirement_key?: string;
  title: string;
  cases?: Array<{
    last_run_status?: string | null;
  }>;
  coverage_pct?: number;
};

function isPassedStatus(status: string | null | undefined): boolean {
  return ["passed", "pass", "success", "green"].includes((status ?? "").toLowerCase());
}

function isFailedStatus(status: string | null | undefined): boolean {
  return ["failed", "fail", "error", "red"].includes((status ?? "").toLowerCase());
}

function isFlakyStatus(status: string | null | undefined): boolean {
  return ["flaky", "unstable", "quarantined"].includes((status ?? "").toLowerCase());
}

function normalizeTraceability(rows: RequirementTraceabilityRow[]): TraceabilityMatrix {
  const features = rows.map((row, index) => {
    const cases = row.cases ?? [];
    return {
      feature_id: row.requirement_id ?? row.requirement_key ?? `requirement-${index}`,
      feature_name: row.title,
      test_count: cases.length,
      passed_count: cases.filter((item) => isPassedStatus(item.last_run_status)).length,
      failed_count: cases.filter((item) => isFailedStatus(item.last_run_status)).length,
      flaky_count: cases.filter((item) => isFlakyStatus(item.last_run_status)).length,
      coverage_pct: Number(row.coverage_pct ?? 0),
    };
  });
  const totalCoverage = features.reduce((sum, item) => sum + item.coverage_pct, 0);
  return {
    features,
    total_tests: features.reduce((sum, item) => sum + item.test_count, 0),
    overall_coverage_pct: features.length > 0 ? Math.round(totalCoverage / features.length) : 0,
  };
}

export function useTraceabilityMatrix(projectId: string) {
  const [data, setData] = useState<TraceabilityMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    apiFetch<RequirementTraceabilityRow[]>(
      `/api/v1/test-management/projects/${projectId}/requirements/traceability`,
    )
      .then((body) => {
        setData(normalizeTraceability(body));
        setError(null);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Bilinmeyen hata"))
      .finally(() => setLoading(false));
  }, [projectId]);

  return { data, loading, error };
}

/**
 * Coverage band → color class.
 * 0-30   red   (severely undercovered)
 * 30-60  amber (partial)
 * 60-85  yellow (mostly covered)
 * 85+    green  (well covered)
 */
export function coverageColorClass(pct: number): string {
  if (pct >= 85) return "bg-emerald-500/30 text-emerald-200";
  if (pct >= 60) return "bg-yellow-500/30 text-yellow-200";
  if (pct >= 30) return "bg-amber-500/30 text-amber-200";
  return "bg-red-500/30 text-red-200";
}
