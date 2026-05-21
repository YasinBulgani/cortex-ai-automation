"use client";

import { useState } from "react";

import { API_BASE, getToken } from "@/lib/api";

type ExportFormat = "markdown" | "csv" | "json" | "xlsx" | "pdf";

const FORMATS: { fmt: ExportFormat; label: string; ext: string }[] = [
  { fmt: "markdown", label: "Markdown (.md)", ext: "md" },
  { fmt: "csv", label: "CSV", ext: "csv" },
  { fmt: "json", label: "JSON", ext: "json" },
  { fmt: "xlsx", label: "Excel (.xlsx)", ext: "xlsx" },
  { fmt: "pdf", label: "PDF", ext: "pdf" },
];

type Props = {
  projectId: string;
  runId: string;
};

/**
 * Execution report export menu — F4.
 *
 * Backend: GET /api/v1/tspm/projects/{projectId}/executions/{runId}/export?format=...
 * Browser, returned Content-Disposition: attachment ile dosyayı otomatik indirir.
 */
export function ExportMenu({ projectId, runId }: Props) {
  const [open, setOpen] = useState(false);
  const [busyFmt, setBusyFmt] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  const download = async (fmt: ExportFormat) => {
    setBusyFmt(fmt);
    setError(null);
    try {
      const token = getToken();
      const res = await fetch(
        `${API_BASE}/api/v1/tspm/projects/${projectId}/executions/${runId}/export?format=${fmt}`,
        {
          credentials: "include",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        },
      );
      if (!res.ok) {
        if (res.status === 501) {
          const body = await res.json().catch(() => ({ detail: "" }));
          throw new Error(body.detail || `${fmt} desteği kurulu değil.`);
        }
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const disposition = res.headers.get("Content-Disposition") || "";
      const filename =
        /filename="?([^";]+)"?/i.exec(disposition)?.[1] ||
        `execution-${runId.slice(0, 8)}.${
          FORMATS.find((f) => f.fmt === fmt)?.ext ?? fmt
        }`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch (e: any) {
      setError(e?.message ?? "Dışa aktarma başarısız");
    } finally {
      setBusyFmt(null);
    }
  };

  return (
    <div className="relative" data-testid="export-menu">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500 transition"
        data-testid="export-menu-toggle"
      >
        ⬇ Dışa aktar
      </button>
      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            data-testid="export-menu-backdrop"
          />
          <div
            className="absolute right-0 top-9 z-50 w-56 rounded-lg border border-slate-700 bg-slate-900 py-1 shadow-xl"
            data-testid="export-menu-panel"
          >
            {FORMATS.map(({ fmt, label }) => (
              <button
                key={fmt}
                type="button"
                disabled={busyFmt !== null}
                onClick={() => download(fmt)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                data-testid={`export-menu-item-${fmt}`}
              >
                <span>{label}</span>
                {busyFmt === fmt && <span className="text-slate-500">…</span>}
              </button>
            ))}
            {error && (
              <p
                className="mx-3 mt-2 rounded border border-red-500/30 bg-red-500/10 px-2 py-1.5 text-[10px] text-red-300"
                data-testid="export-menu-error"
              >
                {error}
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
