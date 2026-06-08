"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouteParam } from "@/lib/use-route-param";
import { useMyWork, type MyWorkItem } from "@/lib/hooks/use-management";
import { PageErrorBoundary } from "../_components/PageErrorBoundary";
import { P_DOT, P_LABEL, R_DOT, RUN_STATUS_DOT, RUN_STATUS_LABEL, TYPE_COLOR, relativeTime } from "../_components/workspace/shared";

type Scope = "open" | "all";

function StatusPill({ status }: { status: string }) {
  const r = R_DOT[status] ?? R_DOT.not_run;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${r.bg} ${r.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${r.dot}`} />
      {r.label}
    </span>
  );
}

function MyWorkBody({ projectId }: { projectId: string }) {
  const [scope, setScope] = useState<Scope>("open");
  const { data: items = [], isLoading, isError, refetch, isFetching } = useMyWork(projectId, scope);

  // Group by run for readability
  const groups = useMemo(() => {
    const map = new Map<string, { run_id: string; run_name: string; run_status: string; environment: string | null; items: MyWorkItem[] }>();
    for (const it of items) {
      let g = map.get(it.run_id);
      if (!g) {
        g = { run_id: it.run_id, run_name: it.run_name, run_status: it.run_status, environment: it.environment, items: [] };
        map.set(it.run_id, g);
      }
      g.items.push(it);
    }
    return Array.from(map.values());
  }, [items]);

  const openCount = items.filter(i => i.status === "not_run" || i.status === "running").length;

  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      {/* Header */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-semibold text-fg">İşlerim</h1>
          <p className="mt-0.5 text-[12px] text-fg-muted">
            Size atanan, çalıştırılmayı bekleyen test case&apos;ler
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Scope toggle */}
          <div className="flex rounded-lg border border-border bg-surface-raised p-0.5">
            {(["open", "all"] as Scope[]).map(s => (
              <button
                key={s}
                onClick={() => setScope(s)}
                className={`rounded-md px-3 py-1 text-[11px] font-semibold transition-colors ${
                  scope === s ? "bg-brand-soft text-brand" : "text-fg-subtle hover:text-fg"
                }`}
              >
                {s === "open" ? "Açık" : "Tümü"}
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            className="rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-[11px] font-semibold text-fg-muted transition-colors hover:text-fg"
          >
            {isFetching ? "Yenileniyor…" : "Yenile"}
          </button>
        </div>
      </div>

      {/* Summary chips */}
      {!isLoading && !isError && (
        <div className="mb-4 flex items-center gap-2 text-[11px] text-fg-muted">
          <span className="rounded-full bg-surface-overlay px-2.5 py-1 font-semibold text-fg">{items.length} toplam</span>
          {scope === "all" && (
            <span className="rounded-full bg-blue-500/10 px-2.5 py-1 font-semibold text-blue-400">{openCount} açık</span>
          )}
        </div>
      )}

      {/* States */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-blue-500" />
        </div>
      ) : isError ? (
        <div className="rounded-xl border border-danger/30 bg-danger-subtle p-6 text-center text-[13px] text-danger">
          İşler yüklenemedi. <button onClick={() => refetch()} className="underline">Tekrar dene</button>
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface-raised p-10 text-center">
          <p className="text-[14px] font-semibold text-fg">Sıfır iş 🎉</p>
          <p className="mt-1 text-[12px] text-fg-muted">
            {scope === "open"
              ? "Size atanmış, bekleyen bir test case yok."
              : "Size atanmış hiç test case yok."}
          </p>
          <Link
            href={`/p/${projectId}/management/runs`}
            className="mt-4 inline-block rounded-lg border border-border bg-surface-overlay px-4 py-2 text-[12px] font-semibold text-fg-muted hover:text-fg"
          >
            Test Koşularına git
          </Link>
        </div>
      ) : (
        <div className="space-y-5">
          {groups.map(g => (
            <div key={g.run_id} className="overflow-hidden rounded-xl border border-border bg-surface-raised">
              {/* Run header */}
              <div className="flex items-center justify-between gap-3 border-b border-border bg-surface-overlay px-4 py-2.5">
                <div className="flex min-w-0 items-center gap-2">
                  <span className={`h-2 w-2 shrink-0 rounded-full ${RUN_STATUS_DOT[g.run_status] ?? "bg-slate-500"}`} />
                  <span className="truncate text-[13px] font-semibold text-fg">{g.run_name}</span>
                  <span className="shrink-0 text-[10px] text-fg-subtle">
                    {RUN_STATUS_LABEL[g.run_status] ?? g.run_status}
                    {g.environment ? ` · ${g.environment}` : ""}
                  </span>
                </div>
                <Link
                  href={`/p/${projectId}/management/runs/${g.run_id}/execute`}
                  className="shrink-0 rounded-md bg-brand px-3 py-1 text-[11px] font-semibold text-white hover:opacity-90"
                >
                  ▶ Çalıştır ({g.items.length})
                </Link>
              </div>

              {/* Cases */}
              <ul className="divide-y divide-border">
                {g.items.map(it => {
                  const pl = it.priority ? P_LABEL[it.priority] : null;
                  return (
                    <li key={it.run_case_id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-overlay">
                      {it.priority && (
                        <span className={`h-2 w-2 shrink-0 rounded-full ${P_DOT[it.priority] ?? "bg-slate-500"}`} title={pl?.label} />
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          {it.case_key && (
                            <span className="shrink-0 font-mono text-[10px] text-fg-subtle">{it.case_key}</span>
                          )}
                          <span className="truncate text-[13px] text-fg">{it.case_title}</span>
                        </div>
                      </div>
                      {it.type && (
                        <span className={`hidden shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold sm:inline ${TYPE_COLOR[it.type] ?? "bg-surface-overlay text-fg-muted"}`}>
                          {it.type}
                        </span>
                      )}
                      <StatusPill status={it.status} />
                      {it.started_at && (
                        <span className="hidden w-16 shrink-0 text-right text-[10px] text-fg-subtle md:inline">
                          {relativeTime(it.started_at)}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MyWorkPage() {
  const projectId = useRouteParam("projectId");
  if (!projectId) return null;
  return (
    <PageErrorBoundary>
      <MyWorkBody projectId={projectId} />
    </PageErrorBoundary>
  );
}
