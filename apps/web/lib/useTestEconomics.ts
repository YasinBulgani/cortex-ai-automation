"use client";

/**
 * Test economics dashboard — F6.
 *
 * Her testin maliyeti (CI dakika + AI token) ve faydası (önlediği bug değeri)
 * üzerinden ROI hesabı.
 *
 * Sectörde benzersiz feature — Neurex differentiation.
 */

import { useEffect, useState } from "react";

export type TestEconomicsRow = {
  test_id: string;
  test_title: string;
  runs_30d: number;
  total_runtime_sec: number;
  ci_cost_usd: number;
  ai_token_cost_usd: number;
  bugs_caught: number;
  estimated_bug_value_usd: number;
  roi_ratio: number;
  classification: string; // "high-value" | "neutral" | "wasteful"
};

export type TestEconomicsSummary = {
  total_ci_cost_usd: number;
  total_bug_value_caught_usd: number;
  overall_roi: number;
  top_value_tests: TestEconomicsRow[];
  wasteful_tests: TestEconomicsRow[];
};

export function useTestEconomics(projectId: string) {
  const [summary, setSummary] = useState<TestEconomicsSummary | null>(null);
  const [rows, setRows] = useState<TestEconomicsRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v1/tspm/projects/${projectId}/economics`, {
      credentials: "include",
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((body) => {
        setSummary(body.summary);
        setRows(body.rows ?? []);
        setError(null);
      })
      .catch((e: any) => setError(e?.message ?? "Bilinmeyen hata"))
      .finally(() => setLoading(false));
  }, [projectId]);

  return { summary, rows, loading, error };
}

/**
 * Standalone classifier — UI'da row decoration için.
 *
 * roi_ratio = bug_value / (ci_cost + ai_cost)
 *   > 5    : high-value (yeşil)
 *   1-5    : neutral (sarı)
 *   < 1    : wasteful (kırmızı) — koşum maliyeti faydanın üzerinde
 */
export function classifyRoi(roi: number): "high-value" | "neutral" | "wasteful" {
  if (roi > 5) return "high-value";
  if (roi >= 1) return "neutral";
  return "wasteful";
}

export function roiBadgeClass(category: "high-value" | "neutral" | "wasteful"): string {
  switch (category) {
    case "high-value":
      return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
    case "neutral":
      return "bg-slate-500/20 text-slate-300 border-slate-500/30";
    case "wasteful":
      return "bg-red-500/20 text-red-300 border-red-500/30";
  }
}
