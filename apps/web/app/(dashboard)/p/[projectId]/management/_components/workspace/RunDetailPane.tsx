"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { useManagementRun, type RunCase } from "@/lib/hooks/use-management";
import { R_DOT, RUN_STATUS_LABEL, IcPlay } from "./shared";

function snapshotCase(rc: RunCase): { case_key?: string; title?: string; priority?: string } {
  const snap = rc.case_snapshot as { case?: { case_key?: string; title?: string; priority?: string } };
  return snap.case ?? {};
}

export function RunDetailPane({ pid, projectId, runId }: { pid: string; projectId: string; runId: string | null }) {
  const { data: run, isLoading } = useManagementRun(pid || undefined, runId || undefined);

  if (!runId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
        <IcPlay />
        <p className="mt-3 text-[13px] font-medium text-fg-muted">Bir run seçin</p>
        <p className="mt-1 text-[11px] text-fg-subtle">Sol panelden bir run seçerek case'lerini ve ilerlemesini görün.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-teal-500" />
      </div>
    );
  }

  if (!run) {
    return <div className="flex flex-1 items-center justify-center"><p className="text-[13px] text-fg-subtle">Run yüklenemedi</p></div>;
  }

  const runCases = run.run_cases ?? [];
  const total = runCases.length;
  const passed = runCases.filter(rc => rc.status === "passed").length;
  const failed = runCases.filter(rc => rc.status === "failed").length;
  const blocked = runCases.filter(rc => rc.status === "blocked").length;
  const notRun = runCases.filter(rc => rc.status === "not_run").length;
  const pct = total > 0 ? Math.round((passed / total) * 100) : 0;

  return (
    <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
      {/* Header */}
      <div className="border-b border-border bg-surface-raised px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <h2 className="truncate text-[15px] font-semibold text-fg">{run.name}</h2>
            <p className="mt-0.5 text-[11px] text-fg-subtle">
              {RUN_STATUS_LABEL[run.status] ?? run.status}{run.environment ? ` · ${run.environment}` : ""} · {total} senaryo
            </p>
          </div>
          <Link href={`/p/${projectId}/management/runs/${run.id}/execute`}
            className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
            <IcPlay /> Yürüt
          </Link>
        </div>

        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 h-1.5 rounded-full bg-surface-overlay overflow-hidden">
            <div className="h-full rounded-full bg-emerald-500/70 transition-all duration-500" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-[11px] font-semibold tabular-nums text-fg-muted">{pct}%</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {[
            { dot: "bg-emerald-500/70", n: passed, l: "passed" },
            { dot: "bg-red-500/80", n: failed, l: "failed" },
            { dot: "bg-amber-500/60", n: blocked, l: "blocked" },
            { dot: "bg-slate-600", n: notRun, l: "kalan" },
          ].map(s => (
            <span key={s.l} className="flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} />
              <span className="text-[11px] font-medium tabular-nums text-fg-muted">{s.n}</span>
              <span className="text-[11px] text-fg-subtle">{s.l}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Case list */}
      <div className="flex-1 overflow-y-auto">
        {runCases.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-[13px] font-medium text-fg-muted">Bu run'a case eklenmemiş</p>
            <p className="mt-1 text-[11px] text-fg-subtle">Yeni run oluştururken case seçin.</p>
          </div>
        ) : (
          <table className="w-full">
            <tbody>
              {runCases.map(rc => {
                const ci = snapshotCase(rc);
                const rd = R_DOT[rc.status] ?? R_DOT.not_run;
                return (
                  <tr key={rc.id} className="border-b border-border-subtle transition-colors hover:bg-surface-overlay">
                    <td className="w-6 pl-4"><span className={cn("inline-block h-1.5 w-1.5 rounded-full", rd.dot)} /></td>
                    <td className="w-[5.5rem] px-3 py-2.5"><span className="font-mono text-[10px] text-fg-subtle">{ci.case_key ?? "—"}</span></td>
                    <td className="px-3 py-2.5"><p className="line-clamp-1 text-[13px] text-fg-muted">{ci.title ?? rc.case_id}</p></td>
                    <td className="w-24 px-3 py-2.5"><span className="text-[11px] text-fg-subtle">{rd.label}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
