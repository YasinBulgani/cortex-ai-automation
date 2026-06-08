"use client";

import { useState } from "react";
import { copyToClipboard, friendlyError } from "@/lib/errors";

export default function ManagementError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const friendly = friendlyError(error);
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);

  const detail = friendly.detail ?? error.message ?? "";

  async function onCopy() {
    const ok = await copyToClipboard(
      `${detail}\n\n${error.digest ? `Digest: ${error.digest}` : ""}`.trim(),
    );
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  }

  return (
    <div
      className="flex min-h-[40vh] flex-col items-center justify-center gap-4 p-8 bg-surface"
      data-testid="management-error"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-red-500/20 bg-red-500/10">
        <svg
          className="w-6 h-6 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-fg">Bir hata oluştu</h2>
      <p className="max-w-md text-center text-sm text-fg">
        {friendly.message}
      </p>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-xl border border-border bg-surface-raised px-4 py-2 text-sm font-medium text-fg hover:border-border-strong hover:text-white transition-colors"
          data-testid="management-error-btn-retry"
        >
          Tekrar Dene
        </button>
        {detail && (
          <button
            type="button"
            onClick={() => setShowDetails((v) => !v)}
            className="rounded-xl border border-border bg-surface-base px-4 py-2 text-sm font-medium text-fg-muted hover:border-border hover:text-fg transition-colors"
            data-testid="management-error-btn-toggle-details"
          >
            {showDetails ? "Detayları gizle" : "Detayları göster"}
          </button>
        )}
      </div>

      {showDetails && detail && (
        <div className="w-full max-w-lg rounded-lg border border-border bg-surface-base/60 p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-[0.18em] text-fg-subtle">
              Teknik detay{" "}
              {error.digest ? `· ${error.digest.slice(0, 8)}` : ""}
            </span>
            <button
              type="button"
              onClick={() => void onCopy()}
              className="text-xs text-fg-muted underline hover:text-white transition-colors"
              data-testid="management-error-btn-copy"
            >
              {copied ? "Kopyalandı" : "Kopyala"}
            </button>
          </div>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words text-[11px] text-fg-muted">
            {detail}
          </pre>
        </div>
      )}
    </div>
  );
}
