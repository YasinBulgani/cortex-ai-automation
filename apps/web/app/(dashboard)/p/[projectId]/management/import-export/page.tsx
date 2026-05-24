"use client";

import { useState } from "react";
import {
  useManagementImports,
  useManagementImportDetail,
  useCreateManagementImportJob,
  useCommitImportJob,
  type ImportJob,
  type ImportJobRow,
} from "@/lib/hooks/use-management";
import { ManagementPanel, ManagementShell, ManagementStat } from "../_components/ManagementShell";

// ── Row status badge ──────────────────────────────────────────────────────────

const ROW_STATUS_STYLES: Record<string, string> = {
  ready:               "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  new:                 "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  duplicate_candidate: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  conflict:            "bg-rose-500/10 text-rose-400 border border-rose-500/20",
  invalid:             "bg-red-500/10 text-red-400 border border-red-500/20",
};

function RowStatusBadge({ status }: { status: string }) {
  const cls = ROW_STATUS_STYLES[status] ?? "bg-slate-700 text-slate-300";
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {status.replace("_", " ")}
    </span>
  );
}

// ── Import job status badge ───────────────────────────────────────────────────

const JOB_STATUS_STYLES: Record<string, string> = {
  preview:   "bg-blue-500/10 text-blue-400",
  committed: "bg-emerald-500/10 text-emerald-400",
  failed:    "bg-rose-500/10 text-rose-400",
};

// ── Detail panel for one import job ──────────────────────────────────────────

function ImportJobDetailPanel({
  jobId,
  projectId,
  onClose,
}: {
  jobId: string;
  projectId: string;
  onClose: () => void;
}) {
  const { data: job, isLoading } = useManagementImportDetail(projectId, jobId);
  const commitMutation = useCommitImportJob(projectId);
  const [committing, setCommitting] = useState(false);

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
      </div>
    );
  }
  if (!job) return null;

  const rows = job.rows ?? [];
  const readyRows = rows.filter((r) => ["ready", "new"].includes(r.status)).length;
  const conflictRows = rows.filter((r) => r.status === "conflict").length;
  const invalidRows = rows.filter((r) => r.status === "invalid").length;

  const handleCommit = async () => {
    setCommitting(true);
    try {
      await commitMutation.mutateAsync(jobId);
    } finally {
      setCommitting(false);
    }
  };

  return (
    <ManagementPanel title={`Import Preview: ${job.filename}`}>
      {/* Summary row */}
      <div className="mb-4 flex flex-wrap gap-4 text-sm">
        <span className="text-slate-400">
          <strong className="text-emerald-400">{readyRows}</strong> ready to import
        </span>
        <span className="text-slate-400">
          <strong className="text-amber-400">{conflictRows}</strong> conflicts
        </span>
        <span className="text-slate-400">
          <strong className="text-rose-400">{invalidRows}</strong> invalid
        </span>
        <span
          className={`ml-auto rounded-full px-2 py-0.5 text-xs font-medium ${
            JOB_STATUS_STYLES[job.status] ?? "bg-slate-700 text-slate-300"
          }`}
        >
          {job.status}
        </span>
      </div>

      {/* Row table */}
      <div className="overflow-x-auto rounded-lg border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-950 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 text-left">Row</th>
              <th className="px-3 py-2 text-left">Title / Data</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2 text-left">Errors</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-center text-slate-500">
                  Satır yok
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-900/50">
                  <td className="px-3 py-2 font-mono text-xs text-slate-500">{row.row_no}</td>
                  <td className="max-w-xs px-3 py-2 truncate text-slate-200">
                    {(row.parsed_data as { title?: string })?.title ??
                      JSON.stringify(row.parsed_data).slice(0, 60)}
                  </td>
                  <td className="px-3 py-2">
                    <RowStatusBadge status={row.status} />
                    {row.conflict_key && (
                      <span className="ml-2 text-xs text-amber-500">{row.conflict_key}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-rose-400">
                    {row.validation_errors.length > 0
                      ? row.validation_errors.map((e) => String((e as { msg?: string }).msg ?? e)).join(", ")
                      : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="mt-4 flex items-center justify-between">
        <button
          onClick={onClose}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
        >
          ← Listeye dön
        </button>
        {job.status === "preview" && (
          <button
            onClick={handleCommit}
            disabled={committing || readyRows === 0}
            className="rounded-lg bg-teal-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:opacity-40"
          >
            {committing ? "Commit ediliyor…" : `${readyRows} satırı Commit Et`}
          </button>
        )}
        {job.status === "committed" && (
          <span className="text-sm text-emerald-400">✓ Commit tamamlandı</span>
        )}
      </div>
    </ManagementPanel>
  );
}

// ── CSV parse helper ──────────────────────────────────────────────────────────

function parseCsvRows(text: string): Record<string, unknown>[] {
  const lines = text.trim().split("\n");
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
  return lines.slice(1).map((line) => {
    const vals = line.split(",").map((v) => v.trim().replace(/^"|"$/g, ""));
    const row: Record<string, unknown> = {};
    headers.forEach((h, i) => { row[h] = vals[i] ?? ""; });
    return row;
  });
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementImportExportPage({
  params,
}: {
  params: { projectId: string };
}) {
  const { projectId } = params;
  const importsQuery = useManagementImports(projectId);
  const createJob    = useCreateManagementImportJob(projectId);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);

  const jobs = importsQuery.data ?? [];

  const pendingJobs   = jobs.filter((j) => j.status === "preview").length;
  const committedJobs = jobs.filter((j) => j.status === "committed").length;

  // ── File upload handler ──

  const handleFile = async (file: File) => {
    setUploading(true);
    try {
      const text = await file.text();
      let rows: Record<string, unknown>[] = [];
      if (file.name.endsWith(".csv")) {
        rows = parseCsvRows(text);
      } else {
        try { rows = JSON.parse(text); } catch { rows = []; }
      }
      await createJob.mutateAsync({ filename: file.name, rows });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
  };

  if (selectedJobId) {
    return (
      <ManagementShell
        projectId={projectId}
        title="Import Preview"
        description="Satır bazlı validation, conflict preview ve commit akışı."
        active="management/import-export"
      >
        <ImportJobDetailPanel
          jobId={selectedJobId}
          projectId={projectId}
          onClose={() => setSelectedJobId(null)}
        />
      </ManagementShell>
    );
  }

  return (
    <ManagementShell
      projectId={projectId}
      title="Import / Export"
      description="Excel/CSV staging, satır bazlı validation, duplicate/conflict preview ve repository export akışı."
      active="management/import-export"
    >
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <ManagementStat
          label="Import Jobs"
          value={String(jobs.length)}
          note={`${pendingJobs} preview bekliyor`}
        />
        <ManagementStat
          label="Committed"
          value={String(committedJobs)}
          note="repository'ye yazıldı"
        />
        <ManagementStat
          label="Formats"
          value="CSV / JSON"
          note="Excel desteği yakında"
        />
      </div>

      {/* Upload zone */}
      <div className="mt-6">
        <ManagementPanel title="Yeni İçe Aktarma">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition ${
              dragOver
                ? "border-teal-400 bg-teal-500/5"
                : "border-slate-700 hover:border-slate-600"
            }`}
          >
            <svg className="mb-3 h-8 w-8 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="mb-1 text-sm text-slate-300">CSV veya JSON dosyası sürükleyin</p>
            <p className="text-xs text-slate-500 mb-3">veya</p>
            <label className="cursor-pointer rounded-lg bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700">
              {uploading ? "Yükleniyor…" : "Dosya Seç"}
              <input
                type="file"
                accept=".csv,.json"
                className="hidden"
                onChange={handleInputChange}
                disabled={uploading}
              />
            </label>
            <p className="mt-3 text-xs text-slate-600">
              CSV sütunları: title, priority, type, status, case_key (opsiyonel)
            </p>
          </div>
        </ManagementPanel>
      </div>

      {/* Job list */}
      <div className="mt-6">
        <ManagementPanel title="Import Geçmişi">
          {importsQuery.isLoading ? (
            <div className="flex h-16 items-center justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
            </div>
          ) : jobs.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-500">Henüz import job yok.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-slate-800 text-xs text-slate-500">
                  <tr>
                    <th className="pb-2 text-left">Dosya</th>
                    <th className="pb-2 text-left">Durum</th>
                    <th className="pb-2 text-left">Satırlar</th>
                    <th className="pb-2 text-left">Tarih</th>
                    <th className="pb-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-900/50">
                      <td className="py-2.5 pr-4 text-slate-200">{job.filename}</td>
                      <td className="py-2.5 pr-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                            JOB_STATUS_STYLES[job.status] ?? "bg-slate-700 text-slate-300"
                          }`}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 text-slate-400">
                        {(job.totals as { rows?: number }).rows ?? "—"}
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-slate-500">
                        {new Date(job.created_at).toLocaleDateString("tr-TR")}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => setSelectedJobId(job.id)}
                          className="rounded px-3 py-1 text-xs text-teal-400 hover:bg-slate-800"
                        >
                          {job.status === "preview" ? "Preview →" : "Detay →"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ManagementPanel>
      </div>
    </ManagementShell>
  );
}
