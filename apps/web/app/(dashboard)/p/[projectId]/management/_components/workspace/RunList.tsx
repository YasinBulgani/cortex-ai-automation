"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import { useManagementRuns, type TestRun } from "@/lib/hooks/use-management";
import { RUN_STATUS_DOT, RUN_STATUS_LABEL, IcPlus } from "./shared";

function RunItem({ run, selected, onSelect }: { run: TestRun; selected: boolean; onSelect: () => void }) {
  const status = run.status || "not_started";
  return (
    <button type="button" onClick={onSelect}
      className={cn("flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left transition-colors",
        selected ? "bg-brand-soft text-brand shadow-xs" : "text-fg-muted hover:bg-surface-overlay hover:text-fg")}>
      <span className={cn("mt-1 h-1.5 w-1.5 shrink-0 rounded-full", RUN_STATUS_DOT[status] ?? "bg-slate-600")} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] leading-snug">{run.name}</p>
        <p className="text-[10px] text-fg-subtle">
          {RUN_STATUS_LABEL[status] ?? status}{run.environment ? ` · ${run.environment}` : ""}
        </p>
      </div>
    </button>
  );
}

export function RunList({ pid, selectedRunId, onSelect, onNewRun }: {
  pid: string; selectedRunId: string | null; onSelect: (id: string) => void; onNewRun: () => void;
}) {
  const { data: runs, isLoading } = useManagementRuns(pid || undefined);
  const all = useMemo(() => runs ?? [], [runs]);

  const groups = useMemo(() => {
    const active = all.filter(r => r.status === "in_progress");
    const pending = all.filter(r => r.status === "not_started" || !r.status);
    const done = all.filter(r => r.status === "completed" || r.status === "failed");
    return [
      { key: "active", label: "Devam Eden", items: active },
      { key: "pending", label: "Bekleyen", items: pending },
      { key: "done", label: "Tamamlanan", items: done },
    ].filter(g => g.items.length > 0);
  }, [all]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
        <span className="text-[12px] font-semibold text-fg">Test Runs</span>
        <button type="button" onClick={onNewRun}
          className="flex items-center gap-1 rounded-lg bg-brand px-2 py-1 text-[11px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
          <IcPlus /> Yeni
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-10 rounded-lg bg-surface-overlay animate-pulse" style={{ opacity: Math.max(0.2, 1 - i * 0.12) }} />
          ))
        ) : all.length === 0 ? (
          <div className="px-2 py-8 text-center">
            <p className="text-[12px] font-medium text-fg-muted">Henüz run yok</p>
            <button type="button" onClick={onNewRun} className="mt-2 text-[11px] font-medium text-brand hover:text-brand-secondary">
              İlk run'ı oluştur →
            </button>
          </div>
        ) : (
          groups.map(g => (
            <div key={g.key}>
              <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">
                {g.label} <span className="text-fg-disabled">({g.items.length})</span>
              </p>
              <div className="space-y-0.5">
                {g.items.map(run => (
                  <RunItem key={run.id} run={run} selected={selectedRunId === run.id} onSelect={() => onSelect(run.id)} />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="border-t border-border px-4 py-2 text-[10px] text-fg-subtle">{all.length} run</div>
    </div>
  );
}
