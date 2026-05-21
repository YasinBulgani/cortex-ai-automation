"use client";

/**
 * Requirement traceability matrix — F3.
 *
 * Backend'den feature × test coverage matrix data çeker; UI'da heatmap
 * gösterimi için pre-aggregated cell'ler oluşturur.
 */

import { useEffect, useState } from "react";

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

export function useTraceabilityMatrix(projectId: string) {
  const [data, setData] = useState<TraceabilityMatrix | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v1/tspm/projects/${projectId}/traceability`, {
      credentials: "include",
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((body) => {
        setData(body);
        setError(null);
      })
      .catch((e: any) => setError(e?.message ?? "Bilinmeyen hata"))
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
