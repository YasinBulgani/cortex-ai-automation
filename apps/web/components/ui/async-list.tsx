"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface AsyncListProps<T> {
  data: T[] | undefined;
  isLoading: boolean;
  emptyText: string;
  emptyAction?: React.ReactNode;
  skeletonCount?: number;
  skeletonHeight?: string;
  children: (items: T[]) => React.ReactNode;
  className?: string;
}

/**
 * Management sayfalarında tekrar eden loading → empty → list üçlüsünü
 * tek bir bileşene indirger.
 *
 * Kullanım:
 *   <AsyncList data={plans} isLoading={isLoading} emptyText="Henüz plan yok">
 *     {(items) => items.map(p => <PlanCard key={p.id} plan={p} />)}
 *   </AsyncList>
 */
export function AsyncList<T>({
  data,
  isLoading,
  emptyText,
  emptyAction,
  children,
  className,
  skeletonCount = 3,
  skeletonHeight = "h-10",
}: AsyncListProps<T>) {
  if (isLoading) {
    return (
      <div className={cn("space-y-2 p-4", className)}>
        {Array.from({ length: skeletonCount }, (_, i) => (
          <div
            key={i}
            className={cn("animate-pulse rounded-lg bg-surface-accent", skeletonHeight)}
            style={{ opacity: Math.max(0.45, 1 - i * 0.08) }}
          />
        ))}
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className={cn("flex flex-col items-center justify-center gap-3 px-4 py-20 text-center", className)}>
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border bg-surface-overlay text-fg-subtle">
          <span className="h-2 w-2 rounded-full bg-brand" />
        </div>
        <p className="max-w-sm text-[13px] font-medium text-fg-muted">{emptyText}</p>
        {emptyAction}
      </div>
    );
  }

  return <>{children(data)}</>;
}
