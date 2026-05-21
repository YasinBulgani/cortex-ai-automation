"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { copyToClipboard, friendlyError } from "@/lib/errors";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  showDetails: boolean;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, showDetails: false, copied: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, showDetails: false, copied: false };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Üretimde Sentry tarafından otomatik yakalanır; yerel log operasyonel destek.
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught:", {
      error,
      componentStack: errorInfo.componentStack,
    });
  }

  private async handleCopy(text: string) {
    const ok = await copyToClipboard(text);
    if (ok) {
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2500);
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      const friendly = friendlyError(this.state.error);
      const detail = friendly.detail ?? this.state.error?.message ?? "";

      return (
        <div
          className="flex min-h-[300px] flex-col items-center justify-center gap-4 rounded-lg border border-slate-800 p-8"
          data-testid="error-boundary"
          role="alert"
          aria-live="assertive"
        >
          <svg className="h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          <h3 className="text-lg font-semibold">{friendly.title}</h3>
          <p className="max-w-md text-center text-sm text-slate-300">{friendly.message}</p>

          <div className="flex gap-2">
            <Button
              onClick={() => this.setState({ hasError: false, error: null, showDetails: false })}
              data-testid="error-boundary-btn-retry"
            >
              Tekrar Dene
            </Button>
            {detail && (
              <Button
                variant="outline"
                onClick={() => this.setState((s) => ({ showDetails: !s.showDetails }))}
                data-testid="error-boundary-btn-toggle-details"
              >
                {this.state.showDetails ? "Detayları gizle" : "Detayları göster"}
              </Button>
            )}
          </div>

          {this.state.showDetails && detail && (
            <div className="w-full max-w-lg rounded-lg border border-slate-800 bg-slate-950/60 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-[0.18em] text-slate-500">
                  Teknik detay
                </span>
                <button
                  type="button"
                  onClick={() => void this.handleCopy(detail)}
                  className="text-xs text-slate-400 underline hover:text-white transition-colors"
                  data-testid="error-boundary-btn-copy"
                >
                  {this.state.copied ? "Kopyalandı" : "Kopyala"}
                </button>
              </div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-400">
                {detail}
              </pre>
            </div>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
