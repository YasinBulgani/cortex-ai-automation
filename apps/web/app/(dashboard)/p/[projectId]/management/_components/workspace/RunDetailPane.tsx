"use client";

import { useState, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api-client";
import {
  useManagementRun,
  useUpdateManagementRun,
  useDeleteManagementRun,
  type RunCase,
} from "@/lib/hooks/use-management";
import { R_DOT, RUN_STATUS_LABEL, IcPlay } from "./shared";

interface Member { user_id: string; email: string; full_name?: string; }

function snapshotCase(rc: RunCase): { case_key?: string; title?: string; priority?: string } {
  const snap = rc.case_snapshot as { case?: { case_key?: string; title?: string; priority?: string } };
  return snap.case ?? {};
}

function fmtDate(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function RunDetailPane({
  pid,
  projectId,
  runId,
  onDeleted,
}: {
  pid: string;
  projectId: string;
  runId: string | null;
  onDeleted?: () => void;
}) {
  const { data: run, isLoading } = useManagementRun(pid || undefined, runId || undefined);
  const updateRun = useUpdateManagementRun(pid);
  const deleteRun = useDeleteManagementRun(pid);

  const { data: membersData } = useQuery({
    queryKey: ["management", "members", projectId],
    queryFn: () => apiFetch<Member[]>(`/api/v1/organizations/projects/${projectId}/members`).then(d => Array.isArray(d) ? d : []),
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
  const userIdMap = useMemo<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const m of membersData ?? []) map[m.user_id] = m.full_name?.trim() || m.email;
    return map;
  }, [membersData]);

  /* --- inline rename state --- */
  const [renaming, setRenaming] = useState(false);
  const [renameVal, setRenameVal] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const startRename = useCallback(() => {
    if (!run) return;
    setRenameVal(run.name);
    setRenaming(true);
    setTimeout(() => inputRef.current?.select(), 0);
  }, [run]);

  const commitRename = useCallback(() => {
    if (!run) return;
    const trimmed = renameVal.trim();
    if (trimmed && trimmed !== run.name) {
      updateRun.mutate({ id: run.id, name: trimmed });
    }
    setRenaming(false);
  }, [run, renameVal, updateRun]);

  const handleRenameKey = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") commitRename();
      if (e.key === "Escape") setRenaming(false);
    },
    [commitRename],
  );

  /* --- delete --- */
  const handleDelete = useCallback(() => {
    if (!run) return;
    const ok = window.confirm(`"${run.name}" adlı run silinecek. Emin misiniz?`);
    if (!ok) return;
    deleteRun.mutate(run.id, {
      onSuccess: () => { onDeleted?.(); },
    });
  }, [run, deleteRun, onDeleted]);

  if (!runId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center text-center p-8">
        <IcPlay />
        <p className="mt-3 text-[13px] font-medium text-fg-muted">Bir koşum seçin</p>
        <p className="mt-1 text-[11px] text-fg-subtle">Sol panelden bir test koşumu seçerek senaryolarını ve ilerlemesini görün.</p>
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
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-[13px] text-fg-subtle">Run yüklenemedi</p>
      </div>
    );
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
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            {renaming ? (
              <input
                ref={inputRef}
                value={renameVal}
                onChange={e => setRenameVal(e.target.value)}
                onBlur={commitRename}
                onKeyDown={handleRenameKey}
                className="w-full rounded border border-brand bg-surface px-2 py-0.5 text-[15px] font-semibold text-fg outline-none"
              />
            ) : (
              <h2
                className="truncate text-[15px] font-semibold text-fg cursor-text select-none"
                onDoubleClick={startRename}
                title="Yeniden adlandırmak için çift tıklayın"
              >
                {run.name}
              </h2>
            )}
            <p className="mt-0.5 text-[11px] text-fg-subtle">
              {RUN_STATUS_LABEL[run.status] ?? run.status}
              {run.environment ? ` · ${run.environment}` : ""}
              {" · "}
              {total} senaryo
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Link
              href={`/p/${projectId}/management/runs/${run.id}/execute`}
              className="flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2 text-[13px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
            >
              <IcPlay /> Yürüt
            </Link>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleteRun.isPending}
              className="flex items-center gap-1 rounded-lg border border-red-500/40 px-3 py-2 text-[12px] font-medium text-red-400 transition-colors hover:bg-red-500/10 disabled:opacity-50"
            >
              Sil
            </button>
          </div>
        </div>

        {/* Meta info: assigned_to, dates */}
        <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[11px] text-fg-subtle">
          {run.assigned_to && (
            <span>
              <span className="font-medium text-fg-muted">Atanan:</span>{" "}
              {userIdMap[run.assigned_to] ?? run.assigned_to}
            </span>
          )}
          <span>
            <span className="font-medium text-fg-muted">Başlangıç:</span>{" "}
            {fmtDate(run.started_at)}
          </span>
          <span>
            <span className="font-medium text-fg-muted">Bitiş:</span>{" "}
            {fmtDate(run.completed_at)}
          </span>
        </div>

        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 h-1.5 rounded-full bg-surface-overlay overflow-hidden">
            <div
              className="h-full rounded-full bg-emerald-500/70 transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
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
                  <tr
                    key={rc.id}
                    className="border-b border-border-subtle transition-colors hover:bg-surface-overlay"
                  >
                    <td className="w-6 pl-4">
                      <span className={cn("inline-block h-1.5 w-1.5 rounded-full", rd.dot)} />
                    </td>
                    <td className="w-[5.5rem] px-3 py-2.5">
                      <span className="font-mono text-[10px] text-fg-subtle">{ci.case_key ?? "—"}</span>
                    </td>
                    <td className="px-3 py-2.5">
                      <p className="line-clamp-1 text-[13px] text-fg-muted">{ci.title ?? rc.case_id}</p>
                    </td>
                    <td className="w-24 px-3 py-2.5">
                      <span className="text-[11px] text-fg-subtle">{rd.label}</span>
                    </td>
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
