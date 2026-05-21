"use client";
import React from "react";

interface Column<T> {
  key: keyof T | string;
  header: string;
  width?: string;
  align?: "left" | "center" | "right";
  render?: (row: T, idx: number) => React.ReactNode;
}

interface DataGridProps<T> {
  columns: Column<T>[];
  rows: T[];
  keyField?: keyof T;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyState?: React.ReactNode;
}

export function DataGrid<T extends Record<string, unknown>>({
  columns, rows, keyField, onRowClick, loading, emptyState,
}: DataGridProps<T>) {
  const alignMap = { left: "text-left", center: "text-center", right: "text-right" };

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-slate-800">
            {columns.map(col => (
              <th
                key={String(col.key)}
                style={col.width ? { width: col.width } : undefined}
                className={`px-4 py-2.5 text-xs font-medium text-slate-400 ${alignMap[col.align ?? "left"]} whitespace-nowrap`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-slate-500 text-sm">
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-slate-600 border-t-blue-400 rounded-full animate-spin" />
                  Yükleniyor...
                </div>
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>
                {emptyState ?? (
                  <div className="px-4 py-12 text-center text-slate-500 text-sm">Kayıt bulunamadı</div>
                )}
              </td>
            </tr>
          ) : (
            rows.map((row, idx) => (
              <tr
                key={keyField ? String(row[keyField]) : idx}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`border-b border-slate-800 transition-colors ${onRowClick ? "cursor-pointer hover:bg-slate-800/60" : "hover:bg-slate-900/40"}`}
              >
                {columns.map(col => {
                  const align = alignMap[col.align ?? "left"];
                  const val = col.render
                    ? col.render(row, idx)
                    : String(row[col.key as keyof T] ?? "—");
                  return (
                    <td key={String(col.key)} className={`px-4 py-3 text-sm ${align}`}>
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
