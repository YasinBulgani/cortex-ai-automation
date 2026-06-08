"use client";

import Link from "next/link";

export interface WorkspaceEmptyStateProps {
  hasFilter: boolean;
  onClearFilters: () => void;
  onNewCase: () => void;
  projectId?: string;
}

export function WorkspaceEmptyState({
  hasFilter,
  onClearFilters,
  onNewCase,
  projectId,
}: WorkspaceEmptyStateProps) {
  if (hasFilter) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-surface-overlay">
          <svg className="h-6 w-6 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
          </svg>
        </div>
        <p className="text-[13px] font-medium text-fg-muted">Filtreyle eşleşen senaryo bulunamadı</p>
        <p className="text-[11px] text-fg-disabled max-w-xs">Arama teriminizi veya filtrelerinizi değiştirmeyi deneyin.</p>
        <button
          type="button"
          onClick={onClearFilters}
          className="mt-1 text-[12px] font-medium text-brand transition-colors hover:opacity-80"
        >
          Filtreleri temizle
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-20 gap-5 text-center px-8">
      {/* Illustration */}
      <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl border border-dashed border-border bg-surface-overlay">
        <svg className="h-9 w-9 text-fg-subtle/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
        </svg>
        <div className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full border border-brand/30 bg-brand-soft">
          <svg className="h-3 w-3 text-brand" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
        </div>
      </div>

      <div>
        <p className="text-[14px] font-semibold text-fg">Bu klasörde senaryo yok</p>
        <p className="mt-1 text-[12px] text-fg-muted max-w-xs">
          Test senaryolarını manuel olarak oluşturun, CSV ile içe aktarın ya da AI ile otomatik üretin.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          onClick={onNewCase}
          className="flex items-center gap-2 rounded-xl bg-brand px-4 py-2 text-[12px] font-semibold text-brand-fg shadow-sm transition-all hover:brightness-105"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4"/>
          </svg>
          Senaryo Ekle
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-2 text-center max-w-sm w-full">
        <button
          type="button"
          onClick={onNewCase}
          className="rounded-xl border border-border bg-surface-overlay px-2 py-3 transition-colors hover:border-brand/40 hover:bg-surface-accent"
        >
          <p className="text-[11px] font-mono font-semibold text-fg-muted">⌘N</p>
          <p className="mt-1 text-[10px] text-fg-disabled">Yeni senaryo</p>
        </button>
        {projectId ? (
          <Link
            href={`/p/${projectId}/management/import-export`}
            className="rounded-xl border border-border bg-surface-overlay px-2 py-3 transition-colors hover:border-brand/40 hover:bg-surface-accent"
          >
            <p className="text-[11px] font-mono font-semibold text-fg-muted">CSV</p>
            <p className="mt-1 text-[10px] text-fg-disabled">İçe aktar</p>
          </Link>
        ) : (
          <div className="rounded-xl border border-border bg-surface-overlay px-2 py-3">
            <p className="text-[11px] font-mono font-semibold text-fg-muted">CSV</p>
            <p className="mt-1 text-[10px] text-fg-disabled">İçe aktar</p>
          </div>
        )}
        <button
          type="button"
          onClick={onNewCase}
          className="rounded-xl border border-border bg-surface-overlay px-2 py-3 transition-colors hover:border-brand/40 hover:bg-surface-accent"
        >
          <p className="text-[11px] font-mono font-semibold text-fg-muted">✦ AI</p>
          <p className="mt-1 text-[10px] text-fg-disabled">AI ile üret</p>
        </button>
      </div>
    </div>
  );
}
