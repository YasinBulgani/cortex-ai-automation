"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch } from "@/lib/api";

type Props = {
  projectId: string;
  runId: string;
  hasFailed: boolean;
};

/**
 * Failed-only re-run trigger — B14.
 *
 * Sadece eski koşumda başarısız olan senaryoları içeren yeni execution oluşturur.
 * `hasFailed=false` ise gri ve disabled.
 */
export function RerunFailedButton({ projectId, runId, hasFailed }: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onClick = async () => {
    if (!hasFailed) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch<{ id: string }>(
        `/api/v1/tspm/projects/${projectId}/executions/${runId}/rerun-failed`,
        { method: "POST" },
      );
      router.push(`/p/${projectId}/executions/${res.id}`);
    } catch (e: any) {
      setError(e?.message ?? "Re-run failed");
      setBusy(false);
    }
  };

  return (
    <div className="relative" data-testid="rerun-failed-button">
      <button
        type="button"
        onClick={onClick}
        disabled={!hasFailed || busy}
        title={
          hasFailed
            ? "Sadece başarısız senaryoları tekrar koş"
            : "Bu koşumda başarısız senaryo yok"
        }
        className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300 hover:bg-amber-500/20 transition disabled:opacity-30 disabled:cursor-not-allowed"
        data-testid="rerun-failed-toggle"
      >
        {busy ? "…" : "↻ Sadece başarısızlar"}
      </button>
      {error && (
        <p
          className="absolute right-0 top-9 z-10 rounded border border-red-500/30 bg-red-500/10 px-2 py-1 text-[10px] text-red-300 whitespace-nowrap"
          data-testid="rerun-failed-error"
        >
          {error}
        </p>
      )}
    </div>
  );
}
