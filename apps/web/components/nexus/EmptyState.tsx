"use client";
import React from "react";

type EmptyIconKey = "empty" | "folder" | "search" | "check" | "code" | "chart" | "clock" | "alert";

const ICONS: Record<EmptyIconKey, string> = {
  empty:  "M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4",
  folder: "M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z",
  search: "M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z",
  check:  "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  code:   "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4",
  chart:  "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  clock:  "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  alert:  "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
};

interface EmptyStateProps {
  /** SVG icon key ("folder", "search" vs.) ya da geriye uyumluluk için emoji string */
  icon?: EmptyIconKey | string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon = "empty", title, description, action }: EmptyStateProps) {
  const isSvgKey = Object.prototype.hasOwnProperty.call(ICONS, icon);

  return (
    <div data-testid="empty-state" className="flex flex-col items-center justify-center py-16 px-6 text-center">
      {isSvgKey ? (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-border bg-bg-subtle">
          <svg
            className="h-6 w-6 text-muted"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
            aria-hidden
          >
            <path strokeLinecap="round" strokeLinejoin="round" d={ICONS[icon as EmptyIconKey]} />
          </svg>
        </div>
      ) : (
        <div className="text-5xl mb-4" aria-hidden>{icon}</div>
      )}
      <h3 className="text-base font-semibold text-fg mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-slate-400 max-w-sm mb-4">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
