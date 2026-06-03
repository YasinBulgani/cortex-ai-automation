"use client";

import { useEffect, useRef, useState } from "react";

interface EvidenceModalProps {
  projectId: string;
  runId: string;
  runCaseId: string;
  caseKey?: string;
  caseTitle?: string;
  /** Modal kapatıldığında çağrılır — evidence yüklendi mi bilgisini iletir */
  onClose: (uploaded: boolean) => void;
}

type FileEntry = { name: string; size: number; preview?: string };

export function EvidenceModal({
  projectId,
  runId,
  runCaseId,
  caseKey,
  caseTitle,
  onClose,
}: EvidenceModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<FileEntry[]>([]);
  const [note, setNote] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Ekrana yapıştırılan screenshot'ı yakala (Ctrl+V)
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = Array.from(e.clipboardData?.items ?? []);
      const imageItem = items.find((i) => i.type.startsWith("image/"));
      if (!imageItem) return;
      const file = imageItem.getAsFile();
      if (!file) return;
      const named = new File([file], `screenshot-${Date.now()}.png`, { type: file.type });
      addFiles([named]);
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, []);

  const addFiles = (incoming: File[]) => {
    setFiles((prev) => [...prev, ...incoming]);
    incoming.forEach((f) => {
      if (f.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (ev) =>
          setPreviews((prev) => [
            ...prev,
            { name: f.name, size: f.size, preview: ev.target?.result as string },
          ]);
        reader.readAsDataURL(f);
      } else {
        setPreviews((prev) => [...prev, { name: f.name, size: f.size }]);
      }
    });
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(e.target.files ?? []));
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(Array.from(e.dataTransfer.files));
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const canSubmit = files.length > 0 || note.trim().length > 0;

  const handleUpload = async () => {
    setError("");
    if (!canSubmit) {
      setError("En az bir dosya yükleyin veya not ekleyin.");
      return;
    }
    setUploading(true);
    let count = 0;
    try {
      // Dosyaları yükle
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(
          `/api/v1/test-management/projects/${projectId}/runs/${runId}/cases/${runCaseId}/evidence`,
          { method: "POST", body: form, credentials: "include" },
        );
        if (res.ok) count++;
      }
      // Sadece not varsa onu text dosyası olarak yükle
      if (note.trim() && files.length === 0) {
        const blob = new Blob([note.trim()], { type: "text/plain" });
        const noteFile = new File([blob], `note-${Date.now()}.txt`, { type: "text/plain" });
        const form = new FormData();
        form.append("file", noteFile);
        const res = await fetch(
          `/api/v1/test-management/projects/${projectId}/runs/${runId}/cases/${runCaseId}/evidence`,
          { method: "POST", body: form, credentials: "include" },
        );
        if (res.ok) count++;
      }
      setUploadedCount(count);
      setTimeout(() => onClose(count > 0), 800);
    } catch {
      setError("Yükleme başarısız. Tekrar deneyin.");
    } finally {
      setUploading(false);
    }
  };

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => e.target === e.currentTarget && onClose(false)}
    >
      <div className="w-full max-w-lg rounded-xl border border-red-500/30 bg-surface-raised shadow-2xl overflow-hidden">
        {/* Başlık */}
        <div className="bg-red-500/10 border-b border-red-500/20 px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-red-400">🚨 FAIL — Evidence Gerekli</p>
              <p className="text-xs text-slate-400 mt-0.5">
                {caseKey && <span className="font-mono mr-2 text-slate-500">{caseKey}</span>}
                {caseTitle}
              </p>
            </div>
            <button
              onClick={() => onClose(false)}
              className="text-slate-500 hover:text-white text-lg leading-none mt-0.5"
            >
              ✕
            </button>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Screenshot, log dosyası veya not ekleyerek FAIL kaydını tamamlayın.
          </p>
        </div>

        <div className="p-5 space-y-4">
          {/* Drag-drop alanı */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors
              ${dragOver
                ? "border-red-400 bg-red-500/10"
                : "border-border bg-surface-overlay hover:border-slate-500 hover:bg-surface-overlay"}
            `}
          >
            <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileInput} />
            <p className="text-2xl mb-2">📎</p>
            <p className="text-sm text-slate-300 font-medium">Dosya sürükle veya tıkla</p>
            <p className="text-xs text-slate-500 mt-1">
              Screenshot yapıştır: <kbd className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px]">Ctrl+V</kbd>
            </p>
          </div>

          {/* Önizlemeler */}
          {previews.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {previews.map((p, i) => (
                <div key={i} className="relative rounded-lg border border-border bg-surface-overlay overflow-hidden">
                  {p.preview ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.preview} alt={p.name} className="w-full h-24 object-cover" />
                  ) : (
                    <div className="h-24 flex items-center justify-center text-slate-400 text-xs p-2 text-center">
                      📄 {p.name}
                    </div>
                  )}
                  <div className="px-2 py-1 flex justify-between items-center">
                    <span className="text-[10px] text-slate-400 truncate">{p.name}</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); removeFile(i); }}
                      className="text-slate-500 hover:text-red-400 text-xs ml-1 shrink-0"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Not alanı */}
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Gözlem Notu (opsiyonel)</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Hatanın nasıl oluştuğunu kısaca açıkla…"
              rows={3}
              className="w-full rounded-lg bg-surface-overlay border border-border px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-red-500/50 resize-none"
            />
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}
          {uploadedCount > 0 && (
            <p className="text-xs text-emerald-400">✅ {uploadedCount} dosya yüklendi — kaydediliyor…</p>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-5 py-3 flex justify-between items-center gap-3">
          <button
            onClick={() => onClose(false)}
            className="text-xs text-slate-400 hover:text-white transition-colors"
          >
            Şimdi değil
          </button>
          <button
            onClick={handleUpload}
            disabled={uploading || !canSubmit}
            className={`
              flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors
              ${canSubmit && !uploading
                ? "bg-red-500 hover:bg-red-600 text-white"
                : "bg-slate-700 text-slate-500 cursor-not-allowed"}
            `}
          >
            {uploading && (
              <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            )}
            {uploading ? "Yükleniyor…" : "Evidence Ekle ve Kaydet"}
          </button>
        </div>
      </div>
    </div>
  );
}
