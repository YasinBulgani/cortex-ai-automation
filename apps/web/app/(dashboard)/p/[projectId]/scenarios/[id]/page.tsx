"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Detail = {
  id: string;
  title: string;
  description: string;
  status: string;
  current_version: number;
  steps: Record<string, unknown>[];
};

export default function ScenarioDetailPage() {
  const projectId = useRouteParam("projectId");
  const id = useRouteParam("id");
  const [s, setS] = useState<Detail | null>(null);

  useEffect(() => {
    apiFetch<Detail>(`/api/v1/tspm/projects/${projectId}/scenarios/${id}`).then(setS).catch((err) => console.warn("[page]:", err));
  }, [projectId, id]);

  if (!s) return <p className="text-sm text-slate-400">Yükleniyor…</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-6" data-testid="scenario-detail-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" data-testid="scenario-detail-heading">{s.title}</h1>
          <p className="mt-1 text-sm text-slate-400">{s.description || "—"}</p>
          <p className="mt-2 text-xs text-slate-400">
            Durum: {s.status} · Sürüm: {s.current_version}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href={`/p/${projectId}/scenarios/edit/${s.id}`}>
            <Button type="button" variant="secondary" data-testid="scenario-detail-btn-edit">
              Düzenle
            </Button>
          </Link>
          <Link href={`/p/${projectId}/scenarios/${s.id}/versions`}>
            <Button type="button" variant="ghost" data-testid="scenario-detail-btn-versions">
              Versiyon Geçmişi
            </Button>
          </Link>
          <Link href={`/p/${projectId}/scenarios`}>
            <Button type="button" variant="ghost" data-testid="scenario-detail-btn-back">
              Listeye dön
            </Button>
          </Link>
        </div>
      </div>
      <section data-testid="scenario-steps" className="rounded-lg border border-slate-800 p-4">
        <h2 className="text-sm font-medium">Adımlar</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm">
          {s.steps?.length ? (
            s.steps.map((st, i) => (
              <li key={i} className="text-slate-400">
                <pre className="whitespace-pre-wrap font-sans text-white">{JSON.stringify(st, null, 2)}</pre>
              </li>
            ))
          ) : (
            <li className="text-slate-400">Adım yok</li>
          )}
        </ol>
      </section>
      <aside className="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-400">
        Versiyon / audit paneli — Faz 2: zaman çizelgesi burada.
      </aside>
    </div>
  );
}
