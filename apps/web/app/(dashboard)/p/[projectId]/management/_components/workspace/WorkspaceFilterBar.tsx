"use client";

import { cn } from "@/lib/utils";

const SEL_CLS =
  "h-8 rounded-lg border border-border bg-surface-raised px-2.5 text-[11px] font-medium text-fg-muted outline-none transition-colors cursor-pointer hover:border-border-strong focus:border-brand focus:ring-2 focus:ring-brand/15";

function IcSearch() {
  return (
    <svg
      className="h-3.5 w-3.5 shrink-0 text-fg-subtle"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  );
}

export interface WorkspaceFilterBarProps {
  nodeName: string;
  totalCount: number;
  filteredCount: number;
  hasFilter: boolean;
  search: string;
  priority: string;
  type: string;
  status: string;
  activeFilterCount: number;
  showArchived: boolean;
  archivedCount: number;
  failedCount: number;
  blockedCount: number;
  onSearchChange: (v: string) => void;
  onPriorityChange: (v: string) => void;
  onTypeChange: (v: string) => void;
  onStatusChange: (v: string) => void;
  onToggleArchived: () => void;
  onClearAll: () => void;
  onNewCase: () => void;
}

export function WorkspaceFilterBar({
  nodeName,
  totalCount,
  filteredCount,
  hasFilter,
  search,
  priority,
  type,
  status,
  activeFilterCount,
  showArchived,
  archivedCount,
  failedCount,
  blockedCount,
  onSearchChange,
  onPriorityChange,
  onTypeChange,
  onStatusChange,
  onToggleArchived,
  onClearAll,
  onNewCase,
}: WorkspaceFilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-raised px-4 py-3 shadow-xs">
      {/* Section name + count */}
      <span className="mr-1 text-[14px] font-semibold text-fg">{nodeName}</span>
      <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] font-medium tabular-nums text-fg-muted">
        {filteredCount}
        {hasFilter && `/${totalCount}`}
      </span>

      {/* Quick filters */}
      {failedCount > 0 && (
        <button
          type="button"
          onClick={() => onStatusChange(status === "failed" ? "" : "failed")}
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
            status === "failed"
              ? "bg-red-500/15 border-red-500/30 text-red-400"
              : "border-red-500/20 text-red-500/60 hover:text-red-400",
          )}
        >
          {failedCount} fail
        </button>
      )}
      {blockedCount > 0 && (
        <button
          type="button"
          onClick={() => onStatusChange(status === "blocked" ? "" : "blocked")}
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
            status === "blocked"
              ? "bg-amber-500/15 border-amber-500/30 text-amber-400"
              : "border-amber-500/20 text-amber-500/60 hover:text-amber-400",
          )}
        >
          {blockedCount} blk
        </button>
      )}

      {/* Archived toggle */}
      {archivedCount > 0 && (
        <button
          type="button"
          onClick={onToggleArchived}
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-medium transition-colors",
            showArchived
              ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
              : "border-border text-fg-subtle hover:text-fg",
          )}
        >
          {showArchived ? "Arşivi Gizle" : `Arşiv (${archivedCount})`}
        </button>
      )}

      <div className="flex-1" />

      {/* Search + active filter badge */}
      <div className="flex items-center gap-1.5">
        <div className="flex w-44 items-center gap-1.5 rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 shadow-xs transition-colors focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
          <IcSearch />
          <input
            type="text"
            value={search}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="Ara…"
            className="flex-1 bg-transparent text-[11px] text-fg placeholder:text-fg-subtle outline-none min-w-0"
          />
        </div>
        {activeFilterCount > 0 && (
          <span className="rounded-full bg-brand px-2 py-0.5 text-[10px] font-semibold text-brand-fg">
            {activeFilterCount}
          </span>
        )}
      </div>

      {/* Filters */}
      <select value={priority} onChange={e => onPriorityChange(e.target.value)} className={SEL_CLS}>
        <option value="">Öncelik</option>
        {["P0", "P1", "P2", "P3"].map(v => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
      <select value={type} onChange={e => onTypeChange(e.target.value)} className={cn(SEL_CLS, "hidden lg:block")}>
        <option value="">Tür</option>
        {["manual", "smoke", "regression", "uat", "exploratory", "api", "e2e"].map(v => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
      <select value={status} onChange={e => onStatusChange(e.target.value)} className={SEL_CLS}>
        <option value="">Koşum</option>
        {["passed", "failed", "blocked", "skipped"].map(v => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
      {hasFilter && (
        <button
          type="button"
          onClick={onClearAll}
          title="Filtreleri temizle"
          className="relative inline-flex items-center justify-center h-6 w-6 rounded-full bg-red-500/15 border border-red-500/25 text-red-400 transition-colors hover:bg-red-500/25 hover:border-red-500/40"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2 2l8 8M10 2l-8 8" />
          </svg>
          {activeFilterCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-red-500 text-[8px] font-bold text-white leading-none">
              {activeFilterCount}
            </span>
          )}
        </button>
      )}

      {/* Add case */}
      <button
        type="button"
        onClick={onNewCase}
        className="flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
      >
        + Senaryo
      </button>
    </div>
  );
}
