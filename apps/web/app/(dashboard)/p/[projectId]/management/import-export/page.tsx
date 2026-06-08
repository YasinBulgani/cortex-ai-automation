"use client";

import { useMemo, useState } from "react";
// xlsx dinamik yükleme — dosya parse fonksiyonu çağrıldığında (~1MB) yüklenir
import {
  useManagementImports,
  useManagementImportDetail,
  useCreateManagementImportJob,
  useCommitImportJob,
  exportManagementRepository,
} from "@/lib/hooks/use-management";
import { useManagementProjectId } from "@/lib/hooks/use-management-project-id";
import { useRouteParam } from "@/lib/use-route-param";

type ColumnKey =
  | "case_key"
  | "title"
  | "suite"
  | "folder"
  | "priority"
  | "severity"
  | "type"
  | "status"
  | "owner"
  | "tags"
  | "preconditions"
  | "steps"
  | "expected_result"
  | "objective"
  | "ignore";

type StagedImport = {
  filename: string;
  fileSize: number;
  headers: string[];
  rows: Record<string, unknown>[];
};

type ValidationIssue = {
  rowNo: number;
  field: string;
  message: string;
};

type LocalPreviewStatus = "ready" | "invalid" | "duplicate_candidate";

const COLUMN_OPTIONS: { key: ColumnKey; label: string; required?: boolean }[] = [
  { key: "ignore", label: "Ignore" },
  { key: "case_key", label: "Case Key" },
  { key: "title", label: "Title", required: true },
  { key: "suite", label: "Suite" },
  { key: "folder", label: "Folder" },
  { key: "priority", label: "Priority" },
  { key: "severity", label: "Severity" },
  { key: "type", label: "Type" },
  { key: "status", label: "Status" },
  { key: "owner", label: "Owner" },
  { key: "tags", label: "Tags" },
  { key: "preconditions", label: "Preconditions" },
  { key: "steps", label: "Steps" },
  { key: "expected_result", label: "Expected Result" },
  { key: "objective", label: "Objective" },
];

const REQUIRED_COLUMNS: ColumnKey[] = ["title"];

const TEMPLATE_COLUMNS = [
  "case_key",
  "title",
  "suite",
  "folder",
  "priority",
  "severity",
  "type",
  "status",
  "tags",
  "preconditions",
  "steps",
  "expected_result",
];

// ── Row status badge ──────────────────────────────────────────────────────────

const ROW_STATUS_STYLES: Record<string, string> = {
  ready:               "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  new:                 "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  duplicate_candidate: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  conflict:            "bg-red-500/10 text-red-400 border border-red-500/20",
  invalid:             "bg-red-500/10 text-red-400 border border-red-500/20",
};

function RowStatusBadge({ status }: { status: string }) {
  const cls = ROW_STATUS_STYLES[status] ?? "bg-surface-accent text-fg";
  const label = status.replace("_", " ");
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

// ── Import job status badge ───────────────────────────────────────────────────

const JOB_STATUS_STYLES: Record<string, string> = {
  preview:   "bg-blue-500/10 text-blue-400",
  committed: "bg-emerald-500/10 text-emerald-400",
  failed:    "bg-red-500/10 text-red-400",
};

function JobStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
        JOB_STATUS_STYLES[status] ?? "bg-surface-accent text-fg"
      }`}
    >
      {status}
    </span>
  );
}

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
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-teal-400" />
      </div>
    );
  }
  if (!job) return null;

  const rows = job.rows ?? [];
  const readyRows = rows.filter((r) => ["ready", "new"].includes(r.status)).length;
  const duplicateRows = rows.filter((r) => r.status === "duplicate_candidate").length;
  const conflictRows = rows.filter((r) => r.status === "conflict").length;
  const invalidRows = rows.filter((r) => r.status === "invalid").length;
  const checkedRows = rows.length;
  const blockedRows = conflictRows + invalidRows;

  const handleCommit = async () => {
    setCommitting(true);
    try {
      await commitMutation.mutateAsync(jobId);
    } finally {
      setCommitting(false);
    }
  };

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-5">
      <div className="mb-5 grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-border bg-bg p-3">
          <p className="text-xs uppercase text-fg-subtle">Dry-run checked</p>
          <p className="mt-1 text-xl font-semibold text-white">{checkedRows}</p>
        </div>
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
          <p className="text-xs uppercase text-emerald-300/70">Ready</p>
          <p className="mt-1 text-xl font-semibold text-emerald-300">{readyRows}</p>
        </div>
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <p className="text-xs uppercase text-amber-300/70">Duplicates</p>
          <p className="mt-1 text-xl font-semibold text-amber-300">{duplicateRows + conflictRows}</p>
        </div>
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
          <p className="text-xs uppercase text-red-300/70">Blocked</p>
          <p className="mt-1 text-xl font-semibold text-red-300">{blockedRows}</p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-fg-muted">
        <JobStatusBadge status={job.status} />
        <span>
          Mapping:{" "}
          <span className="text-fg">
            {Object.keys(job.mapping ?? {}).length > 0 ? "saved with job" : "backend default"}
          </span>
        </span>
        <span className="text-fg-disabled">|</span>
        <span>Commit sadece validation sonrası preview job üzerinden çalışır.</span>
      </div>

      {/* Row table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg text-xs text-fg-subtle">
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
                <td colSpan={4} className="px-3 py-4 text-center text-fg-subtle">
                  Satır yok
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="hover:bg-surface-raised">
                  <td className="px-3 py-2 font-mono text-xs text-fg-subtle">{row.row_no}</td>
                  <td className="max-w-xs px-3 py-2 truncate text-fg">
                    {(row.parsed_data as { title?: string })?.title ??
                      JSON.stringify(row.parsed_data).slice(0, 60)}
                  </td>
                  <td className="px-3 py-2">
                    <RowStatusBadge status={row.status} />
                    {row.conflict_key && (
                      <span className="ml-2 text-xs text-amber-500">{row.conflict_key}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-red-400">
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
          className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-overlay"
        >
          ← Listeye dön
        </button>
        {job.status === "preview" && (
          <button
            onClick={handleCommit}
            disabled={committing || readyRows === 0}
            className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:opacity-40"
          >
            {committing ? "Commit ediliyor…" : `${readyRows} satırı Commit Et`}
          </button>
        )}
        {job.status === "committed" && (
          <span className="text-sm text-emerald-400">✓ Commit tamamlandı</span>
        )}
      </div>
    </section>
  );
}

// ── Encoding-aware file reader ────────────────────────────────────────────────

async function readFileWithEncoding(file: File): Promise<string> {
  try {
    const text = await file.text(); // UTF-8
    // UTF-8 decode hatası yoksa kullan
    if (!text.includes("�")) return text;
  } catch {}
  // ISO-8859-1 fallback
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string ?? "");
    reader.onerror = reject;
    reader.readAsText(file, "ISO-8859-1");
  });
}

// ── CSV parse helper ──────────────────────────────────────────────────────────

function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let cur = ""
  let inQ = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQ) {
      if (ch === '"' && line[i+1] === '"') { cur += '"'; i++ }
      else if (ch === '"') { inQ = false }
      else { cur += ch }
    } else {
      if (ch === '"') { inQ = true }
      else if (ch === ',') { result.push(cur); cur = "" }
      else { cur += ch }
    }
  }
  result.push(cur)
  return result.map(s => s.trim())
}

function parseCsvRows(text: string): Record<string, unknown>[] {
  const lines = text.trim().split("\n");
  if (lines.length === 0) {
    throw new Error("Dosya boş");
  }
  if (lines.length < 2) {
    throw new Error("Dosya yalnızca başlık satırı içeriyor — veri satırı bulunamadı");
  }
  const headers = parseCSVLine(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = parseCSVLine(line);
    const row: Record<string, unknown> = {};
    headers.forEach((h, i) => { row[h] = vals[i] ?? ""; });
    return row;
  });
}

function parseJsonRows(text: string): Record<string, unknown>[] {
  const parsed = JSON.parse(text) as unknown;
  if (Array.isArray(parsed)) {
    return parsed.filter((row): row is Record<string, unknown> => typeof row === "object" && row !== null);
  }
  if (typeof parsed === "object" && parsed !== null && Array.isArray((parsed as { rows?: unknown }).rows)) {
    return (parsed as { rows: unknown[] }).rows.filter(
      (row): row is Record<string, unknown> => typeof row === "object" && row !== null,
    );
  }
  return [];
}

async function parseWorkbookRows(file: File): Promise<Record<string, unknown>[]> {
  // xlsx dinamik import — dosya seçildiğinde indirilir, sayfa yükünü artırmaz
  const XLSX = await import("xlsx");
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheetName = workbook.SheetNames[0];
  if (!sheetName) return [];
  const worksheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, {
    defval: "",
    raw: false,
  });
}

function getHeaders(rows: Record<string, unknown>[]): string[] {
  const headers = new Set<string>();
  rows.slice(0, 20).forEach((row) => {
    Object.keys(row).forEach((key) => headers.add(key));
  });
  return Array.from(headers);
}

function guessColumn(header: string): ColumnKey {
  const normalized = header.toLowerCase().replace(/[\s_-]+/g, "");
  if (["casekey", "key", "id", "testcaseid"].includes(normalized)) return "case_key";
  if (["title", "name", "summary", "testcase", "testcasetitle"].includes(normalized)) return "title";
  if (["suite", "testsuite"].includes(normalized)) return "suite";
  if (["folder", "path"].includes(normalized)) return "folder";
  if (["priority", "prio"].includes(normalized)) return "priority";
  if (["severity", "risk"].includes(normalized)) return "severity";
  if (["type", "casetype"].includes(normalized)) return "type";
  if (["status", "state"].includes(normalized)) return "status";
  if (["owner", "assignee"].includes(normalized)) return "owner";
  if (["tag", "tags", "labels"].includes(normalized)) return "tags";
  if (["precondition", "preconditions"].includes(normalized)) return "preconditions";
  if (["steps", "action", "actions"].includes(normalized)) return "steps";
  if (["expected", "expectedresult", "expectedresults"].includes(normalized)) return "expected_result";
  if (["objective", "description"].includes(normalized)) return "objective";
  return "ignore";
}

function buildInitialMapping(headers: string[]): Record<string, ColumnKey> {
  return headers.reduce<Record<string, ColumnKey>>((acc, header) => {
    acc[header] = guessColumn(header);
    return acc;
  }, {});
}

function valueToString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function applyMapping(rows: Record<string, unknown>[], mapping: Record<string, ColumnKey>) {
  return rows.map((row) => {
    const mapped: Record<string, unknown> = {};
    Object.entries(mapping).forEach(([source, target]) => {
      if (target === "ignore") return;
      const value = row[source];
      if (value === undefined || value === "") return;
      if (target === "tags") {
        mapped[target] = valueToString(value)
          .split(/[;,]/)
          .map((tag) => tag.trim())
          .filter(Boolean);
      } else {
        mapped[target] = value;
      }
    });
    return mapped;
  });
}

function getDuplicateMappedTargets(mapping: Record<string, ColumnKey>): ColumnKey[] {
  const counts = new Map<ColumnKey, number>();
  Object.values(mapping).forEach((target) => {
    if (target === "ignore") return;
    counts.set(target, (counts.get(target) ?? 0) + 1);
  });
  return Array.from(counts.entries())
    .filter(([, count]) => count > 1)
    .map(([target]) => target);
}

function getUnmappedRequiredColumns(mapping: Record<string, ColumnKey>): ColumnKey[] {
  const mappedTargets = new Set(Object.values(mapping));
  return REQUIRED_COLUMNS.filter((field) => !mappedTargets.has(field));
}

function validateMappedRows(rows: Record<string, unknown>[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  rows.forEach((row, index) => {
    REQUIRED_COLUMNS.forEach((field) => {
      if (!valueToString(row[field]).trim()) {
        issues.push({
          rowNo: index + 2,
          field,
          message: `${field} zorunlu`,
        });
      }
    });
  });
  return issues;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function getRowStatus(
  row: Record<string, unknown>,
  rowNo: number,
  issuesByRow: Map<number, ValidationIssue[]>,
  duplicateCaseKeys: Set<string>,
): LocalPreviewStatus {
  if ((issuesByRow.get(rowNo) ?? []).length > 0) return "invalid";
  const caseKey = valueToString(row.case_key).trim();
  if (caseKey && duplicateCaseKeys.has(caseKey)) return "duplicate_candidate";
  return "ready";
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ManagementImportExportPage() {
  const projectId = useRouteParam("projectId");
  const mpid      = useManagementProjectId(projectId || undefined);
  const importsQuery = useManagementImports(mpid || undefined);
  const createJob    = useCreateManagementImportJob(mpid || "");

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<"csv" | "json">("csv");
  const [importError, setImportError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [stagedImport, setStagedImport] = useState<StagedImport | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, ColumnKey>>({});
  const [updateExisting, setUpdateExisting] = useState(true);
  const [conflictMode, setConflictMode] = useState<"skip" | "flag" | "overwrite">("flag");

  const jobs = importsQuery.data ?? [];
  const recentJobs = jobs.slice(0, 5);

  const pendingJobs   = jobs.filter((j) => j.status === "preview").length;
  const committedJobs = jobs.filter((j) => j.status === "committed").length;
  const failedJobs = jobs.filter((j) => j.status === "failed").length;
  const mappedRows = useMemo(
    () => (stagedImport ? applyMapping(stagedImport.rows, columnMapping) : []),
    [columnMapping, stagedImport],
  );
  const validationIssues = useMemo(() => validateMappedRows(mappedRows), [mappedRows]);
  const duplicateMappedTargets = useMemo(() => getDuplicateMappedTargets(columnMapping), [columnMapping]);
  const unmappedRequiredColumns = useMemo(() => getUnmappedRequiredColumns(columnMapping), [columnMapping]);
  const issuesByRow = useMemo(() => {
    const byRow = new Map<number, ValidationIssue[]>();
    validationIssues.forEach((issue) => {
      const current = byRow.get(issue.rowNo) ?? [];
      current.push(issue);
      byRow.set(issue.rowNo, current);
    });
    return byRow;
  }, [validationIssues]);
  const duplicateCaseKeys = useMemo(() => {
    const counts = new Map<string, number>();
    mappedRows.forEach((row) => {
      const caseKey = valueToString(row.case_key).trim();
      if (caseKey) counts.set(caseKey, (counts.get(caseKey) ?? 0) + 1);
    });
    return new Set(
      Array.from(counts.entries())
        .filter(([, count]) => count > 1)
        .map(([caseKey]) => caseKey),
    );
  }, [mappedRows]);
  const mappedColumnCount = Object.values(columnMapping).filter((target) => target !== "ignore").length;
  const hasBlockingValidation = unmappedRequiredColumns.length > 0 || duplicateMappedTargets.length > 0 || validationIssues.length > 0;
  const localStatusCounts = useMemo(() => {
    return mappedRows.reduce<Record<LocalPreviewStatus, number>>(
      (acc, row, index) => {
        const status = getRowStatus(row, index + 2, issuesByRow, duplicateCaseKeys);
        acc[status] += 1;
        return acc;
      },
      { ready: 0, invalid: 0, duplicate_candidate: 0 },
    );
  }, [duplicateCaseKeys, issuesByRow, mappedRows]);

  // ── File upload handler ──

  const MAX_FILE_SIZE_MB = 50;
  const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;

  function validateFile(file: File): string | null {
    const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
    if (ext === ".feature") {
      return "Gherkin .feature dosyaları henüz desteklenmiyor. Lütfen Excel veya CSV formatını kullanın.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return `Dosya boyutu çok büyük. Maksimum ${MAX_FILE_SIZE_MB}MB desteklenir.`;
    }
    const allowed = [".xlsx", ".xls", ".csv", ".json"];
    if (!allowed.includes(ext)) {
      return `Desteklenmeyen dosya tipi. Kabul edilen: ${allowed.join(", ")}`;
    }
    return null;
  }

  const handleFile = async (file: File) => {
    setFileError(null);
    const err = validateFile(file);
    if (err) {
      setFileError(err);
      return;
    }
    setUploading(true);
    try {
      let rows: Record<string, unknown>[] = [];
      if (file.name.endsWith(".csv")) {
        const text = await readFileWithEncoding(file);
        rows = parseCsvRows(text);
      } else if (file.name.endsWith(".xlsx") || file.name.endsWith(".xls")) {
        rows = await parseWorkbookRows(file);
      } else {
        const text = await file.text();
        try { rows = parseJsonRows(text); } catch { rows = []; }
      }
      const headers = getHeaders(rows);
      setStagedImport({ filename: file.name, fileSize: file.size, headers, rows });
      setColumnMapping(buildInitialMapping(headers));
    } catch (parseErr) {
      const message = parseErr instanceof Error ? parseErr.message : "Dosya okunamadı.";
      setFileError(message);
    } finally {
      setUploading(false);
    }
  };

  const handleCreateImportJob = async () => {
    if (!stagedImport) return;
    setImportError(null);
    try {
      await createJob.mutateAsync({
        filename: stagedImport.filename,
        rows: mappedRows,
        mapping: {
          columns: columnMapping,
          source_headers: stagedImport.headers,
          options: {
            update_existing: updateExisting,
            conflict_mode: conflictMode,
            dry_run_first: true,
          },
        },
      });
      setStagedImport(null);
      setColumnMapping({});
    } catch (err) {
      const message = err instanceof Error ? err.message : "Import job oluşturulamadı.";
      console.error("[import-export] createJob failed:", err);
      setImportError(message);
    }
  };

  const handleTemplateDownload = () => {
    const sample = [
      TEMPLATE_COLUMNS.join(","),
      [
        "CASE-001",
        "Login accepts valid credentials",
        "Authentication",
        "Web/Login",
        "P1",
        "critical",
        "regression",
        "active",
        "auth;smoke",
        "User exists",
        "Open login page;Enter credentials;Submit",
        "Dashboard is shown",
      ].join(","),
    ].join("\n");
    const blob = new Blob([sample], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "management-import-template.csv";
    link.click();
    URL.revokeObjectURL(url);
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

  const handleExport = async () => {
    if (!mpid) return;
    setExporting(true);
    setExportError(null);
    try {
      const data = await exportManagementRepository(mpid);

      if (exportFormat === "json") {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `management-repository-${mpid}.json`;
        link.click();
        URL.revokeObjectURL(url);
      } else {
        // csv — RFC4180 export from cases array
        const rawData = data as unknown as { cases?: Record<string, unknown>[] } | Record<string, unknown>[]
        const cases: Record<string, unknown>[] = Array.isArray((rawData as { cases?: unknown }).cases)
          ? (rawData as { cases: Record<string, unknown>[] }).cases
          : (Array.isArray(rawData) ? rawData : []);
        const headers = TEMPLATE_COLUMNS;
        const escape = (v: unknown): string => {
          const s = v === null || v === undefined ? "" : Array.isArray(v) ? (v as unknown[]).join(";") : String(v);
          return s.includes(",") || s.includes('"') || s.includes("\n")
            ? `"${s.replace(/"/g, '""')}"` : s;
        };
        const rows = [
          headers.join(","),
          ...cases.map(c => headers.map(h => escape(c[h])).join(",")),
        ].join("\r\n");
        const blob = new Blob(["﻿" + rows], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `management-repository-${mpid}.csv`;
        link.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Repository export başarısız.";
      console.error("[import-export] export failed:", err);
      setExportError(message);
    } finally {
      setExporting(false);
    }
  };

  if (!mpid) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  if (selectedJobId) {
    return (
    <div className="min-h-full bg-bg px-5 py-5 space-y-5">
        <ImportJobDetailPanel
          jobId={selectedJobId}
          projectId={mpid || ""}
          onClose={() => setSelectedJobId(null)}
        />
      </div>
    );
  }

  return (
    <div className="min-h-full bg-bg px-5 py-5 space-y-5">
      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-surface-raised px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-disabled">Import Jobs</p>
          <p className="mt-1.5 text-2xl font-bold text-fg tabular-nums">{String(jobs.length)}</p>
          <p className="mt-0.5 text-[11px] text-fg-disabled">{pendingJobs} preview bekliyor</p>
        </div>
        <div className="rounded-xl border border-border bg-surface-raised px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-disabled">Committed</p>
          <p className="mt-1.5 text-2xl font-bold text-fg tabular-nums">{String(committedJobs)}</p>
          <p className="mt-0.5 text-[11px] text-fg-disabled">repository'ye yazıldı</p>
        </div>
        <div className="rounded-xl border border-border bg-surface-raised px-4 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-disabled">Formats</p>
          <p className="mt-1.5 text-2xl font-bold text-fg tabular-nums">XLSX / CSV</p>
          <p className="mt-0.5 text-[11px] text-fg-disabled">{failedJobs} failed job</p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_0.8fr]">
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <p className="text-sm text-fg">Excel/CSV şablonu</p>
              <p className="mt-1 text-xs text-fg-subtle">
                Zorunlu alan: title. Opsiyonel alanlar case_key, suite, priority, steps ve expected_result.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {TEMPLATE_COLUMNS.slice(0, 8).map((column) => (
                  <span key={column} className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg-muted">
                    {column}
                  </span>
                ))}
              </div>
            </div>
            <button
              onClick={handleTemplateDownload}
              className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-fg hover:bg-surface-overlay"
            >
              Template CSV
            </button>
          </div>
        </section>

        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <div className="flex h-full flex-col justify-between gap-4">
            <p className="text-sm text-fg-muted">
              Repository snapshot seçilen formatta indirilir; import preview ve mapping ayarları backend job akışında kalır.
            </p>
            {exportError && (
              <p className="text-xs text-red-400">{exportError}</p>
            )}
            <div className="flex items-center gap-2 flex-wrap">
              {(["csv", "json"] as const).map(fmt => (
                <button
                  key={fmt}
                  type="button"
                  onClick={() => setExportFormat(fmt)}
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                    exportFormat === fmt
                      ? "border-teal-500/60 bg-teal-500/10 text-teal-300"
                      : "border-border text-fg-subtle hover:text-fg"
                  }`}
                >
                  {fmt.toUpperCase()}
                </button>
              ))}
              <button
                onClick={handleExport}
                disabled={exporting || !mpid}
                className="rounded-lg border border-teal-500/30 bg-teal-500/10 px-4 py-1.5 text-sm font-semibold text-teal-200 hover:bg-brand-soft disabled:opacity-40 transition-colors"
              >
                {exporting ? "İndiriliyor…" : "Dışa Aktar"}
              </button>
            </div>
          </div>
        </section>
      </div>

      {/* Upload zone */}
      <div className="mt-6 grid gap-4 xl:grid-cols-[0.95fr_1.45fr]">
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 transition ${
              dragOver
                ? "border-teal-400 bg-teal-500/5"
                : "border-border hover:border-border-strong"
            }`}
          >
            <svg className="mb-3 h-8 w-8 text-fg-subtle" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="mb-1 text-sm text-fg">Excel, CSV veya JSON dosyası sürükleyin</p>
            <p className="text-xs text-fg-subtle mb-3">veya</p>
            <label className="cursor-pointer rounded-lg bg-surface-overlay px-4 py-2 text-sm text-fg hover:bg-surface-overlay">
              {uploading ? "Yükleniyor…" : "Dosya Seç"}
              <input
                type="file"
                accept=".xlsx,.xls,.csv,.json"
                className="hidden"
                onChange={handleInputChange}
                disabled={uploading}
              />
            </label>
            <p className="mt-3 text-xs text-fg-disabled">
              Dosya önce staging alanına alınır; mapping ve dry-run kontrolünden sonra import job oluşturulur.
            </p>
          </div>
          {fileError && (
            <div className="mt-3 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-300">
              {fileError}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-border bg-surface-raised p-5">
          {!stagedImport ? (
            <div className="flex min-h-56 items-center justify-center rounded-lg border border-border bg-bg px-6 text-center">
              <div>
                <p className="text-sm font-medium text-fg">Henüz staged dosya yok</p>
                <p className="mt-2 max-w-md text-xs text-fg-subtle">
                  Excel, CSV veya JSON yüklediğinizde kolonlar burada mapping tablosuna dönüşür.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-bg px-3 py-2">
                <div>
                  <p className="text-sm font-medium text-white">{stagedImport.filename}</p>
                  <p className="text-xs text-fg-subtle">
                    {stagedImport.rows.length} rows, {stagedImport.headers.length} source columns, {formatFileSize(stagedImport.fileSize)}
                  </p>
                </div>
                <button
                  onClick={() => { setStagedImport(null); setColumnMapping({}); }}
                  className="rounded border border-border px-3 py-1.5 text-xs text-fg-muted hover:bg-surface-overlay"
                >
                  Temizle
                </button>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border border-border bg-bg p-3">
                  <p className="text-xs uppercase text-fg-subtle">Mapped</p>
                  <p className="mt-1 text-lg font-semibold text-white">{mappedColumnCount}</p>
                </div>
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <p className="text-xs uppercase text-emerald-300/70">Ready rows</p>
                  <p className="mt-1 text-lg font-semibold text-emerald-300">{localStatusCounts.ready}</p>
                </div>
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                  <p className="text-xs uppercase text-red-300/70">Issues</p>
                  <p className="mt-1 text-lg font-semibold text-red-300">{validationIssues.length}</p>
                </div>
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                  <p className="text-xs uppercase text-amber-300/70">Duplicate keys</p>
                  <p className="mt-1 text-lg font-semibold text-amber-300">{localStatusCounts.duplicate_candidate}</p>
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead className="bg-bg text-xs text-fg-subtle">
                    <tr>
                      <th className="px-3 py-2 text-left">Source column</th>
                      <th className="px-3 py-2 text-left">Maps to</th>
                      <th className="px-3 py-2 text-left">Sample</th>
                      <th className="px-3 py-2 text-left">Check</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {stagedImport.headers.map((header) => {
                      const target = columnMapping[header] ?? "ignore";
                      const isDuplicateTarget = duplicateMappedTargets.includes(target);
                      return (
                        <tr key={header}>
                          <td className="px-3 py-2 font-mono text-xs text-fg">{header}</td>
                          <td className="px-3 py-2">
                            <select
                              value={target}
                              onChange={(e) =>
                                setColumnMapping((current) => ({
                                  ...current,
                                  [header]: e.target.value as ColumnKey,
                                }))
                              }
                              className={`w-44 rounded border bg-bg px-2 py-1.5 text-xs text-fg outline-none focus:border-teal-400 ${
                                isDuplicateTarget ? "border-amber-500/60" : "border-border"
                              }`}
                            >
                              {COLUMN_OPTIONS.map((option) => (
                                <option key={option.key} value={option.key}>
                                  {option.label}{option.required ? " *" : ""}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="max-w-xs truncate px-3 py-2 text-xs text-fg-subtle">
                            {valueToString(stagedImport.rows[0]?.[header]) || "—"}
                          </td>
                          <td className="px-3 py-2 text-xs">
                            {isDuplicateTarget ? (
                              <span className="text-amber-300">Duplicate target</span>
                            ) : target === "ignore" ? (
                              <span className="text-fg-disabled">Ignored</span>
                            ) : (
                              <span className="text-emerald-400">Mapped</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <label className="flex items-start gap-3 rounded-lg border border-border bg-bg p-3">
                  <input
                    type="checkbox"
                    checked={updateExisting}
                    onChange={(e) => setUpdateExisting(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-border-strong bg-surface-raised"
                  />
                  <span>
                    <span className="block text-sm text-fg">Update existing</span>
                    <span className="text-xs text-fg-subtle">case_key eşleşirse güncelleme niyeti mapping payloadına eklenir.</span>
                  </span>
                </label>

                <label className="rounded-lg border border-border bg-bg p-3">
                  <span className="block text-sm text-fg">Conflict handling</span>
                  <select
                    value={conflictMode}
                    onChange={(e) => setConflictMode(e.target.value as "skip" | "flag" | "overwrite")}
                    className="mt-2 w-full rounded border border-border bg-surface-raised px-2 py-1.5 text-xs text-fg outline-none focus:border-teal-400"
                  >
                    <option value="flag">Flag for review</option>
                    <option value="skip">Skip conflicts</option>
                    <option value="overwrite">Overwrite mapped fields</option>
                  </select>
                </label>

                <div className="rounded-lg border border-border bg-bg p-3">
                  <span className="block text-sm text-fg">Validation</span>
                  <span className={hasBlockingValidation ? "mt-2 block text-xs text-red-400" : "mt-2 block text-xs text-emerald-400"}>
                    {hasBlockingValidation ? "Mapping veya satır kontrolü gerekiyor" : "Dry-run için hazır"}
                  </span>
                </div>
              </div>

              {(unmappedRequiredColumns.length > 0 || duplicateMappedTargets.length > 0) && (
                <div className="grid gap-3 md:grid-cols-2">
                  {unmappedRequiredColumns.length > 0 && (
                    <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                      <p className="text-xs font-semibold uppercase text-red-300">Required mapping missing</p>
                      <p className="mt-2 text-xs text-red-200">
                        {unmappedRequiredColumns.join(", ")} alanı import job için eşlenmeli.
                      </p>
                    </div>
                  )}
                  {duplicateMappedTargets.length > 0 && (
                    <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                      <p className="text-xs font-semibold uppercase text-amber-300">Duplicate target mapping</p>
                      <p className="mt-2 text-xs text-amber-100">
                        {duplicateMappedTargets.join(", ")} hedeflerine birden fazla kaynak kolon gidiyor.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {validationIssues.length > 0 && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                  <p className="text-xs font-semibold uppercase text-red-300">Dry-run validation summary</p>
                  <ul className="mt-2 space-y-1 text-xs text-red-200">
                    {validationIssues.slice(0, 4).map((issue) => (
                      <li key={`${issue.rowNo}-${issue.field}`}>Row {issue.rowNo}: {issue.message}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="overflow-x-auto rounded-lg border border-border">
                <table className="w-full text-xs">
                  <thead className="bg-bg text-fg-subtle">
                    <tr>
                      <th className="px-3 py-2 text-left">#</th>
                      <th className="px-3 py-2 text-left">Preview</th>
                      <th className="px-3 py-2 text-left">Title</th>
                      <th className="px-3 py-2 text-left">Priority</th>
                      <th className="px-3 py-2 text-left">Type</th>
                      <th className="px-3 py-2 text-left">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {mappedRows.slice(0, 5).map((row, index) => {
                      const rowNo = index + 2;
                      const rowStatus = getRowStatus(row, rowNo, issuesByRow, duplicateCaseKeys);
                      return (
                        <tr key={`${stagedImport.filename}-${index}`}>
                          <td className="px-3 py-2 text-fg-subtle">{index + 1}</td>
                          <td className="px-3 py-2">
                            <RowStatusBadge status={rowStatus} />
                            {(issuesByRow.get(rowNo) ?? []).length > 0 && (
                              <span className="ml-2 text-red-300">
                                {(issuesByRow.get(rowNo) ?? []).map((issue) => issue.message).join(", ")}
                              </span>
                            )}
                          </td>
                          <td className="max-w-xs truncate px-3 py-2 text-fg">{valueToString(row.title) || "—"}</td>
                          <td className="px-3 py-2 text-fg-muted">{valueToString(row.priority) || "—"}</td>
                          <td className="px-3 py-2 text-fg-muted">{valueToString(row.type) || "—"}</td>
                          <td className="px-3 py-2 text-fg-muted">{valueToString(row.status) || "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {importError && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs text-red-300">
                  {importError}
                </div>
              )}

              <div className="flex flex-wrap items-center justify-end gap-3">
                <button
                  onClick={handleCreateImportJob}
                  disabled={createJob.isPending || hasBlockingValidation || mappedRows.length === 0}
                  className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:opacity-40"
                >
                  {createJob.isPending ? "Job oluşturuluyor…" : "Import Job Oluştur"}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Job list */}
      <div className="mt-6">
        <section className="rounded-xl border border-border bg-surface-raised p-5">
          {recentJobs.length > 0 && (
            <div className="mb-4 grid gap-2 md:grid-cols-5">
              {recentJobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  className="rounded-lg border border-border bg-bg p-3 text-left transition hover:border-border hover:bg-surface-raised"
                >
                  <span className="block truncate text-xs font-medium text-fg">{job.filename}</span>
                  <span className="mt-2 flex items-center justify-between gap-2">
                    <JobStatusBadge status={job.status} />
                    <span className="text-xs text-fg-subtle">
                      {(job.totals as { rows?: number }).rows ?? "—"} rows
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
          {importsQuery.isLoading ? (
            <div className="space-y-2 py-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 rounded-lg border border-border bg-bg px-3 py-2.5"
                  style={{ opacity: Math.max(0.3, 1 - i * 0.25) }}>
                  <div className="h-3 w-32 animate-pulse rounded bg-surface-overlay"/>
                  <div className="h-5 w-16 animate-pulse rounded-full bg-surface-overlay"/>
                  <div className="ml-auto h-3 w-12 animate-pulse rounded bg-surface-overlay"/>
                </div>
              ))}
            </div>
          ) : importsQuery.isError ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-xs text-red-400">Import job&apos;ları yüklenemedi.</p>
              <button
                onClick={() => void importsQuery.refetch()}
                className="text-xs text-teal-400 hover:underline"
              >
                Tekrar dene
              </button>
            </div>
          ) : jobs.length === 0 ? (
            <p className="py-4 text-center text-sm text-fg-subtle">Henüz import job yok.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-border text-xs text-fg-subtle">
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
                    <tr key={job.id} className="hover:bg-surface-raised">
                      <td className="py-2.5 pr-4 text-fg">{job.filename}</td>
                      <td className="py-2.5 pr-4">
                        <JobStatusBadge status={job.status} />
                      </td>
                      <td className="py-2.5 pr-4 text-fg-muted">
                        {(job.totals as { rows?: number }).rows ?? "—"}
                      </td>
                      <td className="py-2.5 pr-4 text-xs text-fg-subtle">
                        {new Date(job.created_at).toLocaleDateString("tr-TR")}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => setSelectedJobId(job.id)}
                          className="rounded px-3 py-1 text-xs text-teal-400 hover:bg-surface-overlay"
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
        </section>
      </div>
    </div>
  );
}
