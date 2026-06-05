"use client";

import React from "react";

interface State {
  hasError: boolean;
  message: string;
}

interface Props {
  children: React.ReactNode;
}

export class PageErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message =
      error instanceof Error ? error.message : "Bilinmeyen bir hata oluştu.";
    return { hasError: true, message };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    console.error("[PageErrorBoundary] Caught error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[320px] flex-col items-center justify-center gap-5 px-6 py-16">
          {/* Icon */}
          <div className="flex h-14 w-14 items-center justify-center rounded-full border border-red-500/25 bg-red-500/10">
            <svg
              className="h-6 w-6 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.8}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
          </div>

          {/* Text */}
          <div className="text-center space-y-1.5">
            <p className="text-[14px] font-semibold text-fg">Sayfa yüklenirken bir hata oluştu</p>
            {this.state.message && (
              <p className="text-[11px] text-fg-muted max-w-sm leading-relaxed">
                {this.state.message}
              </p>
            )}
          </div>

          {/* Reload button */}
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="flex items-center gap-2 rounded-xl border border-border bg-surface-raised px-5 py-2 text-[12px] font-medium text-fg-muted transition-colors hover:border-border-strong hover:text-fg"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Sayfayı Yenile
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
