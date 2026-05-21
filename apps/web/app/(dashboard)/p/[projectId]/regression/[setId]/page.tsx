"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Scenario = { id: string; title: string };

type Detail = {
  id: string;
  name: string;
  description: string;
  scenarios: { item_id: string; scenario_id: string; title: string }[];
};

export default function RegressionSetDetailPage() {
  const projectId = useRouteParam("projectId");
  const setId = useRouteParam("setId");
  const [data, setData] = useState<Detail | null>(null);
  const [allScenarios, setAllScenarios] = useState<Scenario[]>([]);
  const [toAdd, setToAdd] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<Detail>(`/api/v1/tspm/projects/${projectId}/regression-sets/${setId}`).then(setData).catch(() => {});
  }, [projectId, setId]);

  useEffect(() => {
    load();
    apiFetch<Scenario[]>(`/api/v1/tspm/projects/${projectId}/scenarios`).then(setAllScenarios).catch(() => {});
  }, [load, projectId]);

  function toggle(id: string) {
    setToAdd((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function addSelected() {
    setErr(null);
    try {
      await apiFetch(`/api/v1/tspm/projects/${projectId}/regression-sets/${setId}/add`, {
        method: "POST",
        json: { scenario_ids: Array.from(toAdd) },
      });
      setToAdd(new Set());
      load();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Hata");
    }
  }

  if (!data) return <p className="text-sm text-slate-400">Yükleniyor…</p>;

  const existing = new Set(data.scenarios.map((s) => s.scenario_id));
  const available = allScenarios.filter((s) => !existing.has(s.id));

  return (
    <div className="mx-auto max-w-4xl space-y-6" data-testid="regression-detail-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" data-testid="regression-detail-heading">{data.name}</h1>
          <p className="text-sm text-slate-400">{data.scenarios.length} senaryo</p>
        </div>
        <Link href={`/p/${projectId}/regression`}>
          <Button type="button" variant="ghost" data-testid="regression-detail-btn-back">Listeye dön</Button>
        </Link>
      </div>

      <section className="rounded-lg border border-slate-800">
        <div className="border-b border-slate-800 px-4 py-2 text-xs font-medium text-slate-400">Mevcut senaryolar</div>
        <ul className="divide-y divide-border">
          {data.scenarios.map((s) => (
            <li key={s.item_id} className="flex items-center gap-3 px-4 py-2 text-sm">
              <Link href={`/p/${projectId}/scenarios/${s.scenario_id}`} className="hover:underline">
                {s.title}
              </Link>
            </li>
          ))}
          {data.scenarios.length === 0 && (
            <li className="px-4 py-4 text-sm text-slate-400">Henüz senaryo eklenmedi.</li>
          )}
        </ul>
      </section>

      {available.length > 0 && (
        <section className="rounded-lg border border-slate-800">
          <div className="border-b border-slate-800 px-4 py-2 text-xs font-medium text-slate-400">Eklenebilir senaryolar</div>
          <ul className="max-h-60 divide-y divide-border overflow-auto">
            {available.map((s) => (
              <li key={s.id} className="flex items-center gap-3 px-4 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={toAdd.has(s.id)}
                  onChange={() => toggle(s.id)}
                  aria-label={s.title}
                  data-testid={`regression-detail-check-${s.id}`}
                />
                <span>{s.title}</span>
              </li>
            ))}
          </ul>
          {toAdd.size > 0 && (
            <div className="border-t border-slate-800 p-3">
              <Button type="button" onClick={addSelected} data-testid="regression-detail-btn-add">
                Seçilenleri ekle ({toAdd.size})
              </Button>
            </div>
          )}
        </section>
      )}
      {err && <p className="text-sm text-red-600">{err}</p>}
    </div>
  );
}
