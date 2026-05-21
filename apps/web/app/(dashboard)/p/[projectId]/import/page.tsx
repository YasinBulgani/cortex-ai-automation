"use client";

import { useState, useCallback } from "react";

import { useRouteParam } from "@/lib/use-route-param";
import { apiFetch } from "@/lib/api";
import { FileDropZone } from "@/components/dnd/FileDropZone";
import { FlowGuideCard } from "@/components/FlowGuideCard";
import {
  PageHeader,
  SectionCard,
  StatCard,
  MetricRow,
} from "@/components/nexus";

type ImportRow = {
  id: string;
  filename: string;
  status: string;
  log: string;
};

const STATUS_STYLES: Record<string, { color: string; dot: string; label: string }> = {
  pending:    { color: "bg-amber-500/10 border-amber-500/20 text-amber-400",   dot: "bg-amber-400",   label: "Bekliyor" },
  processing: { color: "bg-blue-500/10 border-blue-500/20 text-blue-400",     dot: "bg-blue-400 animate-pulse", label: "İşleniyor" },
  completed:  { color: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", dot: "bg-emerald-400", label: "Tamamlandı" },
  failed:     { color: "bg-red-500/10 border-red-500/20 text-red-400",        dot: "bg-red-400",     label: "Başarısız" },
};

export default function ImportPage() {
  const projectId = useRouteParam("projectId");
  const [uploads, setUploads] = useState<ImportRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleFiles = useCallback(async (files: File[]) => {
    setErr(null);
    setUploading(true);
    try {
      const results: ImportRow[] = [];
      for (const file of files) {
        const row = await apiFetch<ImportRow>(`/api/v1/tspm/projects/${projectId}/imports`, {
          method: "POST",
          json: { source_type: "file", filename: file.name, storage_key: "" },
        });
        results.push(row);
      }
      setUploads(prev => [...results, ...prev]);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Yükleme hatası");
    } finally { setUploading(false); }
  }, [projectId]);

  return (
    <div className="min-h-screen bg-slate-950 p-6 flex flex-col gap-4" data-testid="import-page">
      <PageHeader
        icon={
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
        }
        title="İçe Aktarma"
        description="Dosyaları sürükleyip bırakarak veya tıklayarak yükleyin"
      />
      <FlowGuideCard projectId={projectId} stage="discover" />

      {/* Stats */}
      <MetricRow cols={3}>
        <StatCard label="Toplam Yükleme" value={uploads.length} color="slate" />
        <StatCard label="Tamamlanan" value={uploads.filter(u => u.status === "completed").length} color="emerald" />
        <StatCard
          label="Başarısız"
          value={uploads.filter(u => u.status === "failed").length}
          color={uploads.filter(u => u.status === "failed").length > 0 ? "red" : "slate"}
        />
      </MetricRow>

      {/* Drop zone */}
      <div data-testid="import-form" className="rounded-xl border border-slate-700 bg-slate-900/40 overflow-hidden">
        <div data-testid="file-upload">
          <FileDropZone
            onFiles={handleFiles}
            accept=".pdf,.xlsx,.xls,.csv,.json,.xml,.txt,.doc,.docx"
            maxSizeMB={50}
          >
            {uploading ? (
              <div data-testid="upload-status" className="flex flex-col items-center gap-3 py-4">
                <div data-testid="upload-progress" className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-400 rounded-full animate-spin" />
                <p className="text-sm font-medium text-white">Yükleniyor…</p>
              </div>
            ) : undefined}
          </FileDropZone>
        </div>
      </div>

      {err && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="import-alert-error">
          {err}
        </div>
      )}

      {/* Uploaded files */}
      <div data-testid="import-history">
      {uploads.length > 0 && (
        <SectionCard
          title="Yüklenen Dosyalar"
          icon={<svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8" /></svg>}
          right={<span className="text-xs text-slate-500">{uploads.length} dosya</span>}
          noPad
        >
          {uploads.map(row => {
            const sc = STATUS_STYLES[row.status] ?? STATUS_STYLES.pending;
            return (
              <div key={row.id} data-testid="import-history-item" className="flex items-center justify-between px-4 py-3 border-b border-slate-800 last:border-0 hover:bg-slate-800/30">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                    <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{row.filename}</p>
                    <p className="text-xs text-slate-500 font-mono">{row.id.slice(0, 8)}…</p>
                  </div>
                </div>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${sc.color}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
                  {sc.label}
                </span>
              </div>
            );
          })}
        </SectionCard>
      )}
      </div>

      {/* Supported formats */}
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 px-4 py-3">
        <p className="text-xs font-medium text-slate-300 mb-1">Desteklenen Formatlar</p>
        <div className="flex flex-wrap gap-1.5">
          {["PDF", "Excel (.xlsx/.xls)", "CSV", "JSON", "XML", "TXT", "Word (.doc/.docx)"].map(f => (
            <span key={f} className="px-2 py-0.5 rounded border border-slate-700 bg-slate-800 text-xs text-slate-400">{f}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
