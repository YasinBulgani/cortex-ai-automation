"use client";

import * as React from "react";
import { cn } from "../utils/cn";
import { focusRing } from "../tokens/design-tokens";
import { Skeleton } from "../primitives/skeleton";
import { EmptyState } from "../primitives/empty-state";
import { Pagination } from "../primitives/pagination";

export type SortDirection = "asc" | "desc";

export interface SortState<TKey extends string = string> {
  key: TKey;
  direction: SortDirection;
}

export interface DataTableColumn<TRow, TKey extends string = string> {
  /** Benzersiz kolon kimliği (sort + row key için) */
  key: TKey;
  /** Header label */
  header: React.ReactNode;
  /** Hücreyi render et */
  cell: (row: TRow, index: number) => React.ReactNode;
  /** Sıralanabilir mi (default false) */
  sortable?: boolean;
  /** Sayısal/tarih sıralaması için karşılaştırma değeri */
  sortValue?: (row: TRow) => string | number | Date;
  /** Hücre hizalama */
  align?: "left" | "center" | "right";
  /** Kolon genişliği (CSS) */
  width?: string;
  /** Gizli (responsive) */
  hidden?: boolean;
  /** Header'a class */
  headerClassName?: string;
  /** Hücre class'ı */
  cellClassName?: string;
}

export interface DataTableProps<TRow, TKey extends string = string> {
  /** Veri satırları */
  data: ReadonlyArray<TRow>;
  /** Kolon tanımları */
  columns: ReadonlyArray<DataTableColumn<TRow, TKey>>;
  /** Satır key'i (React key + selection için) */
  rowKey: (row: TRow, index: number) => string;
  /** Yükleniyor durumu — skeleton göster */
  loading?: boolean;
  /** Skeleton kaç satır */
  skeletonRows?: number;
  /** Boş veri için — kullanıcı tanımlı EmptyState */
  empty?: React.ReactNode;
  /** Sıralama — controlled */
  sort?: SortState<TKey>;
  /** Sıralama değişiklik callback */
  onSortChange?: (sort: SortState<TKey> | undefined) => void;
  /** Default sıralama (uncontrolled) */
  defaultSort?: SortState<TKey>;
  /** Satıra tıklama */
  onRowClick?: (row: TRow, index: number) => void;
  /** Hover'da yükselme */
  interactive?: boolean;
  /** Compact yükseklik */
  dense?: boolean;
  /** Striped satırlar */
  striped?: boolean;
  /** Sticky header */
  stickyHeader?: boolean;
  /** Toplam satır sayısı (server-side pagination için) — verilmezse data.length */
  totalRows?: number;
  /** Sayfalama — verilirse alta gelir */
  pagination?: {
    page: number;
    pageSize: number;
    onPageChange: (page: number) => void;
  };
  className?: string;
  /** Tablo aria-label */
  label?: string;
}

export function DataTable<TRow, TKey extends string = string>({
  data,
  columns,
  rowKey,
  loading,
  skeletonRows = 5,
  empty,
  sort,
  defaultSort,
  onSortChange,
  onRowClick,
  interactive,
  dense,
  striped,
  stickyHeader,
  totalRows,
  pagination,
  className,
  label,
}: DataTableProps<TRow, TKey>) {
  const isSortControlled = sort !== undefined || onSortChange !== undefined;
  const [internalSort, setInternalSort] = React.useState<SortState<TKey> | undefined>(defaultSort);
  const activeSort = isSortControlled ? sort : internalSort;

  const setSort = (next: SortState<TKey> | undefined) => {
    if (!isSortControlled) setInternalSort(next);
    onSortChange?.(next);
  };

  const visibleColumns = columns.filter(c => !c.hidden);

  // Client-side sıralama (column.sortValue varsa)
  const sortedData = React.useMemo(() => {
    if (!activeSort) return data;
    const col = visibleColumns.find(c => c.key === activeSort.key);
    if (!col?.sortValue) return data;
    const sorted = [...data].sort((a, b) => {
      const va = col.sortValue!(a);
      const vb = col.sortValue!(b);
      if (va < vb) return activeSort.direction === "asc" ? -1 : 1;
      if (va > vb) return activeSort.direction === "asc" ? 1 : -1;
      return 0;
    });
    return sorted;
  }, [data, activeSort, visibleColumns]);

  const toggleSort = (key: TKey) => {
    if (!activeSort || activeSort.key !== key) {
      setSort({ key, direction: "asc" });
      return;
    }
    if (activeSort.direction === "asc") {
      setSort({ key, direction: "desc" });
      return;
    }
    setSort(undefined);
  };

  const cellPad = dense ? "px-3 py-1.5" : "px-4 py-2.5";
  const colCount = visibleColumns.length;

  return (
    <div className={cn("rounded-lg border border-border bg-surface-raised overflow-hidden", className)}>
      <div className={cn("overflow-x-auto", stickyHeader && "max-h-[60vh] overflow-y-auto")}>
        <table aria-label={label} className="w-full border-collapse text-sm">
          <thead className={cn("bg-surface-overlay text-fg-muted text-xs uppercase tracking-wide", stickyHeader && "sticky top-0 z-10")}>
            <tr>
              {visibleColumns.map(col => {
                const isSorted = activeSort?.key === col.key;
                const ariaSort: "ascending" | "descending" | "none" = isSorted
                  ? activeSort!.direction === "asc" ? "ascending" : "descending"
                  : "none";
                return (
                  <th
                    key={col.key}
                    scope="col"
                    aria-sort={col.sortable ? ariaSort : undefined}
                    style={col.width ? { width: col.width } : undefined}
                    className={cn(
                      "font-medium text-left whitespace-nowrap",
                      cellPad,
                      col.align === "right"  && "text-right",
                      col.align === "center" && "text-center",
                      col.headerClassName,
                    )}
                  >
                    {col.sortable ? (
                      <button
                        type="button"
                        onClick={() => toggleSort(col.key)}
                        className={cn(
                          "inline-flex items-center gap-1.5 select-none rounded hover:text-fg transition-colors",
                          focusRing,
                          isSorted && "text-fg",
                        )}
                      >
                        {col.header}
                        <SortIcon direction={isSorted ? activeSort!.direction : undefined} />
                      </button>
                    ) : (
                      col.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: skeletonRows }).map((_, i) => (
                <tr key={i} className="border-t border-border">
                  {visibleColumns.map(col => (
                    <td key={col.key} className={cellPad}>
                      <Skeleton className="h-3 w-3/4" noAnimation={false} />
                    </td>
                  ))}
                </tr>
              ))
            ) : sortedData.length === 0 ? (
              <tr>
                <td colSpan={colCount} className="p-0">
                  {empty ?? <EmptyState title="Veri yok" description="Listelenecek bir kayıt bulunamadı." />}
                </td>
              </tr>
            ) : (
              sortedData.map((row, index) => {
                const key = rowKey(row, index);
                return (
                  <tr
                    key={key}
                    onClick={onRowClick ? () => onRowClick(row, index) : undefined}
                    className={cn(
                      "border-t border-border",
                      striped && index % 2 === 1 && "bg-surface-overlay/30",
                      interactive && "hover:bg-surface-overlay cursor-pointer transition-colors",
                    )}
                  >
                    {visibleColumns.map(col => (
                      <td
                        key={col.key}
                        className={cn(
                          cellPad,
                          col.align === "right"  && "text-right",
                          col.align === "center" && "text-center",
                          col.cellClassName,
                        )}
                      >
                        {col.cell(row, index)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {pagination && (
        <div className="flex items-center justify-between gap-3 border-t border-border bg-surface-base/40 px-4 py-2 text-xs text-fg-muted">
          <span>
            Toplam {totalRows ?? data.length} kayıt
          </span>
          <Pagination
            page={pagination.page}
            totalPages={Math.max(1, Math.ceil((totalRows ?? data.length) / pagination.pageSize))}
            onPageChange={pagination.onPageChange}
          />
        </div>
      )}
    </div>
  );
}

function SortIcon({ direction }: { direction?: SortDirection }) {
  return (
    <span aria-hidden className="text-fg-subtle inline-block w-2.5 text-center">
      {direction === "asc" ? "▲" : direction === "desc" ? "▼" : "⇅"}
    </span>
  );
}
