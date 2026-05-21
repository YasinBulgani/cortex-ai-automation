"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

type Version = {
  id: string;
  version_number: number;
  title: string;
  status: string;
  created_at: string | null;
};

type DiffChange = {
  field: string;
  old_value: string;
  new_value: string;
};

export default function ScenarioVersionsPage() {
  const projectId = useRouteParam("projectId");
  const scenarioId = useRouteParam("id");

  const [versions, setVersions] = useState<Version[]>([]);
  const [selected, setSelected] = useState<[string | null, string | null]>([null, null]);
  const [diff, setDiff] = useState<DiffChange[] | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    apiFetch<Version[]>(
      `/api/v1/tspm/projects/${projectId}/scenarios/${scenarioId}/versions`
    ).then(setVersions).catch((err) => console.warn("[versions]:", err));
  }, [projectId, scenarioId]);

  useEffect(() => {
    load();
  }, [load]);

  function selectVersion(id: string) {
    setDiff(null);
    setSelected((prev) => {
      if (prev[0] === id) return [null, prev[1]];
      if (prev[1] === id) return [prev[0], null];
      if (!prev[0]) return [id, prev[1]];
      return [prev[0], id];
    });
  }

  async function compare() {
    const [v1, v2] = selected;
    if (!v1 || !v2) return;
    setLoading(true);
    try {
      const data = await apiFetch<DiffChange[]>(
        `/api/v1/tspm/projects/${projectId}/scenarios/${scenarioId}/versions/${v1}/diff/${v2}`
      );
      setDiff(data);
    } finally {
      setLoading(false);
    }
  }

  function vLabel(id: string | null) {
    if (!id) return "—";
    const v = versions.find((ver) => ver.id === id);
    return v ? `v${v.version_number}` : id.slice(0, 8);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="versions-page">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight" data-testid="versions-heading">Sürüm Geçmişi</h1>
          <p className="text-sm text-slate-400">Senaryo versiyon zaman çizelgesi</p>
        </div>
        <Link href={`/p/${projectId}/scenarios/${scenarioId}`}>
          <Button type="button" variant="ghost" data-testid="versions-btn-back">Senaryoya dön</Button>
        </Link>
      </div>

      {/* Version selection info */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 p-3 text-sm">
        <span className="text-slate-400">Karşılaştırma:</span>
        <Badge>{vLabel(selected[0])}</Badge>
        <span className="text-slate-400">↔</span>
        <Badge>{vLabel(selected[1])}</Badge>
        <Button
          type="button"
          className="ml-auto h-8 text-xs"
          disabled={!selected[0] || !selected[1] || loading}
          onClick={compare}
          data-testid="versions-btn-compare"
        >
          {loading ? "Yükleniyor…" : "Karşılaştır"}
        </Button>
      </div>

      {/* Timeline */}
      <div data-testid="version-list" className="relative space-y-0 pl-6">
        <div className="absolute left-[11px] top-2 bottom-2 w-px bg-border" />
        {versions.map((v) => {
          const isSelected = selected[0] === v.id || selected[1] === v.id;
          return (
            <button
              key={v.id}
              type="button"
              onClick={() => selectVersion(v.id)}
              className={`relative mb-3 w-full rounded-lg border p-4 text-left transition-colors ${
                isSelected
                  ? "border-blue-500 bg-blue-500/5"
                  : "border-slate-800 hover:border-blue-500/40"
              }`}
            >
              <div
                className={`absolute -left-6 top-5 h-3 w-3 rounded-full border-2 ${
                  isSelected
                    ? "border-blue-500 bg-blue-600"
                    : "border-slate-800 bg-slate-900"
                }`}
              />
              <div className="flex items-center gap-2">
                <span className="font-medium">v{v.version_number}</span>
                <Badge>{v.status}</Badge>
              </div>
              <p className="mt-1 text-sm">{v.title}</p>
              <p className="mt-1 text-xs text-slate-400">
                {v.created_at
                  ? new Date(v.created_at).toLocaleString("tr-TR")
                  : "—"}
              </p>
            </button>
          );
        })}
        {versions.length === 0 && (
          <p className="py-6 text-sm text-slate-400">Sürüm bulunamadı.</p>
        )}
      </div>

      {/* Diff */}
      {diff && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">
            Fark: {vLabel(selected[0])} → {vLabel(selected[1])}
          </h2>
          {diff.length === 0 ? (
            <p className="rounded-lg border border-slate-800 p-4 text-sm text-slate-400">
              İki sürüm arasında fark bulunamadı.
            </p>
          ) : (
            <div className="space-y-2">
              {diff.map((d, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-slate-800 p-4 space-y-2"
                >
                  <p className="text-xs font-medium text-slate-400">{d.field}</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="rounded border border-red-200 bg-red-50 p-2 text-sm dark:border-red-900 dark:bg-red-950/40">
                      <span className="text-xs font-medium text-red-600">Eski</span>
                      <pre className="mt-1 whitespace-pre-wrap font-sans text-red-800 dark:text-red-300">
                        {d.old_value || "—"}
                      </pre>
                    </div>
                    <div className="rounded border border-green-200 bg-green-50 p-2 text-sm dark:border-green-900 dark:bg-green-950/40">
                      <span className="text-xs font-medium text-green-600">Yeni</span>
                      <pre className="mt-1 whitespace-pre-wrap font-sans text-green-800 dark:text-green-300">
                        {d.new_value || "—"}
                      </pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
