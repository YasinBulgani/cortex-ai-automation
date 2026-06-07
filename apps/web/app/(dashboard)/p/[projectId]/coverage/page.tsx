"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { EmptyState, MetricRow, PageHeader, SectionCard, StatCard } from "@/components/nexus";
import { apiFetch } from "@/lib/api";
import { useRouteParam } from "@/lib/use-route-param";

// coverage-matrix endpoint tiplerini yansıtır
type CoverageCell = {
  requirement_id: string;
  scenario_id: string;
  last_result: "passed" | "failed" | "skipped" | "not_run";
};

type CoverageMatrixOut = {
  requirement_ids: string[];
  scenario_ids: string[];
  scenario_titles: Record<string, string>;
  requirement_titles: Record<string, string>;
  requirement_external_ids: Record<string, string>;
  requirement_priorities: Record<string, string>;
  cells: CoverageCell[];
  coverage_pct: number;
  covered_count: number;
  total_requirements: number;
  gap_count: number;
};

// Fallback: requirements list endpoint
type Requirement = {
  id: string;
  external_id: string;
  title: string;
  priority: string;
  scenario_count: number;
};

function resultBadge(result: CoverageCell["last_result"]) {
  const map: Record<string, string> = {
    passed: "bg-emerald-500",
    failed: "bg-red-500",
    skipped: "bg-amber-400",
    not_run: "bg-slate-700",
  };
  const labels: Record<string, string> = {
    passed: "Gecti",
    failed: "Basarisiz",
    skipped: "Atlandi",
    not_run: "Calistirilmadi",
  };
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${map[result] ?? "bg-slate-700"}`}
      title={labels[result] ?? result}
    />
  );
}

function priorityColor(priority: string) {
  if (priority === "high" || priority === "critical") return "text-red-400";
  if (priority === "medium") return "text-amber-400";
  return "text-slate-400";
}

export default function CoveragePage() {
  const projectId = useRouteParam("projectId");

  // Önce coverage-matrix endpoint'ini dene
  const {
    data: matrix,
    isLoading: matrixLoading,
    error: matrixError,
  } = useQuery<CoverageMatrixOut>({
    queryKey: ["coverage", "matrix", projectId],
    queryFn: () =>
      apiFetch<CoverageMatrixOut>(
        `/api/v1/tspm/projects/${projectId}/coverage-matrix`,
      ),
    enabled: !!projectId,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
    retry: 1,
  });

  // matrix hata verirse requirements fallback
  const {
    data: requirements = [],
    isLoading: reqLoading,
  } = useQuery<Requirement[]>({
    queryKey: ["requirements", "list", projectId],
    queryFn: () =>
      apiFetch<Requirement[]>(`/api/v1/tspm/projects/${projectId}/requirements`),
    enabled: !!projectId && !!matrixError,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });

  const loading = matrixLoading || (!!matrixError && reqLoading);

  // matrix varsa ondan hesapla, yoksa requirements'tan
  const covered = matrix
    ? matrix.covered_count
    : requirements.filter((r) => r.scenario_count > 0).length;
  const total = matrix ? matrix.total_requirements : requirements.length;
  const coveragePct = matrix
    ? Math.round(matrix.coverage_pct)
    : total > 0
      ? Math.round((covered / total) * 100)
      : 0;

  const gaps = useMemo(() => {
    if (matrix) {
      return matrix.requirement_ids
        .filter((rId) => !matrix.cells.some((c) => c.requirement_id === rId))
        .map((rId) => ({
          id: rId,
          external_id: matrix.requirement_external_ids[rId] ?? rId.slice(0, 8),
          title: matrix.requirement_titles[rId] ?? rId,
          priority: matrix.requirement_priorities[rId] ?? "medium",
          scenario_count: 0,
        }));
    }
    return requirements.filter((r) => r.scenario_count === 0);
  }, [matrix, requirements]);

  // Senaryo bazlı son sonuçlar (sadece matrix modunda)
  const scenarioResults = useMemo(() => {
    if (!matrix) return null;
    // req x scenario ızgarası için kolaylaştırılmış erişim
    const map: Record<string, Record<string, CoverageCell["last_result"]>> = {};
    for (const cell of matrix.cells) {
      if (!map[cell.requirement_id]) map[cell.requirement_id] = {};
      map[cell.requirement_id][cell.scenario_id] = cell.last_result;
    }
    return map;
  }, [matrix]);

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="coverage-page">
      <PageHeader
        title="Kapsam Matrisi"
        description="Gereksinimlerin senaryo baglantilarini ve kapsam bosluklarini izleyin"
      />

      <MetricRow cols={4} className="mb-5">
        <StatCard label="Gereksinim" value={total} color="slate" />
        <StatCard label="Kapsanan" value={covered} color="emerald" />
        <StatCard
          label="Kapsam"
          value={total === 0 ? "0%" : `${coveragePct}%`}
          color={coveragePct >= 70 ? "emerald" : coveragePct >= 40 ? "amber" : "red"}
        />
        <StatCard
          label="Bosluk"
          value={gaps.length}
          color={gaps.length === 0 ? "emerald" : "amber"}
        />
      </MetricRow>

      {/* Coverage-matrix API degrade olursa kullanıcıya uyarı ver */}
      {matrixError && !matrixLoading && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-400">
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          </svg>
          <span>Kapsam matrisi yüklenemedi — gereksinim listesi gösteriliyor. Matris verisi için sayfayı yenileyin.</span>
        </div>
      )}

      {/* Matris görünümü — sadece coverage-matrix başarılıysa */}
      {matrix && scenarioResults && matrix.scenario_ids.length > 0 && (
        <SectionCard
          title="Gereksinim x Senaryo Matrisi"
          right={
            <span className="text-xs text-slate-500">
              {matrix.requirement_ids.length} gereksinim · {matrix.scenario_ids.length} senaryo
            </span>
          }
          className="mb-4 overflow-x-auto"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60">
                  <th className="px-3 py-2 text-slate-400 min-w-[180px]">Gereksinim</th>
                  {matrix.scenario_ids.map((sId) => (
                    <th
                      key={sId}
                      className="px-2 py-2 text-center text-slate-500 max-w-[60px] truncate"
                      title={matrix.scenario_titles[sId] ?? sId}
                    >
                      {(matrix.scenario_titles[sId] ?? sId).slice(0, 12)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.requirement_ids.map((rId) => (
                  <tr
                    key={rId}
                    className="border-b border-slate-800 last:border-0 hover:bg-slate-900/40"
                  >
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-white">
                        {matrix.requirement_titles[rId] ?? rId}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-slate-500">
                          {matrix.requirement_external_ids[rId] ?? ""}
                        </span>
                        <span
                          className={`text-[10px] font-medium uppercase ${priorityColor(matrix.requirement_priorities[rId] ?? "medium")}`}
                        >
                          {matrix.requirement_priorities[rId] ?? ""}
                        </span>
                      </div>
                    </td>
                    {matrix.scenario_ids.map((sId) => (
                      <td key={sId} className="px-2 py-2.5 text-center">
                        {scenarioResults[rId]?.[sId]
                          ? resultBadge(scenarioResults[rId][sId])
                          : <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-800" title="Baglanti yok" />}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-500" /> Gecti
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" /> Basarisiz
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-400" /> Atlandi
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-700" /> Calistirilmadi
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-slate-800" /> Baglanti yok
            </span>
          </div>
        </SectionCard>
      )}

      <SectionCard
        title="Kapsam Boslukları"
        right={<span className="text-xs text-slate-500">{gaps.length} bosluk</span>}
      >
        {loading ? (
          <div className="space-y-2 py-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-800" />
            ))}
          </div>
        ) : gaps.length === 0 ? (
          <EmptyState
            title="Kapsam boslugu yok"
            description="Tum gereksinimler en az bir senaryoya bagli"
          />
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 bg-slate-900/60 text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-2">ID</th>
                  <th className="px-4 py-2">Gereksinim</th>
                  <th className="px-4 py-2">Oncelik</th>
                  <th className="px-4 py-2 text-right">Senaryo</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((requirement) => (
                  <tr
                    key={requirement.id}
                    className="border-b border-slate-800 last:border-0 hover:bg-slate-900/30"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      {requirement.external_id}
                    </td>
                    <td className="px-4 py-3 font-medium text-white">{requirement.title}</td>
                    <td className={`px-4 py-3 text-sm ${priorityColor(requirement.priority)}`}>
                      {requirement.priority}
                    </td>
                    <td className="px-4 py-3 text-right text-amber-400">
                      {requirement.scenario_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
