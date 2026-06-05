"use client";

export interface WorkspaceEmptyStateProps {
  hasFilter: boolean;
  onClearFilters: () => void;
  onNewCase: () => void;
}

export function WorkspaceEmptyState({
  hasFilter,
  onClearFilters,
  onNewCase,
}: WorkspaceEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-3">
      {hasFilter ? (
        <>
          <p className="text-[13px] font-medium text-fg-muted">Sonuç bulunamadı</p>
          <button
            type="button"
            onClick={onClearFilters}
            className="text-[12px] font-medium text-brand transition-colors hover:text-brand-secondary"
          >
            Filtreleri temizle
          </button>
        </>
      ) : (
        <>
          <p className="text-[13px] font-medium text-fg-muted">Bu bölümde senaryo yok</p>
          <button
            type="button"
            onClick={onNewCase}
            className="rounded-lg bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-colors hover:brightness-105"
          >
            + İlk senaryoyu ekle
          </button>
        </>
      )}
    </div>
  );
}
