"use client";

/**
 * Neurex QA — Doküman Yükleyici Bileşeni
 * PDF, DOCX, TXT, MD destekler.
 * Sürükle-bırak + dosya seçici, yükleme progress göstergesi.
 */

import { useCallback, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";

export interface UploadedDocument {
  full_text: string;
  filename: string;
  format: string;
  page_count: number;
  word_count: number;
  char_count: number;
  chunk_count: number;
  needs_chunking: boolean;
  sections: string[];
  preview: string;
  message: string;
}

interface DocumentUploaderProps {
  projectId: string;
  onUploaded: (doc: UploadedDocument) => void;
  onError?: (msg: string) => void;
}

const ACCEPTED_TYPES = [".pdf", ".docx", ".txt", ".md"];
const FORMAT_ICONS: Record<string, string> = {
  pdf: "📄",
  docx: "📝",
  txt: "📃",
  md: "📋",
};
const FORMAT_COLORS: Record<string, string> = {
  pdf: "text-red-400",
  docx: "text-blue-400",
  txt: "text-slate-400",
  md: "text-purple-400",
};

export function DocumentUploader({ projectId, onUploaded, onError }: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadedDoc, setUploadedDoc] = useState<UploadedDocument | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (!ACCEPTED_TYPES.includes(`.${ext}`)) {
      onError?.(`Desteklenmeyen format: .${ext}. Kabul edilenler: PDF, DOCX, TXT, MD`);
      return;
    }

    const MAX_MB = 20;
    if (file.size > MAX_MB * 1024 * 1024) {
      onError?.(`Dosya çok büyük (${(file.size / 1024 / 1024).toFixed(1)}MB). Maksimum: ${MAX_MB}MB`);
      return;
    }

    setIsUploading(true);
    setProgress(10);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Sahte progress animasyonu
      const progressInterval = setInterval(() => {
        setProgress((p) => Math.min(p + 12, 85));
      }, 300);

      const token = typeof window !== "undefined" ? localStorage.getItem("tspm_access_token") : null;
      const res = await fetch(
        `/api/v1/tspm/projects/${projectId}/wizard/upload-document`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );

      clearInterval(progressInterval);
      setProgress(100);

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Yükleme hatası: ${res.status}`);
      }

      const doc: UploadedDocument = await res.json();
      setUploadedDoc(doc);
      onUploaded(doc);
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "Yükleme başarısız");
    } finally {
      setIsUploading(false);
      setTimeout(() => setProgress(0), 500);
    }
  }, [projectId, onUploaded, onError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  const reset = () => {
    setUploadedDoc(null);
    setProgress(0);
  };

  // ── Yükleme Tamamlandı Görünümü ──────────────────────────────────────────
  if (uploadedDoc) {
    const icon = FORMAT_ICONS[uploadedDoc.format] || "📄";
    const color = FORMAT_COLORS[uploadedDoc.format] || "text-slate-400";

    return (
      <div className="rounded-xl border border-emerald-700/50 bg-emerald-950/30 p-5">
        {/* Başarı satırı */}
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 text-xl">
              {icon}
            </div>
            <div>
              <p className={`text-sm font-semibold ${color}`}>{uploadedDoc.filename}</p>
              <p className="text-xs text-slate-500">{uploadedDoc.message}</p>
            </div>
          </div>
          <button
            onClick={reset}
            className="text-xs text-slate-500 hover:text-slate-300 transition"
          >
            Değiştir
          </button>
        </div>

        {/* İstatistikler */}
        <div className="grid grid-cols-4 gap-2 mb-4">
          {[
            { label: "Sayfa", value: uploadedDoc.page_count },
            { label: "Kelime", value: uploadedDoc.word_count.toLocaleString() },
            { label: "Chunk", value: uploadedDoc.chunk_count },
            { label: "Başlık", value: uploadedDoc.sections.length },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-lg bg-slate-900/60 p-2.5 text-center">
              <p className="text-base font-bold text-white">{value}</p>
              <p className="text-[10px] text-slate-500">{label}</p>
            </div>
          ))}
        </div>

        {/* Başlıklar */}
        {uploadedDoc.sections.length > 0 && (
          <div className="mb-4">
            <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Tespit Edilen Bölümler
            </p>
            <div className="flex flex-wrap gap-1.5">
              {uploadedDoc.sections.slice(0, 8).map((sec, i) => (
                <span key={i} className="rounded-md bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300">
                  {sec.length > 35 ? sec.slice(0, 35) + "…" : sec}
                </span>
              ))}
              {uploadedDoc.sections.length > 8 && (
                <span className="rounded-md bg-slate-800/50 px-2 py-0.5 text-[11px] text-slate-500">
                  +{uploadedDoc.sections.length - 8} daha
                </span>
              )}
            </div>
          </div>
        )}

        {/* Önizleme */}
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Önizleme
          </p>
          <p className="rounded-lg bg-slate-900/60 p-3 text-xs text-slate-400 leading-relaxed font-mono line-clamp-4">
            {uploadedDoc.preview}
          </p>
        </div>

        {/* Chunk uyarısı */}
        {uploadedDoc.needs_chunking && (
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-yellow-700/30 bg-yellow-950/20 px-3 py-2">
            <span className="text-yellow-400">⚡</span>
            <p className="text-xs text-yellow-400">
              Büyük doküman — {uploadedDoc.chunk_count} chunk'a bölündü. AI analizi parça parça çalışacak.
            </p>
          </div>
        )}
      </div>
    );
  }

  // ── Yükleme Alanı ─────────────────────────────────────────────────────────
  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        className={`
          relative flex cursor-pointer flex-col items-center justify-center
          rounded-xl border-2 border-dashed p-10 text-center
          transition-all duration-200
          ${isDragging
            ? "border-blue-500 bg-blue-600/10"
            : "border-slate-700 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-900/60"
          }
          ${isUploading ? "pointer-events-none opacity-80" : ""}
        `}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-4">
            {/* Progress ring */}
            <div className="relative h-14 w-14">
              <svg className="h-14 w-14 -rotate-90" viewBox="0 0 56 56">
                <circle cx="28" cy="28" r="24" fill="none" stroke="#1e293b" strokeWidth="4" />
                <circle
                  cx="28" cy="28" r="24" fill="none"
                  stroke="#3b82f6" strokeWidth="4"
                  strokeDasharray={`${2 * Math.PI * 24}`}
                  strokeDashoffset={`${2 * Math.PI * 24 * (1 - progress / 100)}`}
                  strokeLinecap="round"
                  className="transition-all duration-300"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-blue-400">
                {progress}%
              </span>
            </div>
            <p className="text-sm text-slate-400">Doküman işleniyor...</p>
          </div>
        ) : (
          <>
            {/* Yükleme ikonu */}
            <div className={`
              mb-4 flex h-14 w-14 items-center justify-center rounded-2xl
              transition-colors duration-200
              ${isDragging ? "bg-blue-600/30" : "bg-slate-800"}
            `}>
              <svg
                className={`h-7 w-7 transition-colors ${isDragging ? "text-blue-400" : "text-slate-500"}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>

            <p className="mb-1 text-sm font-medium text-slate-300">
              {isDragging ? "Bırakın!" : "Dosyayı sürükleyin veya tıklayın"}
            </p>
            <p className="text-xs text-slate-500">
              PDF, DOCX, TXT, MD — Maksimum 20MB
            </p>

            {/* Format rozetleri */}
            <div className="mt-4 flex gap-2">
              {["PDF", "DOCX", "TXT", "MD"].map((fmt) => (
                <span key={fmt} className="rounded-md bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-400">
                  {fmt}
                </span>
              ))}
            </div>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.docx,.txt,.md"
        onChange={handleInputChange}
      />
    </div>
  );
}
