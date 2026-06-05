"use client";

import { cn } from "@/lib/utils";

// ─── Run filter state types ───────────────────────────────────────────────────

export type RunStatusFilter = "" | "not_started" | "in_progress" | "completed";
export type RunDateFilter   = "" | "today" | "week" | "month";

export interface RunFilters {
  search:    string;
  status:    RunStatusFilter;
  dateRange: RunDateFilter;
}

// ─── Run Tab mini header ──────────────────────────────────────────────────────

export function RunTabHeader({
  onNewRun,
  filters,
  onFiltersChange,
  totalCount,
  filteredCount,
}: {
  onNewRun: () => void;
  filters: RunFilters;
  onFiltersChange: (f: RunFilters) => void;
  totalCount: number;
  filteredCount: number;
}) {
  const SEL = "h-8 rounded-lg border border-border bg-surface-raised px-2.5 text-[11px] font-medium text-fg-muted outline-none transition-colors cursor-pointer hover:border-border-strong focus:border-brand focus:ring-2 focus:ring-brand/15";
  const hasFilter = !!(filters.search || filters.status || filters.dateRange);
  const activeFilterCount = [filters.search, filters.status, filters.dateRange].filter(Boolean).length;

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface-raised px-4 py-3 shadow-xs">
      <span className="text-[14px] font-semibold text-fg">Test Koşumları</span>

      {/* Filtered count badge */}
      <span className="rounded-full border border-border bg-surface-overlay px-2 py-0.5 text-[10px] font-medium tabular-nums text-fg-muted">
        {hasFilter ? `${filteredCount}/${totalCount}` : totalCount}
      </span>

      <div className="flex-1" />

      {/* Search */}
      <div className="flex w-40 items-center gap-1.5 rounded-lg border border-border bg-surface-raised px-2.5 py-1.5 shadow-xs transition-colors focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/15">
        <svg className="h-3.5 w-3.5 shrink-0 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <input
          type="text"
          value={filters.search}
          onChange={e => onFiltersChange({ ...filters, search: e.target.value })}
          placeholder="Run ara…"
          className="flex-1 bg-transparent text-[11px] text-fg placeholder:text-fg-subtle outline-none min-w-0"
        />
      </div>

      {/* Status filter */}
      <select
        value={filters.status}
        onChange={e => onFiltersChange({ ...filters, status: e.target.value as RunStatusFilter })}
        className={SEL}
      >
        <option value="">Durum</option>
        <option value="not_started">Bekleyen</option>
        <option value="in_progress">Devam Eden</option>
        <option value="completed">Tamamlanan</option>
      </select>

      {/* Date range filter */}
      <select
        value={filters.dateRange}
        onChange={e => onFiltersChange({ ...filters, dateRange: e.target.value as RunDateFilter })}
        className={SEL}
      >
        <option value="">Tarih</option>
        <option value="today">Bugün</option>
        <option value="week">Bu hafta</option>
        <option value="month">Bu ay</option>
      </select>

      {/* Clear filters */}
      {hasFilter && (
        <button
          type="button"
          onClick={() => onFiltersChange({ search: "", status: "", dateRange: "" })}
          title="Filtreleri temizle"
          className="relative inline-flex items-center justify-center h-6 w-6 rounded-full bg-red-500/15 border border-red-500/25 text-red-400 transition-colors hover:bg-red-500/25"
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

      <button type="button" onClick={onNewRun}
        className="rounded-lg bg-brand px-3 py-1.5 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105">
        + Yeni Koşum
      </button>
    </div>
  );
}
