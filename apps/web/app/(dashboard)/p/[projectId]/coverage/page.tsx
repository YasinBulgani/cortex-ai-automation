"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState, MetricRow, PageHeader, SectionCard, StatCard } from "@/components/nexus";
import { apiFetch } from "@/lib/api";
import { useRouteParam } from "@/lib/use-route-param";

type Requirement = {
  id: string;
  external_id: string;
  title: string;
  priority: string;
  scenario_count: number;
};

export default function CoveragePage() {
  const projectId = useRouteParam("projectId");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await apiFetch<Requirement[]>(`/api/v1/tspm/projects/${projectId}/requirements`);
      setRequirements(data);
    } catch (err) {
      console.warn("[coverage]:", err);
      setRequirements([]);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const covered = requirements.filter((requirement) => requirement.scenario_count > 0).length;
  const gaps = useMemo(
    () => requirements.filter((requirement) => requirement.scenario_count === 0),
    [requirements],
  );
  const coveragePct = requirements.length > 0 ? Math.round((covered / requirements.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-slate-950 p-6" data-testid="coverage-page">
      <PageHeader
        title="Kapsam Matrisi"
        description="Gereksinimlerin senaryo bağlantılarını ve kapsam boşluklarını izleyin"
      />

      <MetricRow cols={3} className="mb-5">
        <StatCard label="Gereksinim" value={requirements.length} color="slate" />
        <StatCard label="Kapsanan" value={covered} color="emerald" />
        <StatCard
          label="Kapsam"
          value={requirements.length === 0 ? "0%" : `${coveragePct}%`}
          color={coveragePct >= 70 ? "emerald" : "amber"}
        />
      </MetricRow>

      <SectionCard title="Kapsam Boşlukları" right={<span className="text-xs text-slate-500">{gaps.length} boşluk</span>}>
        {loading ? (
          <div className="py-8 text-sm text-slate-500">Yükleniyor...</div>
        ) : gaps.length === 0 ? (
          <EmptyState title="Kapsam boşluğu yok" description="Tüm gereksinimler en az bir senaryoya bağlı" />
        ) : (
          <div className="overflow-hidden rounded-lg border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-800 bg-slate-900/60 text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-2">ID</th>
                  <th className="px-4 py-2">Gereksinim</th>
                  <th className="px-4 py-2">Öncelik</th>
                  <th className="px-4 py-2 text-right">Senaryo</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((requirement) => (
                  <tr key={requirement.id} className="border-b border-slate-800 last:border-0">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{requirement.external_id}</td>
                    <td className="px-4 py-3 font-medium text-white">{requirement.title}</td>
                    <td className="px-4 py-3 text-slate-400">{requirement.priority}</td>
                    <td className="px-4 py-3 text-right text-amber-400">{requirement.scenario_count}</td>
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
