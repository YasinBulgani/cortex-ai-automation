"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  cell?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  emptyMessage?: string;
  emptyState?: React.ReactNode;
  pageSize?: number;
  className?: string;
  filterValue?: string;
  filterKeys?: (keyof T)[];
  onRowClick?: (row: T) => void;
}

type SortDir = "asc" | "desc" | null;

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  loading = false,
  emptyMessage = "Veri bulunamadı",
  emptyState,
  pageSize = 20,
  className,
  filterValue = "",
  filterKeys = [],
  onRowClick,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = React.useState<string | null>(null);
  const [sortDir, setSortDir] = React.useState<SortDir>(null);
  const [page, setPage] = React.useState(1);

  const filtered = React.useMemo(() => {
    if (!filterValue || filterKeys.length === 0) return data;
    const q = filterValue.toLowerCase();
    return data.filter((row) =>
      filterKeys.some((k) => String(row[k] ?? "").toLowerCase().includes(q))
    );
  }, [data, filterValue, filterKeys]);

  const sorted = React.useMemo(() => {
    if (!sortKey || !sortDir) return filtered;
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      const cmp = String(av).localeCompare(String(bv), "tr", { numeric: true });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const paginated = sorted.slice((page - 1) * pageSize, page * pageSize);

  React.useEffect(() => setPage(1), [filterValue, sortKey, sortDir]);

  function toggleSort(key: string) {
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir("asc");
    } else if (sortDir === "asc") {
      setSortDir("desc");
    } else {
      setSortKey(null);
      setSortDir(null);
    }
  }

  const getCellValue = (row: T, col: Column<T>): React.ReactNode => {
    if (col.cell) return col.cell(row);
    return String(row[col.key as keyof T] ?? "");
  };

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/40">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800">
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className={cn(
                    "px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-400",
                    col.sortable && "cursor-pointer select-none hover:text-white",
                    col.className
                  )}
                  onClick={() => col.sortable && toggleSort(String(col.key))}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable && (
                      <span className="text-xs opacity-50">
                        {sortKey === String(col.key) ? (sortDir === "asc" ? "↑" : "↓") : "↕"}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-slate-800 last:border-0">
                  {columns.map((col) => (
                    <td key={String(col.key)} className="px-4 py-3">
                      <div className="h-4 w-3/4 animate-pulse rounded bg-slate-800" />
                    </td>
                  ))}
                </tr>
              ))
            ) : paginated.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-slate-500">
                  {emptyState ?? emptyMessage}
                </td>
              </tr>
            ) : (
              paginated.map((row, i) => (
                <tr
                  key={i}
                  className={cn(
                    "border-b border-slate-800 last:border-0 transition-colors",
                    onRowClick ? "cursor-pointer hover:bg-slate-800/60" : "hover:bg-slate-900/60"
                  )}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((col) => (
                    <td key={String(col.key)} className={cn("px-4 py-3", col.className)}>
                      {getCellValue(row, col)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>
            {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, sorted.length)} / {sorted.length} kayıt
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page === 1}
              className="rounded-lg px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
            >
              «
            </button>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
            >
              ‹
            </button>
            <span className="px-2 text-slate-300">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded-lg px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
            >
              ›
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page === totalPages}
              className="rounded-lg px-2 py-1 hover:bg-slate-800 disabled:opacity-40"
            >
              »
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
